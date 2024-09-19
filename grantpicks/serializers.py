from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from accounts.serializers import SIMPLE_ACCOUNT_EXAMPLE, AccountSerializer
from base.serializers import TwoDecimalPlacesField

from .models import Project, ProjectContact, ProjectContract, ProjectRepository, Round, Vote, VotePair
from pots.models import PotApplication




class ProjectContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectContact
        fields = ['id', 'name', 'value']

class ProjectContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectContract
        fields = ['id', 'name', 'contract_address']

class ProjectRepositorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectRepository
        fields = ['id', 'label', 'url']

class ProjectSerializer(serializers.ModelSerializer):
    contacts = ProjectContactSerializer(many=True, required=False)
    contracts = ProjectContractSerializer(many=True, required=False)
    repositories = ProjectRepositorySerializer(many=True, required=False)
    owner = AccountSerializer()
    payout_address = AccountSerializer()

    class Meta:
        model = Project
        fields = [
            'id',
            'on_chain_id',
            'image_url',
            'video_url',
            'name',
            'overview',
            'owner',
            'payout_address',
            'contacts',
            'contracts',
            'team_members',
            'repositories',
            'status',
            'submited_ms',
            'updated_ms',
            'admins',
        ]

class RoundSerializer(ModelSerializer):
    current_vault_balance_usd = TwoDecimalPlacesField(max_digits=20, decimal_places=2)
    vault_total_deposits_usd = TwoDecimalPlacesField(max_digits=20, decimal_places=2)

    class Meta:
        model = Round
        fields = [
            "id",  # Include the primary key
            "on_chain_id",
            "factory_contract",
            "deployed_at",
            "owner",
            "admins",
            "name",
            "description",
            "contacts",
            "expected_amount",
            "base_currency",
            "application_start",
            "application_end",
            "voting_start",
            "voting_end",
            "use_whitelist",
            "use_vault",
            "num_picks_per_voter",
            "max_participants",
            "approved_projects",
            "allow_applications",
            "is_video_required",
            "cooldown_end",
            "cooldown_period_ms",
            "compliance_req_desc",
            "compliance_period_ms",
            "compliance_end",
            "allow_remaining_dist",
            "remaining_dist_address",
            "remaining_dist_memo",
            "remaining_dist_at_ms",
            "current_vault_balance",
            "current_vault_balance_usd",
            "remaining_dist_by",
            "referrer_fee_basis_points",
            "vault_total_deposits",
            "vault_total_deposits_usd",
            "round_complete",
        ]
    owner = AccountSerializer()
    remaining_dist_address = AccountSerializer()
    admins = AccountSerializer(many=True)
    remaining_dist_by = AccountSerializer()


class RoundApplicationSerializer(ModelSerializer):

    class Meta:
        model = PotApplication
        fields = [
            "id",
            "round",
            "applicant",
            "project",
            "message",
            "status",
            "submitted_at",
            "updated_at",
            "tx_hash",
        ]

    round = RoundSerializer()
    applicant = AccountSerializer()
    project = ProjectSerializer()


SIMPLE_PROJECT_EXAMPLE = {
    "id": 1,
    "on_chain_id": 123,
    "image_url": "https://example.com/image.png",
    "video_url": "https://example.com/video.mp4",
    "name": "My Project",
    "overview": "This project aims to do something impactful.",
    "owner": "GD4I4FXMIKKKVSGVCGNILRFFHDQHITMDW545SCLGEOKGBN6W44AV6367",
    "payout_address": "GD4I4FXMIKKKVSGVCGNILRFFHDQHITMDW545SCLGEOKGBN6W44AV6367",
    "contacts": [],
    "contracts": [],
    "team_members": [],
    "repositories": [],
    "status": "NEW",
    "submited_ms": 1726657637439,
    "updated_ms": None,
    "admins": [],
}

