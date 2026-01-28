"""
Sync endpoints - fetch data from blockchain RPC and store in database.

Called by frontend after user creates/updates a campaign or donates.
Replaces the 24/7 indexer - now we fetch on-demand when user acts.

Endpoints:
    POST /api/v1/campaigns/{campaign_id}/sync - Sync single campaign
    POST /api/v1/campaigns/{campaign_id}/donations/sync - Sync donations for a campaign
"""
import base64
import json
import logging
from datetime import datetime, timezone

import requests
from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Account
from campaigns.models import Campaign, CampaignDonation
from tokens.models import Token

logger = logging.getLogger(__name__)

CAMPAIGNS_CONTRACT = (
    f"v1.campaign.{settings.POTLOCK_TLA}"
    if settings.ENVIRONMENT == "testnet"
    else f"v1.campaigns.{settings.POTLOCK_TLA}"
)


def fetch_from_rpc(method_name: str, args: dict = None, contract_id: str = None):
    """Fetch data from blockchain via Web4 RPC with JSON-RPC fallback."""
    account_id = contract_id or CAMPAIGNS_CONTRACT
    web4_url = f"{settings.FASTNEAR_RPC_URL}/account/{account_id}/view/{method_name}"

    try:
        response = requests.post(web4_url, json=args or {}, timeout=15)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.warning(f"web4 RPC failed, trying standard JSON-RPC: {e}")

    # Fallback to standard JSON-RPC if Web4 fails
    rpc_url = (
        "https://test.rpc.fastnear.com"
        if settings.ENVIRONMENT == "testnet"
        else "https://free.rpc.fastnear.com"
    )

    args_base64 = base64.b64encode(json.dumps(args or {}).encode()).decode()
    payload = {
        "jsonrpc": "2.0",
        "id": "dontcare",
        "method": "query",
        "params": {
            "request_type": "call_function",
            "account_id": account_id,
            "method_name": method_name,
            "args_base64": args_base64,
            "finality": "optimistic",
        },
    }

    response = requests.post(rpc_url, json=payload, timeout=15)
    result = response.json()

    if "error" in result:
        raise Exception(f"RPC error: {result['error']}")

    result_bytes = bytes(result["result"]["result"])
    return json.loads(result_bytes.decode())


class CampaignSyncAPI(APIView):
    """
    Sync a campaign from blockchain to database.

    Called by frontend after user creates or updates a campaign.
    Fetches current state from RPC via get_campaign, creates/updates in DB.
    """

    @extend_schema(
        summary="Sync campaign from blockchain",
        responses={
            200: OpenApiResponse(description="Campaign synced"),
            404: OpenApiResponse(description="Campaign not found on chain"),
            502: OpenApiResponse(description="RPC failed"),
        },
    )
    def post(self, request, campaign_id: int):
        try:
            data = fetch_from_rpc("get_campaign", {"campaign_id": int(campaign_id)})

            if not data:
                return Response({"error": "Campaign not found on chain"}, status=404)

            # Upsert accounts
            owner, _ = Account.objects.get_or_create(defaults={"chain_id": 1}, id=data["owner"])
            recipient, _ = Account.objects.get_or_create(defaults={"chain_id": 1}, id=data["recipient"])

            # Get token (Account must exist first since Token PK is a OneToOneField)
            token_id = data.get("ft_id") or "near"
            token_acct, _ = Account.objects.get_or_create(defaults={"chain_id": 1}, id=token_id)
            token, _ = Token.objects.get_or_create(account=token_acct, defaults={"decimals": 24})

            # Timestamps
            start_at = datetime.fromtimestamp(data["start_ms"] / 1000, tz=timezone.utc)
            end_at = (
                datetime.fromtimestamp(data["end_ms"] / 1000, tz=timezone.utc)
                if data.get("end_ms")
                else None
            )

            campaign_defaults = {
                "owner": owner,
                "name": data["name"],
                "description": data.get("description"),
                "cover_image_url": data.get("cover_image_url"),
                "recipient": recipient,
                "token": token,
                "start_at": start_at,
                "end_at": end_at,
                "created_at": datetime.fromtimestamp(data["created_ms"] / 1000, tz=timezone.utc)
                if data.get("created_ms")
                else datetime.now(tz=timezone.utc),
                "target_amount": str(data["target_amount"]),
                "min_amount": str(data["min_amount"]) if data.get("min_amount") else None,
                "max_amount": str(data["max_amount"]) if data.get("max_amount") else None,
                "total_raised_amount": str(data.get("total_raised_amount", "0")),
                "net_raised_amount": str(data.get("net_raised_amount", "0")),
                "escrow_balance": str(data.get("escrow_balance", "0")),
                "referral_fee_basis_points": data["referral_fee_basis_points"],
                "creator_fee_basis_points": data["creator_fee_basis_points"],
                "allow_fee_avoidance": data.get("allow_fee_avoidance", False),
            }

            campaign, created = Campaign.objects.update_or_create(
                on_chain_id=int(campaign_id),
                defaults=campaign_defaults,
            )

            # Fetch USD prices (matches indexer behavior)
            try:
                campaign.fetch_usd_prices()
            except Exception as e:
                logger.warning(f"Failed to fetch USD prices for campaign {campaign_id}: {e}")

            return Response(
                {
                    "success": True,
                    "message": "Campaign created" if created else "Campaign updated",
                    "on_chain_id": campaign.on_chain_id,
                }
            )

        except Exception as e:
            logger.error(f"Error syncing campaign {campaign_id}: {e}")
            return Response({"error": str(e)}, status=502)


