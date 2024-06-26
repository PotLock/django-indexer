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
    "update_account_statistics_every_5_minutes": {
        "task": "indexer_app.tasks.update_account_statistics",
        "schedule": crontab(minute="*/5"),  # Executes every 5 minutes
        "options": {"queue": "beat_tasks"},
    },
    "fetch_usd_prices_every_5_minutes": {
        "task": "indexer_app.tasks.fetch_usd_prices",
        "schedule": crontab(minute="*/5"),  # Executes every 5 minutes
        "options": {"queue": "beat_tasks"},
    },
    "update_pot_statistics_every_5_minutes": {
        "task": "indexer_app.tasks.update_pot_statistics",
        "schedule": crontab(minute="*/5"),  # Executes every 5 minutes
        "options": {"queue": "beat_tasks"},
    },
}

app.conf.task_routes = {
    "indexer_app.tasks.update_account_statistics": {"queue": "beat_tasks"},
    "indexer_app.tasks.fetch_usd_prices": {"queue": "beat_tasks"},
    "indexer_app.tasks.update_pot_statistics": {"queue": "beat_tasks"},
}

SPOT_INDEXER_QUEUE_NAME = "spot_indexing"
