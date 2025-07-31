import time
from datetime import datetime
import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Account
from campaigns.models import Campaign, CampaignDonation
from tokens.models import Token



CAMPAIGN_CONTRACT_ID =f"v1.campaign.{settings.POTLOCK_TLA}" if settings.ENVIRONMENT=="testnet" else f"v1.campaigns.staging.{settings.POTLOCK_TLA}"

class Command(BaseCommand):
    help = "Pull campaigns data from contract & populate campaigns table."

    def add_arguments(self, parser):
        parser.add_argument(
            '--campaign-id',
            type=int,
            help='Populate specific campaign by ID (optional)',
        )
        parser.add_argument(
            '--skip-donations',
            action='store_true',
            help='Skip fetching donations for campaigns',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Limit number of campaigns to fetch (default: 100)',
        )

    def handle(self, *args, **options):

        self.stdout.write(
            self.style.SUCCESS(f'Starting to populate campaign data from {CAMPAIGN_CONTRACT_ID}')
        )

        if options['campaign_id']:
            # Fetch specific campaign
            self.fetch_single_campaign(CAMPAIGN_CONTRACT_ID, options['campaign_id'], options['skip_donations'])
        else:
            # Fetch all campaigns
            self.fetch_all_campaigns(CAMPAIGN_CONTRACT_ID, options['limit'], options['skip_donations'])

        self.stdout.write(
            self.style.SUCCESS('Successfully populated campaign data')
        )

    def fetch_all_campaigns(self, contract_id, limit, skip_donations):
        """Fetch all campaigns from the contract"""

        # Get campaigns
        url = f"{settings.FASTNEAR_RPC_URL}/account/{contract_id}/view/get_campaigns"
        params = {
            "from_index.json": 0,
            "limit.json": limit,
        }

        self.stdout.write(f"Fetching campaigns from {url}")

        response = requests.get(url, params=params)
        if response.status_code != 200:
            self.stdout.write(
                self.style.ERROR(
                    f"Request for campaigns data failed ({response.status_code}) with message: {response.text}"
                )
            )
            return

        campaigns = response.json()
        self.stdout.write(f"Found {len(campaigns)} campaigns")

        for campaign_data in campaigns:
            self.process_campaign(campaign_data, skip_donations)
            # Small delay to avoid rate limiting
            time.sleep(0.1)

    def fetch_single_campaign(self, contract_id, campaign_id, skip_donations):
        """Fetch a specific campaign by ID"""

        url = f"{settings.FASTNEAR_RPC_URL}/account/{contract_id}/view/get_campaign"
        params = {
            "campaign_id.json": campaign_id,
        }

        self.stdout.write(f"Fetching campaign {campaign_id} from {url}")

        response = requests.get(url, params=params)
        if response.status_code != 200:
            self.stdout.write(
                self.style.ERROR(
                    f"Request for campaign {campaign_id} failed ({response.status_code}) with message: {response.text}"
                )
            )
            return

        campaign_data = response.json()
        self.process_campaign(campaign_data, skip_donations)

    def process_campaign(self, campaign_data, skip_donations):
        """Process and save a single campaign"""

        try:
            campaign_id = campaign_data["id"]
            self.stdout.write(f"Processing campaign {campaign_id}: {campaign_data.get('name', 'Unnamed')}")

            # Get or create accounts
            owner, _ = Account.objects.get_or_create(
                defaults={"chain_id": 1},
                id=campaign_data["owner"]
            )
            recipient, _ = Account.objects.get_or_create(
                defaults={"chain_id": 1},
                id=campaign_data["recipient"]
            )

            # Get token if specified

            ft_id = campaign_data.get("ft_id") or "near"
            token_acct, token_acct_created = Account.objects.get_or_create(defaults={"chain_id":1},id=ft_id)
            token_defaults = {
                "decimals": 24,
            }
            if token_acct_created:
                print(f"Created new token account: {token_acct}")
                if ft_id != "near":
                    url = f"{settings.FASTNEAR_RPC_URL}/account/{ft_id}/view/ft_metadata"
                    ft_metadata = requests.get(url)
                    if ft_metadata.status_code != 200:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Request for campaigns data failed ({ft_metadata.status_code}) with message: {ft_metadata.text}"
                            )
                        )
                        return
                    else:
                        ft_metadata = ft_metadata.json()
                        if "name" in ft_metadata:
                            token_defaults["name"] = ft_metadata["name"]
                        if "symbol" in ft_metadata:
                            token_defaults["symbol"] = ft_metadata["symbol"]
                        if "icon" in ft_metadata:
                            token_defaults["icon"] = ft_metadata["icon"]
                        if "decimals" in ft_metadata:
                            token_defaults["decimals"] = ft_metadata["decimals"]
            token, _ = Token.objects.get_or_create(
                account=token_acct, defaults=token_defaults
            )

            # Convert timestamps to datetime objects
            start_at = datetime.fromtimestamp(campaign_data["start_ms"] / 1000)
            end_at = None
            if campaign_data.get("end_ms"):
                end_at = datetime.fromtimestamp(campaign_data["end_ms"] / 1000)
            created_at = datetime.fromtimestamp(campaign_data["created_ms"] / 1000)

            # Campaign defaults
            campaign_defaults = {
                "owner": owner,
                "name": campaign_data["name"],
                "description": campaign_data.get("description"),
                "cover_image_url": campaign_data.get("cover_image_url"),
                "recipient": recipient,
                "token": token,
                "start_at": start_at,
                "end_at": end_at,
                "created_at": created_at,
                "target_amount": str(campaign_data["target_amount"]),
                "min_amount": str(campaign_data.get("min_amount", "")) if campaign_data.get("min_amount") else None,
                "max_amount": str(campaign_data.get("max_amount", "")) if campaign_data.get("max_amount") else None,
                "total_raised_amount": str(campaign_data.get("total_raised_amount", "0")),
                "net_raised_amount": str(campaign_data.get("net_raised_amount", "0")),
                "escrow_balance": str(campaign_data.get("escrow_balance", "0")),
                "referral_fee_basis_points": campaign_data["referral_fee_basis_points"],
                "creator_fee_basis_points": campaign_data["creator_fee_basis_points"],
                "allow_fee_avoidance": campaign_data.get("allow_fee_avoidance", False),
            }

            # Create or update campaign
            campaign, created = Campaign.objects.update_or_create(
                on_chain_id=campaign_id,
                defaults=campaign_defaults
            )

            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action} campaign: {campaign.on_chain_id}")

            # Fetch USD prices for the campaign
            try:
                campaign.fetch_usd_prices()
                self.stdout.write(f"  Fetched USD prices for campaign {campaign.on_chain_id}")
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"  Failed to fetch USD prices for campaign {campaign.on_chain_id}: {e}")
                )

            # Fetch donations for this campaign if not skipped
            if not skip_donations:
                self.fetch_campaign_donations(campaign)

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Failed to process campaign {campaign_data.get('id', 'unknown')}: {e}")
            )

    def fetch_campaign_donations(self, campaign):
        """Fetch donations for a specific campaign"""

        # CAMPAIGN_CONTRACT_ID = f"v1.campaigns.staging.{settings.POTLOCK_TLA}"

        # Get donations for campaign with pagination
        page = 0
        limit = 100
        total_donations = 0

        while True:
            url = f"{settings.FASTNEAR_RPC_URL}/account/{CAMPAIGN_CONTRACT_ID}/view/get_donations_for_campaign"
            params = {
                "campaign_id.json": campaign.on_chain_id,
                "from_index.json": page * limit,
                "limit.json": limit,
            }

            self.stdout.write(f"  Fetching donations page {page + 1} for campaign {campaign.on_chain_id}")

            response = requests.get(url, params=params)
            if response.status_code != 200:
                self.stdout.write(
                    self.style.WARNING(
                        f"  Request for donations failed ({response.status_code}) with message: {response.text}"
                    )
                )
                break

            donations = response.json()
            if not donations:
                break

            self.stdout.write(f"  Processing {len(donations)} donations")

            for donation_data in donations:
                self.process_campaign_donation(donation_data, campaign)
                total_donations += 1

            # Break if we got fewer results than the limit (last page)
            if len(donations) < limit:
                break

            page += 1
            # Small delay to avoid rate limiting
            time.sleep(0.1)

        self.stdout.write(f"  Processed {total_donations} donations for campaign {campaign.on_chain_id}")

    def process_campaign_donation(self, donation_data, campaign):
        """Process and save a single campaign donation"""

        try:
            donation_id = donation_data["id"]

            # Get or create donor
            donor, _ = Account.objects.get_or_create(
                defaults={"chain_id": 1},
                id=donation_data["donor_id"]
            )

            # Get referrer if present
            referrer = None
            if donation_data.get("referrer_id"):
                referrer, _ = Account.objects.get_or_create(
                    defaults={"chain_id": 1},
                    id=donation_data["referrer_id"]
                )

            # Convert timestamp
            donated_at = datetime.fromtimestamp(donation_data["donated_at_ms"] / 1000)

            # Handle returned_at if present
            returned_at = None
            if donation_data.get("returned_at_ms"):
                returned_at = datetime.fromtimestamp(donation_data["returned_at_ms"] / 1000)

            # Donation defaults
            donation_defaults = {
                "campaign": campaign,
                "donor": donor,
                "token": campaign.token,  # Use campaign's token
                "total_amount": str(donation_data["total_amount"]),
                "net_amount": str(donation_data["net_amount"]),
                "message": donation_data.get("message"),
                "donated_at": donated_at,
                "protocol_fee": str(donation_data["protocol_fee"]),
                "referrer": referrer,
                "referrer_fee": str(donation_data.get("referrer_fee", "")) if donation_data.get("referrer_fee") else None,
                "creator_fee": str(donation_data["creator_fee"]),
                "returned_at": returned_at,
                "escrowed": donation_data.get("escrowed", False),
                "tx_hash": donation_data.get("tx_hash"),
            }

            # Create or update donation
            donation, created = CampaignDonation.objects.update_or_create(
                on_chain_id=donation_id,
                campaign=campaign,
                defaults=donation_defaults
            )

            if created:
                self.stdout.write(f"    Created donation: {donation.on_chain_id}")

            # Fetch USD prices for the donation
            try:
                donation.fetch_usd_prices()
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"    Failed to fetch USD prices for donation {donation.on_chain_id}: {e}")
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"    Failed to process donation {donation_data.get('id', 'unknown')}: {e}")
            )
