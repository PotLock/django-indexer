import logging
import re

import requests
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Account

from .models import OrganizationVerification, VerificationStatus
from .serializers import (
    OrganizationVerificationSerializer,
    OrgVerificationSubmitSerializer,
)

logger = logging.getLogger(__name__)

PROPUBLICA_API_URL = (
    "https://projects.propublica.org/nonprofits/api/v2/organizations/{ein}.json"
)


def verify_ein_with_propublica(ein: str) -> dict:
    """
    Call ProPublica Nonprofit Explorer API to verify an EIN.
    Returns dict with org data if found, or raises ValueError if not found / not 501(c)(3).
    """
    # Strip dashes for the API call
    clean_ein = ein.replace("-", "")
    url = PROPUBLICA_API_URL.format(ein=clean_ein)

    response = requests.get(url, timeout=15)
    if response.status_code != 200:
        raise ValueError("Could not verify EIN with IRS database.")

    data = response.json()
    org = data.get("organization", {})

    # ProPublica returns "Unknown Organization" for non-existent EINs
    if not org or org.get("name", "").strip() == "Unknown Organization":
        raise ValueError(
            f"EIN {ein} was not found in IRS records. "
            "Please check the number and try again."
        )

    return org


class OrgVerificationSubmitAPI(APIView):
    @extend_schema(
        request=OrgVerificationSubmitSerializer,
        responses={200: OrganizationVerificationSerializer},
        summary="Submit 501(c)(3) verification",
        description=(
            "Submit an EIN for automated 501(c)(3) verification against IRS records "
            "via ProPublica. Auto-approves if subsection_code is 3 (501(c)(3)), "
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

        # Verify with ProPublica
        try:
            org_data = verify_ein_with_propublica(ein)
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
        except requests.RequestException:
            logger.exception("ProPublica API request failed")
            return Response(
                {"detail": "IRS verification service is temporarily unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Determine approval based on subsection code
        subsection_code = org_data.get("subsection_code")
        is_501c3 = subsection_code == 3

        # Get or create account
        account, _ = Account.objects.get_or_create(id=account_id)

        # Normalize EIN to XX-XXXXXXX format
        clean_ein = ein.replace("-", "")
        formatted_ein = f"{clean_ein[:2]}-{clean_ein[2:]}"

        # Build verification data from ProPublica response
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
