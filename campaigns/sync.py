"""
Sync endpoints - fetch data from blockchain RPC and store in database.

Called by frontend after user creates/updates/deletes a campaign, donates,
or processes refunds/escrowed donations.
Replaces the 24/7 indexer - now we fetch on-demand when user acts.

Endpoints:
    POST /api/v1/campaigns/{campaign_id}/sync - Sync single campaign
    POST /api/v1/campaigns/{campaign_id}/donations/sync - Sync single donation via tx_hash
    POST /api/v1/campaigns/{campaign_id}/delete/sync - Sync campaign deletion via tx_hash
    POST /api/v1/campaigns/{campaign_id}/refunds/sync - Sync donation refunds via tx_hash
    POST /api/v1/campaigns/{campaign_id}/unescrow/sync - Sync donation unescrow via tx_hash
"""
import base64
import json
import logging
from datetime import datetime, timezone

import requests
from django.conf import settings
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
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


def fetch_tx_result(tx_hash: str, sender_id: str):
    """
    Fetch transaction result from NEAR RPC.
    Returns the parsed result from the transaction execution.
    """
    rpc_url = (
        "https://test.rpc.fastnear.com"
        if settings.ENVIRONMENT == "testnet"
        else "https://free.rpc.fastnear.com"
    )

    payload = {
        "jsonrpc": "2.0",
        "id": "dontcare",
        "method": "tx",
        "params": {
            "tx_hash": tx_hash,
            "sender_account_id": sender_id,
            "wait_until": "EXECUTED_OPTIMISTIC",
        },
    }

    response = requests.post(rpc_url, json=payload, timeout=30)
    result = response.json()

    if "error" in result:
        raise Exception(f"RPC error fetching tx: {result['error']}")

    return result.get("result")


def parse_events_from_tx(tx_result: dict, event_name: str) -> list[dict]:
  
    events = []
    receipts_outcome = tx_result.get("receipts_outcome", [])

    for outcome in receipts_outcome:
        logs = outcome.get("outcome", {}).get("logs", [])
        for log in logs:
            if not log.startswith("EVENT_JSON:"):
                continue
            try:
                parsed = json.loads(log[len("EVENT_JSON:"):])
                if parsed.get("event") == event_name:
                    for data_item in parsed.get("data", []):
                        events.append(data_item)
            except (json.JSONDecodeError, KeyError):
                continue

    return events


def parse_donation_from_tx(tx_result: dict) -> dict:
    """
    Parse donation data from transaction execution result.
    Looks through receipts_outcome to find the SuccessValue containing donation data.
    """
    receipts_outcome = tx_result.get("receipts_outcome", [])

    for outcome in receipts_outcome:
        status = outcome.get("outcome", {}).get("status", {})
        if isinstance(status, dict) and "SuccessValue" in status:
            success_value = status["SuccessValue"]
            if success_value:
                try:
                    decoded = base64.b64decode(success_value).decode()
                    data = json.loads(decoded)
                    # Check if this looks like donation data
                    if isinstance(data, dict) and "donor_id" in data and "total_amount" in data:
                        return data
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue

    return None


def sync_campaign_from_chain(campaign_id: int) -> tuple[Campaign, bool]:
    """
    Fetch campaign from blockchain and sync to database.
    Returns (campaign, created) tuple.

    This is a shared utility used by both CampaignSyncAPI and when
    ensuring a campaign exists before syncing donations.
    """
    data = fetch_from_rpc("get_campaign", {"campaign_id": int(campaign_id)})

    if not data:
        return None, False

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

    # Note: USD price fetching is skipped here intentionally.
    # A daily cron job will handle USD price updates for all records.

    return campaign, created


