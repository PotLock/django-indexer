import os
from django.conf import settings
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
import json
import requests
from django.core.cache import cache
from django.utils.functional import cached_property

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
    PAGINATED_MPDAO_USER_EXAMPLE,
    PAGINATED_PAYOUT_EXAMPLE,
    PAGINATED_POT_APPLICATION_EXAMPLE,
    PAGINATED_POT_EXAMPLE,
    PAGINATED_POT_FACTORY_EXAMPLE,
    SIMPLE_MPDAO_VOTER_INFO_EXAMPLE,
    SIMPLE_POT_EXAMPLE,
    MpdaoVoterItemSerializer,
    PaginatedMpdaoUsersSerializer,
    PaginatedPotApplicationsResponseSerializer,
    PaginatedPotFactoriesResponseSerializer,
    PaginatedPotPayoutsResponseSerializer,
    PaginatedPotsResponseSerializer,
    PotApplicationSerializer,
    PotFactorySerializer,
    PotPayoutSerializer,
    PotSerializer,
    MpdaoSnapshotSerializer,
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
        pots = Pot.objects.select_related('account', 'pot_factory', 'deployer', 'owner', 'chef').prefetch_related('admins').all()
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
            OpenApiParameter(
                "status",
                str,
                OpenApiParameter.QUERY,
                required=False,
                description="Filter by application status",
            ),
            OpenApiParameter(
                "search",
                str,
                OpenApiParameter.QUERY,
                required=False,
                description="Search by applicant name or account ID",
            ),
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
        
        search_param = request.query_params.get("search")
        if search_param:
            applications = applications.filter(
                Q(applicant__id__icontains=search_param) |
                Q(applicant__near_social_profile_data__name__icontains=search_param)
            )

        # Handle status filter
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

        donations = pot.donations.select_related("donor", "token", 'pot', 'pot__deployer', 'pot__owner', 'pot__chef', 'recipient', 'referrer', 'chef').prefetch_related('pot__admins').all()
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
            OpenApiParameter(
                "search",
                str,
                OpenApiParameter.QUERY,
                required=False,
                description="Search by recipient name or account ID",
            ),
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

        search_param = request.query_params.get("search")
        if search_param:
            payouts = payouts.filter(
                Q(recipient__id__icontains=search_param) |
                Q(recipient__near_social_profile_data__name__icontains=search_param)
            )

        results = self.paginate_queryset(payouts, request, view=self)
        serializer = PotPayoutSerializer(results, many=True)
        return self.get_paginated_response(serializer.data)


class MpdaoVoterMixin:
    @cached_property
    def all_voters(self):
        """Cache the JSON file in memory"""
        json_path = os.path.join(settings.BASE_DIR, 'pots', 'last-snapshot-AllVoters.json')
        with open(json_path, 'r') as file:
            return json.load(file)

    def get_unique_voters(self):
        """Get and cache the unique voters from RPC"""
        cache_key = 'mpdao_unique_voters'
        cached_voters = cache.get(cache_key)
        
        if cached_voters is not None:
            return cached_voters

        url = "https://rpc.web4.near.page/account/mpdao.vote.potlock.near/view/get_unique_voters?election_id.json=1"
        response = requests.get(url)
        
        if response.status_code != 200:
            raise Exception("Error fetching voters from contract")
        
        unique_voters = response.json()
        cache.set(cache_key, unique_voters, 86400)
        return unique_voters

    def get_bulk_account_data(self, voter_ids):
        """Get account data for multiple voters in one query"""
        accounts = {
            account.id: AccountSerializer(account).data 
            for account in Account.objects.select_related().filter(id__in=voter_ids)
        }
        return accounts

    def get_voter_data(self, voter_id):
        """Get voter data from cached JSON"""
        return next(
            (voter for voter in self.all_voters if voter['voter_id'] == voter_id), 
            None
        )


