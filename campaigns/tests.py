from datetime import datetime, timezone
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone as django_timezone

from accounts.models import Account
from tokens.models import Token
from .models import Campaign, CampaignDonation


class CampaignModelTests(TestCase):
    def setUp(self):
        """Set up test data"""
        self.owner = Account.objects.create(id="owner.near")
        self.recipient = Account.objects.create(id="recipient.near")
        self.token = Token.objects.create(
            account=Account.objects.create(id="token.near"),
            name="Test Token",
            symbol="TEST",
            decimals=18,
        )

        self.campaign_data = {
            "on_chain_id": 1,
            "owner": self.owner,
            "name": "Test Campaign",
            "description": "A test campaign",
            "recipient": self.recipient,
            "start_at": django_timezone.now(),
            "created_at": django_timezone.now(),
            "target_amount": "1000000000000000000000000",
            "referral_fee_basis_points": 500,
            "creator_fee_basis_points": 250,
        }

    def test_campaign_creation(self):
        """Test basic campaign creation"""
        campaign = Campaign.objects.create(**self.campaign_data)

        self.assertEqual(campaign.on_chain_id, 1)
        self.assertEqual(campaign.name, "Test Campaign")
        self.assertEqual(campaign.owner, self.owner)
        self.assertEqual(campaign.recipient, self.recipient)
        self.assertEqual(campaign.total_raised_amount, "0")
        self.assertEqual(campaign.net_raised_amount, "0")
        self.assertEqual(campaign.escrow_balance, "0")
        self.assertFalse(campaign.allow_fee_avoidance)

    def test_campaign_with_token(self):
        """Test campaign creation with token"""
        self.campaign_data["token"] = self.token
        campaign = Campaign.objects.create(**self.campaign_data)

        self.assertEqual(campaign.token, self.token)

    def test_campaign_with_optional_fields(self):
        """Test campaign with optional fields"""
        end_time = django_timezone.now()
        self.campaign_data.update({
            "end_at": end_time,
            "cover_image_url": "https://example.com/image.jpg",
            "min_amount": "100000000000000000000",  # 100 tokens
            "max_amount": "10000000000000000000000000",  # 10M tokens
            "allow_fee_avoidance": True,
        })

        campaign = Campaign.objects.create(**self.campaign_data)

        self.assertEqual(campaign.end_at, end_time)
        self.assertEqual(campaign.cover_image_url, "https://example.com/image.jpg")
        self.assertEqual(campaign.min_amount, "100000000000000000000")
        self.assertEqual(campaign.max_amount, "10000000000000000000000000")
        self.assertTrue(campaign.allow_fee_avoidance)

    def test_campaign_string_representation(self):
        """Test campaign string representation"""
        campaign = Campaign.objects.create(**self.campaign_data)
        expected = f"Campaign {campaign.on_chain_id}: {campaign.name}"
        self.assertEqual(str(campaign), expected)

    def test_campaign_ordering(self):
        """Test campaign ordering by creation date"""
        # Create first campaign
        campaign1 = Campaign.objects.create(**self.campaign_data)

        # Create second campaign with different data
        campaign_data_2 = self.campaign_data.copy()
        campaign_data_2["on_chain_id"] = 2
        campaign_data_2["name"] = "Second Campaign"
        campaign_data_2["created_at"] = django_timezone.now()
        campaign2 = Campaign.objects.create(**campaign_data_2)

        # Test ordering (newest first)
        campaigns = list(Campaign.objects.all())
        self.assertEqual(campaigns[0], campaign2)  # Newer campaign first
        self.assertEqual(campaigns[1], campaign1)

    def test_unique_on_chain_id(self):
        """Test that on_chain_id must be unique"""
        Campaign.objects.create(**self.campaign_data)

        # Try to create another campaign with same on_chain_id
        campaign_data_2 = self.campaign_data.copy()
        campaign_data_2["name"] = "Duplicate Campaign"

        with self.assertRaises(Exception):  # Should raise IntegrityError
            Campaign.objects.create(**campaign_data_2)


