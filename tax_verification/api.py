import logging
import re

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Account

from .models import NonprofitRegistry, OrganizationVerification, VerificationStatus
from .serializers import (
    OrganizationVerificationSerializer,
    OrgVerificationSubmitSerializer,
)

logger = logging.getLogger(__name__)


def verify_ein_with_registry(ein: str) -> dict:
    """
    Look up an EIN in the local NonprofitRegistry (populated from IRS EO BMF).
    Returns dict with org data if found, or raises ValueError if not found.
    """
    # Strip dashes — registry stores 9-digit EINs without dashes
    clean_ein = ein.replace("-", "")

    try:
        record = NonprofitRegistry.objects.get(ein=clean_ein)
    except NonprofitRegistry.DoesNotExist:
        raise ValueError(
            f"EIN {ein} was not found in IRS records. "
            "Please check the number and try again."
        )

    # Convert subsection string ("03") to int (3) to match previous ProPublica response shape
    try:
        subsection_code = int(record.subsection) if record.subsection else None
    except ValueError:
        subsection_code = None

    return {
        "name": record.name,
        "address": record.street,
        "city": record.city,
        "state": record.state,
        "zipcode": record.zip,
        "subsection_code": subsection_code,
        "ntee_code": record.ntee_cd,
        "ruling_date": record.ruling,
    }


class OrgVerificationSubmitAPI(APIView):
    @extend_schema(
        request=OrgVerificationSubmitSerializer,
        responses={200: OrganizationVerificationSerializer},
        summary="Submit 501(c)(3) verification",
        description=(
            "Submit an EIN for automated 501(c)(3) verification against local IRS "
            "registry. Auto-approves if subsection_code is 3 (501(c)(3)), "
            "otherwise rejects."
        ),
    )
    def post(self, request):
        serializer = OrgVerificationSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        account_id = serializer.validated_data["account_id"]
        ein = serializer.validated_data["ein"]

        # Validate EIN format (XX-XXXXXXX)
        if not re.match(r"^\d{2}-?\d{7}$", ein):
            return Response(
                {"detail": "Invalid EIN format. Expected XX-XXXXXXX."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if already approved
        existing = OrganizationVerification.objects.filter(
            account_id=account_id
        ).first()
        if existing and existing.status == VerificationStatus.APPROVED:
            return Response(
                {"detail": "This account is already verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify against local IRS registry
        try:
            org_data = verify_ein_with_registry(ein)
        except ValueError as e:
            # If existing record, update it to rejected
            if existing:
                existing.ein = ein
                existing.status = VerificationStatus.REJECTED
                existing.rejection_reason = str(e)
                existing.save()
                return Response(
                    OrganizationVerificationSerializer(existing).data,
                    status=status.HTTP_200_OK,
                )
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Determine approval based on subsection code
        subsection_code = org_data.get("subsection_code")
        is_501c3 = subsection_code == 3

        # Get or create account
        account, _ = Account.objects.get_or_create(id=account_id)

        # Normalize EIN to XX-XXXXXXX format
        clean_ein = ein.replace("-", "")
        formatted_ein = f"{clean_ein[:2]}-{clean_ein[2:]}"

        # Build verification data from registry lookup
        verification_data = {
            "ein": formatted_ein,
            "legal_name": org_data.get("name", ""),
            "address": org_data.get("address", ""),
            "city": org_data.get("city", ""),
            "state": org_data.get("state", ""),
            "zip_code": org_data.get("zipcode", ""),
            "subsection_code": subsection_code,
            "ntee_code": org_data.get("ntee_code", ""),
            "ruling_date": org_data.get("ruling_date", ""),
            "status": (
                VerificationStatus.APPROVED
                if is_501c3
                else VerificationStatus.REJECTED
            ),
            "rejection_reason": (
                None
                if is_501c3
                else f"Organization is not a 501(c)(3). Subsection code: {subsection_code}."
            ),
        }

        if existing:
            for key, value in verification_data.items():
                setattr(existing, key, value)
            existing.save()
            verification = existing
        else:
            verification = OrganizationVerification.objects.create(
                account=account, **verification_data
            )

        return Response(
            OrganizationVerificationSerializer(verification).data,
            status=status.HTTP_200_OK,
        )


class OrgVerificationDetailAPI(APIView):
    @extend_schema(
        responses={200: OrganizationVerificationSerializer},
        summary="Get organization verification status",
        description="Retrieve the 501(c)(3) verification status for a given account.",
    )
    def get(self, request, account_id):
        try:
            verification = OrganizationVerification.objects.get(
                account_id=account_id
            )
        except OrganizationVerification.DoesNotExist:
            return Response(
                {"detail": "No verification found for this account."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            OrganizationVerificationSerializer(verification).data,
            status=status.HTTP_200_OK,
        )
