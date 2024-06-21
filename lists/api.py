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
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import List
from .serializers import (
    PAGINATED_LIST_EXAMPLE,
    PAGINATED_LIST_REGISTRATION_EXAMPLE,
    SIMPLE_LIST_EXAMPLE,
    ListRegistrationSerializer,
    ListSerializer,
    PaginatedListRegistrationsResponseSerializer,
    PaginatedListsResponseSerializer,
)


class ListsListAPI(APIView, LimitOffsetPagination):

    @extend_schema(
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
            500: OpenApiResponse(description="Internal server error"),
        }
    )
    @method_decorator(cache_page(60 * 5))
    def get(self, request: Request, *args, **kwargs):
        lists = List.objects.all()
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
            list_obj = List.objects.get(id=list_id)
        except List.DoesNotExist:
            return Response(
                {"message": f"List with ID {list_id} not found."}, status=404
            )
        serializer = ListSerializer(list_obj)
        return Response(serializer.data)


class ListRegistrationsAPI(APIView, LimitOffsetPagination):

    @extend_schema(
        parameters=[
            OpenApiParameter("list_id", int, OpenApiParameter.PATH),
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
    @method_decorator(cache_page(60 * 5))
    def get(self, request: Request, *args, **kwargs):
        list_id = kwargs.get("list_id")
        try:
            list_obj = List.objects.get(id=list_id)
        except List.DoesNotExist:
            return Response(
                {"message": f"List with ID {list_id} not found."}, status=404
            )

        registrations = list_obj.registrations.all()
        results = self.paginate_queryset(registrations, request, view=self)
        serializer = ListRegistrationSerializer(results, many=True)
        return self.get_paginated_response(serializer.data)