class CampaignDonationModelTests(TestCase):
    def setUp(self):
        """Set up test data"""
        self.owner = Account.objects.create(id="owner.near")
        self.recipient = Account.objects.create(id="recipient.near")
        self.donor = Account.objects.create(id="donor.near")
        self.referrer = Account.objects.create(id="referrer.near")

        self.campaign = Campaign.objects.create(
            on_chain_id=1,
            owner=self.owner,
            name="Test Campaign",
            recipient=self.recipient,
            start_at=django_timezone.now(),
            created_at=django_timezone.now(),
            target_amount="1000000000000000000000000",
            referral_fee_basis_points=500,
            creator_fee_basis_points=250,
        )

        self.donation_data = {
            "on_chain_id": 1,
            "campaign": self.campaign,
            "donor": self.donor,
            "total_amount": "1000000000000000000000000",  # 1M tokens
            "net_amount": "925000000000000000000000",    # After fees
            "donated_at": django_timezone.now(),
            "protocol_fee": "25000000000000000000000",   # 2.5%
            "creator_fee": "25000000000000000000000",    # 2.5%
        }

    def test_campaign_donation_creation(self):
        """Test basic campaign donation creation"""
        donation = CampaignDonation.objects.create(**self.donation_data)

        self.assertEqual(donation.on_chain_id, 1)
        self.assertEqual(donation.campaign, self.campaign)
        self.assertEqual(donation.donor, self.donor)
        self.assertEqual(donation.total_amount, "1000000000000000000000000")
        self.assertEqual(donation.net_amount, "925000000000000000000000")
        self.assertIsNone(donation.returned_at)

    def test_campaign_donation_with_optional_fields(self):
        """Test campaign donation with optional fields"""
        self.donation_data.update({
            "message": "Great cause!",
            "referrer": self.referrer,
            "referrer_fee": "25000000000000000000000",
            "tx_hash": "ABC123DEF456",
        })

        donation = CampaignDonation.objects.create(**self.donation_data)

        self.assertEqual(donation.message, "Great cause!")
        self.assertEqual(donation.referrer, self.referrer)
        self.assertEqual(donation.referrer_fee, "25000000000000000000000")
        self.assertEqual(donation.tx_hash, "ABC123DEF456")

    def test_campaign_donation_with_usd_amounts(self):
        """Test campaign donation with USD amounts"""
        self.donation_data.update({
            "total_amount_usd": Decimal("1000.00"),
            "net_amount_usd": Decimal("925.00"),
            "protocol_fee_usd": Decimal("25.00"),
            "creator_fee_usd": Decimal("25.00"),
        })

        donation = CampaignDonation.objects.create(**self.donation_data)

        self.assertEqual(donation.total_amount_usd, Decimal("1000.00"))
        self.assertEqual(donation.net_amount_usd, Decimal("925.00"))
        self.assertEqual(donation.protocol_fee_usd, Decimal("25.00"))
        self.assertEqual(donation.creator_fee_usd, Decimal("25.00"))

    def test_campaign_donation_refund(self):
        """Test marking donation as refunded"""
        donation = CampaignDonation.objects.create(**self.donation_data)

        # Initially not refunded
        self.assertIsNone(donation.returned_at)

        # Mark as refunded
        refund_time = django_timezone.now()
        donation.returned_at = refund_time
        donation.save()

        self.assertEqual(donation.returned_at, refund_time)

    def test_campaign_donation_string_representation(self):
        """Test campaign donation string representation"""
        donation = CampaignDonation.objects.create(**self.donation_data)
        expected = f"Donation {donation.on_chain_id} to Campaign {self.campaign.on_chain_id}"
        self.assertEqual(str(donation), expected)

    def test_campaign_donation_ordering(self):
        """Test campaign donation ordering by donated_at"""
        # Create first donation
        donation1 = CampaignDonation.objects.create(**self.donation_data)

        # Create second donation
        donation_data_2 = self.donation_data.copy()
        donation_data_2["on_chain_id"] = 2
        donation_data_2["donated_at"] = django_timezone.now()
        donation2 = CampaignDonation.objects.create(**donation_data_2)

        # Test ordering (newest first)
        donations = list(CampaignDonation.objects.all())
        self.assertEqual(donations[0], donation2)  # Newer donation first
        self.assertEqual(donations[1], donation1)

    def test_unique_constraint(self):
        """Test unique constraint on (on_chain_id, campaign)"""
        CampaignDonation.objects.create(**self.donation_data)

        # Try to create another donation with same on_chain_id and campaign
        donation_data_2 = self.donation_data.copy()
        donation_data_2["total_amount"] = "500000000000000000000000"

        with self.assertRaises(Exception):  # Should raise IntegrityError
            CampaignDonation.objects.create(**donation_data_2)

    def test_campaign_relationship(self):
        """Test relationship between campaign and donations"""
        donation = CampaignDonation.objects.create(**self.donation_data)

        # Test forward relationship
        self.assertEqual(donation.campaign, self.campaign)

        # Test reverse relationship
        self.assertIn(donation, self.campaign.donations.all())

    def test_donor_relationship(self):
        """Test relationship between donor and campaign donations"""
        donation = CampaignDonation.objects.create(**self.donation_data)

        # Test forward relationship
        self.assertEqual(donation.donor, self.donor)

        # Test reverse relationship
        self.assertIn(donation, self.donor.campaign_donations.all())


