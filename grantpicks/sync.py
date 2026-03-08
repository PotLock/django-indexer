"""
Sync endpoints for grantpicks - fetch data from Stellar RPC and store in database.

Called by frontend after user performs on-chain actions (create/update project, round, application, list).

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
    POST /api/v1/lists/{list_id}/sync - Sync single list from chain
    POST /api/v1/lists/{list_id}/registrations/sync - Sync registrations for a list from chain
    POST /api/v1/lists/{list_id}/registrations/{registrant_id}/sync - Sync single registration from chain
    POST /api/v1/lists/{list_id}/delete/sync - Delete list from DB after on-chain deletion
"""
import json
import logging
from datetime import datetime

import stellar_sdk
from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Account
from lists.models import List, ListRegistration

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

_STELLAR_LISTS_CONTRACT = {
    "testnet": "CCLXSELRRF67M3K5JJYNT6HRTJN26JDJKZYKR5QTZAEZU2TSCF6OGFZT",
    "dev": "CAIYXP5CNFB5WUBAWEPBZHIKYZGP3IEFXILFMDUT37FZBKNGFJGNJPNT",
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


class StellarListSyncAPI(APIView):
    """POST /api/v1/lists/{list_id}/sync - Sync a single list from Stellar chain."""

    def post(self, request, list_id: int):
        try:
            data = fetch_from_stellar_rpc(
                _STELLAR_LISTS_CONTRACT,
                "get_list",
                [stellar_sdk.scval.to_uint128(list_id)],
            )
            if not data:
                return Response({"error": "List not found on chain"}, status=404)

            # Map Stellar field names to DB fields
            owner_id = data.get("owner", "")
            Account.objects.get_or_create(id=owner_id)

            # default_registration_status comes as array like ["Pending"] from Stellar
            default_status = data.get("default_registration_status", "Pending")
            if isinstance(default_status, list):
                default_status = default_status[0] if default_status else "Pending"

            created_at = datetime.fromtimestamp(data.get("created_ms", 0) / 1000) if data.get("created_ms") else datetime.now()
            updated_at = datetime.fromtimestamp(data.get("updated_ms", 0) / 1000) if data.get("updated_ms") else datetime.now()

            existing_list = List.objects.filter(on_chain_id=int(list_id)).first()

            if existing_list:
                existing_list.name = data.get("name", "")
                existing_list.description = data.get("description", "")
                existing_list.cover_image_url = data.get("cover_img_url") or data.get("cover_image_url")
                existing_list.admin_only_registrations = data.get("admin_only_registrations", False)
                existing_list.default_registration_status = default_status
                existing_list.updated_at = updated_at
                existing_list.save()

                existing_list.admins.clear()
                for admin_id in data.get("admins", []):
                    admin, _ = Account.objects.get_or_create(id=admin_id)
                    existing_list.admins.add(admin)

                return Response({"success": True, "message": "List updated", "on_chain_id": list_id})

            list_obj = List.objects.create(
                on_chain_id=data.get("id", list_id),
                owner_id=owner_id,
                name=data.get("name", ""),
                description=data.get("description", ""),
                cover_image_url=data.get("cover_img_url") or data.get("cover_image_url"),
                admin_only_registrations=data.get("admin_only_registrations", False),
                default_registration_status=default_status,
                created_at=created_at,
                updated_at=updated_at,
            )

            for admin_id in data.get("admins", []):
                admin, _ = Account.objects.get_or_create(id=admin_id)
                list_obj.admins.add(admin)

            return Response({"success": True, "message": "List created", "on_chain_id": list_obj.on_chain_id})

        except Exception as e:
            logger.error(f"Error syncing list {list_id}: {e}")
            return Response({"error": str(e)}, status=502)


class StellarListRegistrationsSyncAPI(APIView):
    """POST /api/v1/lists/{list_id}/registrations/sync - Sync registrations for a list from Stellar chain."""

    def post(self, request, list_id: int):
        try:
            # Ensure list exists in DB
            try:
                list_obj = List.objects.get(on_chain_id=int(list_id))
            except List.DoesNotExist:
                sync = StellarListSyncAPI()
                resp = sync.post(request, list_id)
                if resp.status_code != 200:
                    return Response({"error": "List not found"}, status=404)
                list_obj = List.objects.get(on_chain_id=int(list_id))

            # Fetch all registrations (no status filter — pass None)
            registrations = fetch_from_stellar_rpc(
                _STELLAR_LISTS_CONTRACT,
                "get_registrations_for_list",
                [
                    stellar_sdk.scval.to_uint128(list_id),
                    stellar_sdk.scval.to_void(),
                    stellar_sdk.scval.to_uint64(0),
                    stellar_sdk.scval.to_uint64(100),
                ],
            )

            if not registrations:
                registrations = []

            synced = 0
            for reg in registrations:
                registrant_id = reg.get("registrant_id", "")
                registered_by = reg.get("registered_by", registrant_id)
                Account.objects.get_or_create(id=registrant_id)
                Account.objects.get_or_create(id=registered_by)

                status = reg.get("status", "Pending")
                if isinstance(status, list):
                    status = status[0] if status else "Pending"

                submitted_at = datetime.fromtimestamp(reg.get("submitted_ms", 0) / 1000) if reg.get("submitted_ms") else datetime.now()
                updated_at = datetime.fromtimestamp(reg.get("updated_ms", 0) / 1000) if reg.get("updated_ms") else datetime.now()

                ListRegistration.objects.update_or_create(
                    list=list_obj,
                    registrant_id=registrant_id,
                    defaults={
                        "registered_by_id": registered_by,
                        "status": status,
                        "submitted_at": submitted_at,
                        "updated_at": updated_at,
                        "admin_notes": reg.get("admin_notes"),
                        "registrant_notes": reg.get("registrant_notes"),
                    }
                )
                synced += 1

            return Response({"success": True, "message": f"Synced {synced} registrations", "synced_count": synced})

        except Exception as e:
            logger.error(f"Error syncing registrations for list {list_id}: {e}")
            return Response({"error": str(e)}, status=502)


class StellarSingleRegistrationSyncAPI(APIView):
    """POST /api/v1/lists/{list_id}/registrations/{registrant_id}/sync - Sync single registration from Stellar chain."""

    def post(self, request, list_id: int, registrant_id: str):
        try:
            # Ensure list exists in DB
            try:
                list_obj = List.objects.get(on_chain_id=int(list_id))
            except List.DoesNotExist:
                sync = StellarListSyncAPI()
                resp = sync.post(request, list_id)
                if resp.status_code != 200:
                    return Response({"error": "List not found"}, status=404)
                list_obj = List.objects.get(on_chain_id=int(list_id))

            # Fetch all registrations and find the one we need
            registrations = fetch_from_stellar_rpc(
                _STELLAR_LISTS_CONTRACT,
                "get_registrations_for_list",
                [
                    stellar_sdk.scval.to_uint128(list_id),
                    stellar_sdk.scval.to_void(),
                    stellar_sdk.scval.to_uint64(0),
                    stellar_sdk.scval.to_uint64(100),
                ],
            )

            if not registrations:
                return Response({"error": "No registrations found for list"}, status=404)

            reg = next((r for r in registrations if r.get("registrant_id") == registrant_id), None)
            if not reg:
                return Response({"error": "Registration not found"}, status=404)

            Account.objects.get_or_create(id=reg["registrant_id"])
            registered_by = reg.get("registered_by", reg["registrant_id"])
            Account.objects.get_or_create(id=registered_by)

            status = reg.get("status", "Pending")
            if isinstance(status, list):
                status = status[0] if status else "Pending"

            submitted_at = datetime.fromtimestamp(reg.get("submitted_ms", 0) / 1000) if reg.get("submitted_ms") else datetime.now()
            updated_at = datetime.fromtimestamp(reg.get("updated_ms", 0) / 1000) if reg.get("updated_ms") else datetime.now()

            registration, created = ListRegistration.objects.update_or_create(
                list=list_obj,
                registrant_id=reg["registrant_id"],
                defaults={
                    "registered_by_id": registered_by,
                    "status": status,
                    "submitted_at": submitted_at,
                    "updated_at": updated_at,
                    "admin_notes": reg.get("admin_notes"),
                    "registrant_notes": reg.get("registrant_notes"),
                }
            )

            return Response({"success": True, "message": "Registration synced", "registrant_id": registrant_id, "status": registration.status})

        except Exception as e:
            logger.error(f"Error syncing registration: {e}")
            return Response({"error": str(e)}, status=502)


class StellarListDeleteSyncAPI(APIView):
    """POST /api/v1/lists/{list_id}/delete/sync - Delete list from DB after on-chain deletion."""

    def post(self, request, list_id: int):
        try:
            # Verify list no longer exists on chain
            data = fetch_from_stellar_rpc(
                _STELLAR_LISTS_CONTRACT,
                "get_list",
                [stellar_sdk.scval.to_uint128(list_id)],
            )

            if data:
                return Response({"error": "List still exists on chain — not deleted"}, status=400)

            # List doesn't exist on chain — safe to delete from DB
            deleted_count, _ = List.objects.filter(on_chain_id=int(list_id)).delete()

            if deleted_count > 0:
                logger.info(f"List {list_id} deleted from DB (verified not on chain)")
                return Response({"success": True, "message": "List deleted", "on_chain_id": list_id})

            return Response({"error": "List not found in database"}, status=404)

        except Exception as e:
            # If RPC call fails (e.g. contract panics with "List does not exist"), that confirms deletion
            error_str = str(e)
            if "does not exist" in error_str or "not found" in error_str.lower():
                deleted_count, _ = List.objects.filter(on_chain_id=int(list_id)).delete()
                if deleted_count > 0:
                    logger.info(f"List {list_id} deleted from DB (RPC confirmed not on chain)")
                    return Response({"success": True, "message": "List deleted", "on_chain_id": list_id})
                return Response({"error": "List not found in database"}, status=404)

            logger.error(f"Error syncing list deletion {list_id}: {e}")
            return Response({"error": str(e)}, status=502)
