import base64
import decimal
import json
from datetime import date, datetime

import requests
from django.conf import settings
from django.core.cache import cache
from near_lake_framework.near_primitives import ExecutionOutcome, Receipt

from accounts.models import Account
from activities.models import Activity
from base.logging import logger
from base.utils import format_date, format_to_near
from donations.models import Donation
from indexer_app.models import BlockHeight
from lists.models import List, ListRegistration, ListUpvote
from nadabot.models import NadabotRegistry, Provider, Stamp
from pots.models import (
    Pot,
    PotApplication,
    PotApplicationReview,
    PotFactory,
    PotPayout,
    PotPayoutChallenge,
)
from tokens.models import Token, TokenHistoricalPrice

GECKO_URL = "https://api.coingecko.com/api/v3"


async def handle_nadabot_registry(
        data: dict,
        receiverId: str,
        created_at: datetime
):
    print("nadabot registry init...", data)

    registry, _ = await Account.objects.aget_or_create(id=receiverId)
    owner, _ = await Account.objects.aget_or_create(id=data["owner"])
    nadabot_registry = await NadabotRegistry.objects.acreate(
        id=registry,
        owner=owner,
        created_at=created_at,
        updated_at=created_at,
        source_metadata=data.get('source_metadata')
    )

    if data.get("admins"):
        for admin_id in data["admins"]:
            admin, _ = await Account.objects.aget_or_create(id=admin_id)
            await nadabot_registry.admins.aadd(admin)



async def handle_new_pot(
    data: dict,
    receiverId: str,
    signerId: str,
    predecessorId: str,
    receiptId: str,
    created_at: datetime,
):
    logger.info("new pot deployment process... upsert accounts,")

    # Upsert accounts
    owner, _ = await Account.objects.aget_or_create(id=data["owner"])
    signer, _ = await Account.objects.aget_or_create(id=signerId)
    receiver, _ = await Account.objects.aget_or_create(id=receiverId)

    logger.info("upsert chef")
    if data.get("chef"):
        chef, _ = await Account.objects.aget_or_create(id=data["chef"])

    # Create Pot object
    logger.info("create pot....")
    potObject = await Pot.objects.acreate(
        id=receiver,
        pot_factory_id=predecessorId,
        deployer=signer,
        deployed_at=created_at,
        source_metadata=data["source_metadata"],
        owner_id=data["owner"],
        chef_id=data.get("chef"),
        name=data["pot_name"],
        description=data["pot_description"],
        max_approved_applicants=data["max_projects"],
        base_currency="near",
        application_start=datetime.fromtimestamp(data["application_start_ms"] / 1000),
        application_end=datetime.fromtimestamp(data["application_end_ms"] / 1000),
        matching_round_start=datetime.fromtimestamp(
            data["public_round_start_ms"] / 1000
        ),
        matching_round_end=datetime.fromtimestamp(data["public_round_end_ms"] / 1000),
        registry_provider=data["registry_provider"],
        min_matching_pool_donation_amount=data["min_matching_pool_donation_amount"],
        sybil_wrapper_provider=data["sybil_wrapper_provider"],
        custom_sybil_checks=data.get("custom_sybil_checks"),
        custom_min_threshold_score=data.get("custom_min_threshold_score"),
        referral_fee_matching_pool_basis_points=data[
            "referral_fee_matching_pool_basis_points"
        ],
        referral_fee_public_round_basis_points=data[
            "referral_fee_public_round_basis_points"
        ],
        chef_fee_basis_points=data["chef_fee_basis_points"],
        total_matching_pool="0",
        matching_pool_balance="0",
        matching_pool_donations_count=0,
        total_public_donations="0",
        public_donations_count=0,
        cooldown_period_ms=None,
        all_paid_out=False,
        protocol_config_provider=data["protocol_config_provider"],
    )

    # Add admins to the Pot
    if data.get("admins"):
        for admin_id in data["admins"]:
            admin, _ = await Account.objects.aget_or_create(id=admin_id)
            await potObject.admins.aadd(admin)

    # Create activity object
    await Activity.objects.acreate(
        signer_id=signerId,
        receiver_id=receiverId,
        timestamp=created_at,
        type="Deploy_Pot",
        action_result=data,
        tx_hash=receiptId,
    )


