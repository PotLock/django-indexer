import base64
import json
from datetime import datetime
from math import log

import requests
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.cache import cache
from django.forms.models import model_to_dict
from django.utils import timezone
from near_lake_framework.near_primitives import ExecutionOutcome, Receipt

from accounts.models import Account
from activities.models import Activity
from donations.models import Donation
from indexer_app.models import BlockHeight
from lists.models import List, ListRegistration, ListUpvote
from nadabot.models import BlackList, Group, NadabotRegistry, Provider, Stamp
from pots.models import (
    Pot,
    PotApplication,
    PotApplicationReview,
    PotFactory,
    PotPayout,
    PotPayoutChallenge,
    PotPayoutChallengeAdminResponse,
)
from tokens.models import Token

from .logging import logger

# GECKO_URL = "https://api.coingecko.com/api/v3"  # TODO: move to settings


async def handle_social_profile_update(args_dict, receiver_id, signer_id):
    logger.info(f"handling social profile update for {signer_id}")
    if (
        "data" in args_dict
        and signer_id in args_dict["data"]
        and "profile" in args_dict["data"][signer_id]
    ):
        try:
            # only proceed if this account already exists in db
            account = await Account.objects.filter(id=signer_id).afirst()
            logger.info(f"account: {account}")
            if account:
                logger.info(f"updating social profile for {signer_id}")
                await account.fetch_near_social_profile_data_async()
                # account.fetch_near_social_profile_data()
        except Exception as e:
            logger.error(f"Error in handle_social_profile_update: {e}")


async def handle_new_nadabot_registry(
    data: dict, receiverId: str, created_at: datetime
):
    logger.info(f"nadabot registry init... {data}")

    try:
        registry, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, id=receiverId)
        owner, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, id=data["owner"])
        nadabot_registry, created = await NadabotRegistry.objects.aupdate_or_create(
            account=registry,
            owner=owner,
            created_at=created_at,
            updated_at=created_at,
            source_metadata=data.get("source_metadata"),
        )

        if data.get("admins"):
            for admin_id in data["admins"]:
                admin, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, id=admin_id)
                await nadabot_registry.admins.aadd(admin)
    except Exception as e:
        logger.error(f"Error in registry initiialization: {e}")


async def handle_registry_blacklist_action(
    data: dict, receiverId: str, created_at: datetime
):
    logger.info(f"Registry blacklist action....... {data}")

    try:
        registry, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, id=receiverId)
        bulk_obj = []
        for acct in data["accounts"]:
            account, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, id=acct)
            bulk_obj.append(
                {
                    "registry": registry,
                    "account": account,
                    "reason": data.get("reason"),
                    "date_blacklisted": created_at,
                }
            )
            await BlackList.objects.abulk_create(
                objs=[BlackList(**data) for data in bulk_obj], ignore_conflicts=True
            )
    except Exception as e:
        logger.error(f"Error in adding acct to blacklist: {e}")


async def handle_registry_unblacklist_action(
    data: dict, receiverId: str, created_at: datetime
):
    logger.info(f"Registry remove blacklisted accts....... {data}")

    try:
        registry, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, id=receiverId)
        entries = BlackList.objects.filter(account__in=data["accounts"])
        await entries.adelete()
    except Exception as e:
        logger.error(f"Error in removing acct from blacklist: {e}")