def sync_donation_from_data(campaign: Campaign, donation_data: dict, tx_hash: str = None) -> CampaignDonation:
    """
    Sync a single donation from parsed data to database.

    This is a shared utility for creating/updating a campaign donation.
    """
    # Upsert accounts
    donor, _ = Account.objects.get_or_create(
        defaults={"chain_id": 1}, id=donation_data["donor_id"]
    )

    referrer = None
    if donation_data.get("referrer_id"):
        referrer, _ = Account.objects.get_or_create(
            defaults={"chain_id": 1}, id=donation_data["referrer_id"]
        )

    donated_at = datetime.fromtimestamp(
        donation_data["donated_at_ms"] / 1000, tz=timezone.utc
    )
    returned_at = (
        datetime.fromtimestamp(donation_data["returned_at_ms"] / 1000, tz=timezone.utc)
        if donation_data.get("returned_at_ms")
        else None
    )

    # Get token if specified, otherwise use campaign's token
    token = campaign.token
    if donation_data.get("ft_id"):
        token_acct, _ = Account.objects.get_or_create(
            defaults={"chain_id": 1}, id=donation_data["ft_id"]
        )
        token, _ = Token.objects.get_or_create(
            account=token_acct, defaults={"decimals": 24}
        )

    donation_defaults = {
        "token": token,
        "total_amount": str(donation_data["total_amount"]),
        "net_amount": str(donation_data["net_amount"]),
        "message": donation_data.get("message"),
        "donated_at": donated_at,
        "protocol_fee": str(donation_data["protocol_fee"]),
        "referrer": referrer,
        "referrer_fee": str(donation_data["referrer_fee"]) if donation_data.get("referrer_fee") else None,
        "creator_fee": str(donation_data["creator_fee"]),
        "returned_at": returned_at,
        "escrowed": donation_data.get("is_in_escrow", False),
    }

    if tx_hash:
        donation_defaults["tx_hash"] = tx_hash

    donation, created = CampaignDonation.objects.update_or_create(
        on_chain_id=donation_data["id"],
        campaign=campaign,
        donor=donor,
        defaults=donation_defaults,
    )

    # Note: USD price fetching is skipped here intentionally.
    # A daily cron job will handle USD price updates for all records.

    return donation


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
            campaign, created = sync_campaign_from_chain(campaign_id)

            if not campaign:
                return Response({"error": "Campaign not found on chain"}, status=404)

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


class CampaignDonationSyncAPI(APIView):
    """
    Sync a single donation for a campaign from blockchain.

    Called by frontend after a user donates to a campaign.
    Frontend passes the transaction hash, backend parses the donation from tx result.
    """

    @extend_schema(
        summary="Sync a donation for a campaign",
        description="Sync a single donation using the transaction hash from the donation response.",
        parameters=[
            OpenApiParameter(
                name="tx_hash",
                description="Transaction hash from the donation transaction",
                required=True,
                type=str,
            ),
            OpenApiParameter(
                name="sender_id",
                description="Account ID of the transaction sender (donor)",
                required=True,
                type=str,
            ),
        ],
        responses={
            200: OpenApiResponse(description="Donation synced"),
            400: OpenApiResponse(description="Missing required parameters"),
            404: OpenApiResponse(description="Campaign or donation not found"),
            502: OpenApiResponse(description="RPC failed"),
        },
    )
    def post(self, request, campaign_id: int):
        try:
            # Get required parameters
            tx_hash = request.data.get("tx_hash") or request.query_params.get("tx_hash")
            sender_id = request.data.get("sender_id") or request.query_params.get("sender_id")

            if not tx_hash or not sender_id:
                return Response(
                    {"error": "tx_hash and sender_id are required"},
                    status=400,
                )

            # Ensure campaign exists in DB
            campaign = Campaign.objects.filter(on_chain_id=int(campaign_id)).first()
            if not campaign:
                # Sync campaign first using shared utility
                campaign, _ = sync_campaign_from_chain(campaign_id)
                if not campaign:
                    return Response({"error": "Campaign not found"}, status=404)

            # Fetch transaction result and parse donation data
            tx_result = fetch_tx_result(tx_hash, sender_id)
            if not tx_result:
                return Response({"error": "Transaction not found"}, status=404)

            donation_data = parse_donation_from_tx(tx_result)
            if not donation_data:
                return Response(
                    {"error": "Could not parse donation from transaction result"},
                    status=404,
                )

            # Verify this donation belongs to the specified campaign
            if donation_data.get("campaign_id") != int(campaign_id):
                return Response(
                    {"error": "Donation does not belong to this campaign"},
                    status=400,
                )

            # Sync the donation using shared utility
            donation = sync_donation_from_data(campaign, donation_data, tx_hash)

            # Update campaign totals from chain (single RPC call to get fresh totals)
            campaign_data = fetch_from_rpc(
                "get_campaign", {"campaign_id": int(campaign_id)}
            )
            if campaign_data:
                campaign.total_raised_amount = str(
                    campaign_data.get("total_raised_amount", campaign.total_raised_amount)
                )
                campaign.net_raised_amount = str(
                    campaign_data.get("net_raised_amount", campaign.net_raised_amount)
                )
                campaign.escrow_balance = str(
                    campaign_data.get("escrow_balance", campaign.escrow_balance)
                )
                campaign.save()

            return Response(
                {
                    "success": True,
                    "message": "Donation synced",
                    "donation_id": donation.on_chain_id,
                }
            )

        except Exception as e:
            logger.error(f"Error syncing donation for campaign {campaign_id}: {e}")
            return Response({"error": str(e)}, status=502)


