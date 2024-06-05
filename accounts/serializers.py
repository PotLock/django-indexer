from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, SerializerMethodField

from .models import Account


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            "id",
            "total_donations_in_usd",
            "total_donations_out_usd",
            "total_matching_pool_allocations_usd",
            "donors_count",
        ]


SIMPLE_ACCOUNT_EXAMPLE = {
    "id": "user.near",
    "total_donations_in_usd": "740.00",
    "total_donations_out_usd": "1234.56",
    "total_matching_pool_allocations_usd": "800.01",
    "donors_count": 321,
}
