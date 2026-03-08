"""
Sync endpoints for grantpicks - fetch data from Stellar RPC and store in database.

Called by frontend after user performs on-chain actions (create/update project, round, application).

Endpoints:
    POST /api/v1/projects/{project_id}/sync - Sync single project from chain
    POST /api/v1/projects/sync - Sync multiple projects from chain
    POST /api/v1/rounds/{round_id}/sync - Sync single round from chain
    POST /api/v1/rounds/sync - Sync multiple rounds from chain
    POST /api/v1/rounds/{round_id}/applications/sync - Sync applications for a round from chain
    POST /api/v1/rounds/{round_id}/applications/review/sync - Sync application review from chain (requires applicant_id + reviewer_id)
    POST /api/v1/rounds/{round_id}/approved-projects/sync - Sync approved projects for a round from chain
    POST /api/v1/rounds/{round_id}/deposits/sync - Sync deposits for a round from chain
    POST /api/v1/rounds/{round_id}/votes/sync - Sync votes for a round from chain
    POST /api/v1/rounds/{round_id}/payouts/sync - Sync payouts for a round from chain
"""
import json
import logging
from datetime import datetime

import stellar_sdk
from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView

from indexer_app.tasks import address_to_string
from indexer_app.utils import (
    create_or_update_round,
    create_round_application,
    create_round_payout,
    process_project_event,
    process_rounds_deposit_event,
    process_vote_event,
    update_application,
    update_approved_projects,
    update_round_payout,
)

logger = logging.getLogger(__name__)

# Contract IDs for sync endpoints only — does not affect Celery worker or other code
_STELLAR_ROUND_CONTRACT = {
    "testnet": "CA7A2776JYIOYXPAJFONDC7BVPDWWLZU524UTGIJIQH6HWWOR6LKYQQT",
    "dev": "CDCRTJQ3SP2LJEOT5EA2B6WTGUUI6BVYDJXKYRJCKRSPSYJHXV5V6X3O",
}.get(settings.ENVIRONMENT, "")

_STELLAR_PROJECT_CONTRACT = {
    "testnet": "CA56XSY7YEZ7CJ5FYG7YODQIWE3JNRGZ5S7E7VJAQ675KDS4BLZJ5NJH",
    "dev": "CD6X5JVK6ITAZGOMIUBVJUHFMK34YW2ZEWQ2BDLV6XFRFGNV56A4L3RC",
}.get(settings.ENVIRONMENT, "")


def fetch_from_stellar_rpc(contract_id, function_name, parameters):
    """Call a Stellar contract view method via simulate_transaction."""
    server = stellar_sdk.SorobanServer(
        "https://soroban-testnet.stellar.org"
        if settings.ENVIRONMENT == "testnet"
        else "https://rpc.ankr.com/stellar_soroban"
    )
    public_key = "GAAZI4TCR3TY5OJHCTJC2A4QSY6CJWJH5IAJTGKIN2ER7LBNVKOCCWN7"
    acct = server.load_account(public_key)
    result = server.simulate_transaction(
        transaction_envelope=stellar_sdk.TransactionBuilder(
            source_account=acct,
        )
        .append_invoke_contract_function_op(contract_id, function_name, parameters)
        .set_timeout(30)
        .build()
    )
    if result.results:
        xdr = result.results[0].xdr
        data = stellar_sdk.scval.to_native(xdr)
        data = json.loads(json.dumps(data, default=address_to_string))
        return data
    return None


def _fill_project_defaults(data):
    """Fill in fields the shared handler expects but RPC data may not have."""
    if not data.get("payout_address"):
        data["payout_address"] = data.get("owner", "")
    if not data.get("video_url"):
        data["video_url"] = ""
    if not data.get("updated_ms"):
        data["updated_ms"] = data.get("submited_ms", 0)
    return data


class ProjectSyncAPI(APIView):
    """POST /api/v1/projects/{project_id}/sync - Sync a single project from chain."""

    def post(self, request, project_id: int):
        data = fetch_from_stellar_rpc(
            _STELLAR_PROJECT_CONTRACT,
            "get_project_by_id",
            [stellar_sdk.scval.to_uint128(project_id)],
        )
        if not data:
            return Response({"error": "Project not found on chain"}, status=404)

        result = process_project_event(_fill_project_defaults(data))
        if result:
            return Response({"success": True, "message": "Project synced"})
        return Response({"error": "Failed to process project"}, status=502)


