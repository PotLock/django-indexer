"""
Sync endpoints - fetch data from blockchain RPC and store in database.

Called by frontend after user creates a list/registration.
Replaces the 24/7 indexer - now we fetch on-demand when user acts.

Endpoints:
    POST /api/v1/lists/{list_id}/sync - Sync single list
    POST /api/v1/lists/{list_id}/registrations/sync - Sync all registrations
    POST /api/v1/lists/{list_id}/registrations/{registrant_id}/sync - Sync single registration
"""
import base64
import json
import logging
from datetime import datetime

import requests
from django.conf import settings
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Account
from lists.models import List, ListRegistration

logger = logging.getLogger(__name__)

LISTS_CONTRACT = f"lists.{settings.POTLOCK_TLA}"


def fetch_from_rpc(method_name: str, args: dict = None):

    web4_url = f"{settings.FASTNEAR_RPC_URL}/account/{LISTS_CONTRACT}/view/{method_name}"

    try:
        response = requests.post(web4_url, json=args or {}, timeout=15)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.warning(f"web4 RPC failed, trying standard JSON-RPC: {e}")

    # Fallback to standard JSON-RPC if Web4 fails (504 bad gateway)
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
            "account_id": LISTS_CONTRACT,
            "method_name": method_name,
            "args_base64": args_base64,
            "finality": "optimistic"
        }
    }

    response = requests.post(rpc_url, json=payload, timeout=15)
    result = response.json()

    if "error" in result:
        raise Exception(f"RPC error: {result['error']}")

    # Decode result bytes to JSON 
    result_bytes = bytes(result["result"]["result"])
    return json.loads(result_bytes.decode())


class ListSyncAPI(APIView):
    """
    Sync a list from blockchain to database.

    Called by frontend after user creates a list.
    Fetches current state from RPC, creates/updates in DB.
    """

    @extend_schema(
        summary="Sync list from blockchain",
        responses={
            200: OpenApiResponse(description="List synced"),
            404: OpenApiResponse(description="List not found on chain"),
            502: OpenApiResponse(description="RPC failed"),
        }
    )
    def post(self, request, list_id: int):
        try:
            # Fetch from RPC 
            data = fetch_from_rpc("get_list", {"list_id": int(list_id)})

            if not data:
                return Response({"error": "List not found on chain"}, status=404)

            # Check if already exists
            if List.objects.filter(on_chain_id=int(list_id)).exists():
                return Response({
                    "success": True,
                    "message": "List already exists in database",
                    "on_chain_id": list_id
                })

            # Create list 
            list_obj = List.objects.create(
                id=data["id"],
                on_chain_id=data["id"],
                owner_id=data["owner"],
                name=data["name"],
                description=data.get("description", ""),
                cover_image_url=data.get("cover_image_url"),
                admin_only_registrations=data.get("admin_only_registrations", False),
                default_registration_status=data.get("default_registration_status", "Pending"),
                created_at=datetime.fromtimestamp(data["created_at"] / 1000),
                updated_at=datetime.fromtimestamp(data["updated_at"] / 1000),
            )

            # Create owner account 
            Account.objects.get_or_create(id=data["owner"])

            # Add admins 
            for admin_id in data.get("admins", []):
                admin, _ = Account.objects.get_or_create(id=admin_id)
                list_obj.admins.add(admin)

            return Response({
                "success": True,
                "message": "List synced",
                "on_chain_id": list_obj.on_chain_id
            })

        except Exception as e:
            logger.error(f"Error syncing list {list_id}: {e}")
            return Response({"error": str(e)}, status=502)


