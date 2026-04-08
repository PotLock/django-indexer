import os
import ssl

from celery import Celery
from celery.schedules import crontab
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "base.settings")

app = Celery(
    "indexer",
    # broker=settings.CELERY_BROKER_URL,
    # backend=settings.CELERY_RESULT_BACKEND
)

# SSL configurations for broker and backend
# app.conf.broker_use_ssl = {
#     'ssl_cert_reqs': ssl.CERT_NONE  # TODO: Adjust for production
# }
# app.conf.redis_backend_use_ssl = {
#     'ssl_cert_reqs': ssl.CERT_NONE  # TODO: Adjust for production
# }

app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    # "update_account_statistics_every_5_minutes": {
    #     "task": "indexer_app.tasks.update_account_statistics",
    #     "schedule": crontab(minute="*/5"),  # Executes every 5 minutes
    #     "options": {"queue": "beat_tasks"},
    # },
    # "fetch_usd_prices_every_5_minutes": {
    #     "task": "indexer_app.tasks.fetch_usd_prices",
    #     "schedule": crontab(minute="*/5"),  # Executes every 5 minutes
    #     "options": {"queue": "beat_tasks"},
    # },
    # "update_pot_statistics_every_5_minutes": {
    #     "task": "indexer_app.tasks.update_pot_statistics",
    #     "schedule": crontab(minute="*/5"),  # Executes every 5 minutes
    #     "options": {"queue": "beat_tasks"},
    # },
    "fetch_stellar_events_every_minute": {
        "task": "indexer_app.tasks.stellar_event_indexer",
        "schedule": crontab(minute="*/1"),  # Executes every 1 minutes
        "options": {"queue": "beat_tasks"},
    },
    "process_stellar_event_every_minute": {
        "task": "indexer_app.tasks.process_stellar_events",
        "schedule": crontab(minute="*/1"),  # Executes every 1 minutes
        "options": {"queue": "beat_tasks"},
    },
    "refresh_eo_bmf_monthly": {
        "task": "tax_verification.tasks.refresh_eo_bmf",
        "schedule": crontab(day_of_month="5", hour="4", minute="0"),  # 5th of each month, 4 AM UTC
        "options": {"queue": "beat_tasks"},
    },
    "backfill_missing_data_biweekly": {
        "task": "indexer_app.tasks.backfill_missing_data",
        "schedule": crontab(day_of_week="0", hour="3", minute="0"),  # Every Sunday 3 AM UTC; task self-skips odd weeks for biweekly
        "options": {"queue": "beat_tasks"},
    },
}

app.conf.task_routes = {
    "indexer_app.tasks.update_account_statistics": {"queue": "beat_tasks"},
    "indexer_app.tasks.fetch_usd_prices": {"queue": "beat_tasks"},
    "indexer_app.tasks.update_pot_statistics": {"queue": "beat_tasks"},
    "indexer_app.tasks.stellar_event_indexer": {"queue": "beat_tasks"},
    "indexer_app.tasks.process_stellar_events": {"queue": "beat_tasks"},
    "tax_verification.tasks.refresh_eo_bmf": {"queue": "beat_tasks"},
    "indexer_app.tasks.backfill_missing_data": {"queue": "beat_tasks"},
}

SPOT_INDEXER_QUEUE_NAME = "spot_indexing"
