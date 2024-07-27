from django.db.models import Q
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Account
from accounts.serializers import (
    PAGINATED_ACCOUNT_EXAMPLE,
    AccountSerializer,
    PaginatedAccountsResponseSerializer,
)
from api.pagination import pagination_parameters
from api.pagination import CustomSizePageNumberPagination
from donations.models import Donation
from donations.serializers import (
    PAGINATED_DONATION_EXAMPLE,
    DonationSerializer,
    PaginatedDonationsResponseSerializer,
)

from .models import Pot, PotApplication, PotApplicationStatus, PotFactory
from .serializers import (
    PAGINATED_PAYOUT_EXAMPLE,
    PAGINATED_POT_APPLICATION_EXAMPLE,
    PAGINATED_POT_EXAMPLE,
    PAGINATED_POT_FACTORY_EXAMPLE,
    SIMPLE_POT_EXAMPLE,
    PaginatedPotApplicationsResponseSerializer,
    PaginatedPotFactoriesResponseSerializer,
    PaginatedPotPayoutsResponseSerializer,
    PaginatedPotsResponseSerializer,
    PotApplicationSerializer,
    PotFactorySerializer,
    PotPayoutSerializer,
    PotSerializer,
)


class PotsListAPI(APIView, CustomSizePageNumberPagination):

    @extend_schema(
        parameters=[
            *pagination_parameters,
        ],
        responses={
            200: OpenApiResponse(
                response=PaginatedPotsResponseSerializer,
                description="Returns a paginated list of pots",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="Simple example",
                        description="Example response for pots",
                        value=PAGINATED_POT_EXAMPLE,
                        response_only=True,
                    ),
                ],
            ),
        },
    )
    @method_decorator(cache_page(60 * 5))
    def get(self, request: Request, *args, **kwargs):
        pots = Pot.objects.all()
        results = self.paginate_queryset(pots, request, view=self)
        serializer = PotSerializer(results, many=True)
        return self.get_paginated_response(serializer.data)


class PotFactoriesAPI(APIView, CustomSizePageNumberPagination):

    @extend_schema(
        parameters=[
            *pagination_parameters,
        ],
        responses={
            200: OpenApiResponse(
                response=PaginatedPotFactoriesResponseSerializer,
                description="Returns a paginated list of pot factories",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="Simple example",
                        description="Example response for pot factories",
                        value=PAGINATED_POT_FACTORY_EXAMPLE,
                        response_only=True,
                    ),
                ],
            ),
        },
    )
    @method_decorator(cache_page(60 * 5))
    def get(self, request: Request, *args, **kwargs):
        pot_factories = PotFactory.objects.all()
        results = self.paginate_queryset(pot_factories, request, view=self)
        serializer = PotFactorySerializer(results, many=True)
        return self.get_paginated_response(serializer.data)


class PotDetailAPI(APIView):

    @extend_schema(
        parameters=[
            OpenApiParameter("pot_id", str, OpenApiParameter.PATH),
        ],
        responses={
            200: OpenApiResponse(
                response=PotSerializer,
                description="Returns pot details",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="Simple pot example",
                        description="Example response for pot detail",
                        value=SIMPLE_POT_EXAMPLE,
                        response_only=True,
                    ),
                ],
            ),
            404: OpenApiResponse(description="Pot not found"),
        },
    )
    @method_decorator(cache_page(60 * 5))
    def get(self, request: Request, *args, **kwargs):
        pot_id = kwargs.get("pot_id")
        try:
            pot = Pot.objects.get(account=pot_id)
        except Pot.DoesNotExist:
            return Response({"message": f"Pot with ID {pot_id} not found."}, status=404)
        serializer = PotSerializer(pot)
        return Response(serializer.data)