class MpdaoVotersListAPI(MpdaoVoterMixin, APIView):
    DEFAULT_PAGE_SIZE = 30

    @extend_schema(
        parameters=[
            OpenApiParameter("page", int, OpenApiParameter.QUERY, required=False, description="Page number (starts from 1)"),
            OpenApiParameter("page_size", int, OpenApiParameter.QUERY, required=False, description="Number of items per page (default: 30)"),
        ],
        responses={
            200: OpenApiResponse(
                response=PaginatedMpdaoUsersSerializer,
                description="Returns paginated list of all voters for mpdao round",
                examples=[
                    OpenApiExample(
                        "mpdao-list-example",
                        summary="Paginated voters list",
                        description="Example response for mpdao voters list",
                        value=PAGINATED_MPDAO_USER_EXAMPLE,
                    ),
                ],
            ),
            500: OpenApiResponse(description="Error fetching voters"),
        },
    )
    @method_decorator(cache_page(14400))
    def get(self, request: Request, *args, **kwargs):
        try:
            return self.get_all_voters(request.query_params)
        except Exception as e:
            return Response(
                {"message": f"Error processing voter data: {str(e)}"}, 
                status=500
            )

    def get_all_voters(self, query_params):
        """Handle request for all voters with pagination"""
        try:
            unique_voters = self.get_unique_voters()
            
            try:
                page = max(int(query_params.get('page', 1)), 1)
                page_size = min(int(query_params.get('page_size', self.DEFAULT_PAGE_SIZE)), 170)
            except ValueError:
                page = 1
                page_size = self.DEFAULT_PAGE_SIZE

            # Calculate pagination slices
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            
            # Get paginated voters
            paginated_voters = unique_voters[start_idx:end_idx]
            
            # Get all account data for the page in one query
            accounts = self.get_bulk_account_data(paginated_voters)
            
            voters_data = []
            for voter_id in paginated_voters:
                voter_data = self.get_voter_data(voter_id)
                account_data = accounts.get(voter_id)

                voters_data.append({
                    "voter_id": voter_id,
                    "account_data": account_data,
                    "voter_data": MpdaoSnapshotSerializer(voter_data or {"voter_id": voter_id}).data
                })

            base_url = self.request.build_absolute_uri().split('?')[0]
            
            next_url = None
            if end_idx < len(unique_voters):
                next_params = query_params.copy()
                next_params['page'] = page + 1
                next_params['page_size'] = page_size
                next_url = f"{base_url}?{'&'.join(f'{k}={v}' for k, v in next_params.items())}"

            previous_url = None
            if page > 1:
                prev_params = query_params.copy()
                prev_params['page'] = page - 1
                prev_params['page_size'] = page_size
                previous_url = f"{base_url}?{'&'.join(f'{k}={v}' for k, v in prev_params.items())}"

            response_data = {
                "count": len(paginated_voters),
                "next": next_url,
                "previous": previous_url,
                "results": voters_data
            }

            return Response(response_data)

        except Exception as e:
            return Response(
                {"message": f"Error fetching voters: {str(e)}"}, 
                status=500
            )


class MpdaoVoterDetailAPI(MpdaoVoterMixin, APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter("voter_id", str, OpenApiParameter.PATH, required=True, description="account ID of the voter"),
        ],
        responses={
            200: OpenApiResponse(
                response=MpdaoVoterItemSerializer,
                description="Returns details for a specific voter",
                examples=[
                    OpenApiExample(
                        "mpdao-voter-example",
                        summary="Specific voter details",
                        description="Example response for single voter info",
                        value=SIMPLE_MPDAO_VOTER_INFO_EXAMPLE
                    )
                ]
            ),
            404: OpenApiResponse(description="Voter not found"),
            500: OpenApiResponse(description="Error fetching voter data"),
        },
    )
    @method_decorator(cache_page(14400))
    def get(self, request: Request, voter_id: str, *args, **kwargs):
        try:
            voter_data = self.get_voter_data(voter_id)
            
            accounts = self.get_bulk_account_data([voter_id])
            account_data = accounts.get(voter_id)

            response_data = {
                "voter_id": voter_id,
                "account_data": account_data,
                "voter_data": MpdaoSnapshotSerializer(voter_data or {"voter_id": voter_id}).data
            }
            
            return Response(response_data)
        except Exception as e:
            return Response(
                {"message": f"Error processing voter data: {str(e)}"}, 
                status=500
            )
        