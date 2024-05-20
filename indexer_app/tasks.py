import asyncio
import logging
from pathlib import Path

from celery import shared_task
from celery.signals import task_revoked
from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q, Sum
from near_lake_framework import LakeConfig, streamer

from accounts.models import Account
from donations.models import Donation
from indexer_app.handler import handle_streamer_message
from pots.models import PotPayout

from .logging import logger
from .utils import cache_block_height, get_block_height


async def indexer(network: str, from_block: int, to_block: int):
    """
    Runs the lake indexer framework
    """
    # Initialize lake indexer
    logger.info(f"from block: {from_block}")
    lake_config = LakeConfig.mainnet() if network == "mainnet" else LakeConfig.testnet()
    lake_config.start_block_height = (
        from_block if from_block else logger.info("Starting to index from latest block")
    )
    lake_config.aws_access_key_id = settings.AWS_ACCESS_KEY_ID
    lake_config.aws_secret_key = settings.AWS_SECRET_ACCESS_KEY
    _, streamer_messages_queue = streamer(lake_config)
    block_count = 0

    while True:
        try:
            # streamer_message is the current block
            streamer_message = await streamer_messages_queue.get()
            block_count += 1
            await cache_block_height(
                "current_block_height",
                streamer_message.block.header.height,
                block_count,
                streamer_message.block.header.timestamp,
            )  # current block height
            await handle_streamer_message(streamer_message)
        except Exception as e:
            logger.error(f"Error in streamer_messages_queue: {e}")


@shared_task
def listen_to_near_events():
    logger.info("Listening to NEAR events...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Update below with desired network & block height
        # start_block = get_block_height("current_block_height")
        start_block = 109991746
        logger.info(f"what's the start block, pray tell? {start_block-1}")
        loop.run_until_complete(indexer("mainnet", start_block - 1, None))
    finally:
        loop.close()


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


@task_revoked.connect
def on_task_revoked(request, terminated, signum, expired, **kwargs):
    logger.info(
        f"Task {request.id} revoked; terminated={terminated}, signum={signum}, expired={expired}"
    )