async def handle_new_pot(
    data: dict,
    receiver_id: str,
    signer_id: str,
    predecessorId: str,
    receiptId: str,
    created_at: datetime,
):
    try:

        logger.info("new pot deployment process... upsert accounts,")

        # Upsert accounts
        owner_id = (
            data.get("owner") or signer_id
        )  # owner is optional; if not provided, owner will be transaction signer (this logic is implemented by Pot contract's "new" method)
        owner, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, id=owner_id)
        signer, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, id=signer_id)
        receiver, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, id=receiver_id)

        # check if pot exists
        pot = await Pot.objects.filter(account=receiver).afirst()
        if pot:
            logger.info("Pot already exists, update using api call")
            pot_config_update = sync_to_async(pot.update_configs)
            await pot_config_update()
            return
            

        logger.info("upsert chef")
        if data.get("chef"):
            chef, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, id=data["chef"])

        # Create Pot object
        logger.info(f"creating pot with owner {owner_id}....")
        pot_defaults = {
            "pot_factory_account": predecessorId,
            "deployer": signer,
            "deployed_at": created_at,
            "source_metadata": data["source_metadata"],
            "owner_id": owner_id,
            "chef_id": data.get("chef"),
            "name": data["pot_name"],
            "description": data["pot_description"],
            "max_approved_applicants": data["max_projects"],
            "base_currency": "near",
            "application_start": datetime.fromtimestamp(
                data["application_start_ms"] / 1000
            ),
            "application_end": datetime.fromtimestamp(
                data["application_end_ms"] / 1000
            ),
            "matching_round_start": datetime.fromtimestamp(
                data["public_round_start_ms"] / 1000
            ),
            "matching_round_end": datetime.fromtimestamp(
                data["public_round_end_ms"] / 1000
            ),
            "registry_provider": data["registry_provider"],
            "min_matching_pool_donation_amount": data[
                "min_matching_pool_donation_amount"
            ],
            "sybil_wrapper_provider": data["sybil_wrapper_provider"],
            "custom_sybil_checks": data.get("custom_sybil_checks"),
            "custom_min_threshold_score": data.get("custom_min_threshold_score"),
            "referral_fee_matching_pool_basis_points": data[
                "referral_fee_matching_pool_basis_points"
            ],
            "referral_fee_public_round_basis_points": data[
                "referral_fee_public_round_basis_points"
            ],
            "chef_fee_basis_points": data["chef_fee_basis_points"],
            "total_matching_pool": "0",
            "matching_pool_balance": "0",
            "matching_pool_donations_count": 0,
            "total_public_donations": "0",
            "public_donations_count": 0,
            "cooldown_period_ms": None,
            "all_paid_out": False,
            "protocol_config_provider": data["protocol_config_provider"],
        }
        pot = await Pot.objects.acreate(
            account=receiver, **pot_defaults
        )

        # Add admins to the Pot
        if data.get("admins"):
            for admin_id in data["admins"]:
                admin, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, id=admin_id)
                pot.admins.aadd(admin)

        defaults = {
            "signer_id": signer_id,
            "receiver_id": receiver_id,
            "timestamp": created_at,
            "tx_hash": receiptId,
        }

        activity, activity_created = await Activity.objects.aupdate_or_create(
            action_result=data, type="Deploy_Pot", defaults=defaults
        )
    except Exception as e:
        logger.error(f"Failed to handle new pot, Error: {e}")


async def handle_pot_config_update(
    log_data: dict,
    receiver_id: str,
):
    try:
        pot = await Pot.objects.filter(account=receiver_id).afirst()
        if pot:
            logger.info("Pot already exists, updating using api call")
            pot_config_update = sync_to_async(pot.update_configs)
            await pot_config_update()
        # pot_config = {
        #     "deployer": data["deployed_by"],
        #     "source_metadata": data["source_metadata"],
        #     "owner_id": data["owner"],
        #     "chef_id": data.get("chef"),
        #     "name": data["pot_name"],
        #     "description": data["pot_description"],
        #     "max_approved_applicants": data["max_projects"],
        #     "base_currency": data["base_currency"],
        #     "application_start": datetime.fromtimestamp(
        #         data["application_start_ms"] / 1000
        #     ),
        #     "application_end": datetime.fromtimestamp(
        #         data["application_end_ms"] / 1000
        #     ),
        #     "matching_round_start": datetime.fromtimestamp(
        #         data["public_round_start_ms"] / 1000
        #     ),
        #     "matching_round_end": datetime.fromtimestamp(
        #         data["public_round_end_ms"] / 1000
        #     ),
        #     "registry_provider": data["registry_provider"],
        #     "min_matching_pool_donation_amount": data[
        #         "min_matching_pool_donation_amount"
        #     ],
        #     "sybil_wrapper_provider": data["sybil_wrapper_provider"],
        #     "custom_sybil_checks": data.get("custom_sybil_checks"),
        #     "custom_min_threshold_score": data.get("custom_min_threshold_score"),
        #     "referral_fee_matching_pool_basis_points": data[
        #         "referral_fee_matching_pool_basis_points"
        #     ],
        #     "referral_fee_public_round_basis_points": data[
        #         "referral_fee_public_round_basis_points"
        #     ],
        #     "chef_fee_basis_points": data["chef_fee_basis_points"],
        #     "matching_pool_balance": data["matching_pool_balance"],
        #     "total_public_donations": data["total_public_donations"],
        #     "public_donations_count": data["public_donations_count"],
        #     "cooldown_period_ms": data["cooldown_end_ms"],
        #     "all_paid_out": data["all_paid_out"],
        #     "protocol_config_provider": data["protocol_config_provider"],
        # }

        # pot, created = await Pot.objects.aupdate_or_create(
        #     account=receiver_id, defaults=pot_config
        # )

        # if data.get("admins"):
        #     for admin_id in data["admins"]:
        #         admin, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, id=admin_id)
        #         pot.admins.aadd(admin)
        # await Pot.objects.filter(id=receiver_id).aupdate(**pot_config)
    except Exception as e:
        logger.error(f"Failed to update Pot config, Error: {e}")


