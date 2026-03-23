import logging

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Account

from .models import OrganizationVerification, VerificationStatus
from .serializers import (
    OrganizationVerificationSerializer,
    OrgVerificationSubmitSerializer,
)

logger = logging.getLogger(__name__)


class OrgVerificationSubmitAPI(APIView):
    """
    Submit or update a 501(c)(3) verification request.

    An organization provides their EIN, legal name, address, and authorized signer info.
    The request is queued for manual admin review.
    """

    @extend_schema(
        summary="Submit 501(c)(3) verification",
        description=(
            "Submit or update a 501(c)(3) verification request for an organization. "
            "If a verification already exists and is Pending or Rejected, it will be updated "
            "and status reset to Pending. If already Approved, the request is rejected."
        ),
        request=OrgVerificationSubmitSerializer,
        responses={
            200: OrganizationVerificationSerializer,
            201: OrganizationVerificationSerializer,
            400: OpenApiResponse(description="Validation error or already approved"),
        },
    )
    def post(self, request):
        serializer = OrgVerificationSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        data = serializer.validated_data
        account_id = data.pop("account_id")

        # Get or create the account
        account, _ = Account.objects.get_or_create(
            id=account_id, defaults={"chain_id": 1}
        )

        # Check if verification already exists
        try:
            existing = OrganizationVerification.objects.get(account=account)

            if existing.status == VerificationStatus.APPROVED:
                return Response(
                    {
                        "error": "Verification is already approved. "
                        "Contact admin if you need to make changes."
                    },
                    status=400,
                )

            # Update existing (Pending or Rejected) and reset to Pending
            address_line2 = data.pop("address_line2", None)
            for field, value in data.items():
                setattr(existing, field, value)
            existing.address_line2 = address_line2 or None
            existing.status = VerificationStatus.PENDING
            existing.admin_notes = None
            existing.save()

            return Response(
                OrganizationVerificationSerializer(existing).data, status=200
            )

        except OrganizationVerification.DoesNotExist:
            # Create new verification
            address_line2 = data.pop("address_line2", None)
            verification = OrganizationVerification.objects.create(
                account=account,
                address_line2=address_line2 or None,
                **data,
            )

            return Response(
                OrganizationVerificationSerializer(verification).data, status=201
            )


class OrgVerificationDetailAPI(APIView):
    """
    Get the 501(c)(3) verification status for an organization.
    """

    @extend_schema(
        summary="Get 501(c)(3) verification status",
        description="Returns the verification status for the given account, or 404 if no verification exists.",
        responses={
            200: OrganizationVerificationSerializer,
            404: OpenApiResponse(description="No verification found for this account"),
        },
    )
    def get(self, request, account_id):
        try:
            verification = OrganizationVerification.objects.select_related(
                "account"
            ).get(account_id=account_id)
        except OrganizationVerification.DoesNotExist:
            return Response(
                {"error": "No verification found for this account"}, status=404
            )

        return Response(OrganizationVerificationSerializer(verification).data)
