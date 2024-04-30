import os

from django.conf import settings

from celery import Celery
import ssl

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "base.settings")

app = Celery("indexer",
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
