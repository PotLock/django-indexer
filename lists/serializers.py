from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, SerializerMethodField

from accounts.serializers import SIMPLE_ACCOUNT_EXAMPLE, AccountSerializer

from .models import List, ListRegistration, ListUpvote


class ListUpvoteSerializer(ModelSerializer):
    class Meta:
        model = ListUpvote
        fields = '__all__'


class ListSerializer(ModelSerializer):
    class Meta:
        model = List
        fields = [
            "id",
            "on_chain_id",
            "owner",
            "admins",
            "name",
            "description",
            "upvotes",
            "registrations_count",
            "cover_image_url",
            "admin_only_registrations",
            "default_registration_status",
            "created_at",
            "updated_at",
        ]

    owner = AccountSerializer()
    admins = AccountSerializer(many=True)
    upvotes = ListUpvoteSerializer(many=True)
    registrations_count = SerializerMethodField()
    
    def get_registrations_count(self, obj):
        return obj.registrations.count()

    # def get_owner(self, obj):
    #     return AccountSerializer(obj.owner).data

    # def get_admins(self, obj):
    #     return AccountSerializer(obj.admins.all(), many=True).data


class ListRegistrationSerializer(ModelSerializer):
    class Meta:
        model = ListRegistration
        fields = [
            "id",
            "list",
            "registrant",
            "registered_by",
            "status",
            "submitted_at",
            "updated_at",
            "registrant_notes",
            "admin_notes",
            "tx_hash",
        ]

    list = ListSerializer()
    registrant = AccountSerializer()
    registered_by = AccountSerializer()


SIMPLE_LIST_EXAMPLE = {
    "id": 1,
    "on_chain_id": 1,
    "owner": SIMPLE_ACCOUNT_EXAMPLE,
    "admins": [SIMPLE_ACCOUNT_EXAMPLE],
    "name": "Potlock Public Goods Registry",
    "description": "The official NEAR Protocol Public Goods Registry",
    "cover_image_url": None,
    "admin_only_registrations": False,
    "default_registration_status": "Approved",
    "created_at": "2024-03-27T15:24:46.104000Z",
    "updated_at": "2024-04-30T19:00:51.002000Z",
}

PAGINATED_LIST_EXAMPLE = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [SIMPLE_LIST_EXAMPLE],
}


class PaginatedListsResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = ListSerializer(many=True)


SIMPLE_LIST_REGISTRATION_EXAMPLE = {
    "id": 10,
    "status": "Approved",
    "submitted_at": "2024-06-05T18:01:02.319Z",
    "updated_at": "2024-06-05T18:01:02.319Z",
    "registrant_notes": "I'm excited to apply for this list",
    "admin_notes": "This is a great project that I want on my list.",
    "tx_hash": "EVMQsXorrrxPLHfK9UnbzFUy1SVYWvc8hwSGQZs4RbTk",
    "list": SIMPLE_LIST_EXAMPLE,
    "registrant": SIMPLE_ACCOUNT_EXAMPLE,
    "registered_by": SIMPLE_ACCOUNT_EXAMPLE,
}

PAGINATED_LIST_REGISTRATION_EXAMPLE = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [SIMPLE_LIST_REGISTRATION_EXAMPLE],
}


class PaginatedListRegistrationsResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = ListRegistrationSerializer(many=True)
