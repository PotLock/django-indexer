from rest_framework import serializers
from rest_framework.serializers import (
    ModelSerializer,
    Serializer,
    SerializerMethodField,
)

from accounts.serializers import SIMPLE_ACCOUNT_EXAMPLE, AccountSerializer
from pots.serializers import EXAMPLE_POT_ID, SIMPLE_POT_EXAMPLE, PotSerializer
from tokens.serializers import SIMPLE_TOKEN_EXAMPLE, TokenSerializer

from .models import Donation


class DonationSerializer(ModelSerializer):

    class Meta:
        model = Donation
        fields = [
            "id",
            "on_chain_id",
            "total_amount",
            "total_amount_usd",
            "net_amount",
            "net_amount_usd",
            "matching_pool",
            "message",
            "donated_at",
            "protocol_fee",
            "protocol_fee_usd",
            "referrer_fee",
            "referrer_fee_usd",
            "chef_fee",
            "chef_fee_usd",
            "tx_hash",
            "donor",
            "token",
            "pot",
            "recipient",
            "referrer",
            "chef",
        ]

    donor = SerializerMethodField()
    token = SerializerMethodField()
    pot = SerializerMethodField()
    recipient = SerializerMethodField()
    referrer = SerializerMethodField()
    chef = SerializerMethodField()

    def get_donor(self, obj):
        return AccountSerializer(obj.donor).data

    def get_token(self, obj):
        return TokenSerializer(obj.token).data

    def get_pot(self, obj):
        if obj.pot:
            return PotSerializer(obj.pot).data

    def get_recipient(self, obj):
        if obj.recipient:
            return AccountSerializer(obj.recipient).data

    def get_referrer(self, obj):
        if obj.referrer:
            return AccountSerializer(obj.referrer).data

    def get_chef(self, obj):
        if obj.chef:
            return AccountSerializer(obj.chef).data


SIMPLE_DONATION_EXAMPLE = {
    "id": 100,
    "on_chain_id": 156,
    "total_amount": "1000000000000000000000000",
    "total_amount_usd": "1.17",
    "net_amount": "1000000000000000000000000",
    "net_amount_usd": "1.02",
    "matching_pool": False,
    "message": None,
    "donated_at": "2024-06-05T18:08:40.751Z",
    "protocol_fee": "10000000000000000000000",
    "protocol_fee_usd": "0.27",
    "referrer_fee": "10000000000000000000000",
    "referrer_fee_usd": "0.27",
    "chef_fee": "10000000000000000000000",
    "chef_fee_usd": "0.27",
    "tx_hash": "EVMQsXorrrxPLHfK9UnbzFUy1SVYWvc8hwSGQZs4RbTk",
    "donor": SIMPLE_ACCOUNT_EXAMPLE,
    "token": SIMPLE_TOKEN_EXAMPLE,
    "pot": SIMPLE_POT_EXAMPLE,
    "recipient": SIMPLE_ACCOUNT_EXAMPLE,
    "referrer": SIMPLE_ACCOUNT_EXAMPLE,
    "chef": SIMPLE_ACCOUNT_EXAMPLE,
}

PAGINATED_DONATION_EXAMPLE = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [SIMPLE_DONATION_EXAMPLE],
}


class DonationContractConfigSerializer(Serializer):
    owner = serializers.CharField()
    protocol_fee_basis_points = serializers.IntegerField()
    referral_fee_basis_points = serializers.IntegerField()
    protocol_fee_recipient_account = serializers.CharField()
