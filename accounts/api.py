from django.db.models import Exists, OuterRef
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
)
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from base.logging import logger
from donations.models import Donation
from donations.serializers import (
    PAGINATED_DONATION_EXAMPLE,
    DonationSerializer,
    PaginatedDonationsResponseSerializer,
)
from pots.models import Pot, PotApplication, PotApplicationStatus, PotPayout
from pots.serializers import (
    PAGINATED_PAYOUT_EXAMPLE,
    PAGINATED_POT_APPLICATION_EXAMPLE,
    PAGINATED_POT_EXAMPLE,
    PaginatedPotApplicationsResponseSerializer,
    PaginatedPotPayoutsResponseSerializer,
    PaginatedPotsResponseSerializer,
    PotApplicationSerializer,
    PotPayoutSerializer,
    PotSerializer,
)

from .models import Account
from .serializers import (
    PAGINATED_ACCOUNT_EXAMPLE,
    SIMPLE_ACCOUNT_EXAMPLE,
    AccountSerializer,
    PaginatedAccountsResponseSerializer,
)
from api.pagination import ResultPagination


class DonorsAPI(APIView, PageNumberPagination):

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="sort",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Sort by field, e.g., most_donated_usd",
            )
        ],
        responses={
            200: OpenApiResponse(
                response=PaginatedAccountsResponseSerializer,
                description="Returns a paginated list of donor accounts",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="user.near",
                        description="Example response for donor accounts",
                        value=PAGINATED_ACCOUNT_EXAMPLE,
                        response_only=True,
                    ),
                ],
            ),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    @method_decorator(cache_page(60 * 5))
    def get(self, request: Request, *args, **kwargs):
        # Return all donors
        donations_subquery = Donation.objects.filter(donor_id=OuterRef("pk"))
        donor_accounts = Account.objects.filter(Exists(donations_subquery))
        sort = request.query_params.get("sort", None)
        if sort == "most_donated_usd":
            donor_accounts = donor_accounts.order_by(
                "-total_donations_out_usd"
            )  # TODO: this field name might be changing
        # TODO: add more sort options
        results = self.paginate_queryset(donor_accounts, request, view=self)
        serializer = AccountSerializer(results, many=True)
        return self.get_paginated_response(serializer.data)


class AccountsListAPI(APIView, ResultPagination):

    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=PaginatedAccountsResponseSerializer,
                description="Returns a paginated list of accounts",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="Simple example",
                        description="Example response for accounts data",
                        value=PAGINATED_ACCOUNT_EXAMPLE,
                        response_only=True,
                    ),
                ],
            ),
            500: OpenApiResponse(description="Internal server error"),
        }
    )
    @method_decorator(cache_page(60 * 5))
    def get(self, request: Request, *args, **kwargs):
        accounts = Account.objects.all()
        results = self.paginate_queryset(accounts, request, view=self)
        serializer = AccountSerializer(results, many=True)
        return self.get_paginated_response(serializer.data)


