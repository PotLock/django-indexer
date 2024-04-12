import base64
import decimal
import json
import re
from datetime import datetime

import requests

from indexer_app.models import (
    Account,
    Activity,
    Donation,
    List,
    ListRegistration,
    ListUpvote,
    Pot,
    PotApplication,
    PotApplicationReview,
    PotFactory,
    PotPayout,
    PotPayoutChallenge,
    TokenHistoricalData,
)

GECKO_URL = "https://api.coingecko.com/api/v3"

created_at = datetime.now()

def format_date(date):
    year = date.year
    month = str(date.month).zfill(2)
    day = str(date.day).zfill(2)
    return f"{day}-{month}-{year}"

def format_to_near(yocto_amount):
    near_amount = int(yocto_amount) / (10 ** 24)
    return near_amount

async def handle_new_pot(data, receiverId, signerId, predecessorId, receiptId):
    print("new pot deployment process... upsert accounts,")

    # Upsert accounts
    owner, _ = await Account.objects.aget_or_create(
        id=data["owner"]
    )
    signer, _ = await Account.objects.aget_or_create(
        id=signerId
    )
    receiver, _ = await Account.objects.aget_or_create(
        id=receiverId
    )

    print("upsert chef")
    if data.get("chef"):
        chef, _ = await Account.objects.aget_or_create(
            id=data["chef"]
        )

    # Create Pot object
    print("create pot....")
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
        application_start=datetime.fromtimestamp(data["application_start_ms"]/1000),
        application_end=datetime.fromtimestamp(data["application_end_ms"]/1000),
        matching_round_start=datetime.fromtimestamp(data["public_round_start_ms"]/1000),
        matching_round_end=datetime.fromtimestamp(data["public_round_end_ms"]/1000),
        registry_provider=data["registry_provider"],
        min_matching_pool_donation_amount=data["min_matching_pool_donation_amount"],
        sybil_wrapper_provider=data["sybil_wrapper_provider"],
        custom_sybil_checks=data.get("custom_sybil_checks"),
        custom_min_threshold_score=data.get("custom_min_threshold_score"),
        referral_fee_matching_pool_basis_points=data["referral_fee_matching_pool_basis_points"],
        referral_fee_public_round_basis_points=data["referral_fee_public_round_basis_points"],
        chef_fee_basis_points=data["chef_fee_basis_points"],
        total_matching_pool="0",
        matching_pool_balance="0",
        matching_pool_donations_count=0,
        total_public_donations="0",
        public_donations_count=0,
        cooldown_period_ms=None,
        all_paid_out=False,
        protocol_config_provider=data["protocol_config_provider"]
    )

    # Add admins to the Pot
    if data.get("admins"):
        for admin_id in data["admins"]:
            admin, _ = await Account.objects.aget_or_create(
                id=admin_id
            )
            potObject.admins.aadd(admin)

    # Create activity object
    await Activity.objects.acreate(
        signer_id=signerId,
        receiver_id=receiverId,
        timestamp=created_at,
        type="Deploy_Pot",
        action_result=data,
        tx_hash=receiptId
    )

