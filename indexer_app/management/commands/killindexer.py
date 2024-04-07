from django.core.management.base import BaseCommand
from indexer.celery import app
from celery.app.control import Inspect

class Command(BaseCommand):
    help = 'Kill all running Celery tasks for the indexer'

    def handle(self, *args, **options):
        i = Inspect(app=app)
        active_tasks = i.active()

        if active_tasks is None:
            self.stdout.write(self.style.WARNING('No active tasks found or unable to connect to workers.'))
            return

        for worker, tasks in active_tasks.items():
            for task in tasks:
                app.control.revoke(task_id=task['id'], terminate=True)
                self.stdout.write(self.style.SUCCESS(f"Task {task['id']} revoked."))
