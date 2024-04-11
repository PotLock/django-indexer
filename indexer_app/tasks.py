import asyncio
from pathlib import Path

from celery import shared_task
from django.conf import settings
from near_lake_framework import LakeConfig, streamer

from indexer_app.handler import handle_streamer_message


async def indexer(network: str, from_block: int, to_block: int):
    """
    Runs the lake indexer framework
    """
    # Initialize lake indexer
    lake_config = LakeConfig.mainnet() if network == "mainnet" else LakeConfig.testnet()
    lake_config.start_block_height = (
        from_block if from_block else print("Starting to index from latest block")
    )
    lake_config.aws_access_key_id = settings.AWS_ACCESS_KEY_ID
    lake_config.aws_secret_key = settings.AWS_SECRET_ACCESS_KEY
    _, streamer_messages_queue = streamer(lake_config)
    while True:
        try:
            # streamer_message is the current block
            streamer_message = await streamer_messages_queue.get()
            await handle_streamer_message(streamer_message)
        except Exception as e:
            print("Error in streamer_messages_queue", e)


@shared_task
def listen_to_near_events():
    print("tell us you're alive!!!!")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Update below with desired network & block height
        loop.run_until_complete(indexer("mainnet", 112_724_128, None))
    finally:
        loop.close()
