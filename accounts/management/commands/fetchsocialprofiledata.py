import time

from django.core.management.base import BaseCommand

from accounts.models import Account


class Command(BaseCommand):
    help = "Fetch social profile data for all accounts."

    def handle(self, *args, **options):
        # Get all account addresses
        account_addresses = [account.id for account in Account.objects.all()]

        # Fetch social profile data for each account
        for address in account_addresses:
            account = Account.objects.get(id=address)
            account.fetch_near_social_profile_data()
            self.stdout.write(
                self.style.SUCCESS(f"Fetched social profile data for {address}")
            )
            # wait for 1 second to avoid rate limiting
            time.sleep(1)