class ListRegistrationsSyncAPI(APIView):
    """
    Sync all registrations for a list.

    Called after user registers to a list.
    """

    @extend_schema(
        summary="Sync all registrations for a list",
        responses={
            200: OpenApiResponse(description="Registrations synced"),
            404: OpenApiResponse(description="List not found"),
            502: OpenApiResponse(description="RPC failed"),
        }
    )
    def post(self, request, list_id: int):
        try:
            # Ensure list exists
            try:
                list_obj = List.objects.get(on_chain_id=int(list_id))
            except List.DoesNotExist:
                # Sync list first
                list_sync = ListSyncAPI()
                resp = list_sync.post(request, list_id)
                if resp.status_code != 200:
                    return Response({"error": "List not found"}, status=404)
                list_obj = List.objects.get(on_chain_id=int(list_id))

            # Fetch registrations from RPC
            registrations = fetch_from_rpc("get_registrations_for_list", {"list_id": int(list_id)})

            if not registrations:
                registrations = []

            synced = 0
            for reg in registrations:
                # Create accounts
                Account.objects.get_or_create(id=reg["registrant_id"])
                Account.objects.get_or_create(id=reg.get("registered_by", reg["registrant_id"]))

                # Create/update registration 
                ListRegistration.objects.update_or_create(
                    list=list_obj,
                    registrant_id=reg["registrant_id"],
                    defaults={
                        "id": reg["id"],
                        "registered_by_id": reg.get("registered_by", reg["registrant_id"]),
                        "status": reg.get("status", "Pending"),
                        "submitted_at": datetime.fromtimestamp(reg["submitted_ms"] / 1000),
                        "updated_at": datetime.fromtimestamp(reg["updated_ms"] / 1000),
                        "admin_notes": reg.get("admin_notes"),
                        "registrant_notes": reg.get("registrant_notes"),
                    }
                )
                synced += 1

            return Response({
                "success": True,
                "message": f"Synced {synced} registrations",
                "synced_count": synced
            })

        except Exception as e:
            logger.error(f"Error syncing registrations for list {list_id}: {e}")
            return Response({"error": str(e)}, status=502)


class SingleRegistrationSyncAPI(APIView):
    """
    Sync a single registration.

    More efficient than syncing all when you know the registrant.
    """

    @extend_schema(
        summary="Sync single registration",
        responses={
            200: OpenApiResponse(description="Registration synced"),
            404: OpenApiResponse(description="Not found"),
            502: OpenApiResponse(description="RPC failed"),
        }
    )
    def post(self, request, list_id: int, registrant_id: str):
        try:
            # Ensure list exists
            try:
                list_obj = List.objects.get(on_chain_id=int(list_id))
            except List.DoesNotExist:
                list_sync = ListSyncAPI()
                resp = list_sync.post(request, list_id)
                if resp.status_code != 200:
                    return Response({"error": "List not found"}, status=404)
                list_obj = List.objects.get(on_chain_id=int(list_id))

            # Fetch single registration
            reg = fetch_from_rpc("get_registration", {
                "list_id": int(list_id),
                "registrant_id": registrant_id
            })

            if not reg:
                return Response({"error": "Registration not found"}, status=404)

            # Create accounts
            Account.objects.get_or_create(id=reg["registrant_id"])
            Account.objects.get_or_create(id=reg.get("registered_by", reg["registrant_id"]))

            # Create/update registration
            registration, created = ListRegistration.objects.update_or_create(
                list=list_obj,
                registrant_id=reg["registrant_id"],
                defaults={
                    "id": reg["id"],
                    "registered_by_id": reg.get("registered_by", reg["registrant_id"]),
                    "status": reg.get("status", "Pending"),
                    "submitted_at": datetime.fromtimestamp(reg["submitted_ms"] / 1000),
                    "updated_at": datetime.fromtimestamp(reg["updated_ms"] / 1000),
                    "admin_notes": reg.get("admin_notes"),
                    "registrant_notes": reg.get("registrant_notes"),
                }
            )

            return Response({
                "success": True,
                "message": "Registration synced",
                "registrant_id": registrant_id,
                "status": registration.status
            })

        except Exception as e:
            logger.error(f"Error syncing registration: {e}")
            return Response({"error": str(e)}, status=502)