class CampaignDeleteSyncAPI(APIView):


    @extend_schema(
        summary="Sync campaign deletion from blockchain via tx_hash",
        parameters=[
            OpenApiParameter(name="tx_hash", required=True, type=str),
            OpenApiParameter(name="sender_id", required=True, type=str),
        ],
        responses={
            200: OpenApiResponse(description="Campaign deleted from DB"),
            400: OpenApiResponse(description="Missing parameters or no delete event found"),
            404: OpenApiResponse(description="Campaign not found in DB"),
            502: OpenApiResponse(description="RPC failed"),
        },
    )
    def post(self, request, campaign_id: int):
        try:
            tx_hash = request.data.get("tx_hash") or request.query_params.get("tx_hash")
            sender_id = request.data.get("sender_id") or request.query_params.get("sender_id")

            if not tx_hash or not sender_id:
                return Response(
                    {"error": "tx_hash and sender_id are required"},
                    status=400,
                )

            # Fetch transaction and parse campaign_delete events
            tx_result = fetch_tx_result(tx_hash, sender_id)
            if not tx_result:
                return Response({"error": "Transaction not found"}, status=404)

            delete_events = parse_events_from_tx(tx_result, "campaign_delete")

            # Find the delete event for this specific campaign
            matching_event = None
            for event in delete_events:
                if event.get("campaign_id") == int(campaign_id):
                    matching_event = event
                    break

            if not matching_event:
                return Response(
                    {"error": f"No campaign_delete event found for campaign {campaign_id} in this transaction"},
                    status=400,
                )

            # Event verified — delete from DB
            deleted_count, _ = Campaign.objects.filter(on_chain_id=int(campaign_id)).delete()

            if deleted_count > 0:
                logger.info(f"Campaign {campaign_id} deleted from DB (verified via tx {tx_hash})")
                return Response(
                    {
                        "success": True,
                        "message": "Campaign deleted",
                        "on_chain_id": campaign_id,
                    }
                )

            return Response({"error": "Campaign not found in database"}, status=404)

        except Exception as e:
            logger.error(f"Error syncing campaign deletion {campaign_id}: {e}")
            return Response({"error": str(e)}, status=502)