async def handle_new_pot_factory(data: dict, receiver_id: str, created_at: datetime):
    try:

        logger.info("upserting accounts...")

        # Upsert accounts
        owner, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, 
            id=data["owner"],
        )
        protocol_fee_recipient_account, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, 
            id=data["protocol_fee_recipient_account"],
        )

        receiver, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, 
            id=receiver_id,
        )

        logger.info("creating factory....")
        defaults = {
            "owner": owner,
            "deployed_at": created_at,
            "source_metadata": data["source_metadata"],
            "protocol_fee_basis_points": data["protocol_fee_basis_points"],
            "protocol_fee_recipient": protocol_fee_recipient_account,
            "require_whitelist": data["require_whitelist"],
        }
        # Create Factory object
        factory, factory_created = await PotFactory.objects.aupdate_or_create(
            account=receiver, defaults=defaults
        )

        # Add admins to the PotFactory
        if data.get("admins"):
            for admin_id in data["admins"]:
                admin, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, 
                    id=admin_id,
                )
                await factory.admins.aadd(admin)

        # Add whitelisted deployers to the PotFactory
        if data.get("whitelisted_deployers"):
            for deployer_id in data["whitelisted_deployers"]:
                deployer, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, id=deployer_id)
                await factory.whitelisted_deployers.aadd(deployer)
    except Exception as e:
        logger.error(f"Failed to handle new pot Factory, Error: {e}")


async def handle_new_list(
    signer_id: str, receiver_id: str, status_obj: ExecutionOutcome
):
    # receipt = block.receipts().filter(receiptId=receiptId)[0]
    try:

        data = json.loads(
            base64.b64decode(status_obj.status.get("SuccessValue")).decode(
                "utf-8"
            )  # TODO: RECEIVE AS A FUNCTION ARGUMENT
        )

        logger.info("upserting involveed accts...")

        await Account.objects.aget_or_create(defaults={"chain_id":1}, id=data["owner"])

        await Account.objects.aget_or_create(defaults={"chain_id":1}, id=signer_id)

        await Account.objects.aget_or_create(defaults={"chain_id":1}, id=receiver_id)

        logger.info(f"creating list..... {data}")

        listObject = await List.objects.acreate(
            on_chain_id=data["id"],
            owner_id=data["owner"],
            default_registration_status=data["default_registration_status"],
            name=data["name"],
            description=data["description"],
            cover_image_url=data["cover_image_url"],
            admin_only_registrations=data["admin_only_registrations"],
            created_at=datetime.fromtimestamp(data["created_at"] / 1000),
            updated_at=datetime.fromtimestamp(data["updated_at"] / 1000),
        )

        if data.get("admins"):
            for admin_id in data["admins"]:
                admin_object, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, 
                    id=admin_id,
                )
                await listObject.admins.aadd(admin_object)
    except Exception as e:
        logger.error(f"Failed to handle new list, Error: {e}")


async def handle_new_list_registration(
    data: dict,
    receiver_id: str,
    signer_id: str,
    receipt: Receipt,
    status_obj: ExecutionOutcome,
):
    logger.info(f"new Project data: {data}, {receiver_id}")

    # Retrieve receipt data
    if receipt is None:
        return

    reg_data = json.loads(
        base64.b64decode(status_obj.status["SuccessValue"]).decode(
            "utf-8"
        )  # TODO: RECEIVE AS A FUNCTION ARGUMENT
    )
    # Prepare data for insertion
    project_list = []
    insert_data = []
    for dt in reg_data:
        logger.info(f"dt: {dt}")
        project_list.append({"id": dt["registrant_id"]})
        insert_data.append(
            {
                "id": dt["id"],
                "registrant_id": dt["registrant_id"],
                "list_id": dt["list_id"],
                "status": dt["status"],
                "submitted_at": datetime.fromtimestamp(dt["submitted_ms"] / 1000),
                "updated_at": datetime.fromtimestamp(dt["updated_ms"] / 1000),
                "registered_by_id": dt["registered_by"],
                "admin_notes": dt.get("admin_notes"),
                "registrant_notes": dt.get("registrant_notes"),
                "tx_hash": receipt.receipt_id,
            }
        )
    logger.info(f"insert_data: {insert_data}")

    try:
        await Account.objects.abulk_create(
            objs=[Account(**data) for data in project_list], ignore_conflicts=True
        )
        await Account.objects.aget_or_create(defaults={"chain_id":1}, id=signer_id)
        logger.info("Upserted accounts/registrants(signer)")
    except Exception as e:
        logger.error(f"Encountered error trying to get create acct: {e}")

    try:
        await ListRegistration.objects.abulk_create(
            [ListRegistration(**data) for data in insert_data], ignore_conflicts=True
        )
    except Exception as e:
        logger.error(f"Encountered error trying to create list: {e}")

    # Insert activity
    try:
        defaults = {
            "signer_id": signer_id,
            "receiver_id": receiver_id,
            "timestamp": datetime.fromtimestamp(insert_data[0]["submitted_at"] / 1000),
            "tx_hash": receipt.receipt_id,
        }

        activity, activity_created = await Activity.objects.aupdate_or_create(
            action_result=reg_data, type="Register_Batch", defaults=defaults
        )
    except Exception as e:
        logger.error(f"Encountered error trying to insert activity: {e}")


