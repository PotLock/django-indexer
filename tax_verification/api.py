import logging

import requests
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

PROPUBLICA_API_URL = "https://projects.propublica.org/nonprofits/api/v2/organizations"


def verify_ein_with_propublica(ein: str) -> dict:
    """
    Look up an EIN against the ProPublica Nonprofit Explorer API.
    Returns dict with org data if found, or error info.
    """
    # Strip dash for API lookup (ProPublica expects plain digits)
    ein_digits = ein.replace("-", "")

    try:
        response = requests.get(
            f"{PROPUBLICA_API_URL}/{ein_digits}.json",
            timeout=15,
        )

        if response.status_code == 200:
            data = response.json()
            org = data.get("organization", {})

            if not org or org.get("name") in (None, "", "Unknown Organization"):
                return {"found": False, "reason": "EIN not found in IRS records"}

            return {
                "found": True,
                "name": org.get("name", ""),
                "address": org.get("address", ""),
                "city": org.get("city", ""),
                "state": org.get("state", ""),
                "zip_code": org.get("zipcode", ""),
                "subsection_code": org.get("subsection_code"),
                "ntee_code": org.get("ntee_code", ""),
                "ruling_date": org.get("ruling_date", ""),
            }
        elif response.status_code == 404:
            return {"found": False, "reason": "EIN not found in IRS records"}
        else:
            logger.error(
                f"ProPublica API returned status {response.status_code} for EIN {ein_digits}"
            )
            return {
                "found": False,
                "reason": "Unable to verify EIN at this time. Please try again later.",
            }

    except requests.Timeout:
        logger.error(f"ProPublica API timeout for EIN {ein_digits}")
        return {
            "found": False,
            "reason": "Verification service timed out. Please try again later.",
        }
    except requests.RequestException as e:
        logger.error(f"ProPublica API error for EIN {ein_digits}: {e}")
        return {
            "found": False,
            "reason": "Unable to verify EIN at this time. Please try again later.",
        }


class OrgVerificationSubmitAPI(APIView):
    """
    Submit a 501(c)(3) verification request.

    The EIN is verified against IRS records via ProPublica Nonprofit Explorer.
    If the organization is found and has subsection_code 3 (501(c)(3)),
    it is automatically approved. Otherwise it is rejected.
    """

    @extend_schema(
        summary="Submit 501(c)(3) verification",
        description=(
            "Submit an EIN for 501(c)(3) verification. The EIN is looked up against "
            "IRS records. If found as a valid 501(c)(3), the verification is auto-approved "
            "and IRS data (name, address, etc.) is stored. If not found or not a 501(c)(3), "
            "the request is rejected with a reason."
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
        account_id = data["account_id"]
        ein = data["ein"]

        # Get or create the account
        account, _ = Account.objects.get_or_create(
            id=account_id, defaults={"chain_id": 1}
        )

        # Check if already approved
        try:
            existing = OrganizationVerification.objects.get(account=account)
            if existing.status == VerificationStatus.APPROVED:
                return Response(
                    OrganizationVerificationSerializer(existing).data, status=200
                )
        except OrganizationVerification.DoesNotExist:
            existing = None

        # Verify EIN against ProPublica / IRS data
        result = verify_ein_with_propublica(ein)

        if result["found"]:
            subsection_code = result.get("subsection_code")

            if subsection_code == 3:
                # Valid 501(c)(3) — auto-approve
                verification_data = {
                    "ein": ein,
                    "legal_name": result["name"],
                    "address": result.get("address", ""),
                    "city": result.get("city", ""),
                    "state": result.get("state", ""),
                    "zip_code": result.get("zip_code", ""),
                    "subsection_code": subsection_code,
                    "ntee_code": result.get("ntee_code", ""),
                    "ruling_date": result.get("ruling_date", ""),
                    "status": VerificationStatus.APPROVED,
                    "rejection_reason": None,
                }
            else:
                # Found but not a 501(c)(3)
                verification_data = {
                    "ein": ein,
                    "legal_name": result["name"],
                    "address": result.get("address", ""),
                    "city": result.get("city", ""),
                    "state": result.get("state", ""),
                    "zip_code": result.get("zip_code", ""),
                    "subsection_code": subsection_code,
                    "ntee_code": result.get("ntee_code", ""),
                    "ruling_date": result.get("ruling_date", ""),
                    "status": VerificationStatus.REJECTED,
                    "rejection_reason": f"Organization is not a 501(c)(3). IRS subsection code: {subsection_code}",
                }
        else:
            # Not found in IRS records
            verification_data = {
                "ein": ein,
                "legal_name": "",
                "status": VerificationStatus.REJECTED,
                "rejection_reason": result["reason"],
            }

        if existing:
            # Update existing record
            for field, value in verification_data.items():
                setattr(existing, field, value)
            existing.save()
            return Response(
                OrganizationVerificationSerializer(existing).data, status=200
            )
        else:
            # Create new record
            verification = OrganizationVerification.objects.create(
                account=account, **verification_data
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