class CampaignRefundSyncAPI(APIView):

    @extend_schema(
        summary="Sync donation refunds from blockchain via tx_hash",
        parameters=[
            OpenApiParameter(name="tx_hash", required=True, type=str),
            OpenApiParameter(name="sender_id", required=True, type=str),
        ],
        responses={
            200: OpenApiResponse(description="Refunds synced"),
            400: OpenApiResponse(description="Missing parameters or no refund event found"),
            502: OpenApiResponse(description="RPC failed"),
        },
    )
    def post(self, request, campaign_id: int):
        try:
            tx_hash = request.data.get("tx_hash") or request.query_params.get("tx_hash")
            sender_id = request.data.get("sender_id") or request.query_params.get("sender_id")

            if not tx_hash or not sender_id:
                return Response(
                    {"error": "tx_hash and sender_id are required"},
                    status=400,
                )

            tx_result = fetch_tx_result(tx_hash, sender_id)
            if not tx_result:
                return Response({"error": "Transaction not found"}, status=404)

            refund_events = parse_events_from_tx(tx_result, "escrow_refund")

            # Find refund events for this campaign
            matching_events = [
                e for e in refund_events if e.get("campaign_id") == int(campaign_id)
            ]

            if not matching_events:
                return Response(
                    {"error": f"No escrow_refund event found for campaign {campaign_id} in this transaction"},
                    status=400,
                )

            total_refunded = 0
            now = datetime.now(tz=timezone.utc)

            for event_data in matching_events:
                donation_ids = event_data.get("donations", [])

                # Mark donations as refunded (mirrors handle_campaign_donation_refund)
                updated_count = CampaignDonation.objects.filter(
                    on_chain_id__in=donation_ids, campaign__on_chain_id=int(campaign_id)
                ).update(returned_at=now)

                total_refunded += updated_count

                # Update campaign escrow balance and totals
                try:
                    campaign = Campaign.objects.get(on_chain_id=int(campaign_id))
                    escrow_balance = event_data.get("escrow_balance", "0")
                    campaign.escrow_balance = str(
                        int(campaign.escrow_balance) - int(escrow_balance)
                    )

                    refunded_donations = CampaignDonation.objects.filter(
                        on_chain_id__in=donation_ids, campaign__on_chain_id=int(campaign_id)
                    ).values_list("total_amount", "net_amount")

                    total_amount_refunded = sum(int(d[0]) for d in refunded_donations)
                    net_amount_refunded = sum(int(d[1]) for d in refunded_donations)

                    campaign.total_raised_amount = str(
                        int(campaign.total_raised_amount) - total_amount_refunded
                    )
                    campaign.net_raised_amount = str(
                        int(campaign.net_raised_amount) - net_amount_refunded
                    )
                    campaign.save()

                except Campaign.DoesNotExist:
                    logger.error(f"Campaign {campaign_id} not found for refund update")

            logger.info(f"Synced {total_refunded} refunds for campaign {campaign_id} (tx {tx_hash})")
            return Response(
                {
                    "success": True,
                    "message": f"{total_refunded} donation(s) marked as refunded",
                    "refunded_count": total_refunded,
                }
            )

        except Exception as e:
            logger.error(f"Error syncing refunds for campaign {campaign_id}: {e}")
            return Response({"error": str(e)}, status=502)


class CampaignUnescrowSyncAPI(APIView):

    @extend_schema(
        summary="Sync donation unescrow from blockchain via tx_hash",
        parameters=[
            OpenApiParameter(name="tx_hash", required=True, type=str),
            OpenApiParameter(name="sender_id", required=True, type=str),
        ],
        responses={
            200: OpenApiResponse(description="Unescrow synced"),
            400: OpenApiResponse(description="Missing parameters or no unescrow event found"),
            502: OpenApiResponse(description="RPC failed"),
        },
    )
    def post(self, request, campaign_id: int):
        try:
            tx_hash = request.data.get("tx_hash") or request.query_params.get("tx_hash")
            sender_id = request.data.get("sender_id") or request.query_params.get("sender_id")

            if not tx_hash or not sender_id:
                return Response(
                    {"error": "tx_hash and sender_id are required"},
                    status=400,
                )

            tx_result = fetch_tx_result(tx_hash, sender_id)
            if not tx_result:
                return Response({"error": "Transaction not found"}, status=404)

            unescrow_events = parse_events_from_tx(tx_result, "escrow_process")

            if not unescrow_events:
                return Response(
                    {"error": "No escrow_process event found in this transaction"},
                    status=400,
                )

            total_unescrowed = 0

            for event_data in unescrow_events:
                donation_ids = event_data.get("donation_ids", [])

                # Mark donations as unescrowed (mirrors handle_campaign_donation_unescrowed)
                updated_count = CampaignDonation.objects.filter(
                    on_chain_id__in=donation_ids
                ).update(escrowed=False)

                total_unescrowed += updated_count

            logger.info(f"Synced {total_unescrowed} unescrows for campaign {campaign_id} (tx {tx_hash})")
            return Response(
                {
                    "success": True,
                    "message": f"{total_unescrowed} donation(s) marked as unescrowed",
                    "unescrowed_count": total_unescrowed,
                }
            )

        except Exception as e:
            logger.error(f"Error syncing unescrow for campaign {campaign_id}: {e}")
            return Response({"error": str(e)}, status=502)