async def handle_list_registration_update(
    data: dict, receiver_id: str, status_obj: ExecutionOutcome
):
    logger.info(f"new Project data: {data}, {receiver_id}")

    data = json.loads(
        base64.b64decode(status_obj.status.get("SuccessValue")).decode(
            "utf-8"
        )  # TODO: RECEIVE AS A FUNCTION ARGUMENT
    )

    # Prepare data for update
    regUpdate = {
        "status": data["status"],
        "admin_notes": data["admin_notes"],
        "updated_at": datetime.fromtimestamp(data["updated_ms"] / 1000),
    }

    try:
        # Perform the update
        await ListRegistration.objects.filter(id=data["id"]).aupdate(**regUpdate)
    except Exception as e:
        logger.error(f"Encountered error trying to update ListRegistration: {e}")


async def handle_pot_application(
    data: dict,
    receiver_id: str,
    signer_id: str,
    receipt: Receipt,
    status_obj: ExecutionOutcome,
    created_at: datetime,
):
    try:

        # receipt = block.receipts().filter(lambda receipt: receipt.receiptId == receiptId)[0]
        result = status_obj.status.get("SuccessValue")
        if not result:
            return

        appl_data = json.loads(
            base64.b64decode(result).decode("utf-8")
        )  # TODO: RECEIVE AS A FUNCTION ARGUMENT
        logger.info(f"new pot application data: {data}, {appl_data}")

        # Update or create the account
        project, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, 
            id=appl_data["project_id"],
        )

        # TODO: wouldn't this be the same as the project_id? should inspect
        signer, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, 
            id=signer_id,
        )

        # Create the PotApplication object
        logger.info("creating application.......")
        appl_defaults = {
            "message": appl_data["message"],
            "submitted_at": datetime.fromtimestamp(appl_data["submitted_at"] / 1000),
            "updated_at": created_at,
            "status": appl_data["status"],
            "tx_hash": receipt.receipt_id,
        }
        application, application_created = (
            await PotApplication.objects.aupdate_or_create(
                applicant=project,
                pot_id=receiver_id,
                defaults=appl_defaults,
            )
        )

        # Create the activity object
        logger.info("creating activity for action....")

        defaults = {
            "signer_id": signer_id,
            "receiver_id": receiver_id,
            "timestamp": created_at,
            "tx_hash": receipt.receipt_id,
        }

        activity, activity_created = await Activity.objects.aupdate_or_create(
            action_result=appl_data, type="Submit_Application", defaults=defaults
        )

        logger.info(
            f"PotApplication and Activity created successfully, {activity_created}"
        )
    except Exception as e:
        logger.error(f"Failed to handle pot application, Error: {e}")


async def handle_pot_application_status_change(
    data: dict,
    receiver_id: str,
    signer_id: str,
    receipt: Receipt,
    status_obj: ExecutionOutcome,
):
    try:

        logger.info(f"pot application update data: {data}, {receiver_id}")

        # receipt = next(receipt for receipt in block.receipts() if receipt.receiptId == receiptId)
        update_data = json.loads(
            base64.b64decode(status_obj.status["SuccessValue"]).decode(
                "utf-8"
            )  # TODO: RECEIVE AS A FUNCTION ARGUMENT
        )

        # Retrieve the PotApplication object
        appl = await PotApplication.objects.filter(
            applicant_id=data["project_id"]
        ).afirst()

        if not appl:
            logger.error(
                f"PotApplication object not found for project_id: {data['project_id']}"
            )
            return

        # Create the PotApplicationReview object
        logger.info(f"create review...... {appl}")
        updated_at = datetime.fromtimestamp(update_data.get("updated_at") / 1000)

        defaults = {
            "notes": update_data.get("review_notes"),
            "status": update_data["status"],
            "tx_hash": receipt.receipt_id,
        }

        await PotApplicationReview.objects.aupdate_or_create(
            application_id=appl.id,
            reviewer_id=signer_id,
            reviewed_at=updated_at,
            defaults=defaults,
        )

        # Update the PotApplication object
        await PotApplication.objects.filter(applicant_id=data["project_id"]).aupdate(
            **{"status": update_data["status"], "updated_at": updated_at}
        )

        logger.info("PotApplicationReview and PotApplication updated successfully.")
    except Exception as e:
        logger.error(f"Failed to change pot application status, Error: {e}")


async def handle_default_list_status_change(
    data: dict, receiver_id: str, status_obj: ExecutionOutcome
):
    try:

        logger.info(f"update project data: {data}, {receiver_id}")

        result_data = json.loads(
            base64.b64decode(status_obj.status.get("SuccessValue")).decode(
                "utf-8"
            )  # TODO: RECEIVE AS A FUNCTION ARGUMENT
        )

        list_id = data.get("registration_id")
        list_update = {
            "name": result_data["name"],
            "owner_id": result_data["owner"],
            "default_registration_status": result_data["default_registration_status"],
            "admin_only_registrations": result_data["admin_only_registrations"],
            "updated_at": result_data["updated_at"],
        }
        if result_data.get("description"):
            list_update["description"] = result_data["description"]
        if result_data.get("cover_image_url"):
            list_update["cover_image_url"] = result_data["cover_image_url"]

        await List.objects.filter(id=list_id).aupdate(**list_update)

        logger.info("List updated successfully.")
    except Exception as e:
        logger.error(f"Failed to change list status, Error: {e}")