class AccountDetailAPI(APIView):

    @extend_schema(
        parameters=[
            OpenApiParameter("account_id", str, OpenApiParameter.PATH),
        ],
        responses={
            200: OpenApiResponse(
                response=AccountSerializer,
                description="Returns account details",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="user.near",
                        description="Example response for account detail",
                        value=SIMPLE_ACCOUNT_EXAMPLE,
                        response_only=True,
                    ),
                ],
            ),
            404: OpenApiResponse(description="Account not found"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    @method_decorator(cache_page(60 * 5))
    def get(self, request: Request, *args, **kwargs):
        account_id = kwargs.get("account_id")
        try:
            account = Account.objects.get(id=account_id)
        except Account.DoesNotExist:
            return Response(
                {"message": f"Account with ID {account_id} not found."}, status=404
            )
        serializer = AccountSerializer(account)
        return Response(serializer.data)


class AccountActivePotsAPI(APIView, PageNumberPagination):

    @extend_schema(
        parameters=[
            OpenApiParameter("account_id", str, OpenApiParameter.PATH),
            OpenApiParameter(
                "status",
                str,
                OpenApiParameter.QUERY,
                required=False,
                description="Filter by pot status",
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=PaginatedPotsResponseSerializer,
                description="Returns paginated active pots for the account",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="Simple example",
                        description="Example response for active pots",
                        value=PAGINATED_POT_EXAMPLE,
                        response_only=True,
                    ),
                ],
            ),
            404: OpenApiResponse(description="Account not found"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    @method_decorator(cache_page(60 * 5))
    def get(self, request: Request, *args, **kwargs):
        account_id = kwargs.get("account_id")
        try:
            account = Account.objects.get(id=account_id)
        except Account.DoesNotExist:
            return Response(
                {"message": f"Account with ID {account_id} not found."}, status=404
            )

        now = timezone.now()
        applications = PotApplication.objects.filter(
            applicant=account, status=PotApplicationStatus.APPROVED
        )
        pot_ids = applications.values_list("pot_id", flat=True)
        pots = Pot.objects.filter(id__in=pot_ids)
        if request.query_params.get("status") == "live":
            pots = pots.filter(
                matching_round_start__lte=now, matching_round_end__gte=now
            )
        results = self.paginate_queryset(pots, request, view=self)
        serializer = PotSerializer(results, many=True)
        return self.get_paginated_response(serializer.data)


class AccountPotApplicationsAPI(APIView, PageNumberPagination):

    @extend_schema(
        parameters=[
            OpenApiParameter("account_id", str, OpenApiParameter.PATH),
            OpenApiParameter(
                "status",
                str,
                OpenApiParameter.QUERY,
                description="Filter pot applications by status",
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=PaginatedPotApplicationsResponseSerializer,
                description="Returns paginated pot applications for the account",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="Simple example",
                        description="Example response for pot applications",
                        value=PAGINATED_POT_APPLICATION_EXAMPLE,
                        response_only=True,
                    ),
                ],
            ),
            400: OpenApiResponse(description="Invalid status value"),
            404: OpenApiResponse(description="Account not found"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    @method_decorator(cache_page(60 * 5))
    def get(self, request: Request, *args, **kwargs):
        account_id = kwargs.get("account_id")
        try:
            account = Account.objects.get(id=account_id)
        except Account.DoesNotExist:
            return Response(
                {"message": f"Account with ID {account_id} not found."}, status=404
            )

        applications = PotApplication.objects.filter(applicant=account)
        status_param = request.query_params.get("status")
        if status_param:
            if status_param not in PotApplicationStatus.values:
                return Response(
                    {"message": f"Invalid status value: {status_param}"}, status=400
                )
            applications = applications.filter(status=status_param)
        results = self.paginate_queryset(applications, request, view=self)
        serializer = PotApplicationSerializer(results, many=True)
        return self.get_paginated_response(serializer.data)


class AccountDonationsReceivedAPI(APIView, PageNumberPagination):

    @extend_schema(
        parameters=[
            OpenApiParameter("account_id", str, OpenApiParameter.PATH),
        ],
        responses={
            200: OpenApiResponse(
                response=PaginatedDonationsResponseSerializer,
                description="Returns paginated donations received by the account",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="Simple example",
                        description="Example response for donations received",
                        value=PAGINATED_DONATION_EXAMPLE,
                        response_only=True,
                    ),
                ],
            ),
            404: OpenApiResponse(description="Account not found"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    @method_decorator(cache_page(60 * 5))
    def get(self, request: Request, *args, **kwargs):
        account_id = kwargs.get("account_id")
        try:
            account = Account.objects.get(id=account_id)
        except Account.DoesNotExist:
            return Response(
                {"message": f"Account with ID {account_id} not found."}, status=404
            )

        donations = Donation.objects.filter(recipient=account)
        results = self.paginate_queryset(donations, request, view=self)
        serializer = DonationSerializer(results, many=True)
        return self.get_paginated_response(serializer.data)


class AccountDonationsSentAPI(APIView, PageNumberPagination):

    @extend_schema(
        parameters=[
            OpenApiParameter("account_id", str, OpenApiParameter.PATH),
        ],
        responses={
            200: OpenApiResponse(
                response=PaginatedDonationsResponseSerializer,
                description="Returns paginated donations sent by the account",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="Simple example",
                        description="Example response for donations received",
                        value=PAGINATED_DONATION_EXAMPLE,
                        response_only=True,
                    ),
                ],
            ),
            404: OpenApiResponse(description="Account not found"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    @method_decorator(cache_page(60 * 5))
    def get(self, request: Request, *args, **kwargs):
        account_id = kwargs.get("account_id")
        try:
            account = Account.objects.get(id=account_id)
        except Account.DoesNotExist:
            return Response(
                {"message": f"Account with ID {account_id} not found."}, status=404
            )

        donations = Donation.objects.filter(donor=account)
        results = self.paginate_queryset(donations, request, view=self)
        serializer = DonationSerializer(results, many=True)
        return self.get_paginated_response(serializer.data)


class AccountPayoutsReceivedAPI(APIView, PageNumberPagination):

    @extend_schema(
        parameters=[
            OpenApiParameter("account_id", str, OpenApiParameter.PATH),
        ],
        responses={
            200: OpenApiResponse(
                response=PaginatedPotPayoutsResponseSerializer,
                description="Returns paginated payouts received by the account",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="Simple example",
                        description="Example response for payouts received",
                        value=PAGINATED_PAYOUT_EXAMPLE,
                        response_only=True,
                    ),
                ],
            ),
            404: OpenApiResponse(description="Account not found"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    @method_decorator(cache_page(60 * 5))
    def get(self, request: Request, *args, **kwargs):
        account_id = kwargs.get("account_id")
        try:
            account = Account.objects.get(id=account_id)
        except Account.DoesNotExist:
            return Response(
                {"message": f"Account with ID {account_id} not found."}, status=404
            )

        payouts = PotPayout.objects.filter(recipient=account, paid_at__isnull=False)
        results = self.paginate_queryset(payouts, request, view=self)
        serializer = PotPayoutSerializer(results, many=True)
        return self.get_paginated_response(serializer.data)
