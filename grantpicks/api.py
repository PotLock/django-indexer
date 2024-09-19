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

from .models import Project, Round
from .serializers import (
    PAGINATED_PROJECT_EXAMPLE,
    PAGINATED_ROUND_APPLICATION_EXAMPLE,
    PAGINATED_ROUND_EXAMPLE,
    PAGINATED_VOTE_PAIR_EXAMPLE,
    SIMPLE_ROUND_EXAMPLE,
    PaginatedProjectsResponseSerializer,
    PaginatedRoundApplicationsResponseSerializer,
    PaginatedRoundsResponseSerializer,
    PaginatedVotePairResponseSerializer,
    ProjectSerializer,
    RoundApplicationSerializer,
    RoundSerializer,
    VotePairSerializer,
    VoteSerializer,
)


class RoundsListAPI(APIView, CustomSizePageNumberPagination):

    @extend_schema(
        parameters=[
            *pagination_parameters,
        ],
        responses={
            200: OpenApiResponse(
                response=PaginatedRoundsResponseSerializer,
                description="Returns a paginated list of rounds",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="Simple example",
                        description="Example response for rounds",
                        value=PAGINATED_ROUND_EXAMPLE,
                        response_only=True,
                    ),
                ],
            ),
        },
    )
    @method_decorator(cache_page(60 * 1))
    def get(self, request: Request, *args, **kwargs):
        rounds = Round.objects.all()
        results = self.paginate_queryset(rounds, request, view=self)
        serializer = RoundSerializer(results, many=True)
        return self.get_paginated_response(serializer.data)

class RoundDetailAPI(APIView):

    @extend_schema(
        parameters=[
            OpenApiParameter("round_id", str, OpenApiParameter.PATH),
        ],
        responses={
            200: OpenApiResponse(
                response=RoundSerializer,
                description="Returns rounds details",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="Simple round example",
                        description="Example response for round detail",
                        value=SIMPLE_ROUND_EXAMPLE,
                        response_only=True,
                    ),
                ],
            ),
            404: OpenApiResponse(description="Round not found"),
        },
    )
    @method_decorator(cache_page(60 * 1))
    def get(self, request: Request, *args, **kwargs):
        round_id = kwargs.get("round_id")
        try:
            round = Round.objects.get(id=round_id)
        except Round.DoesNotExist:
            return Response({"message": f"Round with ID {round_id} not found."}, status=404)
        serializer = RoundSerializer(round)
        return Response(serializer.data)


class RoundApplicationsAPI(APIView, CustomSizePageNumberPagination):

    @extend_schema(
        parameters=[
            OpenApiParameter("round_id", str, OpenApiParameter.PATH),
            *pagination_parameters,
        ],
        responses={
            200: OpenApiResponse(
                response=PaginatedRoundApplicationsResponseSerializer,
                description="Returns applications for the round",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="Simple example",
                        description="Example response for round applications",
                        value=PAGINATED_ROUND_APPLICATION_EXAMPLE,
                        response_only=True,
                    ),
                ],
            ),
            404: OpenApiResponse(description="Round not found"),
        },
    )
    @method_decorator(cache_page(60 * 1))
    def get(self, request: Request, *args, **kwargs):
        round_id = kwargs.get("round_id")
        try:
            round = Round.objects.get(id=round_id)
        except Round.DoesNotExist:
            return Response({"message": f"Round with ID {round_id} not found."}, status=404)

        applications = round.applications.all()
        results = self.paginate_queryset(applications, request, view=self)
        serializer = RoundApplicationSerializer(results, many=True)
        return self.get_paginated_response(serializer.data)


class ProjectRoundVotesAPI(APIView, CustomSizePageNumberPagination):

    @extend_schema(
        parameters=[
            OpenApiParameter("round_id", str, OpenApiParameter.PATH),
            OpenApiParameter("project_id", str, OpenApiParameter.PATH),  # Added project_id parameter
            *pagination_parameters,
        ],
        responses={
            200: OpenApiResponse(
                response=PaginatedVotePairResponseSerializer,  # Update to use the appropriate serializer
                description="Returns votes for a project in the round",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="Simple example",
                        description="Example response for votes",
                        value=PAGINATED_VOTE_PAIR_EXAMPLE,  # Update to use the appropriate example
                        response_only=True,
                    ),
                ],
            ),
            404: OpenApiResponse(description="Round or project not found"),
        },
    )
    @method_decorator(cache_page(60 * 1))
    def get(self, request: Request, *args, **kwargs):
        round_id = kwargs.get("round_id")
        project_id = kwargs.get("project_id")  # Get project_id from kwargs
        try:
            round_obj = Round.objects.get(id=round_id)
            # project = Project.objects.get(id=project_id) # comment out now, might use later if decide to return vote pairs instead
        except Round.DoesNotExist:
            return Response({"message": f"Round with ID {round_id} not found."}, status=404)

        # Retrieve votes for the specified project in the round

        votes = round_obj.votes.filter(pairs__project_id=project_id)  # Adjust the filter as needed
        # vote_pairs = project.vote_pairs.all()
        results = self.paginate_queryset(votes, request, view=self)
        serializer = VoteSerializer(results, many=True)  # Use the appropriate serializer for votes
        return self.get_paginated_response(serializer.data)




class ProjectListAPI(APIView, CustomSizePageNumberPagination):

    @extend_schema(
        parameters=[
            *pagination_parameters,
        ],
        responses={
            200: OpenApiResponse(
                response=PaginatedProjectsResponseSerializer,
                description="Returns a paginated list of projects",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="Simple example",
                        description="Example response for projects",
                        value=PAGINATED_PROJECT_EXAMPLE,
                        response_only=True,
                    ),
                ],
            ),
        },
    )
    @method_decorator(cache_page(60 * 5))
    def get(self, request: Request, *args, **kwargs):
        projects = Project.objects.all()
        results = self.paginate_queryset(projects, request, view=self)
        serializer = ProjectSerializer(results, many=True)
        return self.get_paginated_response(serializer.data)