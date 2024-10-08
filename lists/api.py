import random

from django.db.models import Exists, OuterRef
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
from api.pagination import pagination_parameters
from api.pagination import CustomSizePageNumberPagination

from .models import List, ListRegistrationStatus
from .serializers import (
    PAGINATED_LIST_EXAMPLE,
    PAGINATED_LIST_REGISTRATION_EXAMPLE,
    SIMPLE_LIST_EXAMPLE,
    SIMPLE_LIST_REGISTRATION_EXAMPLE,
    ListRegistrationSerializer,
    ListSerializer,
    PaginatedListRegistrationsResponseSerializer,
    PaginatedListsResponseSerializer,
)


class ListsListAPI(APIView, CustomSizePageNumberPagination):

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "account",
                str,
                OpenApiParameter.QUERY,
                description="Filter lists by account",
            ),
            *pagination_parameters,
        ],
        responses={
            200: OpenApiResponse(
                response=PaginatedListsResponseSerializer,
                description="Returns a paginated list of lists",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="Simple example",
                        description="Example response for lists",
                        value=PAGINATED_LIST_EXAMPLE,
                        response_only=True,
                    ),
                ],
            ),
            404: OpenApiResponse(description="Account not found"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    @method_decorator(cache_page(60 * 1))
    def get(self, request: Request, *args, **kwargs):
        lists = List.objects.all()
        account_id = request.query_params.get("account")
        if account_id:
            try:
                account = Account.objects.get(id=account_id)
                lists = lists.filter(owner=account)
            except Account.DoesNotExist:
                return Response(
                    {"message": f"Account with ID {account_id} not found."}, status=404
                )
        results = self.paginate_queryset(lists, request, view=self)
        serializer = ListSerializer(results, many=True)
        return self.get_paginated_response(serializer.data)


class ListDetailAPI(APIView):

    @extend_schema(
        parameters=[
            OpenApiParameter("list_id", int, OpenApiParameter.PATH),
        ],
        responses={
            200: OpenApiResponse(
                response=ListSerializer,
                description="Returns list details",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="Simple list example",
                        description="Example response for list detail",
                        value=SIMPLE_LIST_EXAMPLE,
                        response_only=True,
                    ),
                ],
            ),
            404: OpenApiResponse(description="List not found"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    @method_decorator(cache_page(60 * 5))
    def get(self, request: Request, *args, **kwargs):
        list_id = kwargs.get("list_id")
        try:
            list_obj = List.objects.get(on_chain_id=list_id)
        except List.DoesNotExist:
            return Response(
                {"message": f"List with onchain ID {list_id} not found."}, status=404
            )
        serializer = ListSerializer(list_obj)
        return Response(serializer.data)


class ListRegistrationsAPI(APIView, CustomSizePageNumberPagination):

    @extend_schema(
        parameters=[
            OpenApiParameter("list_id", int, OpenApiParameter.PATH),
            OpenApiParameter(
                "status",
                str,
                OpenApiParameter.QUERY,
                description="Filter registrations by status",
            ),
            OpenApiParameter(
                "category",
                str,
                OpenApiParameter.QUERY,
                description="Filter registrations by category",
            ),
            *pagination_parameters,
        ],
        responses={
            200: OpenApiResponse(
                response=PaginatedListRegistrationsResponseSerializer,
                description="Returns registrations for the list",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="Simple registration example",
                        description="Example response for list registrations",
                        value=PAGINATED_LIST_REGISTRATION_EXAMPLE,
                        response_only=True,
                    ),
                ],
            ),
            404: OpenApiResponse(description="List not found"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    @method_decorator(cache_page(60 * 1))
    def get(self, request: Request, *args, **kwargs):
        list_id = kwargs.get("list_id")
        try:
            list_obj = List.objects.prefetch_related('registrations').get(on_chain_id=list_id)
        except List.DoesNotExist:
            return Response(
                {"message": f"List with on chain ID {list_id} not found."}, status=404
            )

        registrations = list_obj.registrations.select_related().all()
        status_param = request.query_params.get("status")
        category_param = request.query_params.get("category")
        if status_param:
            if status_param not in ListRegistrationStatus.values:
                return Response(
                    {"message": f"Invalid status value: {status_param}"}, status=400
                )
            registrations = registrations.filter(status=status_param)
        if category_param:
            category_regex_pattern = rf'\[.*?"{category_param}".*?\]'
            registrations = registrations.filter(
                registrant__near_social_profile_data__plCategories__iregex=category_regex_pattern
            )
        results = self.paginate_queryset(registrations, request, view=self)
        serializer = ListRegistrationSerializer(results, many=True)
        return self.get_paginated_response(serializer.data)


class ListRandomRegistrationAPI(APIView):

    @extend_schema(
        parameters=[
            OpenApiParameter("list_id", int, OpenApiParameter.PATH),
            OpenApiParameter(
                "status",
                str,
                OpenApiParameter.QUERY,
                description="Filter registrations by status",
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=ListRegistrationSerializer,
                description="Returns a random registration for the list",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="Simple registration example",
                        description="Example response for list registration",
                        value=SIMPLE_LIST_REGISTRATION_EXAMPLE,
                        response_only=True,
                    ),
                ],
            ),
            404: OpenApiResponse(description="List not found"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def get(self, request: Request, *args, **kwargs):
        list_id = kwargs.get("list_id")
        try:
            list_obj = List.objects.get(on_chain_id=list_id)
        except List.DoesNotExist:
            return Response(
                {"message": f"List on chain ID {list_id} not found."}, status=404
            )

        registrations = list_obj.registrations.all()
        status_param = request.query_params.get("status")
        if status_param:
            if status_param not in ListRegistrationStatus.values:
                return Response(
                    {"message": f"Invalid status value: {status_param}"}, status=400
                )
            registrations = registrations.filter(status=status_param)

        # Get a random registration
        registrations_list = list(registrations)
        if not registrations_list:
            return Response(
                {"message": "No registrations found for the given criteria."},
                status=404,
            )

        registration = random.choice(registrations_list)
        serializer = ListRegistrationSerializer(registration)
        return Response(serializer.data)
