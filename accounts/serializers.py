from rest_framework.serializers import ModelSerializer, SerializerMethodField

from .models import Account


class AccountSerializer(ModelSerializer):
    class Meta:
        model = Account
        fields = [
            "id",
            "total_donations_in_usd",
            "total_donations_out_usd",
            "total_matching_pool_allocations_usd",
            "donors_count",
            "near_social_profile_data",
        ]
