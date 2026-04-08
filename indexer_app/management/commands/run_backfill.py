"""
Manually trigger the biweekly backfill task (bypasses the week parity check).

Usage:
    python manage.py run_backfill              # run synchronously (no celery needed)
    python manage.py run_backfill --async      # dispatch to celery worker
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Manually trigger the biweekly backfill task."

    def add_arguments(self, parser):
        parser.add_argument(
            "--async",
            action="store_true",
            default=False,
            dest="run_async",
            help="Dispatch to celery worker instead of running synchronously.",
        )

    def handle(self, *args, **options):
        from indexer_app.tasks import backfill_missing_data

        if options["run_async"]:
            backfill_missing_data.delay()
            self.stdout.write(self.style.SUCCESS("Backfill task dispatched to celery worker."))
        else:
            self.stdout.write(self.style.WARNING("Running backfill synchronously (bypassing week check)..."))
            backfill_missing_data(force=True)
            self.stdout.write(self.style.SUCCESS("Backfill complete."))