async def handle_new_factory(data, receiverId):
    print("upserting accounts...")
    
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

    print("creating factory....")
    # Create Factory object
    factory = await PotFactory.objects.acreate(
        id=receiver,
        owner=owner,
        deployed_at=created_at,
        source_metadata= data["source_metadata"],
        protocol_fee_basis_points=data["protocol_fee_basis_points"],
        protocol_fee_recipient=protocol_fee_recipient_account,
        require_whitelist=data["require_whitelist"]
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
            deployer, _ = await Account.objects.aget_or_create(
                id=deployer_id
            )
            await factory.whitelisted_deployers.aadd(deployer)


async def handle_registry(signerId, receiverId, status_obj):
    # receipt = block.receipts().filter(receiptId=receiptId)[0]
    data = json.loads(base64.b64decode(status_obj.status.get("SuccessValue")).decode("utf-8"))

    print("creating list.....", data)

    
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


    print("upserting involveed accts...")

    await Account.objects.aget_or_create(
        id=data["owner"]
    )

    await Account.objects.aget_or_create(
        id=signerId
    )

    await Account.objects.aget_or_create(
        id=receiverId
    )

    if data.get("admins"):
        for admin_id in data["admins"]:
            admin_object, _ = await Account.objects.aget_or_create(
                id=admin_id,
            )
            await listObject.admins.aadd(admin_object)


async def handle_new_project(data, receiverId, signerId, receipt, status_obj):
    print("new Project data::", data, receiverId)

    # Retrieve receipt data
    if receipt is None:
        return

    reg_data = json.loads(base64.b64decode(status_obj.status["SuccessValue"]).decode("utf-8"))
    print("Receipt data:", reg_data)

    # Prepare data for insertion
    project_list = []
    insert_data = []
    for dt in reg_data:
        project_list.append({"id": dt["registrant_id"]})
        insert_data.append({
            "id": dt["id"],
            "registrant_id": dt["registrant_id"],
            "list_id": dt["list_id"],
            "status": dt["status"],
            "submitted_at": datetime.fromtimestamp(dt["submitted_ms"]/1000),
            "updated_at": datetime.fromtimestamp(dt["updated_ms"]/1000),
            "registered_by_id": dt["registered_by"],
            "admin_notes": dt.get("admin_notes"),
            "registrant_notes": dt.get("registrant_notes"),
            "tx_hash": receipt.receipt_id
        })
    

    try:
        await Account.objects.abulk_create(objs=[Account(**data) for data in project_list], ignore_conflicts=True)
        await Account.objects.aget_or_create(
            id=signerId
        )
        print("Upserted accounts/registrants(signer)")
    except Exception as e:
        print(f"Encountered error trying to get create acct: {e}")

    try:
        await ListRegistration.objects.abulk_create([ListRegistration(**data) for data in insert_data])
    except Exception as e:
        print(f"Encountered error trying to create list: {e}")

    print("Upserted List List:", reg_data)

    # Insert activity
    try:
        await Activity.objects.acreate(
            signer_id=signerId,
            receiver_id=receiverId,
            timestamp=insert_data[0]["submitted_at"],
            type="Register_Batch",
            action_result=reg_data,
            tx_hash=receipt.receipt_id
        )
    except Exception as e:
        print(f"Encountered error trying to insert activity: {e}")

async def handle_project_registration_update(data, receiverId, status_obj):
    print("new Project data::", data, receiverId)

    data = json.loads(base64.b64decode(status_obj.status.get("SuccessValue")).decode("utf-8"))

    # Prepare data for update
    regUpdate = {
        "status": data["status"],
        "admin_notes": data["admin_notes"],
        "updated_at": datetime.fromtimestamp(data["updated_ms"] / 1000),
    }

    try:
        # Perform the update
        await ListRegistration.objects.filter(id=data["id"]).aupdate(**regUpdate)
        print("Updated ListRegistration with id:", data["id"])
    except Exception as e:
        print(f"Encountered error trying to update ListRegistration: {e}")

async def handle_pot_application(data, receiverId, signerId, receipt, status_obj):
    # receipt = block.receipts().filter(lambda receipt: receipt.receiptId == receiptId)[0]
    result = status_obj.status.get("SuccessValue")
    if not result:
        return

    appl_data = json.loads(base64.b64decode(result).decode("utf-8"))
    print("new pot application data::", data, appl_data["message"], appl_data["submitted_at"])

    # Update or create the account
    project, _ = await Account.objects.aget_or_create(
        id=data["project_id"],
    )

    signer, _ = await Account.objects.aget_or_create(
        id=signerId,
    )

    # Create the PotApplication object
    print("creating application.......")
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
    print("creating activity for action....")
    await Activity.objects.acreate(
        signer=signer,
        receiver_id=receiverId,
        timestamp=application.submitted_at,
        type="Submit_Application",
        action_result=appl_data,
        tx_hash=receipt.receipt_id,
    )

    print("PotApplication and Activity created successfully.")

async def handle_application_status_change(data, receiverId, signerId, receipt, status_obj):
    print("pot application update data::", data, receiverId)

    # receipt = next(receipt for receipt in block.receipts() if receipt.receiptId == receiptId)
    update_data = json.loads(base64.b64decode(status_obj.status["SuccessValue"]).decode("utf-8"))

    # Retrieve the PotApplication object
    appl = await PotApplication.objects.filter(applicant_id=data["project_id"]).afirst()

    # Create the PotApplicationReview object
    print("create review......", appl)
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
    await PotApplication.objects.filter(applicant_id=data["project_id"]).aupdate(**{"status": update_data["status"], "updated_at": updated_at})

    print("PotApplicationReview and PotApplication updated successfully.")

async def handle_default_list_status_change(data, receiverId, status_obj):
    print("update project data::", data, receiverId)

    result_data = json.loads(base64.b64decode(status_obj.status.get("SuccessValue")).decode("utf-8"))

    list_id = data.get("registration_id")
    list_update = {
        "name": result_data["name"],
        "owner_id": result_data["owner"],
        "default_registration_status": result_data["default_registration_status"],
        "admin_only_registrations": result_data["admin_only_registrations"],
        "updated_at": result_data["updated_at"],
    }
    if result_data.get("description"):
        list_update["description"] =  result_data["description"]
    if result_data.get("cover_image_url"):
        list_update["cover_image_url"] =  result_data["cover_image_url"]

    await List.objects.filter(id=list_id).aupdate(**list_update)

    print("List updated successfully.")

async def handle_up_voting(data, receiverId, signerId, receiptId):
    print("upvote list::", data, receiverId)

    acct, _ = await Account.objects.aget_or_create(
        id=signerId,
    )

    created_at = datetime.now()

    await ListUpvote.objects.acreate(
        list_id = data.get("list_id") or receiverId,
        account_id = signerId,
        created_at = created_at,
    )

    await Activity.objects.acreate(
        signer_id = signerId,
        receiver_id= receiverId,
        timestamp = created_at,
        type = "Upvote",
        action_result = data,
        tx_hash = receiptId,
    )


    print("Upvote and activity records created successfully.")

async def handle_setting_payout(data, receiverId, receipt):
    print("set payout data::", data, receiverId)
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


async def handle_payout(data, receiverId, receiptId):
    data = data["payout"]
    print("fulfill payout data::", data, receiverId)
    payout = {
        "recipient_id": data["project_id"],
        "amount": data["amount"],
        "paid_at": data.get("paid_at", created_at),
        "tx_hash": receiptId,
    }
    await PotPayout.objects.filter(recipient_id=data["project_id"]).aupdate(**payout)


async def handle_payout_challenge(data, receiverId, signerId, receiptId):
    print("challenging payout..: ", data, receiverId)
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
        signer_id = signerId,
        receiver_id = receiverId,
        timestamp = created_at,
        type = "Challenge_Payout",
        action_result = payoutChallenge,
        tx_hash = receiptId,
    )


