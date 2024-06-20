from rest_framework.serializers import ModelSerializer, SerializerMethodField

from base.serializers import TwoDecimalStringField
from tokens.serializers import SIMPLE_TOKEN_EXAMPLE

from .models import Pot, PotApplication, PotPayout


class PotSerializer(ModelSerializer):
    total_matching_pool_usd = TwoDecimalStringField(max_digits=20, decimal_places=2)
    total_public_donations_usd = TwoDecimalStringField(max_digits=20, decimal_places=2)

    class Meta:
        model = Pot
        fields = [
            "id",
            "pot_factory",
            "deployer",
            "deployed_at",
            "source_metadata",
            "owner",
            "admins",
            "chef",
            "name",
            "description",
            "max_approved_applicants",
            "base_currency",
            "application_start",
            "application_end",
            "matching_round_start",
            "matching_round_end",
            "registry_provider",
            "min_matching_pool_donation_amount",
            "sybil_wrapper_provider",
            "custom_sybil_checks",
            "custom_min_threshold_score",
            "referral_fee_matching_pool_basis_points",
            "referral_fee_public_round_basis_points",
            "chef_fee_basis_points",
            "total_matching_pool",
            "total_matching_pool_usd",
            "matching_pool_balance",
            "matching_pool_donations_count",
            "total_public_donations",
            "total_public_donations_usd",
            "public_donations_count",
            "cooldown_end",
            "cooldown_period_ms",
            "all_paid_out",
            "protocol_config_provider",
        ]


class PotApplicationSerializer(ModelSerializer):

    class Meta:
        model = PotApplication
        fields = [
            "id",
            "pot",
            "applicant",
            "message",
            "status",
            "submitted_at",
            "updated_at",
            "tx_hash",
        ]

    pot = SerializerMethodField()

    def get_pot(self, obj):
        return PotSerializer(obj.pot).data


class PotPayoutSerializer(ModelSerializer):
    class Meta:
        model = PotPayout
        fields = "__all__"  # TODO: potentially adjust this e.g. for formatting of datetimes, adding convenience fields etc


EXAMPLE_POT_ID = "some-pot.v1.potfactory.potlock.near"

SIMPLE_POT_EXAMPLE = {
    "id": "some-pot.v1.potfactory.potlock.near",
    "deployed_at": "2024-02-16T17:45:03.600845Z",
    "source_metadata": {
        "link": "https://github.com/PotLock/core",
        "version": "0.1.0",
        "commit_hash": "2db43b1182eb97d34e1b67f21b44c7084b364358",
    },
    "name": "My Pot Name",
    "description": "To support impactful open source software projects.",
    "max_approved_applicants": 50,
    "base_currency": "near",
    "application_start": "2024-04-08T04:00:00Z",
    "application_end": "2024-04-22T03:59:00Z",
    "matching_round_start": "2024-04-22T04:00:00Z",
    "matching_round_end": "2024-05-06T03:59:00Z",
    "registry_provider": "registry.potlock.near:is_registered",
    "min_matching_pool_donation_amount": "0",
    "sybil_wrapper_provider": "v1.nadabot.near:is_human",
    "custom_sybil_checks": None,
    "custom_min_threshold_score": None,
    "referral_fee_matching_pool_basis_points": 500,
    "referral_fee_public_round_basis_points": 500,
    "chef_fee_basis_points": 500,
    "total_matching_pool": "10000000000000000000",
    "total_matching_pool_usd": "100.17",
    "matching_pool_balance": "10000000000000000000",
    "matching_pool_donations_count": 0,
    "total_public_donations": "100000000000000000",
    "total_public_donations_usd": "1.17",
    "public_donations_count": 0,
    "cooldown_end": None,
    "cooldown_period_ms": None,
    "all_paid_out": False,
    "protocol_config_provider": "v1.potfactory.potlock.near:get_protocol_config",
    "pot_factory": "v1.potfactory.potlock.near",
    "deployer": "ossround.near",
    "owner": "ossround.near",
    "chef": "plugrel.near",
    "admins": [],
}

PAGINATED_POT_EXAMPLE = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [SIMPLE_POT_EXAMPLE],
}

SIMPLE_POT_APPLICATION_EXAMPLE = {
    "id": 2,
    "message": "Hi, I'm a great project and I'd like to apply for this pot.",
    "status": "Pending",
    "submitted_at": "2024-06-05T18:06:45.519Z",
    "updated_at": "2024-06-05T18:06:45.519Z",
    "tx_hash": "EVMQsXorrrxPLHfK9UnbzFUy1SVYWvc8hwSGQZs4RbTk",
    "pot": SIMPLE_POT_EXAMPLE,
    "applicant": "applicant.near",
}

PAGINATED_POT_APPLICATION_EXAMPLE = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [SIMPLE_POT_APPLICATION_EXAMPLE],
}

SIMPLE_PAYOUT_EXAMPLE = {
    "id": 4,
    "amount": "1000000000000000000000000",
    "amount_paid_usd": "1.27",
    "paid_at": "2024-06-05T18:12:39.014Z",
    "tx_hash": "EVMQsXorrrxPLHfK9UnbzFUy1SVYWvc8hwSGQZs4RbTk",
    "pot": SIMPLE_POT_EXAMPLE,
    "recipient": "someproject.near",
    "token": SIMPLE_TOKEN_EXAMPLE,
}

PAGINATED_PAYOUT_EXAMPLE = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [SIMPLE_PAYOUT_EXAMPLE],
}
