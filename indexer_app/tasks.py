import asyncio
import logging
from pathlib import Path

from celery import shared_task
from celery.signals import task_revoked
from django.conf import settings
from django.db import transaction
from django.db.models import Count, Sum
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
        start_block = get_block_height("current_block_height")
        # start_block = 105_534_694  # manually setting for reindexing TODO: remove this
        logger.info(f"what's the start block, pray tell? {start_block-1}")
        loop.run_until_complete(indexer("mainnet", start_block - 1, None))
    finally:
        loop.close()


@shared_task
def update_account_statistics():
    logger = logging.getLogger("jobs")
    logger.info("Updating account statistics...")

    accounts = Account.objects.all()
    for account in accounts:
        try:
            with transaction.atomic():
                logger.info(f"Updating statistics for account {account.id}...")
                # donors count
                account.donors_count = Donation.objects.filter(
                    recipient=account
                ).aggregate(Count("donor", distinct=True))["donor__count"]

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
                    ).aggregate(Sum("amount_usd"))["amount_usd__sum"]
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
                logger.info(f"Account {account.id} statistics updated.")
        except Exception as e:
            logger.error(f"Failed to update statistics for account {account.id}: {e}")


@task_revoked.connect
def on_task_revoked(request, terminated, signum, expired, **kwargs):
    logger.info(
        f"Task {request.id} revoked; terminated={terminated}, signum={signum}, expired={expired}"
    )
