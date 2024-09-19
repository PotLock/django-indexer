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
from near_lake_framework import LakeConfig, streamer
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
from .utils import create_or_update_round, create_round_application, get_block_height, get_ledger_sequence, process_application_to_round, process_project_event, process_rounds_deposit_event, process_vote_event, save_block_height, update_application, update_approved_projects, update_ledger_sequence

CURRENT_BLOCK_HEIGHT_KEY = "current_block_height"


async def indexer(from_block: int, to_block: int):
    """
    Runs the lake indexer framework
    """
    # Initialize lake indexer
    logger.info(f"from block: {from_block}")
    lake_config = (
        LakeConfig.testnet()
        if settings.ENVIRONMENT == "testnet"
        else LakeConfig.mainnet()
    )
    lake_config.start_block_height = (
        from_block
        if from_block
        else logger.info(
            "Starting to index from latest block"
        )  # TODO: wtf is this shitty code
    )
    lake_config.aws_access_key_id = settings.AWS_ACCESS_KEY_ID
    lake_config.aws_secret_key = settings.AWS_SECRET_ACCESS_KEY
    _, streamer_messages_queue = streamer(lake_config)
    block_count = 0

    while True:
        try:
            # Log time before fetching a new block
            fetch_start_time = time.time()
            # streamer_message is the current block
            streamer_message = await streamer_messages_queue.get()
            fetch_end_time = time.time()
            logger.info(
                f"Time to fetch new block: {fetch_end_time - fetch_start_time:.4f} seconds"
            )
            block_count += 1

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
        logger.info(f"what's the start block, pray tell? {start_block-1}")
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
        logger.info(f"Spot index start block: {start_block-1}")
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

@shared_task
def stellar_event_indexer():
    server = stellar_sdk.SorobanServer(
        "https://soroban-testnet.stellar.org"
        if settings.ENVIRONMENT == "testnet" or settings.ENVIRONMENT == "local"
        else "https://horizon.stellar.org"
    )
    contract_ids = [settings.STELLAR_CONTRACT_ID, settings.STELLAR_PROJECTS_REGISTRY_CONTRACT]
    start_sequence = get_ledger_sequence()
    # start_sequence = 12169
    if not start_sequence:
        start_sequence = 12169
    jobs_logger.info(f"Ingesting Stellar events from ledger {start_sequence}... contracts: {contract_ids}")
    try:
        # Fetch events for the current sequence
        events = server.get_events(
            start_ledger=start_sequence,
            filters=[
                EventFilter(
                        event_type=EventFilterType.CONTRACT,
                        contract_ids=contract_ids
                    )
            ]
        )
        stellar_events = []
        for event in events.events:
            event_name = stellar_sdk.scval.to_native(event.topic[0])
            event_value = event.value
            if event.value is not None:
                event_value = stellar_sdk.scval.to_native(event.value)
                event_value = json.loads(json.dumps(event_value, default=address_to_string))
                print("event value:. ", event_value)
            stellar_events.append(StellarEvent(
                ledger_sequence=event.ledger,
                event_type=event_name,
                contract_id=event.contract_id,
                ingested_at=event.ledger_close_at,
                transaction_hash=event.transaction_hash,
                data=event_value
            ))
    
        if len(stellar_events) > 0:
            StellarEvent.objects.bulk_create(
                objs=stellar_events,
                ignore_conflicts=True
            )
            update_ledger_sequence(events.latest_ledger, event.ledger_close_at)
            jobs_logger.info(f"Ingested {len(stellar_events)} Stellar events from ledger {start_sequence} to {events.latest_ledger}...")

    except Exception as e:
        jobs_logger.error(f"Error processing ledger {start_sequence}: {e}")



@shared_task
def process_stellar_events():
    unprocessed_events = StellarEvent.objects.filter(processed=False).order_by('id')
    jobs_logger.info(f"Processing {unprocessed_events.count()} unprocessed Stellar events...")

    for event in unprocessed_events:
        try:
            event_data = event.data
            event_name = event.event_type

            if event_name == 'c_project':
                process_project_event(event_data)
                event.processed = True
            
            elif event_name == 'c_round' or event_name == 'u_round':
                create_or_update_round(event_data, event.contract_id, event.ingested_at)
                # Mark event as processed
                event.processed = True

            elif event_name == 'apply_to_round':
                process_application_to_round(event_data, event.transaction_hash)
                # Mark event as processed
                event.processed = True            

            elif event_name == 'c_app':
                create_round_application(event_data, event.transaction_hash)
                event.processed = True


            elif event_name == 'u_app': # application review and aproval
                jobs_logger.info(f"eventulating data for event, {event_data}")
                update_application(event_data, event.transaction_hash)
                event.processed = True
            
            elif event_name == 'u_ap':
                jobs_logger.info(f"eventulating data for approved project event, {event_data}")
                update_approved_projects(event_data)
                event.processed = True
            
            elif event_name == 'c_depo':
                process_rounds_deposit_event(event_data, event.transaction_hash)
                # Mark event as processed
                event.processed = True

            elif event_name == 'c_vote':
                process_vote_event(event_data, event.transaction_hash)
                # Mark event as processed
                event.processed = True
            event.save()

        except Exception as e:
            jobs_logger.error(f"Error processing Stellar event { event_name, event.id}: {e}")

    jobs_logger.info(f"Finished processing Stellar events.")




@task_revoked.connect
def on_task_revoked(request, terminated, signum, expired, **kwargs):
    logger.info(
        f"Task {request.id} revoked; terminated={terminated}, signum={signum}, expired={expired}"
    )
