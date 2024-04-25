import asyncio
from pathlib import Path

from celery import shared_task
from django.conf import settings
from near_lake_framework import LakeConfig, streamer

from indexer_app.handler import handle_streamer_message

from .utils import cache_block_height, get_block_height


async def indexer(network: str, from_block: int, to_block: int):
    """
    Runs the lake indexer framework
    """
    # Initialize lake indexer
    print(f"from block: {from_block}")
    lake_config = LakeConfig.mainnet() if network == "mainnet" else LakeConfig.testnet()
    lake_config.start_block_height = (
        from_block if from_block else print("Starting to index from latest block")
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
            await cache_block_height("current_block_height", streamer_message.block.header.height, block_count) # current block height
            await handle_streamer_message(streamer_message)
        except Exception as e:
            print("Error in streamer_messages_queue", e)


@shared_task
def listen_to_near_events():
    print("Listening to near events...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Update below with desired network & block height
        start_block = get_block_height('current_block_height')
        # start_block = 104_963_982
        print("what's the start block, pray tell?", start_block-1)
        loop.run_until_complete(indexer("mainnet", start_block-1, None))
    finally:
        loop.close()


from celery.signals import task_revoked

@task_revoked.connect
def on_task_revoked(request, terminated, signum, expired, **kwargs):
    print(f"Task {request.id} revoked; terminated={terminated}, signum={signum}, expired={expired}")
