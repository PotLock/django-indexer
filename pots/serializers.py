import requests
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from django.conf import settings

from accounts.serializers import SIMPLE_ACCOUNT_EXAMPLE, AccountSerializer
from base.serializers import TwoDecimalPlacesField
from tokens.serializers import SIMPLE_TOKEN_EXAMPLE, TokenSerializer

from .models import Pot, PotApplication, PotFactory, PotPayout, PotApplicationReview


class PotSerializer(ModelSerializer):
    total_matching_pool_usd = TwoDecimalPlacesField(max_digits=20, decimal_places=2)
    total_public_donations_usd = TwoDecimalPlacesField(max_digits=20, decimal_places=2)

    class Meta:
        model = Pot
        fields = [
            "account",
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

    deployer = AccountSerializer()
    owner = AccountSerializer()
    admins = AccountSerializer(many=True)
    chef = AccountSerializer()


class PotFactorySerializer(ModelSerializer):

    class Meta:
        model = PotFactory
        fields = [
            "account",
            "owner",
            "admins",
            "whitelisted_deployers",
            "source_metadata",
            "deployed_at",
            "protocol_fee_basis_points",
            "require_whitelist",
            "protocol_fee_recipient",
        ]

    owner = AccountSerializer()
    protocol_fee_recipient = AccountSerializer()
    admins = AccountSerializer(many=True)
    whitelisted_deployers = AccountSerializer(many=True)


class ApplicationReviewSerializer(serializers.ModelSerializer):
    reviewer = serializers.SerializerMethodField()

    class Meta:
        model = PotApplicationReview
        fields = [
            "reviewer",
            "notes",
            "status",
            "reviewed_at",
            "tx_hash"
        ]

    def get_reviewer(self, obj):
        return obj.reviewer.id


class PotApplicationSerializer(ModelSerializer):
    reviews = ApplicationReviewSerializer(many=True)

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
            "reviews",
        ]

    pot = PotSerializer()
    applicant = AccountSerializer()


class PotPayoutSerializer(ModelSerializer):
    class Meta:
        model = PotPayout
        fields = [
            "id",
            "pot",
            "recipient",
            "amount",
            "amount_paid_usd",
            "token",
            "paid_at",
            "tx_hash",
        ]

    pot = PotSerializer()
    recipient = AccountSerializer()
    token = TokenSerializer()


EXAMPLE_POT_ID = "some-pot.v1.potfactory.potlock.near"

EXAMPLE_POT_FACTORY_ID = "v1.potfactory.potlock.near"


SIMPLE_POT_EXAMPLE = {
    "account": "some-pot.v1.potfactory.potlock.near",
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
    "deployer": SIMPLE_ACCOUNT_EXAMPLE,
    "owner": SIMPLE_ACCOUNT_EXAMPLE,
    "chef": SIMPLE_ACCOUNT_EXAMPLE,
    "admins": [SIMPLE_ACCOUNT_EXAMPLE],
}

PAGINATED_POT_EXAMPLE = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [SIMPLE_POT_EXAMPLE],
}


class PaginatedPotsResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = PotSerializer(many=True)

SIMPLE_MPDAO_VOTER_INFO_EXAMPLE = {
    "voter_id": "01f7f1d124232a78b2a2f8e8ac21219d1ecd131ab592c2d9cae505d3c3cd21b6",
    "account_data": {
        "id": "01f7f1d124232a78b2a2f8e8ac21219d1ecd131ab592c2d9cae505d3c3cd21b6",
        "total_donations_in_usd": 0.0,
        "total_donations_out_usd": 0.0,
        "total_matching_pool_allocations_usd": 0.0,
        "donors_count": 0,
        "near_social_profile_data": {
            "name": "Manny98"
        }
    },
    "voter_data": {
        "voter_id": "01f7f1d124232a78b2a2f8e8ac21219d1ecd131ab592c2d9cae505d3c3cd21b6",
        "balance_in_contract": None,
        "voting_power": None,
        "locking_positions": None,
        "vote_positions": None,
        "staking_token_balance": "0",
        "staking_token_id": "meta-pool.near"
    }
}