class PotApplicationsAPI(APIView, CustomSizePageNumberPagination):

    @extend_schema(
        parameters=[
            OpenApiParameter("pot_id", str, OpenApiParameter.PATH),
            *pagination_parameters,
        ],
        responses={
            200: OpenApiResponse(
                response=PaginatedPotApplicationsResponseSerializer,
                description="Returns applications for the pot",
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
            404: OpenApiResponse(description="Pot not found"),
        },
    )
    @method_decorator(cache_page(60 * 5))
    def get(self, request: Request, *args, **kwargs):
        pot_id = kwargs.get("pot_id")
        try:
            pot = Pot.objects.get(account=pot_id)
        except Pot.DoesNotExist:
            return Response({"message": f"Pot with ID {pot_id} not found."}, status=404)

        applications = pot.applications.all()
        results = self.paginate_queryset(applications, request, view=self)
        serializer = PotApplicationSerializer(results, many=True)
        return self.get_paginated_response(serializer.data)


class PotDonationsAPI(APIView, CustomSizePageNumberPagination):

    @extend_schema(
        parameters=[
            OpenApiParameter("pot_id", str, OpenApiParameter.PATH),
            *pagination_parameters,
        ],
        responses={
            200: OpenApiResponse(
                response=PaginatedDonationsResponseSerializer,
                description="Returns donations for the pot",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="Simple example",
                        description="Example response for donations",
                        value=PAGINATED_DONATION_EXAMPLE,
                        response_only=True,
                    ),
                ],
            ),
            404: OpenApiResponse(description="Pot not found"),
        },
    )
    @method_decorator(cache_page(60 * 5))
    def get(self, request: Request, *args, **kwargs):
        pot_id = kwargs.get("pot_id")
        try:
            pot = Pot.objects.get(account=pot_id)
        except Pot.DoesNotExist:
            return Response({"message": f"Pot with ID {pot_id} not found."}, status=404)

        donations = pot.donations.all()
        results = self.paginate_queryset(donations, request, view=self)
        serializer = DonationSerializer(results, many=True)
        return self.get_paginated_response(serializer.data)


class PotSponsorsAPI(APIView, CustomSizePageNumberPagination):

    @extend_schema(
        parameters=[
            OpenApiParameter("pot_id", str, OpenApiParameter.PATH),
            *pagination_parameters,
        ],
        responses={
            200: OpenApiResponse(
                response=PaginatedAccountsResponseSerializer,
                description="Returns sponsors for the pot",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="user.near",
                        description="Example response for sponsors",
                        value=PAGINATED_ACCOUNT_EXAMPLE,
                        response_only=True,
                    ),
                ],
            ),
            404: OpenApiResponse(description="Pot not found"),
        },
    )
    @method_decorator(cache_page(60 * 5))
    def get(self, request: Request, *args, **kwargs):
        pot_id = kwargs.get("pot_id")
        try:
            pot = Pot.objects.get(account=pot_id)
        except Pot.DoesNotExist:
            return Response({"message": f"Pot with ID {pot_id} not found."}, status=404)

        sponsor_ids = (
            Donation.objects.filter(pot=pot, matching_pool=True)
            .values_list("donor", flat=True)
            .distinct()
        )
        sponsors = Account.objects.filter(id__in=sponsor_ids)
        results = self.paginate_queryset(sponsors, request, view=self)
        serializer = AccountSerializer(results, many=True)
        return self.get_paginated_response(serializer.data)


class PotPayoutsAPI(APIView, CustomSizePageNumberPagination):

    @extend_schema(
        parameters=[
            OpenApiParameter("pot_id", str, OpenApiParameter.PATH),
            *pagination_parameters,
        ],
        responses={
            200: OpenApiResponse(
                response=PaginatedPotPayoutsResponseSerializer,
                description="Returns payouts for the pot",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="Simple example",
                        description="Example response for payouts",
                        value=PAGINATED_PAYOUT_EXAMPLE,
                        response_only=True,
                    ),
                ],
            ),
            404: OpenApiResponse(description="Pot not found"),
        },
    )
    @method_decorator(cache_page(60 * 5))
    def get(self, request: Request, *args, **kwargs):
        pot_id = kwargs.get("pot_id")
        try:
            pot = Pot.objects.get(account=pot_id)
        except Pot.DoesNotExist:
            return Response({"message": f"Pot with ID {pot_id} not found."}, status=404)

        payouts = pot.payouts.all()
        results = self.paginate_queryset(payouts, request, view=self)
        serializer = PotPayoutSerializer(results, many=True)
        return self.get_paginated_response(serializer.data)