async def handle_new_pot_factory(data: dict, receiverId: str, created_at: datetime):
    logger.info("upserting accounts...")

    # Upsert accounts
    owner, _ = await Account.objects.aget_or_create(
        id=data["owner"],
    )
    protocol_fee_recipient_account, _ = await Account.objects.aget_or_create(
        id=data["protocol_fee_recipient_account"],
    )

    receiver, _ = await Account.objects.aget_or_create(
        id=receiverId,
    )

    logger.info("creating factory....")
    # Create Factory object
    factory = await PotFactory.objects.acreate(
        id=receiver,
        owner=owner,
        deployed_at=created_at,
        source_metadata=data["source_metadata"],
        protocol_fee_basis_points=data["protocol_fee_basis_points"],
        protocol_fee_recipient=protocol_fee_recipient_account,
        require_whitelist=data["require_whitelist"],
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


async def handle_new_list(signerId: str, receiverId: str, status_obj: ExecutionOutcome):
    # receipt = block.receipts().filter(receiptId=receiptId)[0]
    data = json.loads(
        base64.b64decode(status_obj.status.get("SuccessValue")).decode("utf-8")
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

    await Account.objects.aget_or_create(id=signerId)

    await Account.objects.aget_or_create(id=receiverId)

    if data.get("admins"):
        for admin_id in data["admins"]:
            admin_object, _ = await Account.objects.aget_or_create(
                id=admin_id,
            )
            await listObject.admins.aadd(admin_object)


async def handle_new_list_registration(
    data: dict,
    receiverId: str,
    signerId: str,
    receipt: Receipt,
    status_obj: ExecutionOutcome,
):
    logger.info(f"new Project data: {data}, {receiverId}")

    # Retrieve receipt data
    if receipt is None:
        return

    reg_data = json.loads(
        base64.b64decode(status_obj.status["SuccessValue"]).decode("utf-8")
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
        await Account.objects.aget_or_create(id=signerId)
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
        await Activity.objects.acreate(
            signer_id=signerId,
            receiver_id=receiverId,
            timestamp=insert_data[0]["submitted_at"],
            type="Register_Batch",
            action_result=reg_data,
            tx_hash=receipt.receipt_id,
        )
    except Exception as e:
        logger.error(f"Encountered error trying to insert activity: {e}")


async def handle_list_registration_update(
    data: dict, receiverId: str, status_obj: ExecutionOutcome
):
    logger.info(f"new Project data: {data}, {receiverId}")

    data = json.loads(
        base64.b64decode(status_obj.status.get("SuccessValue")).decode("utf-8")
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
    receiverId: str,
    signerId: str,
    receipt: Receipt,
    status_obj: ExecutionOutcome,
    created_at: datetime,
):
    # receipt = block.receipts().filter(lambda receipt: receipt.receiptId == receiptId)[0]
    result = status_obj.status.get("SuccessValue")
    if not result:
        return

    appl_data = json.loads(base64.b64decode(result).decode("utf-8"))
    logger.info(f"new pot application data: {data}, {appl_data}")

    # Update or create the account
    project, _ = await Account.objects.aget_or_create(
        id=data["project_id"],
    )

    signer, _ = await Account.objects.aget_or_create(
        id=signerId,
    )

    # Create the PotApplication object
    logger.info("creating application.......")
    application = await PotApplication.objects.acreate(
        pot_id=receiverId,
        applicant=project,
        message=appl_data["message"],
        submitted_at=datetime.fromtimestamp(appl_data["submitted_at"] / 1000),
        updated_at=created_at,
        status=appl_data["status"],
        tx_hash=receipt.receipt_id,
    )

    # Create the activity object
    logger.info("creating activity for action....")
    await Activity.objects.acreate(
        signer=signer,
        receiver_id=receiverId,
        timestamp=application.submitted_at,
        type="Submit_Application",
        action_result=appl_data,
        tx_hash=receipt.receipt_id,
    )

    logger.info("PotApplication and Activity created successfully.")


async def handle_pot_application_status_change(
    data: dict,
    receiverId: str,
    signerId: str,
    receipt: Receipt,
    status_obj: ExecutionOutcome,
):
    logger.info(f"pot application update data: {data}, {receiverId}")

    # receipt = next(receipt for receipt in block.receipts() if receipt.receiptId == receiptId)
    update_data = json.loads(
        base64.b64decode(status_obj.status["SuccessValue"]).decode("utf-8")
    )

    # Retrieve the PotApplication object
    appl = await PotApplication.objects.filter(
        applicant_id=data["project_id"]
    ).afirst()  # TODO: handle this being None

    # Create the PotApplicationReview object
    logger.info(f"create review...... {appl}")
    updated_at = datetime.fromtimestamp(update_data.get("updated_at") / 1000)
    await PotApplicationReview.objects.acreate(
        application_id=appl.id,
        reviewer_id=signerId,
        notes=update_data.get("review_notes"),
        status=update_data["status"],
        reviewed_at=updated_at,
        tx_hash=receipt.receipt_id,
    )

    # Update the PotApplication object
    await PotApplication.objects.filter(applicant_id=data["project_id"]).aupdate(
        **{"status": update_data["status"], "updated_at": updated_at}
    )

    logger.info("PotApplicationReview and PotApplication updated successfully.")


async def handle_default_list_status_change(
    data: dict, receiverId: str, status_obj: ExecutionOutcome
):
    logger.info(f"update project data: {data}, {receiverId}")

    result_data = json.loads(
        base64.b64decode(status_obj.status.get("SuccessValue")).decode("utf-8")
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


async def handle_list_upvote(
    data: dict, receiverId: str, signerId: str, receiptId: str
):
    logger.info(f"upvote list: {data}, {receiverId}")

    acct, _ = await Account.objects.aget_or_create(
        id=signerId,
    )

    created_at = datetime.now()

    await ListUpvote.objects.acreate(
        list_id=data.get("list_id") or receiverId,
        account_id=signerId,
        created_at=created_at,
    )

    await Activity.objects.acreate(
        signer_id=signerId,
        receiver_id=receiverId,
        timestamp=created_at,
        type="Upvote",
        action_result=data,
        tx_hash=receiptId,
    )

    logger.info("Upvote and activity records created successfully.")


async def handle_set_payouts(data: dict, receiverId: str, receipt: Receipt):
    logger.info(f"set payout data: {data}, {receiverId}")
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

    await PotPayout.objects.abulk_create(insertion_data)


async def handle_transfer_payout(
    data: dict, receiverId: str, receiptId: str, created_at: datetime
):
    data = data["payout"]
    logger.info(f"fulfill payout data: {data}, {receiverId}")
    payout = {
        "recipient_id": data["project_id"],
        "amount": data["amount"],
        "paid_at": data.get("paid_at", created_at),
        "tx_hash": receiptId,
    }
    await PotPayout.objects.filter(recipient_id=data["project_id"]).aupdate(**payout)


async def handle_payout_challenge(
    data: dict, receiverId: str, signerId: str, receiptId: str
):
    logger.info(f"challenging payout..: {data}, {receiverId}")
    created_at = datetime.now()
    payoutChallenge = {
        "challenger_id": signerId,
        "pot_id": receiverId,
        "created_at": created_at,
        "message": data["reason"],
        "tx_hash": receiptId,
    }
    await PotPayoutChallenge.objects.acreate(**payoutChallenge)

    await Activity.objects.acreate(
        signer_id=signerId,
        receiver_id=receiverId,
        timestamp=created_at,
        type="Challenge_Payout",
        action_result=payoutChallenge,
        tx_hash=receiptId,
    )


async def handle_list_admin_removal(data, receiverId, signerId, receiptId):
    logger.info(f"removing admin...: {data}, {receiverId}")
    list_obj = await List.objects.aget(id=data["list_id"])

    for acct in data["admins"]:
        await list_obj.admins.aremove({"admins_id": acct})  # ??

    activity = {
        "signer_id": signerId,
        "receiver_id": receiverId,
        "timestamp": datetime.now(),
        "type": "Remove_List_Admin",
        "tx_hash": receiptId,
    }

    await Activity.objects.acreate(**activity)


async def handle_nadabot_admin_add(data, receiverId):
    logger.info(f"adding admin...: {data}, {receiverId}")
    obj = await NadabotRegistry.objects.aget(id=receiverId)

    for acct in data["account_ids"]:
        await obj.admins.aadd({"admins_id": acct})  # ??


# TODO: Need to abstract some actions.
async def handle_batch_donations(
    receiverId: str,
    signerId: str,
    actionName: str,
    receipt_obj: Receipt,
    log_data: list,
):
    logger.info("BAtch Transaction for donation...")
    for event_data in log_data:
        donation_data = event_data["donation"]
        net_amount = int(donation_data["total_amount"]) - int(
            donation_data["protocol_fee"]
        )
        logger.info(f"Donation data: {donation_data}, {net_amount}")
        # insert donate contract which is the receiver id(because of activitry relationship mainly)
        donate_contract, _ = await Account.objects.aget_or_create(id=receiverId)
        donated_at = datetime.fromtimestamp(
            (donation_data.get("donated_at") or donation_data.get("donated_at_ms"))
            / 1000
        )

        # Upsert donor account
        donor, _ = await Account.objects.aget_or_create(id=donation_data["donor_id"])

        recipient = None
        if donation_data.get("recipient_id"):
            recipient, _ = await Account.objects.aget_or_create(
                id=donation_data["recipient_id"]
            )
        else:
            if not donation_data.get("matching_pool"):
                recipient, _ = await Account.objects.aget_or_create(
                    id=donation_data["project_id"]
                )

        if donation_data.get("referrer_id"):
            referrer, _ = await Account.objects.aget_or_create(
                id=donation_data["referrer_id"]
            )

        # Upsert token account
        token_acct, _ = await Account.objects.aget_or_create(
            id=(donation_data.get("ft_id") or "near")
        )

        # Upsert token
        try:
            token = await Token.objects.aget(id=token_acct)
        except Token.DoesNotExist:
            # TODO: fetch metadata from token contract (ft_metadata) and add decimals to token record. For now adding 12 which is most common
            token = await Token.objects.acreate(id=token_acct, decimals=12)

        # Fetch historical token data
        # late_p = await token.get_most_recent_price()
        try:
            logger.info("fetching historical price...")
            endpoint = f"{GECKO_URL}/coins/{donation_data.get('ft_id', 'near')}/history?date={format_date(donated_at)}&localization=false"
            response = requests.get(endpoint)
            price_data = response.json()
            unit_price = (
                price_data.get("market_data", {}).get("current_price", {}).get("usd")
            )
            logger.info(f"the usd price is what, {unit_price}")
            await TokenHistoricalPrice.objects.acreate(
                token=token,
                price_usd=unit_price,
            )
        except Exception as e:
            logger.warning(f"api rate limit? {e}")
            # TODO: NB: below method has not been tested
            # historical_price = await token.get_most_recent_price() # to use model methods, we might have to use asgiref sync_to_async
            historical = await TokenHistoricalPrice.objects.aget(
                token=token,
                price_usd=unit_price,
            )
            # print("fetched old price:", historical_price.price_usd)
            unit_price = historical.price_usd

        total_amount = donation_data["total_amount"]
        net_amount = net_amount - int(donation_data.get("referrer_fee") or 0)

        # Calculate USD amounts
        totalnearAmount = format_to_near(total_amount)
        netnearAmount = format_to_near(net_amount)
        total_amount_usd = unit_price * totalnearAmount
        net_amount_usd = unit_price * netnearAmount

        logger.info(f"inserting donations... {total_amount_usd}")
        donation = await Donation.objects.acreate(
            on_chain_id=donation_data["id"],
            donor=donor,
            total_amount=total_amount,
            total_amount_usd=total_amount_usd,
            net_amount_usd=net_amount_usd,
            net_amount=net_amount,
            ft=token_acct,
            message=donation_data.get("message"),
            donated_at=donated_at,
            matching_pool=donation_data.get("matching_pool", False),
            recipient=recipient,
            protocol_fee=donation_data["protocol_fee"],
            referrer=referrer if donation_data.get("referrer_id") else None,
            referrer_fee=donation_data.get("referrer_fee"),
            tx_hash=receipt_obj.receipt_id,
        )

        if actionName != "direct":
            logger.info("selecting pot to make public donation update")
            pot = await Pot.objects.aget(id=receiverId)
            await Donation.objects.filter(id=donation.id).aupdate(**{"pot": pot})
            potUpdate = {
                "total_public_donations": int(pot.total_public_donations or 0)
                + int(total_amount),
            }
            if donation_data.get("matching_pool"):
                potUpdate["total_matching_pool"] = (
                    pot.total_matching_pool or 0
                ) + total_amount
                potUpdate["matching_pool_donations_count"] = (
                    pot.matching_pool_donations_count or 0
                ) + 1
                # accountUpdate = {}
            else:
                potUpdate["public_donations_count"] = (
                    pot.public_donations_count or 0
                ) + 1
            await Pot.objects.filter(id=receiverId).aupdate(**potUpdate)

        # donation_recipient = donation_data.get('project_id', donation_data['recipient_id'])
        logger.info(
            f"update totl donated for {donor.id}, {donor.total_donations_out_usd + decimal.Decimal(total_amount_usd)}"
        )
        await Account.objects.filter(id=donor.id).aupdate(
            **{
                "total_donations_out_usd": donor.total_donations_out_usd
                + decimal.Decimal(total_amount_usd)
            }
        )
        if recipient:
            acct = await Account.objects.aget(id=recipient.id)
            logger.info(f"selected {acct} to perform donor count update")
            acctUpdate = {
                "donors_count": acct.donors_count + 1,
                "total_donations_in_usd": acct.total_donations_in_usd
                + decimal.Decimal(net_amount_usd),
            }
            await Account.objects.filter(id=recipient.id).aupdate(**acctUpdate)

        # Insert activity record
        await Activity.objects.acreate(
            signer_id=signerId,
            receiver_id=receiverId,
            timestamp=donation.donated_at,
            type="Donate_Direct",
            action_result=donation_data,
            tx_hash=receipt_obj.receipt_id,
        )


async def handle_new_donations(
    data: dict,
    receiverId: str,
    signerId: str,
    actionName: str,
    receipt_obj: Receipt,
    status_obj: ExecutionOutcome,
    log_data: list,
    created_at: datetime,
):
    logger.info(f"new donation data: {data}, {receiverId}")

    if (
        actionName == "direct"
    ) and receiverId == "donate.potlock.near":  # early pot donations followed similarly to direct donations i.e they returned result instead of events.
        logger.info("calling donate contract...")
        # Handle direct donation

        if not log_data:
            return

        if len(log_data) > 1:
            # log_data = [
            #     x
            #     for x in log_data
            #     if x["donation"]["recipient_id"] == data["recipient_id"]
            # ]
            return await handle_batch_donations(
                receiverId, signerId, actionName, receipt_obj, log_data
            )

        logger.info(f"event after possible filtering: {log_data}")

        event_data = log_data[0]
        donation_data = event_data["donation"]
        net_amount = int(donation_data["total_amount"]) - int(
            donation_data["protocol_fee"]
        )
        logger.info(f"Donation data: {donation_data}, {net_amount}")
        # insert donate contract which is the receiver id(because of activitry relationship mainly)
        donate_contract, _ = await Account.objects.aget_or_create(id=receiverId)

    else:
        result = status_obj.status.get("SuccessValue")
        if not result:
            return
        # Handle non-direct donation
        donation_data = json.loads(base64.b64decode(result).decode("utf-8"))
        net_amount = int(donation_data["net_amount"])

    donated_at = datetime.fromtimestamp(
        (donation_data.get("donated_at") or donation_data.get("donated_at_ms")) / 1000
    )

    # Upsert donor account
    donor, _ = await Account.objects.aget_or_create(id=donation_data["donor_id"])
    recipient = None

    if donation_data.get("recipient_id"):
        recipient, _ = await Account.objects.aget_or_create(
            id=donation_data["recipient_id"]
        )
    if donation_data.get("project_id"):
        recipient, _ = await Account.objects.aget_or_create(
            id=donation_data["project_id"]
        )

    if donation_data.get("referrer_id"):
        referrer, _ = await Account.objects.aget_or_create(
            id=donation_data["referrer_id"]
        )

    # Upsert token account
    token_acct, _ = await Account.objects.aget_or_create(
        id=(donation_data.get("ft_id") or "near")
    )

    # Upsert token
    try:
        token = await Token.objects.aget(id=token_acct)
    except Token.DoesNotExist:
        # TODO: fetch metadata from token contract (ft_metadata) and add decimals to token record. For now adding 12 which is most common
        token = await Token.objects.acreate(id=token_acct, decimals=12)

    # Fetch historical token data
    # late_p = await token.get_most_recent_price()
    try:
        logger.info("fetching historical price...")
        endpoint = f"{GECKO_URL}/coins/{donation_data.get('ft_id', 'near')}/history?date={format_date(donated_at)}&localization=false"
        response = requests.get(endpoint)
        price_data = response.json()
        unit_price = (
            price_data.get("market_data", {}).get("current_price", {}).get("usd")
        )
        await TokenHistoricalPrice.objects.acreate(  # need to change token model to use token as id
            token=token,
            price_usd=unit_price,
        )
    except Exception as e:
        logger.warning(f"api rate limit? {e}")
        # TODO: NB: below method has not been tested
        # historical_price = await token.get_most_recent_price() # to use model methods, we might have to use asgiref sync_to_async
        historical = await TokenHistoricalPrice.objects.aget(token=token)
        # print("fetched old price:", historical_price.price_usd)
        unit_price = historical.price_usd

    total_amount = donation_data["total_amount"]
    net_amount = net_amount - int(donation_data.get("referrer_fee") or 0)

    # Calculate USD amounts
    totalnearAmount = format_to_near(total_amount)
    netnearAmount = format_to_near(net_amount)
    total_amount_usd = unit_price * totalnearAmount
    net_amount_usd = unit_price * netnearAmount

    logger.info(f"inserting donations... {total_amount_usd}")
    if actionName == "direct":  #
        donation = await Donation.objects.acreate(
            on_chain_id=donation_data["id"],
            donor=donor,
            total_amount=total_amount,
            total_amount_usd=total_amount_usd,
            net_amount_usd=net_amount_usd,
            net_amount=net_amount,
            ft=token_acct,
            message=donation_data.get("message"),
            donated_at=donated_at,
            matching_pool=donation_data.get("matching_pool", False),
            recipient=recipient,
            protocol_fee=donation_data["protocol_fee"],
            referrer=referrer if donation_data.get("referrer_id") else None,
            referrer_fee=donation_data.get("referrer_fee"),
            tx_hash=receipt_obj.receipt_id,
        )

    if actionName != "direct":
        logger.info("selecting pot to make public donation update")
        pot = await Pot.objects.aget(id=receiverId)
        donation = await Donation.objects.acreate(
            on_chain_id=donation_data["id"],
            donor=donor,
            pot=pot,
            total_amount=total_amount,
            total_amount_usd=total_amount_usd,
            net_amount_usd=net_amount_usd,
            net_amount=net_amount,
            ft=token_acct,
            message=donation_data.get("message"),
            donated_at=donated_at,
            matching_pool=donation_data.get("matching_pool", False),
            recipient=recipient,
            protocol_fee=donation_data["protocol_fee"],
            referrer=referrer if donation_data.get("referrer_id") else None,
            referrer_fee=donation_data.get("referrer_fee"),
            tx_hash=receipt_obj.receipt_id,
        )
        potUpdate = {
            "total_public_donations": str(
                int(pot.total_public_donations or 0) + int(total_amount)
            ),
            "total_public_donations_usd": int(pot.total_public_donations_usd or 0.0)
            + total_amount_usd,
        }
        if donation_data.get("matching_pool"):
            potUpdate["total_matching_pool"] = str(
                int(pot.total_matching_pool or 0) + int(total_amount)
            )
            potUpdate["total_matching_pool"] = (
                pot.total_matching_pool_usd or 0.0
            ) + total_amount_usd
            potUpdate["matching_pool_donations_count"] = (
                pot.matching_pool_donations_count or 0
            ) + 1

            if recipient:
                await Account.objects.filter(id=recipient.id).aupdate(
                    **{
                        "total_matching_pool_allocations_usd": recipient.total_matching_pool_allocations_usd
                        + total_amount_usd
                    }
                )

            # accountUpdate = {}
        else:
            potUpdate["public_donations_count"] = (pot.public_donations_count or 0) + 1

        await Pot.objects.filter(id=receiverId).aupdate(**potUpdate)

    # donation_recipient = donation_data.get('project_id', donation_data['recipient_id'])
    logger.info(
        f"update totl donated for {donor.id}, {donor.total_donations_out_usd + decimal.Decimal(total_amount_usd)}"
    )
    await Account.objects.filter(id=donor.id).aupdate(
        **{
            "total_donations_out_usd": donor.total_donations_out_usd
            + decimal.Decimal(total_amount_usd)
        }
    )
    if recipient:
        acct = await Account.objects.aget(id=recipient.id)
        logger.info(f"selected {acct} to perform donor count update")
        acctUpdate = {
            "donors_count": acct.donors_count + 1,
            "total_donations_in_usd": acct.total_donations_in_usd
            + decimal.Decimal(net_amount_usd),
        }
        await Account.objects.filter(id=recipient.id).aupdate(**acctUpdate)

    # Insert activity record
    await Activity.objects.acreate(
        signer_id=signerId,
        receiver_id=receiverId,
        timestamp=donation.donated_at,
        type=(
            "Donate_Direct"
            if actionName == "direct"
            else (
                "Donate_Pot_Matching_Pool"
                if donation.matching_pool
                else "Donate_Pot_Public"
            )
        ),
        action_result=donation_data,
        tx_hash=receipt_obj.receipt_id,
    )

async def handle_update_default_human_threshold(
        data: dict,
        receiverId: str
):
    print("update landing...", data)

    reg = await NadabotRegistry.objects.filter(id=receiverId).aupdate(
        **{"default_human_threshold": data["default_human_threshold"]}
    )

    print("updated threshold..")


async def handle_new_provider(
    data: dict,
    receiverId: str,
    signerId: str
):
    print("new provider data:", data, receiverId)
    data = data["provider"]
    
    print(
        "upserting accounts involved",
        data["submitted_by"]
    )

    # Upsert donor account
    submitter, _ = await Account.objects.aget_or_create(id=data["submitted_by"])

    provider_id = data["id"]
    
    if provider_id == 13:
        provider_id = await cache.aget("last_id", 1)
        await cache.aset("last_id", provider_id+1)
    
    provider = await Provider.objects.acreate(
        id=provider_id,
        contract_id=data["contract_id"],
        method_name=data["method_name"],
        provider_name=data["provider_name"],
        description=data.get("description"),
        status=data["status"],
        admin_notes=data.get("admin_notes"),
        default_weight=data["default_weight"],
        gas=data.get("gas"),
        tags=data.get("tags"),
        icon_url=data.get("icon_url"),
        external_url=data.get("external_url"),
        submitted_by=data["submitted_by"],
        submitted_at_ms = datetime.fromtimestamp(data.get("submitted_at_ms") / 1000),
        stamp_validity_ms = datetime.fromtimestamp(data.get("stamp_validity_ms") / 1000) if data.get("stamp_validity_ms") else None,
        account_id_arg_name = data["account_id_arg_name"],
        custom_args = data.get("custom_args"),
        registry_id=receiverId
    )


async def handle_add_stamp(
    data: dict,
    receiverId: str,
    signerId: str
):
    print("new stamp data:", data, receiverId)
    data = data["stamp"]
    
    print(
        "upserting accounts involved",
        data["user_id"]
    )

    # Upsert donor account
    user, _ = await Account.objects.aget_or_create(id=data["user_id"])

    stamp = await Stamp.objects.acreate(
        user=user,
        provider_id=data["provider_id"],
        verification_date = datetime.fromtimestamp(data["validated_at_ms"] / 1000)
    )



async def cache_block_height(key: str, height: int, block_count: int) -> int:
    await cache.aset(key, height)
    # the cache os the default go to for the restart block, the db is a backup if the redis server crashes.
    if (block_count % int(settings.BLOCK_SAVE_HEIGHT or 400)) == 0:
        logger.info(f"saving daylight, {height}")
        await BlockHeight.objects.aupdate_or_create(
            id=1, defaults={"block_height": height, "updated_at": datetime.now()}
        )  # better than ovverriding model's save method to get a singleton? we need only one entry
    return height


def get_block_height(key: str) -> int:
    block_height = cache.get(key)
    if not block_height:
        record = BlockHeight.objects.filter(id=1).first()
        block_height = 104_922_190 if not record else record.block_height
    return block_height