async def handle_list_upvote(
    data: dict, receiver_id: str, signer_id: str, receiptId: str
):
    try:

        logger.info(f"upvote list: {data}, {receiver_id}")

        acct, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, 
            id=signer_id,
        )

        created_at = datetime.now()

        await ListUpvote.objects.aupdate_or_create(
            list_id=data.get("list_id") or receiver_id,
            account_id=signer_id,
        )

        defaults = {
            "signer_id": signer_id,
            "receiver_id": receiver_id,
            "timestamp": created_at,
            "tx_hash": receiptId,
        }

        activity, activity_created = await Activity.objects.aupdate_or_create(
            action_result=data, type="Upvote", defaults=defaults
        )

        logger.info(
            f"Upvote and activity records created successfully. {activity_created}"
        )
    except Exception as e:
        logger.error(f"Failed to upvote list, Error: {e}")


async def handle_set_payouts(data: dict, receiver_id: str, receipt: Receipt):
    try:

        logger.info(f"set payout data: {data}, {receiver_id}")
        payouts = data.get("payouts", [])
        pot = await Pot.objects.aget(account=receiver_id)
        near_acct, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, id="near")
        near_token, _ = await Token.objects.aget_or_create(
            account=near_acct
        )  # Pots only support native NEAR

        insertion_data = []
        for payout in payouts:
            # General question: should we register projects as accounts?
            pot_payout = PotPayout(
                pot=pot,
                recipient_id=payout.get("project_id"),
                amount=payout.get("amount"),
                token=near_token,
                paid_at=None,
                tx_hash=receipt.receipt_id,
            )
            insertion_data.append(pot_payout)

        await PotPayout.objects.abulk_create(insertion_data, ignore_conflicts=True)
        url = f"{settings.FASTNEAR_RPC_URL}/account/{receiver_id}/view/get_config"
        response = requests.get(url)
        if response.status_code != 200:
            logger.error(f"Failed to get config for pot {receiver_id}: {response.text}")
        else:
            data = response.json()
            pot = await Pot.objects.aget(account=receiver_id)
            pot.cooldown_end = datetime.fromtimestamp(data["cooldown_end_ms"] / 1000)
            await pot.asave()
    except Exception as e:
        logger.error(f"Failed to set payouts, Error: {e}")


async def handle_transfer_payout(
    data: dict, receiver_id: str, receiptId: str, created_at: datetime
):
    try:

        data = data["payout"]
        logger.info(f"fulfill payout data: {data}, {receiver_id}, {created_at}")
        payout = {
            "recipient_id": data["project_id"],
            "amount": data["amount"],
            "paid_at": data["paid_at"] or created_at,
            "tx_hash": receiptId,
        }
        await PotPayout.objects.filter(recipient_id=data["project_id"]).aupdate(
            **payout
        )
        # check if all_paid_out is now true
        url = f"{settings.FASTNEAR_RPC_URL}/account/{receiver_id}/view/get_config"
        response = requests.get(url)
        if response.status_code != 200:
            logger.error(f"Failed to get config for pot {receiver_id}: {response.text}")
        else:
            data = response.json()
            pot = await Pot.objects.aget(account=receiver_id)
            pot.all_paid_out = data["all_paid_out"]
            await pot.asave()
    except Exception as e:
        logger.error(f"Failed to create payout data, Error: {e}")


async def handle_payout_challenge(
    data: dict, receiver_id: str, signer_id: str, receiptId: str, created_at: datetime
):
    try:
        acct, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, id=signer_id)
        logger.info(f"challenging payout..: {data}, {receiver_id}")
        payoutChallenge = {
            "created_at": created_at,
            "message": data["reason"],
            "tx_hash": receiptId,
        }
        await PotPayoutChallenge.objects.aupdate_or_create(
            challenger_id=signer_id, pot_id=receiver_id, defaults=payoutChallenge
        )

        defaults = {
            "signer_id": signer_id,
            "receiver_id": receiver_id,
            "timestamp": created_at,
            "tx_hash": receiptId,
        }

        activity, activity_created = await Activity.objects.aupdate_or_create(
            action_result=payoutChallenge, type="Challenge_Payout", defaults=defaults
        )
    except Exception as e:
        logger.error(f"Failed to create payoutchallenge, Error: {e}")


async def handle_payout_challenge_response(
    data: dict, receiver_id: str, signer_id: str, receiptId: str, created_at: datetime
):
    try:
        logger.info(f"responding to payout challenge..: {data}, {receiver_id}")
        response_defaults = {
            "admin_id": signer_id,
            "message": data.get("notes"),
            "resolved": data.get("resolve_challenge"),
            "tx_hash": receiptId,
        }
        await PotPayoutChallengeAdminResponse.objects.aupdate_or_create(
            challenger_id=data["challenger_id"],
            pot_id=receiver_id,
            created_at=created_at,
            defaults=response_defaults,
        )
    except Exception as e:
        logger.error(f"Failed to handle admin challeneg response, Error: {e}")


