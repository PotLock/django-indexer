from django.core.management.base import BaseCommand

from indexer_app.tasks import spot_index_near_events


class Command(BaseCommand):
    help = "Invoke the Near Data Lake indexer task"

    def add_arguments(self, parser):
        parser.add_argument(
            "start_block",
            type=int,
            help="The starting block number for the Near Data Lake indexer task",
        )

    def handle(self, *args, **options):
        start_block = options["start_block"]
        # Invoke Celery task
        try:
            spot_index_near_events.delay(start_block=start_block)
            self.stdout.write(
                self.style.SUCCESS(
                    "Successfully invoked the Near Data Lake indexer task"
                )
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to invoke task: {str(e)}"))
