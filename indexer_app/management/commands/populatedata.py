import time
from datetime import date, datetime

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from accounts.models import Account
from activities.models import Activity
from donations.models import Donation
from lists.models import List, ListRegistration
from pots.models import (
    Pot,
    PotApplication,
    PotApplicationReview,
    PotPayout,
    PotPayoutChallenge,
    PotPayoutChallengeAdminResponse,
)
from tokens.models import Token


class Command(BaseCommand):
    help = "Pull donations data from contract & populate donations table."

    def handle(self, *args, **options):
        # lists
        LISTS_CONTRACT_ID = "lists.potlock.near"
        url = f"https://rpc.web4.near.page/account/{LISTS_CONTRACT_ID}/view/get_lists"
        lists = requests.get(url)
        if lists.status_code != 200:
            print(
                f"Request for lists data failed ({lists.status_code}) with message: {lists.text}"
            )
            return
        lists = lists.json()
        print("lists: ", lists)
        print(f"adding {len(lists)} direct lists")
        for l in lists:
            list_id = l["id"]
            owner, _ = Account.objects.get_or_create(id=l["owner"])
            list_defaults = {
                "on_chain_id": list_id,
                "owner": owner,
                "name": l["name"],
                "description": l["description"],
                "cover_image_url": l["cover_image_url"],
                "admin_only_registrations": l["admin_only_registrations"],
                "default_registration_status": l["default_registration_status"],
                "created_at": datetime.fromtimestamp(l["created_at"] / 1000),
                "updated_at": datetime.fromtimestamp(l["updated_at"] / 1000),
            }
            list, created = List.objects.update_or_create(
                on_chain_id=list_id, defaults=list_defaults
            )
            print("created list: ", list.on_chain_id, created)
            # add admins
            for admin in l["admins"]:
                admin_obj, _ = Account.objects.get_or_create(id=admin)
                list.admins.add(admin_obj)
            # get registrations in pages
            page = 0
            limit = 300
            while True:
                time.sleep(1)
                url = f"https://rpc.web4.near.page/account/{LISTS_CONTRACT_ID}/view/get_registrations_for_list"
                params = {
                    "list_id.json": list_id,
                    "from_index.json": page * limit,
                    "limit.json": limit,
                }
                registrations = requests.get(url, params=params)
                if registrations.status_code != 200:
                    print(
                        f"Request for registrations data failed ({registrations.status_code}) with message: {registrations.text}"
                    )
                    return
                registrations = registrations.json()
                print("registrations: ", registrations)
                print(f"adding {len(registrations)} registrations")
                for reg in registrations:
                    registrant, _ = Account.objects.get_or_create(
                        id=reg["registrant_id"]
                    )
                    registrar = registrant
                    if "registered_by" in reg:
                        registrar, _ = Account.objects.get_or_create(
                            id=reg["registered_by"]
                        )
                    registration_defaults = {
                        "list": list,
                        "registrant": registrant,
                        "registered_by": registrar,
                        "status": reg["status"],
                        "submitted_at": datetime.fromtimestamp(
                            reg["submitted_ms"] / 1000
                        ),
                        "updated_at": datetime.fromtimestamp(reg["updated_ms"] / 1000),
                        "registrant_notes": reg["registrant_notes"],
                        "admin_notes": reg["admin_notes"],
                        "tx_hash": None,
                    }
                    registration, created = ListRegistration.objects.update_or_create(
                        registrant=registrant,
                        list=list,
                        defaults=registration_defaults,
                    )
                    print("created registration: ", registration.id, created)
                if len(registrations) == limit:
                    page += 1
                else:
                    break
            # TODO: get upvotes (none currently so don't have to worry about it at this point)
        # direct donations
        # get direct donations in pages
        DONATE_CONTRACT_ID = "donate.potlock.near"
        page = 0
        limit = 300
        while True:
            time.sleep(1)
            url = f"https://rpc.web4.near.page/account/{DONATE_CONTRACT_ID}/view/get_donations"
            params = {"from_index.json": page * limit, "limit.json": limit}
            donations = requests.get(url, params=params)
            if donations.status_code != 200:
                print(
                    f"Request for direct donations data failed ({donations.status_code}) with message: {donations.text}"
                )
                return
            donations = donations.json()
            print(f"adding {len(donations)} direct donations")
            for donation in donations:
                donor, _ = Account.objects.get_or_create(id=donation["donor_id"])
                referrer = None
                recipient, _ = Account.objects.get_or_create(
                    id=donation["recipient_id"]
                )
                ft_id = donation["ft_id"]
                ft_acct, _ = Account.objects.get_or_create(id=ft_id)
                token_defaults = {
                    "decimals": 24,
                }
                if ft_id != "near":
                    time.sleep(1)
                    url = f"https://rpc.web4.near.page/account/{ft_id}/view/ft_metadata"
                    ft_metadata = requests.get(url)
                    if ft_metadata.status_code != 200:
                        print(
                            f"Request for ft_metadata failed ({ft_metadata.status_code}) with message: {ft_metadata.text}"
                        )
                    else:
                        ft_metadata = ft_metadata.json()
                        if "name" in ft_metadata:
                            token_defaults["name"] = ft_metadata["name"]
                        if "symbol" in ft_metadata:
                            token_defaults["symbol"] = ft_metadata["symbol"]
                        if "icon" in ft_metadata:
                            token_defaults["icon"] = ft_metadata["icon"]
                        if "decimals" in ft_metadata:
                            token_defaults["decimals"] = ft_metadata["decimals"]
                ft_token, _ = Token.objects.update_or_create(
                    id=ft_acct, defaults=token_defaults
                )
                if donation.get("referrer_id"):
                    referrer, _ = Account.objects.get_or_create(
                        id=donation["referrer_id"]
                    )

                total_amount = int(donation["total_amount"])
                protocol_fee = int(donation["protocol_fee"])
                referrer_fee = int(donation["referrer_fee"] or 0)
                net_amount = total_amount - protocol_fee - referrer_fee

                donation_defaults = {
                    "donor": donor,
                    "total_amount": donation["total_amount"],
                    "total_amount_usd": None,  # USD amounts will be added later
                    "net_amount_usd": None,
                    "net_amount": str(net_amount),
                    "token": ft_token,
                    "message": donation["message"],
                    "donated_at": datetime.fromtimestamp(
                        donation["donated_at_ms"] / 1000
                    ),
                    "matching_pool": False,
                    "recipient": recipient,
                    "protocol_fee": donation["protocol_fee"],
                    "referrer": referrer,
                    "referrer_fee": donation["referrer_fee"],
                    "tx_hash": None,
                }
                donation, created = Donation.objects.update_or_create(
                    on_chain_id=donation["id"], pot=None, defaults=donation_defaults
                )
                print("created donation: ", donation.on_chain_id, created)
                # # add donation activity
                # activity_type = (
                #     "Donate_Pot_Matching_Pool"
                #     if donation.matching_pool
                #     else "Donate_Pot_Public"
                # )
                # defaults = {
                #     "signer_id": donor.id,
                #     "receiver_id": pot_id,
                #     "timestamp": donation.donated_at,
                #     "tx_hash": None,
                # }
                # activity, _ = Activity.objects.update_or_create(
                #     type=activity_type,
                #     action_result=None,
                #     defaults=defaults,
                # )
            if len(donations) == limit:
                page += 1
            else:
                break
        # pot factory
        POTFACTORY_ID = "v1.potfactory.potlock.near"
        # pots
        near_acct, _ = Account.objects.get_or_create(id="near")
        url = f"{settings.FASTNEAR_RPC_URL}/account/{POTFACTORY_ID}/view/get_pots"
        response = requests.get(url)
        if response.status_code != 200:
            print(
                f"Request for donations data failed ({response.status_code}) with message: {response.text}"
            )
            return
        pots = response.json()
        print("pots data; ", pots)
        for pot in pots:
            # if pot["id"] != "marketing.v1.potfactory.potlock.near":
            #     continue  # TODO: REMOVE THIS
            print("sleeping for 1 second")
            time.sleep(1)
            pot_id = pot["id"]
            deployed_by = pot["deployed_by"]
            deployed_at_ms = pot["deployed_at_ms"]
            print("handling pot: ", pot_id)
            # fetch config for pot
            url = f"{settings.FASTNEAR_RPC_URL}/account/{pot_id}/view/get_config"
            response = requests.get(url)
            if response.status_code != 200:
                print(
                    f"Request for pot config failed ({response.status_code}) with message: {response.text}"
                )
                return
            config = response.json()
            print("config data; ", config)
            url = f"{settings.FASTNEAR_RPC_URL}/account/{pot_id}/view/get_contract_source_metadata"
            response = requests.get(url)
            if response.status_code != 200:
                print(
                    f"Request for pot source metadata failed ({response.status_code}) with message: {response.text}"
                )
                return
            source_metadata = response.json()
            print("source metadata; ", source_metadata)
            # add or update pot
            pot_acct, _ = Account.objects.get_or_create(id=pot_id)
            owner, _ = Account.objects.get_or_create(id=config["owner"])
            if config.get("chef"):
                chef, _ = Account.objects.get_or_create(id=config["chef"])
            pot_defaults = {
                "pot_factory_id": POTFACTORY_ID,
                "owner_id": config["owner"],
                "chef_id": config["chef"],
                "name": config["pot_name"],
                "description": config["pot_description"],
                "max_approved_applicants": config["max_projects"],
                "base_currency": config["base_currency"],
                "application_start": datetime.fromtimestamp(
                    config["application_start_ms"] / 1000
                ),
                "application_end": datetime.fromtimestamp(
                    config["application_end_ms"] / 1000
                ),
                "matching_round_start": datetime.fromtimestamp(
                    config["public_round_start_ms"] / 1000
                ),
                "matching_round_end": datetime.fromtimestamp(
                    config["public_round_end_ms"] / 1000
                ),
                "deployer_id": config["deployed_by"],
                "deployed_at": datetime.fromtimestamp(deployed_at_ms / 1000),
                "source_metadata": source_metadata,
                "registry_provider": config["registry_provider"],
                "min_matching_pool_donation_amount": config[
                    "min_matching_pool_donation_amount"
                ],
                "sybil_wrapper_provider": config["sybil_wrapper_provider"],
                "custom_sybil_checks": config["custom_sybil_checks"],
                "custom_min_threshold_score": config["custom_min_threshold_score"],
                "referral_fee_matching_pool_basis_points": config[
                    "referral_fee_matching_pool_basis_points"
                ],
                "referral_fee_public_round_basis_points": config[
                    "referral_fee_public_round_basis_points"
                ],
                "chef_fee_basis_points": config["chef_fee_basis_points"],
                "total_matching_pool": "0",
                "matching_pool_balance": "0",
                "matching_pool_donations_count": 0,
                "total_public_donations": "0",
                "public_donations_count": 0,
                "cooldown_period_ms": None,
                "cooldown_end": (
                    None
                    if not config["cooldown_end_ms"]
                    else datetime.fromtimestamp(config["cooldown_end_ms"] / 1000)
                ),
                "all_paid_out": config["all_paid_out"],
                "protocol_config_provider": config["protocol_config_provider"],
            }
            pot, created = Pot.objects.update_or_create(
                id=pot_acct, defaults=pot_defaults
            )
            print("pot created? ", created)
            print("adding admins")
            for admin in config["admins"]:
                admin_obj, _ = Account.objects.get_or_create(id=admin)
                pot.admins.add(admin_obj)
            # add activity
            activity_defaults = {
                "signer_id": owner.id,
                "receiver_id": POTFACTORY_ID,
                "timestamp": datetime.fromtimestamp(deployed_at_ms / 1000),
                "tx_hash": None,
            }
            activity, _ = Activity.objects.update_or_create(
                type="Deploy_Pot", action_result=None, defaults=activity_defaults
            )
            # get applications in pages
            page = 0
            limit = 300
            while True:
                time.sleep(1)
                url = (
                    f"https://rpc.web4.near.page/account/{pot_id}/view/get_applications"
                )
                params = {"from_index.json": page * limit, "limit.json": limit}
                applications = requests.get(url, params=params)
                if applications.status_code != 200:
                    print(
                        f"Request for applications data failed ({applications.status_code}) with message: {applications.text}"
                    )
                    return
                applications = applications.json()
                print(f"adding {len(applications)} applications")
                for appl in applications:
                    applicant, _ = Account.objects.get_or_create(id=appl["project_id"])
                    application_defaults = {
                        "applicant": applicant,
                        "pot": pot,
                        "message": appl["message"],
                        "status": appl["status"],
                        "submitted_at": datetime.fromtimestamp(
                            appl["submitted_at"] / 1000
                        ),
                        "updated_at": (
                            None
                            if not appl["updated_at"]
                            else datetime.fromtimestamp(appl["updated_at"] / 1000)
                        ),
                    }
                    application, _ = PotApplication.objects.update_or_create(
                        pot=pot, applicant=applicant, defaults=application_defaults
                    )
                    # if status != Pending, add PotApplicationReview also, default to pot owner
                    if application.status != "Pending":
                        review_defaults = {
                            "application": application,
                            "reviewer": owner,
                            "notes": appl["review_notes"],
                            "status": application.status,
                            "reviewed_at": application.updated_at,
                            "tx_hash": None,
                        }
                        review, _ = PotApplicationReview.objects.update_or_create(
                            application=application,
                            reviewer=owner,
                            defaults=review_defaults,
                        )
                if len(applications) == limit:
                    page += 1
                else:
                    break
            # get pot donations in pages
            page = 0
            limit = 300
            while True:
                time.sleep(1)
                url = f"https://rpc.web4.near.page/account/{pot_id}/view/get_donations"
                params = {"from_index.json": page * limit, "limit.json": limit}
                donations = requests.get(url, params=params)
                if donations.status_code != 200:
                    print(
                        f"Request for donations data failed ({donations.status_code}) with message: {donations.text}"
                    )
                    return
                donations = donations.json()
                print(f"adding {len(donations)} donations")
                for donation in donations:
                    donor, _ = Account.objects.get_or_create(id=donation["donor_id"])
                    project = None
                    referrer = None
                    chef = None
                    if donation.get("project_id"):
                        project, _ = Account.objects.get_or_create(
                            id=donation["project_id"]
                        )
                    if donation.get("referrer_id"):
                        referrer, _ = Account.objects.get_or_create(
                            id=donation["referrer_id"]
                        )
                    if donation.get("chef_id"):
                        chef, _ = Account.objects.get_or_create(id=donation["chef_id"])

                    # net_amount is 0 for some donations, so calculate it
                    net_amount = donation["net_amount"]
                    if net_amount == "0":
                        total_amount = int(donation["total_amount"])
                        protocol_fee = int(donation["protocol_fee"])
                        referrer_fee = int(donation["referrer_fee"] or 0)
                        chef_fee = int(donation["chef_fee"] or 0)
                        net_amount = (
                            total_amount - protocol_fee - referrer_fee - chef_fee
                        )

                    # pot donations always NEAR
                    ft_acct, _ = Account.objects.get_or_create(id="near")
                    ft_token, _ = Token.objects.get_or_create(id=ft_acct)
                    donation_defaults = {
                        "donor": donor,
                        "total_amount": donation["total_amount"],
                        "total_amount_usd": None,  # USD amounts will be added later
                        "net_amount_usd": None,
                        "net_amount": net_amount,
                        "token": ft_token,
                        "message": donation["message"],
                        "donated_at": datetime.fromtimestamp(
                            donation["donated_at"] / 1000
                        ),
                        "matching_pool": donation["matching_pool"],
                        "recipient": project,
                        "protocol_fee": donation["protocol_fee"],
                        "referrer": referrer,
                        "referrer_fee": donation["referrer_fee"],
                        "chef": chef,
                        "chef_fee": donation["chef_fee"],
                        "tx_hash": None,
                    }
                    donation, _ = Donation.objects.update_or_create(
                        on_chain_id=donation["id"], pot=pot, defaults=donation_defaults
                    )
                    print("added donation: ", donation.on_chain_id)
                    # # add donation activity
                    # activity_type = (
                    #     "Donate_Pot_Matching_Pool"
                    #     if donation.matching_pool
                    #     else "Donate_Pot_Public"
                    # )
                    # defaults = {
                    #     "signer_id": donor.id,
                    #     "receiver_id": pot_id,
                    #     "timestamp": donation.donated_at,
                    #     "tx_hash": None,
                    # }
                    # activity, _ = Activity.objects.update_or_create(
                    #     type=activity_type,
                    #     action_result=None,
                    #     defaults=defaults,
                    # )
                if len(donations) == limit:
                    page += 1
                else:
                    break
            if "payouts" in config:
                for payout in config["payouts"]:
                    paid_at = (
                        None
                        if "paid_at" not in payout
                        else datetime.fromtimestamp(payout["paid_at"] / 1000)
                    )
                    recipient, _ = Account.objects.get_or_create(
                        id=payout["project_id"]
                    )
                    near_token, _ = Token.objects.get_or_create(id=near_acct)
                    payout_defaults = {
                        "pot": pot,
                        "recipient": recipient,
                        "amount": payout["amount"],
                        "amount_paid_usd": None,
                        "token": near_token,  # pots only support native NEAR
                        "paid_at": paid_at,
                        "tx_hash": None,
                    }
                    payout, _ = PotPayout.objects.update_or_create(
                        pot=pot, recipient=recipient, defaults=payout_defaults
                    )
            # get pot challenges & admin responses
            page = 0
            limit = 300
            while True:
                time.sleep(1)
                url = f"https://rpc.web4.near.page/account/{pot_id}/view/get_payouts_challenges"
                params = {"from_index.json": page * limit, "limit.json": limit}
                challenges = requests.get(url, params=params)
                if challenges.status_code != 200:
                    print(
                        f"Request for challenges data failed ({challenges.status_code}) with message: {challenges.text}"
                    )
                    return
                challenges = challenges.json()
                print(f"adding {len(challenges)} challenges")
                for c in challenges:
                    challenger, _ = Account.objects.get_or_create(id=c["challenger_id"])
                    challenge_defaults = {
                        "challenger": challenger,
                        "pot": pot,
                        "message": c["reason"],
                        "created_at": datetime.fromtimestamp(c["created_at"] / 1000),
                    }
                    challenge, _ = PotPayoutChallenge.objects.update_or_create(
                        pot=pot, challenger=challenger, defaults=challenge_defaults
                    )
                    # if status != Pending, add PotApplicationReview also, default to pot owner
                    if c["admin_notes"] or c["resolved"]:
                        response_defaults = {
                            "challenger": challenger,
                            "pot": pot,
                            "admin": owner,  # don't actually know who did it, just using owner for this backfilling
                            "created_at": datetime.fromtimestamp(
                                c["created_at"] / 1000
                            ),  # not exactly correct but we don't know currently
                            "message": c["admin_notes"],
                            "resolved": c["resolved"],
                        }
                        review, _ = (
                            PotPayoutChallengeAdminResponse.objects.update_or_create(
                                challenger=challenger,
                                pot=pot,
                                defaults=response_defaults,
                            )
                        )
                if len(challenges) == limit:
                    page += 1
                else:
                    break
