"""
Sync endpoints for grantpicks projects - fetch data from Stellar RPC and store in database.

Called by frontend after user creates/updates a project on-chain.
Replaces the Celery stellar_event_indexer for project data.

Endpoints:
    POST /api/v1/projects/{project_id}/sync - Sync single project from chain
    POST /api/v1/projects/sync - Sync multiple projects from chain
"""
import json
import logging

import stellar_sdk
from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView

from indexer_app.tasks import address_to_string
from indexer_app.utils import process_project_event

logger = logging.getLogger(__name__)


def fetch_from_stellar_rpc(contract_id, function_name, parameters):
    """Call a Stellar contract view method via simulate_transaction."""
    server = stellar_sdk.SorobanServer(
        "https://soroban-testnet.stellar.org"
        if settings.ENVIRONMENT in ("testnet", "local")
        else "https://horizon.stellar.org"
    )
    public_key = "GAMFYFI7TIAPMLSAWIECFZCN52TR3NUIO74YM7ECBCPM6J743KENH367"
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


class ProjectSyncAPI(APIView):
    """POST /api/v1/projects/{project_id}/sync - Sync a single project from chain."""

    def post(self, request, project_id: int):
        data = fetch_from_stellar_rpc(
            settings.STELLAR_PROJECTS_REGISTRY_CONTRACT,
            "get_project_by_id",
            [stellar_sdk.scval.to_uint128(project_id)],
        )
        if not data:
            return Response({"error": "Project not found on chain"}, status=404)

        result = process_project_event(data)
        if result:
            return Response({"success": True, "message": "Project synced"})
        return Response({"error": "Failed to process project"}, status=502)


class ProjectsListSyncAPI(APIView):
    """POST /api/v1/projects/sync - Sync multiple projects from chain."""

    def post(self, request):
        skip = int(request.data.get("skip", 0))
        limit = int(request.data.get("limit", 100))

        data = fetch_from_stellar_rpc(
            settings.STELLAR_PROJECTS_REGISTRY_CONTRACT,
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
            if process_project_event(project_data):
                synced += 1

        return Response({"success": True, "synced": synced, "total": len(data)})
