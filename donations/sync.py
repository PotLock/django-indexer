"""
Sync endpoints for direct donations - fetch data from blockchain RPC and store in database.

Called by frontend after user makes a direct donation.

Endpoints:
    POST /api/v1/donations/sync - Sync single donation via tx_hash
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
from donations.models import Donation
from tokens.models import Token

logger = logging.getLogger(__name__)

DONATION_CONTRACT = f"donate.{settings.POTLOCK_TLA}"


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
                    # Check if this looks like direct donation data
                    if isinstance(data, dict) and "donor_id" in data and "recipient_id" in data:
                        return data
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue

    return None


class DirectDonationSyncAPI(APIView):
    """
    Sync a direct donation from blockchain to database.

    Called by frontend after a user makes a direct donation.
    Frontend passes the transaction hash, backend parses the donation from tx result.
    """

    @extend_schema(
        summary="Sync a direct donation",
        description="Sync a single direct donation using the transaction hash from the donation response.",
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
            404: OpenApiResponse(description="Donation not found in transaction"),
            502: OpenApiResponse(description="RPC failed"),
        },
    )
    def post(self, request):
        try:
            # Get required parameters
            tx_hash = request.data.get("tx_hash") or request.query_params.get("tx_hash")
            sender_id = request.data.get("sender_id") or request.query_params.get("sender_id")

            if not tx_hash or not sender_id:
                return Response(
                    {"error": "tx_hash and sender_id are required"},
                    status=400,
                )

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

            # Upsert accounts
            donor, _ = Account.objects.get_or_create(
                defaults={"chain_id": 1}, id=donation_data["donor_id"]
            )
            recipient, _ = Account.objects.get_or_create(
                defaults={"chain_id": 1}, id=donation_data["recipient_id"]
            )

            referrer = None
            if donation_data.get("referrer_id"):
                referrer, _ = Account.objects.get_or_create(
                    defaults={"chain_id": 1}, id=donation_data["referrer_id"]
                )

            # Get or create token
            token_id = donation_data.get("ft_id") or "near"
            token_acct, _ = Account.objects.get_or_create(defaults={"chain_id": 1}, id=token_id)
            token, _ = Token.objects.get_or_create(account=token_acct, defaults={"decimals": 24})

            # Parse timestamp
            donated_at = datetime.fromtimestamp(
                donation_data["donated_at_ms"] / 1000, tz=timezone.utc
            )

            # Create or update donation
            donation_defaults = {
                "donor": donor,
                "recipient": recipient,
                "token": token,
                "total_amount": str(donation_data["total_amount"]),
                "net_amount": str(donation_data["net_amount"]),
                "message": donation_data.get("message"),
                "donated_at": donated_at,
                "protocol_fee": str(donation_data.get("protocol_fee", "0")),
                "referrer": referrer,
                "referrer_fee": str(donation_data["referrer_fee"]) if donation_data.get("referrer_fee") else None,
                "matching_pool": False,
                "tx_hash": tx_hash,
            }

            donation, created = Donation.objects.update_or_create(
                on_chain_id=donation_data["id"],
                pot__isnull=True,  # Direct donations have no pot
                defaults=donation_defaults,
            )

            return Response(
                {
                    "success": True,
                    "message": "Donation synced",
                    "donation_id": donation.on_chain_id,
                    "created": created,
                }
            )

        except Exception as e:
            logger.error(f"Error syncing direct donation: {e}")
            return Response({"error": str(e)}, status=502)
