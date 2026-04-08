import asyncio
from datetime import datetime
import json
import logging
import time
from pathlib import Path

import requests
from billiard.exceptions import WorkerLostError
from celery import shared_task
from celery.signals import task_revoked, worker_shutdown
from django.conf import settings
from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Cast, NullIf
from near_lake_framework import LakeConfig, streamer, Network
import stellar_sdk
from stellar_sdk.soroban_server import EventFilter, EventFilterType
from stellar_sdk import Address, stellar_xdr, scval

from accounts.models import Account
from base.celery import SPOT_INDEXER_QUEUE_NAME
from donations.models import Donation
from grantpicks.models import Round, RoundDeposit, StellarEvent, ProjectContact
from indexer_app.handler import handle_streamer_message
from pots.models import Pot, PotApplication, PotApplicationStatus, PotPayout

from .logging import logger
from .utils import (
    create_or_update_round,
    create_round_application,
    create_round_payout,
    get_block_height,
    get_ledger_sequence,
    handle_stellar_list_admin_ops,
    handle_stellar_list_update,
    process_application_to_round,
    process_project_event,
    process_rounds_deposit_event,
    process_vote_event,
    save_block_height,
    update_application,
    update_approved_projects,
    update_ledger_sequence,
    update_round_payout,
    handle_stellar_list,
    handle_new_stellar_list_registration,
    update_list_registrations,
)

CURRENT_BLOCK_HEIGHT_KEY = "current_block_height"


async def indexer(from_block: int, to_block: int):
    """
    Runs the lake indexer framework
    """
    # Initialize lake indexer
    logger.info(f"from block: {from_block}")

    lake_config = LakeConfig(
        Network.TESTNET if settings.ENVIRONMENT == "testnet" else Network.MAINNET,
        settings.AWS_ACCESS_KEY_ID,
        settings.AWS_SECRET_ACCESS_KEY,
        from_block,
    )
    _, streamer_messages_queue = streamer(lake_config)

    while True:
        try:
            # Log time before fetching a new block
            fetch_start_time = time.time()
            # streamer_message is the current block
            streamer_message = await asyncio.wait_for(
                streamer_messages_queue.get(), settings.INDEXER_STREAMER_WAIT_TIME
            )
            fetch_end_time = time.time()
            logger.info(
                f"Time to fetch new block: {fetch_end_time - fetch_start_time:.4f} seconds"
            )
            # Log time before caching block height
            save_start_time = time.time()
            # Update current block height
            asyncio.create_task(
                save_block_height(
                    streamer_message.block.header.height,
                    streamer_message.block.header.timestamp,
                )
            )
            save_end_time = time.time()

            logger.info(
                f"Time to save block height: {save_end_time - save_start_time:.4f} seconds"
            )

            # Log time before handling the streamer message
            handle_start_time = time.time()
            await handle_streamer_message(streamer_message)
            handle_end_time = time.time()
            logger.info(
                f"Time to handle streamer message: {handle_end_time - handle_start_time:.4f} seconds"
            )

            # Log total time for one iteration
            iteration_end_time = time.time()
            logger.info(
                f"Total time for one iteration: {iteration_end_time - fetch_start_time:.4f} seconds"
            )

        except asyncio.TimeoutError:
            logger.warning(
                "Stream stalled: no new blocks within timeout, restarting..."
            )  # raise Exception so sytemd can restart the worker
            raise Exception("Stream stalled: restarting...")

        except Exception as e:
            logger.error(f"Error in streamer_messages_queue: {e}")