async def handle_list_admin_removal(data, receiverId, signerId, receiptId):
    print("removing admin...:", data, receiverId)
    list_obj = await List.objects.aget(id=data["list_id"])

    for acct in data["admins"]:
        list_obj.admins.remove({"admins_id": acct}) # ??

    activity = {
        "signer_id": signerId,
        "receiver_id": receiverId,
        "timestamp": datetime.now(),
        "type": "Remove_List_Admin",
        "tx_hash": receiptId,
    }

    await Activity.objects.acreate(**activity)

async def handle_new_donations(data, receiverId, signerId, actionName, receipt_obj, status_obj, log_data):
    print("new donation data:", data, receiverId)

    if actionName == "direct":
        print("calling donate contract...")
        # Handle direct donation

        if not log_data: return
        
        if len(log_data) > 1:
            log_data = [x for x in log_data if x['donation']['recipient_id'] == data['recipient_id']]
        
        print("event after possible filtering:", log_data)

        event_data = log_data[0]
        donation_data = event_data['donation']
        net_amount =  int(donation_data['total_amount']) - int(donation_data['protocol_fee'])
        print("Donation data:", donation_data, net_amount)
        # insert donate contract which is the receiver id(because of activitry relationship mainly)
        donate_contract, _ = await Account.objects.aget_or_create(id=receiverId)

    else:
        # Handle non-direct donation
        donation_data = json.loads(base64.b64decode(status_obj.status.get("SuccessValue")).decode("utf-8"))
        net_amount = int(donation_data['net_amount'])
        print("donation data decoded...", donation_data)

    donated_at = datetime.fromtimestamp((donation_data.get('donated_at') or donation_data.get('donated_at_ms')) / 1000)

    print("upserting accounts involved", donation_data['donor_id'], donation_data.get('recipient_id'))
    
    # Upsert donor account
    donor, _ = await Account.objects.aget_or_create(id=donation_data['donor_id'])

    if donation_data.get('recipient_id'):
        recipient, _ = await Account.objects.aget_or_create(id=donation_data['recipient_id'])
    else:
        recipient, _ = await Account.objects.aget_or_create(id=donation_data['project_id'])

    if donation_data.get('referrer_id'):
        referrer, _ = await Account.objects.aget_or_create(id=donation_data['referrer_id'])

    print("get set", donor, recipient)

    # Upsert token account
    token, _ = await Account.objects.aget_or_create(id=(donation_data.get('ft_id') or'near'))


    
    # Fetch historical token data
    try:
        print("fetching historical price...")
        endpoint = f"{GECKO_URL}/coins/{donation_data.get('ft_id', 'near')}/history?date={format_date(donated_at)}&localization=false"
        response = requests.get(endpoint)
        price_data = response.json()
        unit_price = price_data.get('market_data', {}).get('current_price', {}).get('usd')
        hist_data = {
            'token_id': donation_data.get('ft_id', 'near'),
            'last_updated': created_at,
            'historical_price': unit_price,
        }
        print("price data to insert", hist_data)
        # Replace with appropriate Django model insertion
        await TokenHistoricalData.objects.aupdate_or_create(token_id=hist_data['token_id'], defaults={'last_updated': hist_data['last_updated'], 'historical_price_usd': hist_data['historical_price']})
    except Exception as e:
        print("api rate limit?", e)
        # Replace with appropriate Django model selection
        historical_price = await TokenHistoricalData.objects.aget(token_id=donation_data.get('ft_id', 'near')).first()
        print("fetched old price:", historical_price.historical_price)
        unit_price = historical_price.historical_price

    total_amount = donation_data['total_amount']
    net_amount = net_amount - (donation_data.get('referrer_fee') or 0)

    # Calculate USD amounts
    totalnearAmount = format_to_near(total_amount)
    netnearAmount = format_to_near(net_amount)
    total_amount_usd = unit_price * totalnearAmount
    net_amount_usd = unit_price * netnearAmount

    print("inserting donations...", total_amount_usd)
    donation = await Donation.objects.acreate(
        id=donation_data['id'],
        donor=donor,
        total_amount=total_amount,
        total_amount_usd=total_amount_usd,
        net_amount_usd=net_amount_usd,
        net_amount=net_amount,
        ft=token,
        message=donation_data.get('message'),
        donated_at=donated_at,
        matching_pool=donation_data.get('matching_pool', False),
        recipient=recipient,
        protocol_fee=donation_data['protocol_fee'],
        referrer=referrer if donation_data.get('referrer_id') else None,
        referrer_fee=donation_data.get('referrer_fee'),
        tx_hash=receipt_obj.receipt_id,
    )

    if actionName != "direct":
        print("selecting pot to make public donation update")
        pot = await Pot.objects.aget(id=receiverId)
        Donation.objects.filter(id=donation.id).aupdate(**{"pot": pot})
        potUpdate = {
            'total_public_donations': (pot.total_public_donations or 0) + total_amount,
        }
        if donation_data.get('matching_pool'):
            potUpdate['total_matching_pool'] = (pot.total_matching_pool or 0) + total_amount
            potUpdate['matching_pool_donations_count'] = (pot.matching_pool_donations_count or 0) + 1
            # accountUpdate = {}
        else:
            potUpdate['public_donations_count'] = (pot.public_donations_count or 0) + 1
        await Pot.objects.filter(id=pot.id).aupdate(**potUpdate)

    # donation_recipient = donation_data.get('project_id', donation_data['recipient_id'])
    print(f"update totl donated for {donor.id}, {donor.total_donated_usd + decimal.Decimal(total_amount_usd)}")
    await Account.objects.filter(id=donor.id).aupdate(**{"total_donated_usd" : donor.total_donated_usd + decimal.Decimal(total_amount_usd)})
    if recipient:
        acct = await Account.objects.aget(id=recipient.id)
        print(f"selected {acct} to perform donor count update")
        acctUpdate = {
            'donors_count': acct.donors_count + 1,
            'total_donations_received_usd': acct.total_donations_received_usd + decimal.Decimal(net_amount_usd)
        }
        await Account.objects.filter(id=recipient.id).aupdate(**acctUpdate)

    # Insert activity record
    await Activity.objects.acreate(
        signer_id=signerId,
        receiver_id=receiverId,
        timestamp=donation.donated_at,
        type="Donate_Direct" if actionName == "direct" else ("Donate_Pot_Matching_Pool" if donation.matching_pool else "Donate_Pot_Public"),
        action_result=donation_data,
        tx_hash=receipt_obj.receipt_id,
    )

def match_version_pattern(receiver):
    pattern = r'^v\d+\.potfactory\.potlock\.near$'
    return bool(re.match(pattern, receiver))