async def handle_list_admin_removal(data, receiver_id, signer_id, receiptId):
    try:

        logger.info(f"removing admin...: {data}, {receiver_id}")
        list_obj = await List.objects.aget(id=data["list_id"])

        for acct in data["admins"]:
            list_obj.admins.remove({"admins_id": acct})  # maybe check

        activity = {
            "signer_id": signer_id,
            "receiver_id": receiver_id,
            "timestamp": datetime.now(),
            "tx_hash": receiptId,
        }

        activity, activity_created = await Activity.objects.aupdate_or_create(
            type="Remove_List_Admin", defaults=activity
        )
    except Exception as e:
        logger.error(f"Failed to remove list admin, Error: {e}")


async def handle_add_nadabot_admin(data, receiverId):
    logger.info(f"adding admin...: {data}, {receiverId}")
    try:
        obj = await NadabotRegistry.objects.aget(account=receiverId)

        for acct in data["account_ids"]:
            user, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, id=acct)
            await obj.admins.aadd(user)
    except Exception as e:
        logger.error(f"Failed to add nadabot admin, Error: {e}")


async def handle_add_factory_deployers(data, receiverId):
    logger.info(f"adding factory deployer...: {data}, {receiverId}")
    try:
        factory = await PotFactory.objects.aget(account=receiverId)
        for acct in data["whitelisted_deployers"]:
            user, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, id=acct)
            await factory.whitelisted_deployers.aadd(user)
    except Exception as e:
        logger.error(f"Failed to add factory whitelisted deployers, Error: {e}")


async def handle_set_factory_configs(data, receiverId):
    logger.info(f"setting factory configs...: {data}, {receiverId}")
    try:
        factory = await PotFactory.objects.aget(account=receiverId)
        config_update = sync_to_async(factory.update_configs)
        await config_update()
    except Exception as e:
        logger.error(f"Failed to update factory configs, Error: {e}")


# # TODO: Need to abstract some actions.
# async def handle_batch_donations(
#     receiver_id: str,
#     signer_id: str,
#     action_name: str,
#     receipt_obj: Receipt,
#     log_data: list,
# ):
#     logger.info("Batch Transaction for donation...")
#     for event_data in log_data:
#         await handle_new_donations(
#             event_data["donation"],
#             receiver_id,
#             signer_id,
#             action_name,
#             receipt_obj,
#             status_obj=None,
#             log_data=[event_data],
#         )

# TODO: create handle_new_pot_donation & handle_new_direct_donation functions & share common logic with _handle_new_donation function


