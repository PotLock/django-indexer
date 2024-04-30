from django.core.management.base import BaseCommand
from indexer_app.tasks import listen_to_near_events

class Command(BaseCommand):
    help = 'Invoke the Near Data Lake indexer task'

    def handle(self, *args, **options):
        # Invoke Celery task
        try:
            listen_to_near_events.delay()
            self.stdout.write(self.style.SUCCESS('Successfully invoked the Near Data Lake indexer task'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to invoke task: {str(e)}'))
