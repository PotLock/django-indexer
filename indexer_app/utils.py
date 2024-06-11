import base64
import json
from datetime import datetime

import requests
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
from pots.models import (
    Pot,
    PotApplication,
    PotApplicationReview,
    PotFactory,
    PotPayout,
    PotPayoutChallenge,
    PotPayoutChallengeAdminResponse,
)

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
        owner, _ = await Account.objects.aget_or_create(id=owner_id)
        signer, _ = await Account.objects.aget_or_create(id=signer_id)
        receiver, _ = await Account.objects.aget_or_create(id=receiver_id)

        logger.info("upsert chef")
        if data.get("chef"):
            chef, _ = await Account.objects.aget_or_create(id=data["chef"])

        # Create Pot object
        logger.info(f"creating pot with owner {owner_id}....")
        pot_defaults = {
            "pot_factory_id": predecessorId,
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
        pot, created = await Pot.objects.aupdate_or_create(
            id=receiver, defaults=pot_defaults
        )

        # Add admins to the Pot
        if data.get("admins"):
            for admin_id in data["admins"]:
                admin, _ = await Account.objects.aget_or_create(id=admin_id)
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


async def handle_new_pot_factory(data: dict, receiver_id: str, created_at: datetime):
    try:

        logger.info("upserting accounts...")

        # Upsert accounts
        owner, _ = await Account.objects.aget_or_create(
            id=data["owner"],
        )
        protocol_fee_recipient_account, _ = await Account.objects.aget_or_create(
            id=data["protocol_fee_recipient_account"],
        )

        receiver, _ = await Account.objects.aget_or_create(
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
            id=receiver, defaults=defaults
        )

        # Add admins to the PotFactory
        if data.get("admins"):
            for admin_id in data["admins"]:
                admin, _ = await Account.objects.aget_or_create(
                    id=admin_id,
                )
                await factory.admins.aadd(admin)

        # Add whitelisted deployers to the PotFactory
        if data.get("whitelisted_deployers"):
            for deployer_id in data["whitelisted_deployers"]:
                deployer, _ = await Account.objects.aget_or_create(id=deployer_id)
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

        logger.info(f"creating list..... {data}")

        listObject = await List.objects.acreate(
            id=data["id"],
            owner_id=data["owner"],
            default_registration_status=data["default_registration_status"],
            name=data["name"],
            description=data["description"],
            cover_image_url=data["cover_image_url"],
            admin_only_registrations=data["admin_only_registrations"],
            created_at=datetime.fromtimestamp(data["created_at"] / 1000),
            updated_at=datetime.fromtimestamp(data["updated_at"] / 1000),
        )

        logger.info("upserting involveed accts...")

        await Account.objects.aget_or_create(id=data["owner"])

        await Account.objects.aget_or_create(id=signer_id)

        await Account.objects.aget_or_create(id=receiver_id)

        if data.get("admins"):
            for admin_id in data["admins"]:
                admin_object, _ = await Account.objects.aget_or_create(
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

    try:
        await Account.objects.abulk_create(
            objs=[Account(**data) for data in project_list], ignore_conflicts=True
        )
        await Account.objects.aget_or_create(id=signer_id)
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
        project, _ = await Account.objects.aget_or_create(
            id=data["project_id"],
        )

        signer, _ = await Account.objects.aget_or_create(
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

        acct, _ = await Account.objects.aget_or_create(
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

        insertion_data = []
        for payout in payouts:
            # General question: should we register projects as accounts?
            potPayout = {
                "recipient_id": payout.get("project_id"),
                "amount": payout.get("amount"),
                "ft_id": payout.get("ft_id", "near"),
                "tx_hash": receipt.receipt_id,
            }
            insertion_data.append(potPayout)

        await PotPayout.objects.abulk_create(insertion_data, ignore_conflicts=True)
    except Exception as e:
        logger.error(f"Failed to set payouts, Error: {e}")


async def handle_transfer_payout(
    data: dict, receiver_id: str, receiptId: str, created_at: datetime
):
    try:

        data = data["payout"]
        logger.info(f"fulfill payout data: {data}, {receiver_id}")
        payout = {
            "recipient_id": data["project_id"],
            "amount": data["amount"],
            "paid_at": data.get("paid_at", created_at),
            "tx_hash": receiptId,
        }
        await PotPayout.objects.filter(recipient_id=data["project_id"]).aupdate(
            **payout
        )
    except Exception as e:
        logger.error(f"Failed to create payout data, Error: {e}")


async def handle_payout_challenge(
    data: dict, receiver_id: str, signer_id: str, receiptId: str, created_at: datetime
):
    try:

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
            "admin": signer_id,
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
    result: dict,  # Donation object (note that these vary between direct and pot donations - see examples of each in ./examples.txt)
):
    logger.info(f"handle_new_donation data: {data}, {receiver_id}")
    donation_data = json.loads(base64.b64decode(result).decode("utf-8"))
    logger.info(f"decoded result: {donation_data}")

    if "net_amount" in donation_data:
        net_amount = int(donation_data["net_amount"])
    else:
        # direct donations don't have net_amount property, so have to calculate it here
        net_amount = (
            int(donation_data["total_amount"])
            - int(donation_data["protocol_fee"])
            - donation_data["referrer_fee"]
            or 0
        )

    donated_at = datetime.fromtimestamp(
        (donation_data.get("donated_at") or donation_data.get("donated_at_ms")) / 1000
    )

    try:
        # Upsert donor account
        donor, _ = await Account.objects.aget_or_create(id=donation_data["donor_id"])
        recipient = None
        referrer = None
        chef = None

        if donation_data.get("recipient_id"):  # direct donations have recipient_id
            recipient, _ = await Account.objects.aget_or_create(
                id=donation_data["recipient_id"]
            )
        if donation_data.get("project_id"):  # pot donations have project_id
            recipient, _ = await Account.objects.aget_or_create(
                id=donation_data["project_id"]
            )

        if donation_data.get("referrer_id"):
            referrer, _ = await Account.objects.aget_or_create(
                id=donation_data["referrer_id"]
            )

        if donation_data.get("chef_id"):
            chef, _ = await Account.objects.aget_or_create(id=donation_data["chef_id"])

        # Upsert token account
        token_acct, _ = await Account.objects.aget_or_create(
            id=(donation_data.get("ft_id") or "near")
        )
    except Exception as e:
        logger.error(f"Failed to create/get an account involved in donation: {e}")

    try:

        total_amount = donation_data["total_amount"]

        logger.info(f"inserting {donation_type} donation")
        default_data = {
            "donor": donor,
            "total_amount": total_amount,
            "total_amount_usd": None,  # USD amounts will be added later
            "net_amount_usd": None,
            "net_amount": net_amount,
            "ft": token_acct,
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
            default_data["pot"] = await Pot.objects.aget(id=receiver_id)

        logger.info(f"default donation data: {default_data}")

        donation, donation_created = await Donation.objects.aupdate_or_create(
            on_chain_id=donation_data["id"], defaults=default_data
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


async def cache_block_height(
    key: str, height: int, block_count: int, block_timestamp: int
) -> int:
    await cache.aset(key, height)
    # the cache os the default go to for the restart block, the db is a backup if the redis server crashes.
    if (block_count % int(settings.BLOCK_SAVE_HEIGHT or 400)) == 0:
        logger.info(f"saving daylight, {height}")
        await BlockHeight.objects.aupdate_or_create(
            id=1,
            defaults={
                "block_height": height,
                "block_timestamp": datetime.fromtimestamp(block_timestamp / 1000000000),
                "updated_at": timezone.now(),
            },
        )  # better than ovverriding model's save method to get a singleton? we need only one entry
    return height


def get_block_height(key: str) -> int:
    block_height = cache.get(key)
    if not block_height:
        record = BlockHeight.objects.filter(id=1).first()
        block_height = 104_922_190 if not record else record.block_height
    return block_height