class CampaignDonationsSyncAPI(APIView):
    """
    Sync all donations for a campaign from blockchain.

    Called by frontend after a user donates to a campaign.
    Fetches donations via get_donations_for_campaign RPC call.
    """

    @extend_schema(
        summary="Sync donations for a campaign",
        responses={
            200: OpenApiResponse(description="Donations synced"),
            404: OpenApiResponse(description="Campaign not found"),
            502: OpenApiResponse(description="RPC failed"),
        },
    )
    def post(self, request, campaign_id: int):
        try:
            # Ensure campaign exists in DB
            campaign = Campaign.objects.filter(on_chain_id=int(campaign_id)).first()
            if not campaign:
                # Sync campaign first
                campaign_sync = CampaignSyncAPI()
                resp = campaign_sync.post(request, campaign_id)
                if resp.status_code != 200:
                    return Response({"error": "Campaign not found"}, status=404)
                campaign = Campaign.objects.get(on_chain_id=int(campaign_id))

            # Fetch donations from RPC
            donations = fetch_from_rpc(
                "get_donations_for_campaign", {"campaign_id": int(campaign_id)}
            )

            if not donations:
                donations = []

            synced = 0
            for don in donations:
                # Upsert accounts
                donor, _ = Account.objects.get_or_create(defaults={"chain_id": 1}, id=don["donor_id"])

                referrer = None
                if don.get("referrer_id"):
                    referrer, _ = Account.objects.get_or_create(defaults={"chain_id": 1}, id=don["referrer_id"])

                donated_at = datetime.fromtimestamp(don["donated_at_ms"] / 1000, tz=timezone.utc)
                returned_at = (
                    datetime.fromtimestamp(don["returned_at_ms"] / 1000, tz=timezone.utc)
                    if don.get("returned_at_ms")
                    else None
                )

                donation_defaults = {
                    "token": campaign.token,
                    "total_amount": str(don["total_amount"]),
                    "net_amount": str(don["net_amount"]),
                    "message": don.get("message"),
                    "donated_at": donated_at,
                    "protocol_fee": str(don["protocol_fee"]),
                    "referrer": referrer,
                    "referrer_fee": str(don["referrer_fee"]) if don.get("referrer_fee") else None,
                    "creator_fee": str(don["creator_fee"]),
                    "returned_at": returned_at,
                    "escrowed": don.get("is_in_escrow", False),
                }

                donation, _ = CampaignDonation.objects.update_or_create(
                    on_chain_id=don["id"],
                    campaign=campaign,
                    donor=donor,
                    defaults=donation_defaults,
                )

                # Fetch USD prices (matches indexer behavior)
                try:
                    donation.fetch_usd_prices()
                except Exception as e:
                    logger.warning(f"Failed to fetch USD prices for donation {don['id']}: {e}")

                synced += 1

            # Also update campaign totals from chain
            campaign_data = fetch_from_rpc(
                "get_campaign", {"campaign_id": int(campaign_id)}
            )
            if campaign_data:
                campaign.total_raised_amount = str(campaign_data.get(
                    "total_raised_amount", campaign.total_raised_amount
                ))
                campaign.net_raised_amount = str(campaign_data.get(
                    "net_raised_amount", campaign.net_raised_amount
                ))
                campaign.escrow_balance = str(campaign_data.get(
                    "escrow_balance", campaign.escrow_balance
                ))
                campaign.save()

            return Response(
                {
                    "success": True,
                    "message": f"Synced {synced} donations",
                    "synced_count": synced,
                }
            )

        except Exception as e:
            logger.error(
                f"Error syncing donations for campaign {campaign_id}: {e}"
            )
            return Response({"error": str(e)}, status=502)