async def handle_new_donation(
    data: dict,
    receiver_id: str,
    signer_id: str,
    donation_type: str,  # "direct" or "pot"
    receipt_obj: Receipt,
    donation_data: dict,  # Donation object (note that these vary between direct and pot donations - see examples of each in ./examples.txt)
):
    logger.info(f"handle_new_donation args data: {data}, {receiver_id}")
    logger.info(f"donation data: {donation_data}")

    if "net_amount" in donation_data and donation_data["net_amount"] != "0":
        net_amount = int(donation_data["net_amount"])
    else:
        # direct donations don't have net_amount property, so have to calculate it here
        total_amount = int(donation_data["total_amount"])
        protocol_fee = int(donation_data["protocol_fee"])
        referrer_fee = int(donation_data["referrer_fee"] or 0)
        chef_fee = int(donation_data.get("chef_fee") or 0)

        net_amount = total_amount - protocol_fee - referrer_fee - chef_fee

    donated_at = datetime.fromtimestamp(
        (donation_data.get("donated_at") or donation_data.get("donated_at_ms")) / 1000
    )

    try:
        # insert donate contract which is the receiver id(because of activity relationship mainly)
        donate_contract, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, id=receiver_id)
        # Upsert donor account
        donor, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, id=donation_data["donor_id"])
        recipient = None
        referrer = None
        chef = None

        if donation_data.get("recipient_id"):  # direct donations have recipient_id
            recipient, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, 
                id=donation_data["recipient_id"]
            )
        if donation_data.get("project_id"):  # pot donations have project_id
            recipient, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, 
                id=donation_data["project_id"]
            )

        if donation_data.get("referrer_id"):
            referrer, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, 
                id=donation_data["referrer_id"]
            )

        if donation_data.get("chef_id"):
            chef, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, id=donation_data["chef_id"])

        # Upsert token account
        ft_id = donation_data.get("ft_id") or "near"
        token_acct, token_acct_created = await Account.objects.aget_or_create(defaults={"chain_id":1}, id=ft_id)
        token_defaults = {
            "decimals": 24,
        }
        if token_acct_created:
            logger.info(f"Created new token account: {token_acct}")
            if ft_id != "near":
                url = f"{settings.FASTNEAR_RPC_URL}/account/{ft_id}/view/ft_metadata"
                ft_metadata = requests.get(url)
                if ft_metadata.status_code != 200:
                    logger.error(
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
        token, _ = await Token.objects.aupdate_or_create(
            account=token_acct, defaults=token_defaults
        )

    except Exception as e:
        logger.error(f"Failed to create/get an account involved in donation: {e}")

    try:

        total_amount = donation_data["total_amount"]

        logger.info(f"inserting {donation_type} donation")
        default_data = {
            "donor": donor,
            "pot": None,
            "total_amount": total_amount,
            "total_amount_usd": None,  # USD amounts will be added later
            "net_amount_usd": None,
            "net_amount": net_amount,
            "token": token,
            "message": donation_data.get("message"),
            "donated_at": donated_at,
            "matching_pool": donation_data.get("matching_pool", False),
            "recipient": recipient,
            "protocol_fee": donation_data["protocol_fee"],
            "referrer": referrer,
            "referrer_fee": donation_data.get("referrer_fee"),
            "chef": chef,
            "chef_fee": donation_data.get("chef_fee"),
            "tx_hash": receipt_obj.receipt_id,
        }

        if donation_type == "pot":
            default_data["pot"] = await Pot.objects.aget(account=receiver_id)

        logger.info(f"default donation data: {default_data}")

        donation, donation_created = await Donation.objects.aupdate_or_create(
            on_chain_id=donation_data["id"],
            pot=default_data["pot"],
            defaults=default_data,
        )
        logger.info(f"Created donation? {donation_created}")
        logger.info(f"donation: {donation.to_dict()}")

        # fetch USD prices
        await donation.fetch_usd_prices_async()  # might not need to await this?

        # Insert or update activity record
        activity_type = (
            "Donate_Direct"
            if donation_type == "direct"
            else (
                "Donate_Pot_Matching_Pool"
                if donation.matching_pool
                else "Donate_Pot_Public"
            )
        )
        defaults = {
            "signer_id": signer_id,
            "receiver_id": receiver_id,
            "timestamp": donation.donated_at,
            "tx_hash": receipt_obj.receipt_id,
        }
        try:
            activity, activity_created = await Activity.objects.aupdate_or_create(
                action_result=donation_data, type=activity_type, defaults=defaults
            )
            if activity_created:
                logger.info(f"Activity created: {activity}")
            else:
                logger.info(f"Activity updated: {activity}")
        except Exception as e:
            logger.info(f"Failed to create Activity: {e}")
    except Exception as e:
        logger.error(f"Failed to create/update donation: {e}")

    ### COMMENTING OUT FOR NOW SINCE WE HAVE PERIODIC JOB RUNNING TO UPDATE ACCOUNT STATS (NB: DOESN'T CURRENTLY COVER POT STATS)
    ### CAN ALWAYS ADD BACK IF DESIRED
    # if donation_created:  # only do stats updates if donation object was created

    #     if action_name != "direct":

    #         potUpdate = {
    #             "total_public_donations": str(
    #                 int(pot.total_public_donations or 0) + int(total_amount)
    #             ),
    #             "total_public_donations_usd": int(pot.total_public_donations_usd or 0.0)
    #             + total_amount_usd,
    #         }
    #         if donation_data.get("matching_pool"):
    #             potUpdate["total_matching_pool"] = str(
    #                 int(pot.total_matching_pool or 0) + int(total_amount)
    #             )
    #             potUpdate["total_matching_pool"] = (
    #                 pot.total_matching_pool_usd or 0.0
    #             ) + total_amount_usd
    #             potUpdate["matching_pool_donations_count"] = (
    #                 pot.matching_pool_donations_count or 0
    #             ) + 1

    #             if recipient:
    #                 await Account.objects.filter(id=recipient.id).aupdate(
    #                     **{
    #                         "total_matching_pool_allocations_usd": recipient.total_matching_pool_allocations_usd
    #                         + total_amount_usd
    #                     }
    #                 )

    #             # accountUpdate = {}
    #         else:
    #             potUpdate["public_donations_count"] = (
    #                 pot.public_donations_count or 0
    #             ) + 1

    #         await Pot.objects.filter(id=receiver_id).aupdate(**potUpdate)

    #     # donation_recipient = donation_data.get('project_id', donation_data['recipient_id'])
    #     logger.info(
    #         f"update total donated for {donor.id}, {donor.total_donations_out_usd + decimal.Decimal(total_amount_usd)}"
    #     )
    #     await Account.objects.filter(id=donor.id).aupdate(
    #         **{
    #             "total_donations_out_usd": donor.total_donations_out_usd
    #             + decimal.Decimal(total_amount_usd)
    #         }
    #     )
    #     if recipient:
    #         acct = await Account.objects.aget(id=recipient.id)
    #         logger.info(f"selected {acct} to perform donor count update")
    #         acctUpdate = {
    #             "donors_count": acct.donors_count + 1,
    #             "total_donations_in_usd": acct.total_donations_in_usd
    #             + decimal.Decimal(net_amount_usd),
    #         }
    #         await Account.objects.filter(id=recipient.id).aupdate(**acctUpdate)


async def handle_update_default_human_threshold(data: dict, receiverId: str):
    logger.info(f"update threshold data... {data}")

    try:

        reg = await NadabotRegistry.objects.filter(account=receiverId).aupdate(
            **{"default_human_threshold": data["default_human_threshold"]}
        )
        logger.info("updated threshold..")
    except Exception as e:
        logger.error(f"Failed to update default threshold, Error: {e}")


async def handle_new_provider(data: dict, receiverId: str, signerId: str):
    logger.info(f"new provider data: {data}, {receiverId}")
    data = data["provider"]

    logger.info(
        f"upserting accounts involved, {data['submitted_by']}, {data['contract_id']}"
    )

    try:
        submitter, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, id=data["submitted_by"])
        contract, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, id=data["contract_id"])

        provider_id = data["id"]

        # due to an event malfunction from the contract, the first 13 migrated(migrated from a previous contract) providers,
        # had the same id emitted for them, the id `13`, so we have to catch it and manoeuvre aroubd it.
        # TODO: REMOVE when next version contract is deployed, as this issue would be fixed.
        if provider_id == 13:
            provider_id = await cache.aget("last_id", 1)
            await cache.aset("last_id", provider_id + 1)

        provider = await Provider.objects.aupdate_or_create(
            on_chain_id=provider_id,
            contract=contract,
            method_name=data["method_name"],
            name=data["provider_name"],
            description=data.get("description"),
            status=data["status"],
            admin_notes=data.get("admin_notes"),
            default_weight=data["default_weight"],
            gas=data.get("gas"),
            tags=data.get("tags"),
            icon_url=data.get("icon_url"),
            external_url=data.get("external_url"),
            submitted_by_id=data["submitted_by"],
            submitted_at=datetime.fromtimestamp(data.get("submitted_at_ms") / 1000),
            stamp_validity_ms=(
                datetime.fromtimestamp(data.get("stamp_validity_ms") / 1000)
                if data.get("stamp_validity_ms")
                else None
            ),
            account_id_arg_name=data["account_id_arg_name"],
            custom_args=data.get("custom_args"),
            registry_id=receiverId,
        )
    except Exception as e:
        logger.error(f"Failed to add new stamp provider: {e}")


