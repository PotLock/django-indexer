from django.utils import timezone
from rest_framework import serializers
from rest_framework.serializers import (
    ModelSerializer,
    Serializer,
    SerializerMethodField,
)

from accounts.serializers import SIMPLE_ACCOUNT_EXAMPLE, AccountSerializer
from tokens.serializers import SIMPLE_TOKEN_EXAMPLE, TokenSerializer

from .models import Campaign, CampaignDonation


class CampaignSerializer(ModelSerializer):
    class Meta:
        model = Campaign
        fields = [
            "on_chain_id",
            "name",
            "description",
            "cover_image_url",
            "start_at",
            "end_at",
            "created_at",
            "target_amount",
            "target_amount_usd",
            "min_amount",
            "min_amount_usd",
            "max_amount",
            "max_amount_usd",
            "total_raised_amount",
            "total_raised_amount_usd",
            "net_raised_amount",
            "net_raised_amount_usd",
            "escrow_balance",
            "escrow_balance_usd",
            "referral_fee_basis_points",
            "creator_fee_basis_points",
            "allow_fee_avoidance",
            "owner",
            "recipient",
            "token",
            "status",
        ]

    owner = AccountSerializer()
    recipient = AccountSerializer()
    token = TokenSerializer()
    status = serializers.SerializerMethodField()

    def get_status(self, obj):
        """
        Get campaign status: active, ended, or upcoming
        """
        from django.utils import timezone

        now = timezone.now()

        if obj.start_at > now:
            return "upcoming"

        if obj.end_at is not None and obj.end_at <= now:
            return "ended"

        if obj.max_amount is not None:
            try:
                net_raised = int(obj.net_raised_amount)
                max_amount = int(obj.max_amount)
                if net_raised >= max_amount:
                    return "ended"
            except (ValueError, TypeError):
                # If we can't parse the amounts, assume not maxed out
                pass

        return "active"



class CampaignDonationSerializer(ModelSerializer):
    class Meta:
        model = CampaignDonation
        fields = [
            "id",
            "on_chain_id",
            "total_amount",
            "total_amount_usd",
            "net_amount",
            "net_amount_usd",
            "message",
            "donated_at",
            "protocol_fee",
            "protocol_fee_usd",
            "referrer_fee",
            "referrer_fee_usd",
            "creator_fee",
            "creator_fee_usd",
            "returned_at",
            "escrowed",
            "tx_hash",
            "campaign",
            "donor",
            "token",
            "referrer",
        ]

    campaign = CampaignSerializer()
    donor = AccountSerializer()
    token = TokenSerializer()
    referrer = AccountSerializer()


SIMPLE_CAMPAIGN_EXAMPLE = {
    "on_chain_id": 1,
    "name": "Help Build Community Center",
    "description": "Fundraising campaign to build a new community center for local residents.",
    "cover_image_url": "https://example.com/campaign-image.jpg",
    "start_at": "2024-01-01T00:00:00Z",
    "end_at": "2024-03-01T00:00:00Z",
    "created_at": "2023-12-15T10:30:00Z",
    "target_amount": "10000000000000000000000000",
    "target_amount_usd": "10000.00",
    "min_amount": "1000000000000000000000000",
    "min_amount_usd": "1000.00",
    "max_amount": None,
    "max_amount_usd": None,
    "total_raised_amount": "2500000000000000000000000",
    "total_raised_amount_usd": "2500.00",
    "net_raised_amount": "2375000000000000000000000",
    "net_raised_amount_usd": "2375.00",
    "escrow_balance": "0",
    "escrow_balance_usd": "0.00",
    "referral_fee_basis_points": 500,
    "creator_fee_basis_points": 250,
    "allow_fee_avoidance": False,
    "status": "active",
    "owner": SIMPLE_ACCOUNT_EXAMPLE,
    "recipient": SIMPLE_ACCOUNT_EXAMPLE,
    "token": SIMPLE_TOKEN_EXAMPLE,
}

SIMPLE_CAMPAIGN_DONATION_EXAMPLE = {
    "id": 100,
    "on_chain_id": 50,
    "total_amount": "1000000000000000000000000",
    "total_amount_usd": "1000.00",
    "net_amount": "925000000000000000000000",
    "net_amount_usd": "925.00",
    "message": "Great cause! Happy to support.",
    "donated_at": "2024-01-15T14:20:30Z",
    "protocol_fee": "25000000000000000000000",
    "protocol_fee_usd": "25.00",
    "referrer_fee": "25000000000000000000000",
    "referrer_fee_usd": "25.00",
    "creator_fee": "25000000000000000000000",
    "creator_fee_usd": "25.00",
    "returned_at": None,
    "tx_hash": "ABC123DEF456GHI789JKL012MNO345PQR678STU901VWX234YZA567BCD890",
    "campaign": SIMPLE_CAMPAIGN_EXAMPLE,
    "donor": SIMPLE_ACCOUNT_EXAMPLE,
    "token": SIMPLE_TOKEN_EXAMPLE,
    "referrer": SIMPLE_ACCOUNT_EXAMPLE,
}

PAGINATED_CAMPAIGNS_EXAMPLE = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [SIMPLE_CAMPAIGN_EXAMPLE],
}

PAGINATED_CAMPAIGN_DONATIONS_EXAMPLE = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [SIMPLE_CAMPAIGN_DONATION_EXAMPLE],
}


class PaginatedCampaignsResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = CampaignSerializer(many=True)


class PaginatedCampaignDonationsResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = CampaignDonationSerializer(many=True)


class CampaignContractConfigSerializer(Serializer):
    owner = serializers.CharField()
    protocol_fee_basis_points = serializers.IntegerField()
    protocol_fee_recipient_account = serializers.CharField()
    default_referral_fee_basis_points = serializers.IntegerField()
    default_creator_fee_basis_points = serializers.IntegerField()
