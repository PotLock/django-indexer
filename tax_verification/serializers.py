from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from accounts.serializers import AccountSerializer

from .models import OrganizationVerification


class OrgVerificationSubmitSerializer(serializers.Serializer):
    account_id = serializers.CharField(required=True, help_text="NEAR account ID")
    ein = serializers.CharField(
        max_length=10,
        required=True,
        help_text="EIN in XX-XXXXXXX format (e.g. 53-0196605)",
    )


class OrganizationVerificationSerializer(ModelSerializer):
    account = AccountSerializer()

    class Meta:
        model = OrganizationVerification
        fields = [
            "id",
            "account",
            "ein",
            "legal_name",
            "address",
            "city",
            "state",
            "zip_code",
            "subsection_code",
            "ntee_code",
            "ruling_date",
            "status",
            "rejection_reason",
            "submitted_at",
            "updated_at",
        ]
