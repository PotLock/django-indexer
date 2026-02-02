"""
Sync endpoints - fetch data from blockchain RPC and store in database.

Called by frontend after user creates/updates a list/registration or pot/donation/application.
Replaces the 24/7 indexer - now we fetch on-demand when user acts.

Endpoints:
    Lists:
        POST /api/v1/lists/{list_id}/sync - Sync single list
        POST /api/v1/lists/{list_id}/registrations/sync - Sync all registrations
        POST /api/v1/lists/{list_id}/registrations/{registrant_id}/sync - Sync single registration

    Pots:
        POST /api/v1/pots/{pot_id}/sync - Sync pot config from chain
        POST /api/v1/pots/{pot_id}/donations/sync - Sync all donations for a pot
        POST /api/v1/pots/{pot_id}/applications/sync - Sync all applications for a pot
        POST /api/v1/pots/{pot_id}/payouts/sync - Sync all payouts for a pot
        POST /api/v1/pots/{pot_id}/challenges/sync - Sync payout challenges for a pot

    Direct Donations:
        POST /api/v1/donations/sync - Sync direct donations (with optional ?donor_id or ?recipient_id filter)

    Accounts:
        POST /api/v1/accounts/{account_id}/sync - Sync account profile and recalculate stats
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
from donations.models import Donation
from lists.models import List, ListRegistration
from pots.models import Pot, PotApplication, PotApplicationReview, PotFactory, PotPayout, PotPayoutChallenge, PotPayoutChallengeAdminResponse
from tokens.models import Token

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
    heavy_methods = ["get_registrations_for_list", "get_donations", "get_applications", "get_payouts_challenges"]
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
            if List.objects.filter(on_chain_id=int(list_id)).exists():
                return Response({
                    "success": True,
                    "message": "List already exists in database",
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

            # Fetch all registrations and filter (contract doesn't have single-registration lookup)
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


class PotSyncAPI(APIView):
    """
    Sync a pot (campaign) from blockchain to database.

    Called by frontend after user deploys or updates a pot.
    Fetches current config from RPC via get_config, creates/updates in DB.
    """

    @extend_schema(
        summary="Sync pot config from blockchain",
        responses={
            200: OpenApiResponse(description="Pot synced"),
            404: OpenApiResponse(description="Pot not found on chain"),
            502: OpenApiResponse(description="RPC failed"),
        }
    )
    def post(self, request, pot_id: str):
        try:
            # Fetch pot config from RPC (each pot is its own contract)
            config = fetch_from_rpc("get_config", contract_id=pot_id)

            if not config:
                return Response({"error": "Pot not found on chain"}, status=404)

            # Upsert accounts
            Account.objects.get_or_create(id=pot_id)
            owner, _ = Account.objects.get_or_create(id=config["owner"])

            chef = None
            if config.get("chef"):
                chef, _ = Account.objects.get_or_create(id=config["chef"])

            # Derive pot factory from pot account ID (e.g. mypot.v1.potfactory.potlock.near -> v1.potfactory.potlock.near)
            factory_id = ".".join(pot_id.split(".")[1:]) if "." in pot_id else pot_id
            factory_account, _ = Account.objects.get_or_create(id=factory_id)

            # Check if pot already exists
            existing_pot = Pot.objects.filter(account_id=pot_id).first()

            if existing_pot:
                # Update existing pot config (same as Pot.update_configs)
                existing_pot.owner = owner
                existing_pot.chef = chef
                existing_pot.name = config.get("pot_name", "")
                existing_pot.description = config.get("pot_description", "")
                existing_pot.max_approved_applicants = config.get("max_projects", 0)
                existing_pot.base_currency = config.get("base_currency", "near")
                existing_pot.application_start = datetime.fromtimestamp(config["application_start_ms"] / 1000)
                existing_pot.application_end = datetime.fromtimestamp(config["application_end_ms"] / 1000)
                existing_pot.matching_round_start = datetime.fromtimestamp(config["public_round_start_ms"] / 1000)
                existing_pot.matching_round_end = datetime.fromtimestamp(config["public_round_end_ms"] / 1000)
                existing_pot.registry_provider = config.get("registry_provider")
                existing_pot.min_matching_pool_donation_amount = config.get("min_matching_pool_donation_amount", "0")
                existing_pot.sybil_wrapper_provider = config.get("sybil_wrapper_provider")
                existing_pot.custom_sybil_checks = config.get("custom_sybil_checks")
                existing_pot.custom_min_threshold_score = config.get("custom_min_threshold_score")
                existing_pot.referral_fee_matching_pool_basis_points = config["referral_fee_matching_pool_basis_points"]
                existing_pot.referral_fee_public_round_basis_points = config["referral_fee_public_round_basis_points"]
                existing_pot.chef_fee_basis_points = config["chef_fee_basis_points"]
                if config.get("cooldown_end_ms"):
                    existing_pot.cooldown_end = datetime.fromtimestamp(config["cooldown_end_ms"] / 1000)
                existing_pot.all_paid_out = config.get("all_paid_out", False)
                existing_pot.protocol_config_provider = config.get("protocol_config_provider")
                existing_pot.save()

                # Update admins
                existing_pot.admins.clear()
                for admin_id in config.get("admins", []):
                    admin, _ = Account.objects.get_or_create(id=admin_id)
                    existing_pot.admins.add(admin)

                return Response({
                    "success": True,
                    "message": "Pot config updated",
                    "pot_id": pot_id
                })
            else:
                # Ensure pot factory exists
                if not PotFactory.objects.filter(account_id=factory_id).exists():
                    return Response({
                        "error": f"Pot factory {factory_id} not found in database. Sync the factory first."
                    }, status=404)

                # Create new pot
                pot = Pot.objects.create(
                    account_id=pot_id,
                    pot_factory_id=factory_id,
                    deployer=owner,  # best guess when syncing; deployer not in config
                    deployed_at=datetime.now(),
                    source_metadata=config.get("source_metadata", {}),
                    owner=owner,
                    chef=chef,
                    name=config.get("pot_name", ""),
                    description=config.get("pot_description", ""),
                    max_approved_applicants=config.get("max_projects", 0),
                    base_currency=config.get("base_currency", "near"),
                    application_start=datetime.fromtimestamp(config["application_start_ms"] / 1000),
                    application_end=datetime.fromtimestamp(config["application_end_ms"] / 1000),
                    matching_round_start=datetime.fromtimestamp(config["public_round_start_ms"] / 1000),
                    matching_round_end=datetime.fromtimestamp(config["public_round_end_ms"] / 1000),
                    registry_provider=config.get("registry_provider"),
                    min_matching_pool_donation_amount=config.get("min_matching_pool_donation_amount", "0"),
                    sybil_wrapper_provider=config.get("sybil_wrapper_provider"),
                    custom_sybil_checks=config.get("custom_sybil_checks"),
                    custom_min_threshold_score=config.get("custom_min_threshold_score"),
                    referral_fee_matching_pool_basis_points=config["referral_fee_matching_pool_basis_points"],
                    referral_fee_public_round_basis_points=config["referral_fee_public_round_basis_points"],
                    chef_fee_basis_points=config["chef_fee_basis_points"],
                    total_matching_pool=config.get("matching_pool_balance", "0"),
                    total_matching_pool_usd=None,
                    matching_pool_balance=config.get("matching_pool_balance", "0"),
                    matching_pool_donations_count=config.get("matching_pool_donations_count", 0),
                    total_public_donations=config.get("total_public_donations", "0"),
                    public_donations_count=config.get("public_donations_count", 0),
                    cooldown_period_ms=config.get("cooldown_period_ms"),  # This is duration, not timestamp
                    all_paid_out=config.get("all_paid_out", False),
                    protocol_config_provider=config.get("protocol_config_provider"),
                )

                # Add admins
                for admin_id in config.get("admins", []):
                    admin, _ = Account.objects.get_or_create(id=admin_id)
                    pot.admins.add(admin)

                return Response({
                    "success": True,
                    "message": "Pot created",
                    "pot_id": pot_id
                })

        except Exception as e:
            logger.error(f"Error syncing pot {pot_id}: {e}")
            return Response({"error": str(e)}, status=502)


class PotDonationsSyncAPI(APIView):
    """
    Sync all donations for a pot from blockchain.

    Called by frontend after a user donates to a pot.
    Fetches donations via get_donations RPC call.
    """

    @extend_schema(
        summary="Sync all donations for a pot",
        responses={
            200: OpenApiResponse(description="Donations synced"),
            404: OpenApiResponse(description="Pot not found"),
            502: OpenApiResponse(description="RPC failed"),
        }
    )
    def post(self, request, pot_id: str):
        try:
            # Ensure pot exists in DB
            pot = Pot.objects.filter(account_id=pot_id).first()
            if not pot:
                # Try to sync pot first
                pot_sync = PotSyncAPI()
                resp = pot_sync.post(request, pot_id)
                if resp.status_code != 200:
                    return Response({"error": "Pot not found"}, status=404)
                pot = Pot.objects.get(account_id=pot_id)

            # Fetch donations from RPC (use longer timeout for pots with many donations)
            donations = fetch_from_rpc("get_donations", contract_id=pot_id, timeout=120)

            if not donations:
                donations = []

            # Get or create NEAR token (Token uses Account as primary key)
            near_account, _ = Account.objects.get_or_create(id="near")
            near_token, _ = Token.objects.get_or_create(
                account=near_account,
                defaults={"name": "NEAR", "symbol": "NEAR", "decimals": 24}
            )

            synced = 0
            for don in donations:
                # Upsert accounts
                donor, _ = Account.objects.get_or_create(id=don["donor_id"])

                recipient = None
                if don.get("project_id"):
                    recipient, _ = Account.objects.get_or_create(id=don["project_id"])
                elif don.get("recipient_id"):
                    recipient, _ = Account.objects.get_or_create(id=don["recipient_id"])

                referrer = None
                if don.get("referrer_id"):
                    referrer, _ = Account.objects.get_or_create(id=don["referrer_id"])

                chef = None
                if don.get("chef_id"):
                    chef, _ = Account.objects.get_or_create(id=don["chef_id"])

                # Calculate net_amount if not present
                total_amount = don.get("total_amount", "0")
                net_amount = don.get("net_amount")
                if not net_amount or net_amount == "0":
                    protocol_fee = int(don.get("protocol_fee", "0"))
                    referrer_fee = int(don.get("referrer_fee") or "0")
                    chef_fee = int(don.get("chef_fee") or "0")
                    net_amount = str(int(total_amount) - protocol_fee - referrer_fee - chef_fee)

                # Determine token (Token uses Account as primary key)
                ft_id = don.get("ft_id", "near")
                if ft_id == "near":
                    token = near_token
                else:
                    ft_account, _ = Account.objects.get_or_create(id=ft_id)
                    token, _ = Token.objects.get_or_create(
                        account=ft_account,
                        defaults={"name": ft_id, "decimals": 24}
                    )

                donated_at = datetime.fromtimestamp(
                    (don.get("donated_at") or don.get("donated_at_ms", 0)) / 1000
                )

                Donation.objects.update_or_create(
                    on_chain_id=don["id"],
                    pot=pot,
                    defaults={
                        "donor": donor,
                        "total_amount": total_amount,
                        "net_amount": net_amount,
                        "token": token,
                        "matching_pool": don.get("matching_pool", False),
                        "message": don.get("message"),
                        "donated_at": donated_at,
                        "recipient": recipient,
                        "protocol_fee": don.get("protocol_fee", "0"),
                        "referrer": referrer,
                        "referrer_fee": don.get("referrer_fee"),
                        "chef": chef,
                        "chef_fee": don.get("chef_fee"),
                    }
                )
                synced += 1

            return Response({
                "success": True,
                "message": f"Synced {synced} donations",
                "synced_count": synced
            })

        except Exception as e:
            logger.error(f"Error syncing donations for pot {pot_id}: {e}")
            return Response({"error": str(e)}, status=502)


class PotApplicationsSyncAPI(APIView):
    """
    Sync all applications for a pot from blockchain.

    Called by frontend after a user applies to a pot or an application is reviewed.
    Fetches applications via get_applications RPC call.
    """

    @extend_schema(
        summary="Sync all applications for a pot",
        responses={
            200: OpenApiResponse(description="Applications synced"),
            404: OpenApiResponse(description="Pot not found"),
            502: OpenApiResponse(description="RPC failed"),
        }
    )
    def post(self, request, pot_id: str):
        try:
            # Ensure pot exists
            pot = Pot.objects.filter(account_id=pot_id).first()
            if not pot:
                pot_sync = PotSyncAPI()
                resp = pot_sync.post(request, pot_id)
                if resp.status_code != 200:
                    return Response({"error": "Pot not found"}, status=404)
                pot = Pot.objects.get(account_id=pot_id)

            # Fetch applications from RPC (use longer timeout for pots with many applications)
            applications = fetch_from_rpc("get_applications", contract_id=pot_id, timeout=120)

            if not applications:
                applications = []

            synced = 0
            for app in applications:
                # Upsert applicant account
                applicant, _ = Account.objects.get_or_create(id=app["project_id"])

                submitted_at = datetime.fromtimestamp(app["submitted_at"] / 1000)
                updated_at = datetime.fromtimestamp(app["updated_at"] / 1000) if app.get("updated_at") else submitted_at

                application, created = PotApplication.objects.update_or_create(
                    pot=pot,
                    applicant=applicant,
                    defaults={
                        "message": app.get("message", ""),
                        "status": app.get("status", "Pending"),
                        "submitted_at": submitted_at,
                        "updated_at": updated_at,
                    }
                )

                # Sync review notes if present
                if app.get("review_notes") and app.get("status") != "Pending":
                    reviewer_id = app.get("reviewed_by", pot.owner_id)
                    reviewer, _ = Account.objects.get_or_create(id=reviewer_id)
                    PotApplicationReview.objects.update_or_create(
                        application=application,
                        reviewer=reviewer,
                        reviewed_at=updated_at,
                        defaults={
                            "notes": app.get("review_notes"),
                            "status": app["status"],
                        }
                    )

                synced += 1

            return Response({
                "success": True,
                "message": f"Synced {synced} applications",
                "synced_count": synced
            })

        except Exception as e:
            logger.error(f"Error syncing applications for pot {pot_id}: {e}")
            return Response({"error": str(e)}, status=502)


class PotPayoutsSyncAPI(APIView):
    """
    Sync all payouts for a pot from blockchain.

    Called by frontend after chef sets payouts or payouts are transferred.
    Payouts are included in the get_config response.
    """

    @extend_schema(
        summary="Sync all payouts for a pot",
        responses={
            200: OpenApiResponse(description="Payouts synced"),
            404: OpenApiResponse(description="Pot not found"),
            502: OpenApiResponse(description="RPC failed"),
        }
    )
    def post(self, request, pot_id: str):
        try:
            # Ensure pot exists
            pot = Pot.objects.filter(account_id=pot_id).first()
            if not pot:
                pot_sync = PotSyncAPI()
                resp = pot_sync.post(request, pot_id)
                if resp.status_code != 200:
                    return Response({"error": "Pot not found"}, status=404)
                pot = Pot.objects.get(account_id=pot_id)

            # Fetch config from RPC (payouts are included in config)
            config = fetch_from_rpc("get_config", contract_id=pot_id)

            if not config:
                return Response({"error": "Pot config not found on chain"}, status=404)

            # Get payouts from config
            payouts = config.get("payouts", [])

            if not payouts:
                return Response({
                    "success": True,
                    "message": "No payouts set yet",
                    "synced_count": 0
                })

            # Get or create NEAR token (pots only support native NEAR)
            near_account, _ = Account.objects.get_or_create(id="near")
            near_token, _ = Token.objects.get_or_create(
                account=near_account,
                defaults={"name": "NEAR", "symbol": "NEAR", "decimals": 24}
            )

            # Also update pot's cooldown_end and all_paid_out from config
            if config.get("cooldown_end_ms"):
                pot.cooldown_end = datetime.fromtimestamp(config["cooldown_end_ms"] / 1000)
            pot.all_paid_out = config.get("all_paid_out", False)
            pot.save()

            synced = 0
            for payout in payouts:
                # Upsert recipient account
                recipient, _ = Account.objects.get_or_create(id=payout["project_id"])

                # Parse paid_at if present
                paid_at = None
                if payout.get("paid_at"):
                    paid_at = datetime.fromtimestamp(payout["paid_at"] / 1000)

                PotPayout.objects.update_or_create(
                    pot=pot,
                    recipient=recipient,
                    defaults={
                        "amount": payout["amount"],
                        "token": near_token,
                        "paid_at": paid_at,
                    }
                )
                synced += 1

            return Response({
                "success": True,
                "message": f"Synced {synced} payouts",
                "synced_count": synced,
                "all_paid_out": pot.all_paid_out
            })

        except Exception as e:
            logger.error(f"Error syncing payouts for pot {pot_id}: {e}")
            return Response({"error": str(e)}, status=502)


class DirectDonationsSyncAPI(APIView):
    """
    Sync direct donations from the donate contract.

    Called by frontend after a user makes a direct donation (not to a pot).
    Fetches donations via get_donations RPC call on donate.{potlock_tla}.

    Supports optional filtering by donor_id or recipient_id query params.
    """

    @extend_schema(
        summary="Sync direct donations from blockchain",
        responses={
            200: OpenApiResponse(description="Donations synced"),
            502: OpenApiResponse(description="RPC failed"),
        }
    )
    def post(self, request):
        try:
            DONATE_CONTRACT = f"donate.{settings.POTLOCK_TLA}"

            # Optional filters
            donor_id = request.query_params.get("donor_id")
            recipient_id = request.query_params.get("recipient_id")

            # Fetch all donations from donate contract (paginated)
            all_donations = []
            from_index = 0
            limit = 300

            while True:
                donations = fetch_from_rpc(
                    "get_donations",
                    {"from_index": from_index, "limit": limit},
                    contract_id=DONATE_CONTRACT,
                    timeout=120
                )

                if not donations:
                    break

                all_donations.extend(donations)

                if len(donations) < limit:
                    break
                from_index += limit

            # Apply filters if provided
            if donor_id:
                all_donations = [d for d in all_donations if d.get("donor_id") == donor_id]
            if recipient_id:
                all_donations = [d for d in all_donations if d.get("recipient_id") == recipient_id]

            # Get or create NEAR token
            near_account, _ = Account.objects.get_or_create(id="near")
            near_token, _ = Token.objects.get_or_create(
                account=near_account,
                defaults={"name": "NEAR", "symbol": "NEAR", "decimals": 24}
            )

            synced = 0
            for don in all_donations:
                # Upsert accounts
                donor, _ = Account.objects.get_or_create(id=don["donor_id"])
                recipient, _ = Account.objects.get_or_create(id=don["recipient_id"])

                referrer = None
                if don.get("referrer_id"):
                    referrer, _ = Account.objects.get_or_create(id=don["referrer_id"])

                # Calculate net_amount
                total_amount = int(don["total_amount"])
                protocol_fee = int(don.get("protocol_fee", "0"))
                referrer_fee = int(don.get("referrer_fee") or "0")
                net_amount = str(total_amount - protocol_fee - referrer_fee)

                # Determine token
                ft_id = don.get("ft_id", "near")
                if ft_id == "near":
                    token = near_token
                else:
                    ft_account, _ = Account.objects.get_or_create(id=ft_id)
                    token, _ = Token.objects.get_or_create(
                        account=ft_account,
                        defaults={"name": ft_id, "decimals": 24}
                    )

                donated_at = datetime.fromtimestamp(don["donated_at_ms"] / 1000)

                # Direct donations have pot=None
                Donation.objects.update_or_create(
                    on_chain_id=don["id"],
                    pot=None,
                    defaults={
                        "donor": donor,
                        "total_amount": don["total_amount"],
                        "net_amount": net_amount,
                        "token": token,
                        "message": don.get("message"),
                        "donated_at": donated_at,
                        "matching_pool": False,
                        "recipient": recipient,
                        "protocol_fee": don.get("protocol_fee", "0"),
                        "referrer": referrer,
                        "referrer_fee": don.get("referrer_fee"),
                    }
                )
                synced += 1

            return Response({
                "success": True,
                "message": f"Synced {synced} direct donations",
                "synced_count": synced
            })

        except Exception as e:
            logger.error(f"Error syncing direct donations: {e}")
            return Response({"error": str(e)}, status=502)


class PotPayoutChallengesSyncAPI(APIView):
    """
    Sync payout challenges for a pot from blockchain.

    Called by frontend after a user challenges payouts.
    Fetches challenges via get_payouts_challenges RPC call.
    """

    @extend_schema(
        summary="Sync payout challenges for a pot",
        responses={
            200: OpenApiResponse(description="Challenges synced"),
            404: OpenApiResponse(description="Pot not found"),
            502: OpenApiResponse(description="RPC failed"),
        }
    )
    def post(self, request, pot_id: str):
        try:
            # Ensure pot exists
            pot = Pot.objects.filter(account_id=pot_id).first()
            if not pot:
                pot_sync = PotSyncAPI()
                resp = pot_sync.post(request, pot_id)
                if resp.status_code != 200:
                    return Response({"error": "Pot not found"}, status=404)
                pot = Pot.objects.get(account_id=pot_id)

            # Fetch challenges from RPC (paginated)
            all_challenges = []
            from_index = 0
            limit = 300

            while True:
                challenges = fetch_from_rpc(
                    "get_payouts_challenges",
                    {"from_index": from_index, "limit": limit},
                    contract_id=pot_id,
                    timeout=120
                )

                if not challenges:
                    break

                all_challenges.extend(challenges)

                if len(challenges) < limit:
                    break
                from_index += limit

            synced = 0
            for c in all_challenges:
                challenger, _ = Account.objects.get_or_create(id=c["challenger_id"])

                created_at = datetime.fromtimestamp(c["created_at"] / 1000)

                challenge, _ = PotPayoutChallenge.objects.update_or_create(
                    pot=pot,
                    challenger=challenger,
                    defaults={
                        "message": c.get("reason", ""),
                        "created_at": created_at,
                    }
                )

                # If there's an admin response, create it
                if c.get("admin_notes") or c.get("resolved"):
                    # Use pot owner as admin (we don't know the actual admin from RPC)
                    PotPayoutChallengeAdminResponse.objects.update_or_create(
                        challenger=challenger,
                        pot=pot,
                        defaults={
                            "admin": pot.owner,
                            "created_at": created_at,
                            "message": c.get("admin_notes", ""),
                            "resolved": c.get("resolved", False),
                        }
                    )

                synced += 1

            return Response({
                "success": True,
                "message": f"Synced {synced} payout challenges",
                "synced_count": synced
            })

        except Exception as e:
            logger.error(f"Error syncing payout challenges for pot {pot_id}: {e}")
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
                    contract_id="social.near"
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
