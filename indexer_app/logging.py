import logging

import psutil

logger = logging.getLogger("indexer")


def log_memory_usage(stage):
    process = psutil.Process()
    memory_info = process.memory_info()
    logger.info(
        f"{stage} - RSS: {memory_info.rss / 1024 / 1024:.2f} MB, VMS: {memory_info.vms / 1024 / 1024:.2f} MB"
    )
