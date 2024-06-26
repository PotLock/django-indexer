from celery.app.control import Inspect
from django.core.management.base import BaseCommand

from base.celery import SPOT_INDEXER_QUEUE_NAME, app


class Command(BaseCommand):
    help = "Kill all running Celery tasks in the spot queue for the indexer"

    def handle(self, *args, **options):
        i = Inspect(app=app)
        active_tasks = i.active()

        if active_tasks is None:
            self.stdout.write(
                self.style.WARNING(
                    "No active tasks found or unable to connect to workers."
                )
            )
            return

        for worker, tasks in active_tasks.items():
            for task in tasks:
                queue = task.get("delivery_info", {}).get("routing_key")
                if queue == SPOT_INDEXER_QUEUE_NAME:
                    app.control.revoke(task_id=task["id"], terminate=True)
                    self.stdout.write(self.style.SUCCESS(f"Task {task['id']} revoked."))

        self.stdout.write(
            self.style.SUCCESS(
                f"All tasks in {SPOT_INDEXER_QUEUE_NAME} queue have been revoked."
            )
        )