class ProjectsListSyncAPI(APIView):
    """POST /api/v1/projects/sync - Sync multiple projects from chain."""

    def post(self, request):
        skip = int(request.data.get("skip", 0))
        limit = int(request.data.get("limit", 100))

        data = fetch_from_stellar_rpc(
            _STELLAR_PROJECT_CONTRACT,
            "get_projects",
            [
                stellar_sdk.scval.to_uint64(skip),
                stellar_sdk.scval.to_uint64(limit),
            ],
        )
        if not data:
            return Response({"error": "No projects found"}, status=404)

        synced = 0
        for project_data in data:
            if process_project_event(_fill_project_defaults(project_data)):
                synced += 1

        return Response({"success": True, "synced": synced, "total": len(data)})


class RoundSyncAPI(APIView):
    """POST /api/v1/round/{round_id}/sync - Sync a single round from chain."""

    def post(self, request, round_id: int):
        data = fetch_from_stellar_rpc(
            _STELLAR_ROUND_CONTRACT,
            "get_round",
            [stellar_sdk.scval.to_uint128(round_id)],
        )
        if not data:
            return Response({"error": "Round not found on chain"}, status=404)

        timestamp = datetime.fromtimestamp(data.get("deployed_at", 0) / 1000) if data.get("deployed_at") else datetime.now()
        result = create_or_update_round(data, _STELLAR_ROUND_CONTRACT, timestamp)
        if result:
            return Response({"success": True, "message": "Round synced"})
        return Response({"error": "Failed to process round"}, status=502)


class RoundsListSyncAPI(APIView):
    """POST /api/v1/rounds/sync - Sync multiple rounds from chain."""

    def post(self, request):
        skip = int(request.data.get("skip", 0))
        limit = int(request.data.get("limit", 100))

        data = fetch_from_stellar_rpc(
            _STELLAR_ROUND_CONTRACT,
            "get_rounds",
            [
                stellar_sdk.scval.to_uint64(skip),
                stellar_sdk.scval.to_uint64(limit),
            ],
        )
        if not data:
            return Response({"error": "No rounds found"}, status=404)

        synced = 0
        for round_data in data:
            timestamp = datetime.fromtimestamp(round_data.get("deployed_at", 0) / 1000) if round_data.get("deployed_at") else datetime.now()
            if create_or_update_round(round_data, _STELLAR_ROUND_CONTRACT, timestamp):
                synced += 1

        return Response({"success": True, "synced": synced, "total": len(data)})


class RoundApplicationsSyncAPI(APIView):
    """POST /api/v1/round/{round_id}/applications/sync - Sync applications for a round from chain."""

    def post(self, request, round_id: int):
        skip = int(request.data.get("skip", 0))
        limit = int(request.data.get("limit", 100))

        data = fetch_from_stellar_rpc(
            _STELLAR_ROUND_CONTRACT,
            "get_applications_for_round",
            [
                stellar_sdk.scval.to_uint128(round_id),
                stellar_sdk.scval.to_uint64(skip),
                stellar_sdk.scval.to_uint64(limit),
            ],
        )
        if not data:
            return Response({"error": "No applications found for this round"}, status=404)

        synced = 0
        for app_data in data:
            if create_round_application([round_id, app_data], tx_hash=None):
                synced += 1

        return Response({"success": True, "synced": synced, "total": len(data)})


