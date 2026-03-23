from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from accounts.serializers import AccountSerializer

from .models import OrganizationVerification


class OrgVerificationSubmitSerializer(serializers.Serializer):
    account_id = serializers.CharField(required=True, help_text="NEAR account ID")
    ein = serializers.CharField(
        max_length=10, required=True, help_text="EIN in XX-XXXXXXX format"
    )
    legal_name = serializers.CharField(
        max_length=255, required=True, help_text="Legal name as registered with IRS"
    )
    address_line1 = serializers.CharField(max_length=255, required=True)
    address_line2 = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    city = serializers.CharField(max_length=100, required=True)
    state = serializers.CharField(
        max_length=2, required=True, help_text="US state code (e.g. CA, NY)"
    )
    zip_code = serializers.CharField(max_length=10, required=True)
    signer_name = serializers.CharField(
        max_length=255,
        required=True,
        help_text="Name of person authorized to sign tax receipts",
    )
    signer_title = serializers.CharField(
        max_length=100,
        required=True,
        help_text="Title of authorized signer (e.g. Executive Director)",
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
            "address_line1",
            "address_line2",
            "city",
            "state",
            "zip_code",
            "signer_name",
            "signer_title",
            "status",
            "admin_notes",
            "submitted_at",
            "updated_at",
        ]