PAGINATED_MPDAO_USER_EXAMPLE = {
    "count": 30,
    "next": "http://127.0.0.1:8000/api/v1/mpdao/voter-info?page=3&page_size=30",
    "previous": None,
    "results": [SIMPLE_MPDAO_VOTER_INFO_EXAMPLE],
}

SIMPLE_POT_FACTORY_EXAMPLE = {
    "account": "v1.potfactory.potlock.near",
    "owner": SIMPLE_ACCOUNT_EXAMPLE,
    "admins": [SIMPLE_ACCOUNT_EXAMPLE],
    "whitelisted_deployers": [SIMPLE_ACCOUNT_EXAMPLE],
    "source_metadata": {
        "link": "https://github.com/PotLock/core",
        "version": "1.0.0",
        "commit_hash": "e6b108e9442920333b44eb1a4068b9b9ae551d79",
    },
    "deployed_at": "2024-02-12T13:49:58.940854Z",
    "protocol_fee_basis_points": 200,
    "require_whitelist": False,
    "protocol_fee_recipient": SIMPLE_ACCOUNT_EXAMPLE,
}


class PaginatedPotFactoriesResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = PotFactorySerializer(many=True)


PAGINATED_POT_FACTORY_EXAMPLE = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [SIMPLE_POT_FACTORY_EXAMPLE],
}

POT_APPLICATION_REVIEW_EXAMPLE = {
    "reviewer": SIMPLE_ACCOUNT_EXAMPLE,
    "notes": "Looks good!",
    "status": "Approved",
    "reviewed_at": "2024-06-05T18:12:39.014Z",
    "tx_hash": "EVMQsXorrrxPLHfK9UnbzFUy1SVYWvc8hwSGQZs4RbTk",
}


SIMPLE_POT_APPLICATION_EXAMPLE = {
    "id": 2,
    "message": "Hi, I'm a great project and I'd like to apply for this pot.",
    "status": "Pending",
    "submitted_at": "2024-06-05T18:06:45.519Z",
    "updated_at": "2024-06-05T18:06:45.519Z",
    "tx_hash": "EVMQsXorrrxPLHfK9UnbzFUy1SVYWvc8hwSGQZs4RbTk",
    "pot": SIMPLE_POT_EXAMPLE,
    "applicant": SIMPLE_ACCOUNT_EXAMPLE,
    "reviews": [POT_APPLICATION_REVIEW_EXAMPLE],
}

PAGINATED_POT_APPLICATION_EXAMPLE = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [SIMPLE_POT_APPLICATION_EXAMPLE],
}


class PaginatedPotApplicationsResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = PotApplicationSerializer(many=True)


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


class PaginatedPotPayoutsResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = PotPayoutSerializer(many=True)


class LockingPositionSerializer(serializers.Serializer):
    index = serializers.IntegerField()
    amount = serializers.CharField()
    locking_period = serializers.IntegerField()
    voting_power = serializers.CharField()
    unlocking_started_at = serializers.CharField(allow_null=True)
    is_unlocked = serializers.BooleanField()
    is_unlocking = serializers.BooleanField()
    is_locked = serializers.BooleanField()


class VotePositionSerializer(serializers.Serializer):
    votable_address = serializers.CharField()
    votable_object_id = serializers.CharField()
    voting_power = serializers.CharField()


class MpdaoVoterSerializer(serializers.Serializer):
    voter_id = serializers.CharField()
    balance_in_contract = serializers.CharField(allow_null=True)
    voting_power = serializers.CharField(allow_null=True)
    locking_positions = LockingPositionSerializer(many=True, allow_null=True)
    vote_positions = VotePositionSerializer(many=True, allow_null=True)

    staking_token_balance = serializers.SerializerMethodField()

    staking_token_id = serializers.SerializerMethodField()  # mpdao is only available on mainnet, 

    def get_staking_token_balance(self, obj):
        voter_id = obj.get('voter_id')
        url = f"https://rpc.web4.near.page/account/meta-pool.near/view/ft_balance_of?account_id={voter_id}"
        response = requests.get(url)
        if response.status_code == 200:
            balance = response.json()
            return balance
        return "0"
    
    def get_staking_token_id(self, obj):
        return "meta-pool.near"
        