@shared_task
def listen_to_near_events():
    logger.info("Listening to NEAR events...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Update below with desired network & block height
        start_block = get_block_height()
        # start_block = 112682360
        logger.info(f"what's the start block, pray tell? {start_block - 1}")
        loop.run_until_complete(indexer(start_block - 1, None))
    except WorkerLostError:
        pass  # don't log to Sentry
    finally:
        loop.close()


@shared_task(queue=SPOT_INDEXER_QUEUE_NAME)
def spot_index_near_events(start_block):
    logger.info("Spot indexing NEAR events...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        logger.info(f"Spot index start block: {start_block - 1}")
        loop.run_until_complete(indexer(start_block - 1, None))
    except WorkerLostError:
        pass  # don't log to Sentry
    finally:
        loop.close()


# @worker_shutdown.connect
# def worker_shutdown_handler(sig, how, exitcode, **kwargs):
#     if sig == 15:
#         logger.info(
#             "Celery worker shutdown initiated by signal 15 (SIGTERM)."
#         )  # avoid logging to Sentry
#     else:
#         logger.error("Celery worker shutdown due to signal %d.", sig)


jobs_logger = logging.getLogger("jobs")


# @shared_task
# def fetch_usd_prices():
#     donations = Donation.objects.filter(
#         Q(total_amount_usd__isnull=True) | Q(net_amount_usd__isnull=True)
#     )
#     jobs_logger.info(f"Fetching USD prices for {donations.count()} donations...")
#     loop = asyncio.get_event_loop()
#     tasks = [loop.create_task(donation.fetch_usd_prices()) for donation in donations]
#     loop.run_until_complete(asyncio.gather(*tasks))


@shared_task
def fetch_usd_prices():
    donations = Donation.objects.filter(
        Q(total_amount_usd__isnull=True)
        | Q(net_amount_usd__isnull=True)
        | Q(protocol_fee_usd__isnull=True)
        | Q(referrer_fee__isnull=False, referrer_fee_usd__isnull=True)
        | Q(chef_fee__isnull=False, chef_fee_usd__isnull=True)
    )
    donations_count = donations.count()
    jobs_logger.info(f"Fetching USD prices for {donations_count} donations...")
    for donation in donations:
        try:
            donation.fetch_usd_prices()
        except Exception as e:
            jobs_logger.error(
                f"Failed to fetch USD prices for donation {donation.id}: {e}"
            )
    jobs_logger.info(f"USD prices fetched for {donations_count} donations.")

    # payouts
    payouts = PotPayout.objects.filter(
        amount_paid_usd__isnull=True, paid_at__isnull=False
    )
    payouts_count = payouts.count()
    jobs_logger.info(f"Fetching USD prices for {payouts_count} payouts...")
    for payout in payouts:
        try:
            payout.fetch_usd_prices()
        except Exception as e:
            jobs_logger.error(f"Failed to fetch USD prices for payout {payout.id}: {e}")

    jobs_logger.info(f"USD prices fetched for {payouts_count} payouts.")


@shared_task
def update_pot_statistics():
    pots = Pot.objects.all()
    pots_count = pots.count()
    jobs_logger.info(f"Updating statistics for {pots_count} pots...")
    for pot in pots:
        matching_pool_donations = Donation.objects.filter(pot=pot, matching_pool=True)
        public_donations = Donation.objects.filter(pot=pot, matching_pool=False)
        try:
            print(f"Processing pot: {pot.account}")

            # total matching pool
            pot.total_matching_pool = sum(
                int(donation.total_amount)
                for donation in matching_pool_donations
                if donation.total_amount.isdigit()
            )
            jobs_logger.info(f"Total matching pool: {pot.total_matching_pool}")

            # total matching pool usd
            pot.total_matching_pool_usd = sum(
                donation.total_amount_usd
                for donation in matching_pool_donations
                if donation.total_amount_usd
            )
            jobs_logger.info(f"Total matching pool USD: {pot.total_matching_pool_usd}")

            # matching pool balance (get from contract)
            url = (
                f"{settings.FASTNEAR_RPC_URL}/account/{pot.account.id}/view/get_config"
            )
            response = requests.get(url)
            if response.status_code != 200:
                jobs_logger.error(
                    f"Failed to get matching pool balance for pot {pot.account}: {response.text}"
                )
            else:
                data = response.json()
                pot.matching_pool_balance = data["matching_pool_balance"]
                jobs_logger.info(
                    f"Matching pool balance for pot {pot.account}: {pot.matching_pool_balance}"
                )

            # matching pool donations count
            pot.matching_pool_donations_count = matching_pool_donations.count()
            jobs_logger.info(
                f"Matching pool donations count: {pot.matching_pool_donations_count}"
            )

            # total public donations
            pot.total_public_donations = sum(
                int(donation.total_amount)
                for donation in public_donations
                if donation.total_amount.isdigit()
            )
            jobs_logger.info(f"Total public donations: {pot.total_public_donations}")

            # total public donations usd
            pot.total_public_donations_usd = sum(
                donation.total_amount_usd
                for donation in public_donations
                if donation.total_amount_usd
            )
            jobs_logger.info(
                f"Total public donations USD: {pot.total_public_donations_usd}"
            )

            # public donations count
            pot.public_donations_count = public_donations.count()
            jobs_logger.info(f"Public donations count: {pot.public_donations_count}")

            # Save changes
            pot.save(
                update_fields=[
                    "total_matching_pool",
                    "total_matching_pool_usd",
                    "matching_pool_balance",
                    "matching_pool_donations_count",
                    "total_public_donations",
                    "total_public_donations_usd",
                    "public_donations_count",
                ]
            )
        except Exception as e:
            jobs_logger.error(f"Failed to update statistics for pot {pot.account}: {e}")


@shared_task
def update_account_statistics():
    accounts = Account.objects.all()
    accounts_count = accounts.count()
    jobs_logger.info(f"Updating statistics for {accounts_count} accounts...")
    for account in accounts:
        try:
            # jobs_logger.info(f"Updating statistics for account {account.id}...")
            # donors count
            account.donors_count = Donation.objects.filter(recipient=account).aggregate(
                Count("donor", distinct=True)
            )["donor__count"]

            # donations received usd
            account.total_donations_in_usd = (
                Donation.objects.filter(recipient=account).aggregate(
                    Sum("total_amount_usd")
                )["total_amount_usd__sum"]
                or 0
            )

            # donations sent usd
            account.total_donations_out_usd = (
                Donation.objects.filter(donor=account).aggregate(
                    Sum("total_amount_usd")
                )["total_amount_usd__sum"]
                or 0
            )

            # matching pool allocations usd
            account.total_matching_pool_allocations_usd = (
                PotPayout.objects.filter(
                    recipient=account, paid_at__isnull=False
                ).aggregate(Sum("amount_paid_usd"))["amount_paid_usd__sum"]
                or 0
            )

            # Save changes
            account.save(
                update_fields=[
                    "donors_count",
                    "total_donations_in_usd",
                    "total_donations_out_usd",
                    "total_matching_pool_allocations_usd",
                ]
            )
            # jobs_logger.info(f"Account {account.id} statistics updated.")
        except Exception as e:
            jobs_logger.error(
                f"Failed to update statistics for account {account.id}: {e}"
            )
    jobs_logger.info(f"Account stats for {accounts.count()} accounts updated.")


def address_to_string(obj):
    if isinstance(obj, Address):
        return obj.address
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


# Todo: Change model so thatthe event indexer saves the event and queues a task to immediately process the event,
# so we don;t have a separate beat that's looping through


@shared_task
def stellar_event_indexer():
    server = stellar_sdk.SorobanServer(settings.STELLAR_RPC_URL)
    contract_ids = [
        settings.STELLAR_CONTRACT_ID,
        settings.STELLAR_PROJECTS_REGISTRY_CONTRACT,
        settings.STELLAR_LIST_CONTRACT,
    ]
    if contract_ids == ["", "", ""]:
        return
    start_sequence = get_ledger_sequence()
    # start_sequence = 668843
    if not start_sequence:
        start_sequence = 58655649
    jobs_logger.info(
        f"Ingesting Stellar events from ledger {start_sequence}... contracts: {contract_ids}"
    )
    try:
        # Fetch events for the current sequence
        events = server.get_events(
            start_ledger=start_sequence,
            filters=[
                EventFilter(
                    event_type=EventFilterType.CONTRACT, contract_ids=contract_ids
                )
            ],
        )
        stellar_events = []
        ledger_timestamp = datetime.now()
        for event in events.events:
            event_name = stellar_sdk.scval.to_native(event.topic[0])
            event_value = event.value
            if event.value is not None:
                event_value = stellar_sdk.scval.to_native(event.value)
                event_value = json.loads(
                    json.dumps(event_value, default=address_to_string)
                )
            stellar_events.append(
                StellarEvent(
                    ledger_sequence=event.ledger,
                    event_type=event_name,
                    contract_id=event.contract_id,
                    ingested_at=event.ledger_close_at,
                    transaction_hash=event.transaction_hash,
                    data=event_value,
                )
            )

        if len(stellar_events) > 0:
            StellarEvent.objects.bulk_create(objs=stellar_events, ignore_conflicts=True)
            ledger_timestamp = event.ledger_close_at
            jobs_logger.info(
                f"Ingested {len(stellar_events)} Stellar events from ledger {start_sequence} to {events.latest_ledger}..."
            )
        update_ledger_sequence(events.latest_ledger, ledger_timestamp)

    except Exception as e:
        jobs_logger.error(f"Error processing ledger {start_sequence}: {e}")


@shared_task
def process_stellar_events():
    unprocessed_events = StellarEvent.objects.filter(processed=False).order_by("id")
    jobs_logger.info(
        f"Processing {unprocessed_events.count()} unprocessed Stellar events..."
    )

    for event in unprocessed_events:
        try:
            event_data = event.data
            event_name = event.event_type

            if event_name == "c_project":
                event.processed = process_project_event(event_data)

            elif event_name == "c_round" or event_name == "u_round":
                # Mark event as processed
                event.processed = create_or_update_round(
                    event_data, event.contract_id, event.ingested_at
                )

            elif event_name == "apply_to_round":
                # Mark event as processed
                event.processed = process_application_to_round(
                    event_data, event.transaction_hash
                )

            elif event_name == "c_app":
                event.processed = create_round_application(
                    event_data, event.transaction_hash
                )

            elif event_name == "u_app":  # application review and aproval
                event.processed = update_application(event_data, event.transaction_hash)

            elif event_name == "u_ap":
                event.processed = update_approved_projects(
                    event_data,
                    time_stamp=event.ingested_at,
                    tx_hash=event.transaction_hash,
                )

            elif event_name == "c_depo":
                event.processed = process_rounds_deposit_event(
                    event_data, event.transaction_hash
                )

            elif event_name == "c_vote":
                event.processed = process_vote_event(event_data, event.transaction_hash)
            elif event_name == "c_pay":
                event.processed = create_round_payout(
                    event_data, event.transaction_hash
                )
            elif event_name == "u_pay":
                event.processed = update_round_payout(
                    event_data, event.transaction_hash
                )
            elif event_name == "c_list":
                event.processed = handle_stellar_list(
                    event_data, event.contract_id, event.ingested_at
                )
            elif event_name == "u_list":
                event.processed = handle_stellar_list_update(
                    event_data, event.contract_id, event.ingested_at
                )
            elif event_name == "c_reg":
                event.processed = handle_new_stellar_list_registration(
                    event_data, event.contract_id, event.transaction_hash
                )
            elif event_name == "u_reg":
                event.processed = update_list_registrations(
                    event_data, event.contract_id
                )
            elif event_name == "u_adm":
                event.processed = handle_stellar_list_admin_ops(
                    event_data,
                    event.contract_id,
                    event.ingested_at,
                    event.transaction_hash,
                )
            event.save()

        except Exception as e:
            jobs_logger.error(
                f"Error processing Stellar event {event_name, event.id}: {e}"
            )

    jobs_logger.info(f"Finished processing Stellar events.")


@shared_task
def backfill_missing_data(force=False):
    """
    Biweekly backfill task: compare on-chain state with DB and fill any gaps.

    Catches data that was missed when on-demand sync API calls failed but the
    transaction went through on-chain. Handles: accounts, lists, registrations,
    donations, pots (applications & payouts), and campaigns (if app is installed).

    Scheduled every Sunday at 3 AM UTC, but only runs on even ISO weeks
    to achieve a biweekly (~every 14 days) cadence.

    Args:
        force: If True, skip the week parity check (for manual runs).
    """
    import base64
    import json
    import time as _time
    from datetime import datetime, timezone

    import requests
    from django.apps import apps
    from django.conf import settings
    from django.db import connection

    from accounts.models import Account
    from donations.models import Donation
    from lists.models import List, ListRegistration
    from pots.models import Pot, PotApplication, PotPayout
    from tokens.models import Token

    # Only run on even ISO weeks for biweekly cadence (skip check if forced)
    now = datetime.now(tz=timezone.utc)
    if not force and now.isocalendar().week % 2 != 0:
        jobs_logger.info("Backfill skipped — odd week (runs biweekly on even weeks).")
        return

    LISTS_CONTRACT = f"lists.{settings.POTLOCK_TLA}"
    DONATE_CONTRACT = f"donate.{settings.POTLOCK_TLA}"

    def rpc_call(contract_id, method_name, args=None, timeout=60):
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
                "account_id": contract_id,
                "method_name": method_name,
                "args_base64": args_base64,
                "finality": "optimistic",
            },
        }
        for rpc_url in rpc_endpoints:
            try:
                response = requests.post(rpc_url, json=payload, timeout=timeout)
                result = response.json()
                if "error" in result:
                    continue
                if "error" in result.get("result", {}):
                    continue
                result_field = result.get("result", {})
                if "result" not in result_field:
                    return None
                result_bytes = bytes(result_field["result"])
                return json.loads(result_bytes.decode())
            except Exception:
                continue
        return None

    def rpc_call_paginated(contract_id, method_name, base_args, page_size=300, delay=0.5):
        all_results = []
        page = 0
        while True:
            args = {**base_args, "from_index": page * page_size, "limit": page_size}
            results = rpc_call(contract_id, method_name, args, timeout=120)
            if results is None:
                break
            all_results.extend(results)
            if len(results) < page_size:
                break
            page += 1
            _time.sleep(delay)
        return all_results

    def fix_sequences():
        tables = [
            ("lists_listregistration", "id"),
            ("lists_list", "id"),
            ("donations_donation", "id"),
        ]
        with connection.cursor() as cursor:
            for table, col in tables:
                try:
                    seq_name = f"{table}_{col}_seq"
                    cursor.execute(
                        f"SELECT setval('{seq_name}', COALESCE((SELECT MAX({col}) FROM {table}), 0) + 1, false)"
                    )
                except Exception as e:
                    jobs_logger.warning(f"Could not reset sequence for {table}: {e}")

    def backfill_accounts():
        """Backfill accounts from list registrations on-chain."""
        jobs_logger.info("Backfill: checking accounts...")
        db_lists = List.objects.all()
        if not db_lists.exists():
            return 0

        missing_count = 0
        for list_obj in db_lists:
            on_chain_regs = rpc_call_paginated(
                LISTS_CONTRACT,
                "get_registrations_for_list",
                {"list_id": list_obj.on_chain_id},
                page_size=300,
            )
            if on_chain_regs is None:
                continue

            # Collect all account IDs referenced in registrations
            account_ids = set()
            for reg in on_chain_regs:
                account_ids.add(reg["registrant_id"])
                if reg.get("registered_by"):
                    account_ids.add(reg["registered_by"])

            # Also add list owner and admins from on-chain data
            on_chain_list = rpc_call(LISTS_CONTRACT, "get_list", {"list_id": list_obj.on_chain_id})
            if on_chain_list:
                account_ids.add(on_chain_list["owner"])
                for admin_id in on_chain_list.get("admins", []):
                    account_ids.add(admin_id)

            existing_ids = set(Account.objects.filter(id__in=account_ids).values_list("id", flat=True))
            new_ids = account_ids - existing_ids

            for aid in new_ids:
                Account.objects.get_or_create(id=aid)
            if new_ids:
                jobs_logger.info(f"  Created {len(new_ids)} missing accounts from list {list_obj.on_chain_id}")
                missing_count += len(new_ids)

            _time.sleep(0.3)

        jobs_logger.info(f"Backfill accounts: {missing_count} created.")
        return missing_count

    def backfill_lists():
        jobs_logger.info("Backfill: checking lists...")
        on_chain_lists = rpc_call(LISTS_CONTRACT, "get_lists")
        if not on_chain_lists:
            jobs_logger.error("Failed to fetch lists from contract")
            return 0

        db_list_ids = set(List.objects.values_list("on_chain_id", flat=True))
        on_chain_ids = {l["id"] for l in on_chain_lists}
        missing_ids = on_chain_ids - db_list_ids

        if not missing_ids:
            jobs_logger.info("Backfill lists: all in sync.")
            return 0

        missing_count = 0
        for l in on_chain_lists:
            if l["id"] not in missing_ids:
                continue
            owner, _ = Account.objects.get_or_create(id=l["owner"])
            list_obj, _ = List.objects.update_or_create(
                on_chain_id=l["id"],
                defaults={
                    "owner": owner,
                    "name": l["name"],
                    "description": l.get("description", ""),
                    "cover_image_url": l.get("cover_image_url"),
                    "admin_only_registrations": l.get("admin_only_registrations", False),
                    "default_registration_status": l.get("default_registration_status", "Pending"),
                    "created_at": datetime.fromtimestamp(l["created_at"] / 1000, tz=timezone.utc),
                    "updated_at": datetime.fromtimestamp(l["updated_at"] / 1000, tz=timezone.utc),
                },
            )
            for admin_id in l.get("admins", []):
                admin, _ = Account.objects.get_or_create(id=admin_id)
                list_obj.admins.add(admin)
            missing_count += 1

        jobs_logger.info(f"Backfill lists: {missing_count} created.")
        return missing_count

    def backfill_registrations():
        jobs_logger.info("Backfill: checking registrations...")
        db_lists = List.objects.all()
        if not db_lists.exists():
            return 0

        total_missing = 0
        for list_obj in db_lists:
            on_chain_regs = rpc_call_paginated(
                LISTS_CONTRACT,
                "get_registrations_for_list",
                {"list_id": list_obj.on_chain_id},
                page_size=300,
            )
            if on_chain_regs is None:
                continue

            db_registrant_ids = set(
                ListRegistration.objects.filter(list=list_obj).values_list("registrant_id", flat=True)
            )
            on_chain_registrant_ids = {r["registrant_id"] for r in on_chain_regs}
            missing = on_chain_registrant_ids - db_registrant_ids

            if not missing:
                continue

            for reg in on_chain_regs:
                if reg["registrant_id"] not in missing:
                    continue
                registrant, _ = Account.objects.get_or_create(id=reg["registrant_id"])
                registered_by, _ = Account.objects.get_or_create(
                    id=reg.get("registered_by", reg["registrant_id"])
                )
                ListRegistration.objects.update_or_create(
                    list=list_obj,
                    registrant=registrant,
                    defaults={
                        "registered_by": registered_by,
                        "status": reg["status"],
                        "submitted_at": datetime.fromtimestamp(reg["submitted_ms"] / 1000, tz=timezone.utc),
                        "updated_at": datetime.fromtimestamp(reg["updated_ms"] / 1000, tz=timezone.utc),
                        "admin_notes": reg.get("admin_notes"),
                        "registrant_notes": reg.get("registrant_notes"),
                        "tx_hash": None,
                    },
                )
                total_missing += 1

            _time.sleep(0.5)

        jobs_logger.info(f"Backfill registrations: {total_missing} created.")
        return total_missing

    def backfill_donations():
        jobs_logger.info("Backfill: checking direct donations...")
        on_chain_donations = rpc_call_paginated(
            DONATE_CONTRACT, "get_donations", {}, page_size=300,
        )
        if on_chain_donations is None:
            jobs_logger.error("Failed to fetch donations from contract")
            return 0

        db_donation_ids = set(
            Donation.objects.filter(pot__isnull=True).values_list("on_chain_id", flat=True)
        )
        on_chain_ids = {d["id"] for d in on_chain_donations}
        missing_ids = on_chain_ids - db_donation_ids

        if not missing_ids:
            jobs_logger.info("Backfill donations: all in sync.")
            return 0

        missing_count = 0
        for d in on_chain_donations:
            if d["id"] not in missing_ids:
                continue

            donor, _ = Account.objects.get_or_create(id=d.get("donor_id", ""))
            recipient, _ = Account.objects.get_or_create(id=d.get("recipient_id", ""))
            ft_id = d.get("ft_id", "near")
            token_id = ft_id if ft_id != "near" else "near"
            token_acct, _ = Account.objects.get_or_create(id=token_id)
            token, _ = Token.objects.get_or_create(account=token_acct, defaults={"decimals": 24})

            referrer = None
            if d.get("referrer_id"):
                referrer, _ = Account.objects.get_or_create(id=d["referrer_id"])

            chef = None
            if d.get("chef_id"):
                chef, _ = Account.objects.get_or_create(id=d["chef_id"])

            Donation.objects.update_or_create(
                on_chain_id=d["id"],
                pot__isnull=True,
                defaults={
                    "donor": donor,
                    "total_amount": d.get("total_amount", "0"),
                    "net_amount": d.get("net_amount", "0"),
                    "token": token,
                    "matching_pool": d.get("matching_pool", False),
                    "message": d.get("message"),
                    "donated_at": datetime.fromtimestamp(d["donated_at_ms"] / 1000, tz=timezone.utc),
                    "recipient": recipient,
                    "protocol_fee": d.get("protocol_fee", "0"),
                    "referrer_fee": d.get("referrer_fee"),
                    "referrer": referrer,
                    "chef": chef,
                    "chef_fee": d.get("chef_fee"),
                    "tx_hash": None,
                },
            )
            missing_count += 1

        jobs_logger.info(f"Backfill donations: {missing_count} created.")
        return missing_count

    def backfill_pots():
        jobs_logger.info("Backfill: checking pots (applications & payouts)...")
        db_pots = Pot.objects.all()
        if not db_pots.exists():
            return 0

        total_missing = 0
        for pot in db_pots:
            pot_contract = str(pot.account_id)
            if not pot_contract or "." not in pot_contract:
                continue

            # Applications
            on_chain_apps = rpc_call_paginated(pot_contract, "get_applications", {}, page_size=300)
            if on_chain_apps is not None:
                db_app_ids = set(
                    PotApplication.objects.filter(pot=pot).values_list("applicant_id", flat=True)
                )
                on_chain_app_ids = {a.get("project_id", a.get("applicant_id", "")) for a in on_chain_apps}
                missing_apps = on_chain_app_ids - db_app_ids

                if missing_apps:
                    for a in on_chain_apps:
                        applicant_id = a.get("project_id", a.get("applicant_id", ""))
                        if applicant_id not in missing_apps:
                            continue
                        applicant, _ = Account.objects.get_or_create(id=applicant_id)
                        PotApplication.objects.update_or_create(
                            pot=pot,
                            applicant=applicant,
                            defaults={
                                "message": a.get("message", ""),
                                "status": a.get("status", "Pending"),
                                "submitted_at": datetime.fromtimestamp(
                                    a["submitted_at"] / 1000, tz=timezone.utc
                                ) if a.get("submitted_at") else now,
                                "updated_at": datetime.fromtimestamp(
                                    a["updated_at"] / 1000, tz=timezone.utc
                                ) if a.get("updated_at") else None,
                                "tx_hash": None,
                            },
                        )
                    total_missing += len(missing_apps)

            # Payouts
            on_chain_payouts = rpc_call_paginated(pot_contract, "get_payouts", {}, page_size=300)
            if on_chain_payouts is not None:
                db_payout_recipients = set(
                    PotPayout.objects.filter(pot=pot).values_list("recipient_id", flat=True)
                )
                on_chain_payout_recipients = {
                    p.get("project_id", p.get("recipient_id", "")) for p in on_chain_payouts
                }
                missing_payouts = on_chain_payout_recipients - db_payout_recipients
                if missing_payouts:
                    for p in on_chain_payouts:
                        recipient_id = p.get("project_id", p.get("recipient_id", ""))
                        if recipient_id not in missing_payouts:
                            continue
                        recipient, _ = Account.objects.get_or_create(id=recipient_id)
                        token = None
                        if p.get("ft_id"):
                            token_acct, _ = Account.objects.get_or_create(id=p["ft_id"])
                            token, _ = Token.objects.get_or_create(account=token_acct, defaults={"decimals": 24})
                        PotPayout.objects.update_or_create(
                            pot=pot,
                            recipient=recipient,
                            defaults={
                                "amount": p.get("amount", "0"),
                                "token": token,
                                "paid_at": datetime.fromtimestamp(
                                    p["paid_at"] / 1000, tz=timezone.utc
                                ) if p.get("paid_at") else None,
                                "tx_hash": None,
                            },
                        )
                    total_missing += len(missing_payouts)

            _time.sleep(0.5)

        jobs_logger.info(f"Backfill pots: {total_missing} missing apps/payouts created.")
        return total_missing

    def backfill_campaigns():
        """Backfill campaigns and campaign donations from on-chain data."""
        if not apps.is_installed("campaigns"):
            jobs_logger.info("Backfill campaigns: app not installed, skipping.")
            return 0

        from campaigns.models import Campaign, CampaignDonation

        CAMPAIGNS_CONTRACT = (
            f"v1.campaign.{settings.POTLOCK_TLA}"
            if settings.ENVIRONMENT == "testnet"
            else f"v1.campaigns.{settings.POTLOCK_TLA}"
        )

        jobs_logger.info("Backfill: checking campaigns...")

        # Fetch all campaigns by iterating with get_campaign until we get None
        # The contract uses sequential IDs starting from 1
        on_chain_campaigns = []
        campaign_id = 1
        consecutive_failures = 0
        while consecutive_failures < 3:
            data = rpc_call(CAMPAIGNS_CONTRACT, "get_campaign", {"campaign_id": campaign_id})
            if data is None:
                consecutive_failures += 1
                campaign_id += 1
                continue
            consecutive_failures = 0
            data["_chain_id"] = campaign_id
            on_chain_campaigns.append(data)
            campaign_id += 1
            _time.sleep(0.3)

        if not on_chain_campaigns:
            jobs_logger.info("Backfill campaigns: no campaigns found on chain.")
            return 0

        db_campaign_ids = set(Campaign.objects.values_list("on_chain_id", flat=True))
        total_missing = 0

        for data in on_chain_campaigns:
            cid = data.get("id", data["_chain_id"])
            if cid in db_campaign_ids:
                # Still update existing campaigns to sync latest state (e.g. raised amounts)
                try:
                    campaign = Campaign.objects.get(on_chain_id=cid)
                    campaign.total_raised_amount = str(data.get("total_raised_amount", "0"))
                    campaign.net_raised_amount = str(data.get("net_raised_amount", "0"))
                    campaign.escrow_balance = str(data.get("escrow_balance", "0"))
                    campaign.save(update_fields=["total_raised_amount", "net_raised_amount", "escrow_balance"])
                except Campaign.DoesNotExist:
                    pass
                continue

            # Create missing campaign
            owner, _ = Account.objects.get_or_create(id=data["owner"])
            recipient, _ = Account.objects.get_or_create(id=data["recipient"])

            token = None
            token_id = data.get("ft_id")
            if token_id:
                token_acct, _ = Account.objects.get_or_create(id=token_id)
                token, _ = Token.objects.get_or_create(account=token_acct, defaults={"decimals": 24})

            start_at = datetime.fromtimestamp(data["start_ms"] / 1000, tz=timezone.utc)
            end_at = (
                datetime.fromtimestamp(data["end_ms"] / 1000, tz=timezone.utc)
                if data.get("end_ms") else None
            )
            created_at = (
                datetime.fromtimestamp(data["created_ms"] / 1000, tz=timezone.utc)
                if data.get("created_ms") else now
            )

            Campaign.objects.update_or_create(
                on_chain_id=cid,
                defaults={
                    "owner": owner,
                    "name": data["name"],
                    "description": data.get("description"),
                    "cover_image_url": data.get("cover_image_url"),
                    "recipient": recipient,
                    "token": token,
                    "start_at": start_at,
                    "end_at": end_at,
                    "created_at": created_at,
                    "target_amount": str(data["target_amount"]),
                    "min_amount": str(data["min_amount"]) if data.get("min_amount") else None,
                    "max_amount": str(data["max_amount"]) if data.get("max_amount") else None,
                    "total_raised_amount": str(data.get("total_raised_amount", "0")),
                    "net_raised_amount": str(data.get("net_raised_amount", "0")),
                    "escrow_balance": str(data.get("escrow_balance", "0")),
                    "referral_fee_basis_points": data["referral_fee_basis_points"],
                    "creator_fee_basis_points": data["creator_fee_basis_points"],
                    "allow_fee_avoidance": data.get("allow_fee_avoidance", False),
                },
            )
            total_missing += 1

        # Backfill campaign donations for all campaigns
        for campaign in Campaign.objects.all():
            on_chain_donations = rpc_call_paginated(
                CAMPAIGNS_CONTRACT,
                "get_donations_for_campaign",
                {"campaign_id": campaign.on_chain_id},
                page_size=300,
            )
            if on_chain_donations is None:
                continue

            db_donation_ids = set(
                CampaignDonation.objects.filter(campaign=campaign).values_list("on_chain_id", flat=True)
            )
            on_chain_ids = {d["id"] for d in on_chain_donations}
            missing = on_chain_ids - db_donation_ids

            if not missing:
                continue

            for d in on_chain_donations:
                if d["id"] not in missing:
                    continue

                donor, _ = Account.objects.get_or_create(id=d["donor_id"])
                referrer = None
                if d.get("referrer_id"):
                    referrer, _ = Account.objects.get_or_create(id=d["referrer_id"])

                don_token = campaign.token
                if d.get("ft_id"):
                    token_acct, _ = Account.objects.get_or_create(id=d["ft_id"])
                    don_token, _ = Token.objects.get_or_create(account=token_acct, defaults={"decimals": 24})

                donated_at = datetime.fromtimestamp(d["donated_at_ms"] / 1000, tz=timezone.utc)
                returned_at = (
                    datetime.fromtimestamp(d["returned_at_ms"] / 1000, tz=timezone.utc)
                    if d.get("returned_at_ms") else None
                )

                CampaignDonation.objects.update_or_create(
                    on_chain_id=d["id"],
                    campaign=campaign,
                    donor=donor,
                    defaults={
                        "token": don_token,
                        "total_amount": str(d["total_amount"]),
                        "net_amount": str(d["net_amount"]),
                        "message": d.get("message"),
                        "donated_at": donated_at,
                        "protocol_fee": str(d["protocol_fee"]),
                        "referrer": referrer,
                        "referrer_fee": str(d["referrer_fee"]) if d.get("referrer_fee") else None,
                        "creator_fee": str(d["creator_fee"]),
                        "returned_at": returned_at,
                        "escrowed": d.get("is_in_escrow", False),
                        "tx_hash": None,
                    },
                )
                total_missing += 1

            _time.sleep(0.5)

        jobs_logger.info(f"Backfill campaigns: {total_missing} missing entries created.")
        return total_missing

    # === Main backfill execution ===
    jobs_logger.info(f"=== Biweekly Backfill Starting (ISO week {now.isocalendar().week}) ===")

    fix_sequences()

    total = 0
    total += backfill_accounts()
    total += backfill_lists()
    total += backfill_registrations()
    total += backfill_donations()
    total += backfill_pots()
    total += backfill_campaigns()

    if total == 0:
        jobs_logger.info("=== Backfill complete: everything in sync! ===")
    else:
        jobs_logger.info(f"=== Backfill complete: {total} missing entries created. ===")


@task_revoked.connect
def on_task_revoked(request, terminated, signum, expired, **kwargs):
    logger.info(
        f"Task {request.id} revoked; terminated={terminated}, signum={signum}, expired={expired}"
    )