class ApplicationReviewSyncAPI(APIView):
    """POST /api/v1/rounds/{round_id}/applications/review/sync - Sync application review.

    Fetches the application from Stellar RPC, then updates the DB.
    Only requires applicant_id (to look up the application on-chain) and
    reviewer_id (not stored in the contract's RoundApplication struct).

    Expected request body:
    {
        "applicant_id": "GXYZ...",
        "reviewer_id": "GABC...",
        "tx_hash": "abc123..."  // optional
    }
    """

    def post(self, request, round_id: int):
        data = request.data
        required_fields = ["applicant_id", "reviewer_id"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            return Response({"error": f"Missing required fields: {missing}"}, status=400)

        applicant_id = data["applicant_id"]
        reviewer_id = data["reviewer_id"]
        tx_hash = data.get("tx_hash")

        # Fetch application from Stellar RPC
        application_data = fetch_from_stellar_rpc(
            _STELLAR_ROUND_CONTRACT,
            "get_application",
            [
                stellar_sdk.scval.to_uint128(round_id),
                stellar_sdk.scval.to_address(applicant_id),
            ],
        )
        if not application_data:
            return Response({"error": "Application not found on chain"}, status=404)

        # Format as [round_id, application_data, reviewer_id] — exactly how Celery worker passes it
        event_data = [round_id, application_data, reviewer_id]
        result = update_application(event_data, tx_hash)
        if result:
            return Response({"success": True, "message": "Application review synced"})
        return Response({"error": "Failed to sync application review"}, status=502)


class ApprovedProjectsSyncAPI(APIView):
    """POST /api/v1/rounds/{round_id}/approved-projects/sync - Sync approved projects.

    Fetches approved project IDs from Stellar RPC, then updates the DB.
    No request body needed.
    """

    def post(self, request, round_id: int):
        # Fetch approved projects from Stellar RPC
        project_ids = fetch_from_stellar_rpc(
            _STELLAR_ROUND_CONTRACT,
            "get_approved_projects",
            [stellar_sdk.scval.to_uint128(round_id)],
        )
        if project_ids is None:
            return Response({"error": "Could not fetch approved projects from chain"}, status=502)
        if not project_ids:
            return Response({"success": True, "message": "No approved projects on chain", "synced": 0})

        # Format as [round_id, [project_ids]] — exactly how Celery worker passes it
        event_data = [round_id, project_ids]
        result = update_approved_projects(event_data)
        if result:
            return Response({"success": True, "message": "Approved projects synced", "synced": len(project_ids)})
        return Response({"error": "Failed to sync approved projects"}, status=502)


class RoundDepositsSyncAPI(APIView):
    """POST /api/v1/rounds/{round_id}/deposits/sync - Sync deposits for a round from chain."""

    def post(self, request, round_id: int):
        skip = int(request.data.get("skip", 0))
        limit = int(request.data.get("limit", 100))

        data = fetch_from_stellar_rpc(
            _STELLAR_ROUND_CONTRACT,
            "get_deposits_for_round",
            [
                stellar_sdk.scval.to_uint128(round_id),
                stellar_sdk.scval.to_uint64(skip),
                stellar_sdk.scval.to_uint64(limit),
            ],
        )
        if not data:
            return Response({"error": "No deposits found for this round"}, status=404)

        synced = 0
        for deposit_data in data:
            if process_rounds_deposit_event([round_id, deposit_data], tx_hash=None):
                synced += 1

        return Response({"success": True, "synced": synced, "total": len(data)})


class RoundVotesSyncAPI(APIView):
    """POST /api/v1/rounds/{round_id}/votes/sync - Sync votes for a round from chain."""

    def post(self, request, round_id: int):
        skip = int(request.data.get("skip", 0))
        limit = int(request.data.get("limit", 100))

        data = fetch_from_stellar_rpc(
            _STELLAR_ROUND_CONTRACT,
            "get_votes_for_round",
            [
                stellar_sdk.scval.to_uint128(round_id),
                stellar_sdk.scval.to_uint64(skip),
                stellar_sdk.scval.to_uint64(limit),
            ],
        )
        if not data:
            return Response({"error": "No votes found for this round"}, status=404)

        synced = 0
        for vote_data in data:
            if process_vote_event([round_id, vote_data], tx_hash=None):
                synced += 1

        return Response({"success": True, "synced": synced, "total": len(data)})


class RoundPayoutsSyncAPI(APIView):
    """POST /api/v1/rounds/{round_id}/payouts/sync - Sync payouts for a round from chain.

    Fetches all payouts from the contract. Creates new payouts and updates existing ones
    (e.g. when paid_at_ms is set after processing).
    """

    def post(self, request, round_id: int):
        skip = int(request.data.get("skip", 0))
        limit = int(request.data.get("limit", 100))

        data = fetch_from_stellar_rpc(
            _STELLAR_ROUND_CONTRACT,
            "get_payouts_for_round",
            [
                stellar_sdk.scval.to_uint128(round_id),
                stellar_sdk.scval.to_uint64(skip),
                stellar_sdk.scval.to_uint64(limit),
            ],
        )
        if not data:
            return Response({"error": "No payouts found for this round"}, status=404)

        synced = 0
        for payout_data in data:
            event = [round_id, payout_data]
            # Try update first (payout may already exist in DB); if not found, create then update
            if not update_round_payout(event, tx_hash=None):
                create_round_payout(event, tx_hash=None)
                if payout_data.get("paid_at_ms"):
                    update_round_payout(event, tx_hash=None)
            synced += 1

        return Response({"success": True, "synced": synced, "total": len(data)})