SIMPLE_ROUND_EXAMPLE = {
    "id": 1,
    "name": "InteractGrant TO Apply V1",
    "owner": "GD4I4FXMIKKKVSGVCGNILRFFHDQHITMDW545SCLGEOKGBN6W44AV6367",
    "contacts": [],
    "use_vault": True,
    "description": "This is a test round",
    "use_whitelist": False,
    "voting_start": "2024-06-25T00:00:00Z",  
    "voting_end": "2024-06-30T00:00:00Z",    
    "cooldown_end": None,
    "expected_amount": 100000000000,
    "max_participants": 10,
    "compliance_end": None,
    "is_video_required": False,
    "remaining_dist_by": "GD4I4FXMIKKKVSGVCGNILRFFHDQHITMDW545SCLGEOKGBN6W44AV6367",
    "round_complete": None,
    "allow_applications": True,
    "application_start": "2024-06-20T00:00:00Z", 
    "application_end": "2024-06-25T00:00:00Z",    
    "cooldown_period_ms": None,
    "compliance_req_desc": "This is a compliance requirement",
    "num_picks_per_voter": 2,
    "remaining_dist_memo": "",
    "allow_remaining_dist": False,
    "remaining_dist_address": "GD4I4FXMIKKKVSGVCGNILRFFHDQHITMDW545SCLGEOKGBN6W44AV6367",
    "vault_total_deposits": 0,
    "current_vault_balance": 0,
    "referrer_fee_basis_points": 0,
}

PAGINATED_ROUND_EXAMPLE = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [SIMPLE_ROUND_EXAMPLE],
}

PAGINATED_PROJECT_EXAMPLE = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [SIMPLE_PROJECT_EXAMPLE],
}



class PaginatedRoundsResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = RoundSerializer(many=True)


class PaginatedProjectsResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = ProjectSerializer(many=True)




SIMPLE_ROUND_APPLICATION_EXAMPLE = {
    "id": 2,
    "message": "Hi, I'm a great project and I'd like to apply for this pot.",
    "status": "Pending",
    "submitted_at": "2024-06-05T18:06:45.519Z",
    "updated_at": "2024-06-05T18:06:45.519Z",
    "tx_hash": "EVMQsXorrrxPLHfK9UnbzFUy1SVYWvc8hwSGQZs4RbTk",
    "round": SIMPLE_ROUND_EXAMPLE,
    "applicant": SIMPLE_ACCOUNT_EXAMPLE,
}

PAGINATED_ROUND_APPLICATION_EXAMPLE = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [SIMPLE_ROUND_APPLICATION_EXAMPLE],
}


class PaginatedRoundApplicationsResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = RoundApplicationSerializer(many=True)



class VoteSerializer(serializers.ModelSerializer):
    round = serializers.PrimaryKeyRelatedField(queryset=Round.objects.all())
    voter = AccountSerializer()

    class Meta:
        model = Vote
        fields = [
            'id',
            'round',
            'voter',
            'tx_hash',
            'voted_at',
        ]



class PaginatedVotesResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField() 
    next = serializers.CharField(allow_null=True) 
    previous = serializers.CharField(allow_null=True) 
    results = VoteSerializer(many=True)



class VotePairSerializer(serializers.ModelSerializer):
    vote = VoteSerializer() 
    project = ProjectSerializer()

    class Meta:
        model = VotePair
        fields = [
            'vote',
            'pair_id',
            'project',
        ]

class PaginatedVotePairResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField() 
    next = serializers.CharField(allow_null=True) 
    previous = serializers.CharField(allow_null=True) 
    results = VotePairSerializer(many=True)


SIMPLE_VOTE_EXAMPLE = {
    "id": 1,
    "round": 1,  
    "voter": SIMPLE_ACCOUNT_EXAMPLE,
    "tx_hash": "0x123456789abcdef",
    "voted_at": "2024-06-25T00:00:00Z",  
}


SIMPLE_VOTE_PAIR_EXAMPLE = {
    "vote": SIMPLE_VOTE_EXAMPLE,
    "pair_id": 1, 
    "project": SIMPLE_PROJECT_EXAMPLE
}

PAGINATED_VOTE_PAIR_EXAMPLE = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [SIMPLE_VOTE_PAIR_EXAMPLE],
}