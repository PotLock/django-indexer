"""
Sync endpoints - fetch data from blockchain RPC and store in database.

Called by frontend after user creates/updates a list/registration or account profile.
Replaces the 24/7 indexer - now we fetch on-demand when user acts.

Endpoints:
    Lists:
        POST /api/v1/lists/{list_id}/sync - Sync single list
        POST /api/v1/lists/{list_id}/registrations/sync - Sync all registrations
        POST /api/v1/lists/{list_id}/registrations/{registrant_id}/sync - Sync single registration

    Accounts:
        POST /api/v1/accounts/{account_id}/sync - Sync account profile and recalculate stats
"""
import base64
import json
import logging
from datetime import datetime

import requests
from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Account
from donations.models import Donation
from lists.models import List, ListRegistration

logger = logging.getLogger(__name__)

LISTS_CONTRACT = f"lists.{settings.POTLOCK_TLA}"


def fetch_from_rpc(method_name: str, args: dict = None, contract_id: str = None, timeout: int = 60):
    """
    Fetch data from NEAR RPC with multiple fallbacks and retry logic.

    Order of attempts:
    1. Web4 RPC (most efficient)
    2. FastNear free RPC
    3. Official NEAR RPC (most reliable but rate-limited)
    """
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    account_id = contract_id or LISTS_CONTRACT

    # Create session with retry logic
    session = requests.Session()
    retries = Retry(total=2, backoff_factor=0.5, status_forcelist=[502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))

    # Try Web4 RPC first (skip for heavy methods that often fail)
    heavy_methods = ["get_registrations_for_list"]
    if method_name not in heavy_methods:
        web4_url = f"{settings.FASTNEAR_RPC_URL}/account/{account_id}/view/{method_name}"
        try:
            response = session.post(web4_url, json=args or {}, timeout=timeout)
            if response.status_code == 200:
                return response.json()
            logger.warning(f"web4 RPC returned status {response.status_code}")
        except Exception as e:
            logger.warning(f"web4 RPC failed: {e}")

    # RPC endpoints to try in order
    rpc_endpoints = [
        "https://free.rpc.fastnear.com" if settings.ENVIRONMENT != "testnet" else "https://test.rpc.fastnear.com",
        "https://rpc.mainnet.near.org" if settings.ENVIRONMENT != "testnet" else "https://rpc.testnet.near.org",
    ]

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
            "finality": "optimistic"
        }
    }

    last_error = None
    for rpc_url in rpc_endpoints:
        try:
            logger.info(f"Trying RPC: {rpc_url} for {method_name}")
            response = session.post(rpc_url, json=payload, timeout=timeout)
            result = response.json()

            if "error" in result:
                logger.warning(f"RPC error from {rpc_url}: {result['error']}")
                last_error = result["error"]
                continue

            if "error" in result.get("result", {}):
                logger.warning(f"Contract error from {rpc_url}: {result['result']['error']}")
                last_error = result["result"]["error"]
                continue

            # Decode result bytes to JSON
            if "result" not in result.get("result", {}):
                return None
            result_bytes = bytes(result["result"]["result"])
            return json.loads(result_bytes.decode())

        except requests.exceptions.Timeout:
            logger.warning(f"RPC {rpc_url} timed out after {timeout}s")
            last_error = f"Timeout after {timeout}s"
        except Exception as e:
            logger.warning(f"RPC {rpc_url} failed: {e}")
            last_error = str(e)

    raise Exception(f"All RPC endpoints failed. Last error: {last_error}")


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
            existing_list = List.objects.filter(on_chain_id=int(list_id)).first()

            if existing_list:
                # Update existing list
                existing_list.name = data["name"]
                existing_list.description = data.get("description", "")
                existing_list.cover_image_url = data.get("cover_image_url")
                existing_list.admin_only_registrations = data.get("admin_only_registrations", False)
                existing_list.default_registration_status = data.get("default_registration_status", "Pending")
                existing_list.updated_at = datetime.fromtimestamp(data["updated_at"] / 1000)
                existing_list.save()

                # Update admins
                existing_list.admins.clear()
                for admin_id in data.get("admins", []):
                    admin, _ = Account.objects.get_or_create(id=admin_id)
                    existing_list.admins.add(admin)

                return Response({
                    "success": True,
                    "message": "List updated",
                    "on_chain_id": list_id
                })

            # Create list (on_chain_id is the blockchain ID, id is auto-generated)
            list_obj = List.objects.create(
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
                "message": "List created",
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

            # Fetch registrations from RPC (use longer timeout for large lists)
            registrations = fetch_from_rpc("get_registrations_for_list", {"list_id": int(list_id)}, timeout=120)

            if not registrations:
                registrations = []

            synced = 0
            for reg in registrations:
                # Create accounts
                Account.objects.get_or_create(id=reg["registrant_id"])
                Account.objects.get_or_create(id=reg.get("registered_by", reg["registrant_id"]))

                # Create/update registration (id is AutoField, use list+registrant as unique key)
                ListRegistration.objects.update_or_create(
                    list=list_obj,
                    registrant_id=reg["registrant_id"],
                    defaults={
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

            # Fetch all registrations and filter (contract doesn't have single-registration lookup by registrant_id)
            registrations = fetch_from_rpc("get_registrations_for_list", {"list_id": int(list_id)}, timeout=120)

            if not registrations:
                return Response({"error": "No registrations found for list"}, status=404)

            # Find the specific registration
            reg = next((r for r in registrations if r.get("registrant_id") == registrant_id), None)

            if not reg:
                return Response({"error": "Registration not found"}, status=404)

            # Create accounts
            Account.objects.get_or_create(id=reg["registrant_id"])
            Account.objects.get_or_create(id=reg.get("registered_by", reg["registrant_id"]))

            # Create/update registration (id is AutoField, use list+registrant as unique key)
            registration, created = ListRegistration.objects.update_or_create(
                list=list_obj,
                registrant_id=reg["registrant_id"],
                defaults={
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


class AccountSyncAPI(APIView):
    """
    Sync account data and recalculate donation stats.

    Called by frontend after actions that affect an account's totals.
    Fetches NEAR Social profile and recalculates donation totals from DB.
    """

    @extend_schema(
        summary="Sync account and recalculate stats",
        responses={
            200: OpenApiResponse(description="Account synced"),
            502: OpenApiResponse(description="RPC failed"),
        }
    )
    def post(self, request, account_id: str):
        from django.db.models import Sum, Count

        try:
            account, created = Account.objects.get_or_create(id=account_id)

            # Fetch NEAR Social profile
            try:
                profile_data = fetch_from_rpc(
                    "get",
                    {"keys": [f"{account_id}/profile/**"]},
                    contract_id="social.near" if settings.ENVIRONMENT != "testnet" else "v1.social08.testnet"
                )
                if profile_data and account_id in profile_data:
                    account.near_social_profile_data = profile_data[account_id].get("profile", {})
            except Exception as e:
                logger.warning(f"Failed to fetch social profile for {account_id}: {e}")

            # Recalculate donation totals from existing DB records
            donations_received = Donation.objects.filter(recipient_id=account_id).aggregate(
                total_usd=Sum('total_amount_usd'),
                count=Count('id')
            )
            donations_sent = Donation.objects.filter(donor_id=account_id).aggregate(
                total_usd=Sum('total_amount_usd'),
                count=Count('id')
            )

            account.total_donations_in_usd = donations_received['total_usd'] or 0
            account.total_donations_out_usd = donations_sent['total_usd'] or 0
            account.donors_count = Donation.objects.filter(
                recipient_id=account_id
            ).values('donor').distinct().count()

            account.save()

            return Response({
                "success": True,
                "message": "Account synced",
                "account_id": account_id,
                "created": created,
                "total_donations_in_usd": str(account.total_donations_in_usd),
                "total_donations_out_usd": str(account.total_donations_out_usd),
                "donors_count": account.donors_count
            })

        except Exception as e:
            logger.error(f"Error syncing account {account_id}: {e}")
            return Response({"error": str(e)}, status=502)