async def handle_add_stamp(data: dict, receiverId: str, signerId: str):
    logger.info(f"new stamp data: {data}, {receiverId}")
    data = data["stamp"]

    logger.info(f"upserting accounts involved, {data['user_id']}")

    user, _ = await Account.objects.aget_or_create(defaults={"chain_id":1}, id=data["user_id"])
    provider, _ = await Provider.objects.aget_or_create(on_chain_id=data["provider_id"])

    try:
        stamp = await Stamp.objects.aupdate_or_create(
            user=user,
            provider=provider,
            verified_at=datetime.fromtimestamp(data["validated_at_ms"] / 1000),
        )
    except Exception as e:
        logger.error(f"Failed to create stamp: {e}")


async def handle_new_group(data: dict, created_at: datetime):
    logger.info(f"new group data: {data}")
    group_data = data.get("group", {})
    try:
        # group enums can have values, they are represented as a dict in the events from the indexer, and enum choices without values are presented as normal strings:
        # withValue: {'group': {'id': 5, 'name': 'Here we go again', 'providers': [8, 1, 4, 6], 'rule': {'IncreasingReturns': 10}}}
        # noValue: {"id":6,"name":"Lachlan test group","providers":[1,2],"rule":"Highest"}
        rule = group_data["rule"]
        rule_key = rule
        rule_val = None
        if type(rule) == dict:
            rule_key = next(iter(rule))
            rule_val = rule.get(rule_key)

        group = await Group.objects.acreate(
            id=group_data["id"],
            name=group_data["name"],
            created_at=created_at,
            updated_at=created_at,
            rule_type=rule_key,
            rule_val=rule_val,
        )

        logger.info(f"addding provider.... : {group_data['providers']}")
        if group_data.get("providers"):
            for provider_id in group_data["providers"]:
                provider, _ = await Provider.objects.aget_or_create(
                    on_chain_id=provider_id
                )
                await group.providers.aadd(provider)
    except Exception as e:
        logger.error(f"Failed to create group, because: {e}")


async def save_block_height(block_height: int, block_timestamp: int):
    await BlockHeight.objects.aupdate_or_create(
        id=1,
        defaults={
            "block_height": block_height,
            "block_timestamp": datetime.fromtimestamp(block_timestamp / 1000000000),
            "updated_at": timezone.now(),
        },
    )  # better than ovverriding model's save method to get a singleton? we need only one entry
    # return height


def get_block_height() -> int:
    record = BlockHeight.objects.filter(id=1).first()
    if record:
        return record.block_height
