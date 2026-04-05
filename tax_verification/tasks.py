import logging

from celery import shared_task
from django.core.management import call_command

jobs_logger = logging.getLogger("jobs")


@shared_task
def refresh_eo_bmf():
    jobs_logger.info("Starting scheduled EO BMF refresh...")
    try:
        call_command("refresh_eo_bmf")
        jobs_logger.info("Scheduled EO BMF refresh completed.")
    except Exception as e:
        jobs_logger.error(f"Scheduled EO BMF refresh failed: {e}")
        raise