class CampaignModelMethodTests(TestCase):
    def setUp(self):
        """Set up test data"""
        self.owner = Account.objects.create(id="owner.near")
        self.recipient = Account.objects.create(id="recipient.near")

        self.campaign = Campaign.objects.create(
            on_chain_id=1,
            owner=self.owner,
            name="Test Campaign",
            recipient=self.recipient,
            start_at=django_timezone.now(),
            created_at=django_timezone.now(),
            target_amount="1000000000000000000000000",
            referral_fee_basis_points=500,
            creator_fee_basis_points=250,
        )

    def test_to_dict_method(self):
        """Test campaign to_dict method"""
        campaign_dict = self.campaign.to_dict()

        self.assertIsInstance(campaign_dict, dict)
        self.assertEqual(campaign_dict['on_chain_id'], 1)
        self.assertEqual(campaign_dict['name'], "Test Campaign")
        self.assertEqual(campaign_dict['target_amount'], "1000000000000000000000000")


class CampaignDonationMethodTests(TestCase):
    def setUp(self):
        """Set up test data"""
        self.owner = Account.objects.create(id="owner.near")
        self.recipient = Account.objects.create(id="recipient.near")
        self.donor = Account.objects.create(id="donor.near")

        self.campaign = Campaign.objects.create(
            on_chain_id=1,
            owner=self.owner,
            name="Test Campaign",
            recipient=self.recipient,
            start_at=django_timezone.now(),
            created_at=django_timezone.now(),
            target_amount="1000000000000000000000000",
            referral_fee_basis_points=500,
            creator_fee_basis_points=250,
        )

        self.donation = CampaignDonation.objects.create(
            on_chain_id=1,
            campaign=self.campaign,
            donor=self.donor,
            total_amount="1000000000000000000000000",
            net_amount="925000000000000000000000",
            donated_at=django_timezone.now(),
            protocol_fee="25000000000000000000000",
            creator_fee="25000000000000000000000",
        )

    def test_to_dict_method(self):
        """Test campaign donation to_dict method"""
        donation_dict = self.donation.to_dict()

        self.assertIsInstance(donation_dict, dict)
        self.assertEqual(donation_dict['on_chain_id'], 1)
        self.assertEqual(donation_dict['total_amount'], "1000000000000000000000000")
        self.assertEqual(donation_dict['net_amount'], "925000000000000000000000")
