import requests
from django.utils import timezone
from django.db.models import Q, F, FloatField
from django.db.models.functions import Cast
from django.conf import settings
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

from api.pagination import pagination_parameters
from api.pagination import CustomSizePageNumberPagination
from base.logging import logger

from .models import Campaign, CampaignDonation
from .serializers import (
    CampaignSerializer,
    CampaignDonationSerializer,
    CampaignContractConfigSerializer,
    PaginatedCampaignsResponseSerializer,
    PaginatedCampaignDonationsResponseSerializer,
    SIMPLE_CAMPAIGN_EXAMPLE,
    SIMPLE_CAMPAIGN_DONATION_EXAMPLE,
    PAGINATED_CAMPAIGNS_EXAMPLE,
    PAGINATED_CAMPAIGN_DONATIONS_EXAMPLE,
)

CAMPAIGN_CONTRACT = "v1.campaign." + settings.POTLOCK_TLA


class CampaignsAPI(APIView, CustomSizePageNumberPagination):
    @extend_schema(
        parameters=[
            *pagination_parameters,
            OpenApiParameter(
                name="owner",
                description="Filter campaigns by owner account ID",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="recipient",
                description="Filter campaigns by recipient account ID",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="token",
                description="Filter campaigns by token account ID",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="status",
                description="Filter by active campaigns (true/false)",
                required=False,
                type=str,
                enum=["active", "upcoming", "ended", "unfufilled"],
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=PaginatedCampaignsResponseSerializer,
                description="Returns paginated list of campaigns",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="Paginated campaigns response",
                        description="Example response for campaigns list",
                        value=PAGINATED_CAMPAIGNS_EXAMPLE,
                        response_only=True,
                    ),
                ],
            ),
        },
    )
    @method_decorator(cache_page(60 * 5))
    def get(self, request: Request, *args, **kwargs):
        """Get paginated list of campaigns with optional filters"""
        queryset = Campaign.objects.select_related('owner', 'recipient', 'token').all()

        # Apply filters
        owner = request.query_params.get('owner')
        if owner:
            queryset = queryset.filter(owner__id=owner)

        recipient = request.query_params.get('recipient')
        if recipient:
            queryset = queryset.filter(recipient__id=recipient)

        token = request.query_params.get('token')
        if token:
            queryset = queryset.filter(token__account__id=token.lower())

        status = request.query_params.get('status')
        if status:
            now = timezone.now()
            status = status.lower()
            queryset = queryset.annotate(
            cast_net_raised=Cast('net_raised_amount', FloatField()),
            cast_max_amount=Cast('max_amount', FloatField()),
            cast_target=Cast('target_amount', FloatField())
        )
            if status == 'upcoming':
                queryset = queryset.filter(start_at__gt=now)
            elif status == 'active':
                queryset = queryset.filter(
                start_at__lte=now
                    ).filter(
                        Q(end_at__isnull=True) | Q(end_at__gt=now)
                    ).filter(
                        Q(max_amount__isnull=True) | Q(cast_net_raised__lt=F('cast_max_amount'))
                    )
            elif status == 'ended':
                queryset = queryset.filter(
                Q(end_at__isnull=False, end_at__lte=now) |
                Q(max_amount__isnull=False, cast_net_raised__gte=F('cast_max_amount'))
            )
            elif status == 'unfufilled':
                queryset = queryset.filter(
                Q(end_at__isnull=False, end_at__lte=now),
                cast_net_raised__lt=F('cast_target')
            )

        # Paginate results
        page = self.paginate_queryset(queryset, request)
        if page is not None:
            serializer = CampaignSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = CampaignSerializer(queryset, many=True)
        return Response(serializer.data)


class CampaignDetailAPI(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="campaign_id",
                description="Campaign ID",
                required=True,
                type=int,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=CampaignSerializer,
                description="Returns campaign details",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="Campaign details",
                        description="Example response for campaign details",
                        value=SIMPLE_CAMPAIGN_EXAMPLE,
                        response_only=True,
                    ),
                ],
            ),
            404: OpenApiResponse(description="Campaign not found"),
        },
    )
    @method_decorator(cache_page(60 * 5))
    def get(self, request: Request, campaign_id: int, *args, **kwargs):
        """Get campaign details by ID"""
        try:
            campaign = Campaign.objects.select_related(
                'owner', 'recipient', 'token'
            ).get(on_chain_id=campaign_id)
            serializer = CampaignSerializer(campaign)
            return Response(serializer.data)
        except Campaign.DoesNotExist:
            return Response({'error': 'Campaign not found'}, status=404)


class CampaignDonationsAPI(APIView, CustomSizePageNumberPagination):
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="campaign_id",
                description="Campaign ID",
                required=True,
                type=int,
                location=OpenApiParameter.PATH,
            ),
            *pagination_parameters,
            OpenApiParameter(
                name="donor",
                description="Filter donations by donor account ID",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="exclude_refunded",
                description="Exclude refunded donations (true/false)",
                required=False,
                type=bool,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=PaginatedCampaignDonationsResponseSerializer,
                description="Returns paginated list of campaign donations",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="Paginated campaign donations response",
                        description="Example response for campaign donations list",
                        value=PAGINATED_CAMPAIGN_DONATIONS_EXAMPLE,
                        response_only=True,
                    ),
                ],
            ),
            404: OpenApiResponse(description="Campaign not found"),
        },
    )
    @method_decorator(cache_page(60 * 2))
    def get(self, request: Request, campaign_id: int, *args, **kwargs):
        """Get paginated list of donations for a specific campaign"""
        try:
            campaign = Campaign.objects.get(on_chain_id=campaign_id)
        except Campaign.DoesNotExist:
            return Response({'error': 'Campaign not found'}, status=404)

        queryset = CampaignDonation.objects.select_related(
            'campaign', 'donor', 'token', 'referrer'
        ).filter(campaign=campaign)

        # Apply filters
        donor = request.query_params.get('donor')
        if donor:
            queryset = queryset.filter(donor__id=donor)

        exclude_refunded = request.query_params.get('exclude_refunded')
        if exclude_refunded and exclude_refunded.lower() == 'true':
            queryset = queryset.filter(returned_at__isnull=True)

        # Paginate results
        page = self.paginate_queryset(queryset, request)
        if page is not None:
            serializer = CampaignDonationSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = CampaignDonationSerializer(queryset, many=True)
        return Response(serializer.data)


class AllCampaignDonationsAPI(APIView, CustomSizePageNumberPagination):
    @extend_schema(
        parameters=[
            *pagination_parameters,
            OpenApiParameter(
                name="donor",
                description="Filter donations by donor account ID",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="campaign_id",
                description="Filter donations by campaign ID",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="exclude_refunded",
                description="Exclude refunded donations (true/false)",
                required=False,
                type=bool,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=PaginatedCampaignDonationsResponseSerializer,
                description="Returns paginated list of all campaign donations",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="Paginated campaign donations response",
                        description="Example response for all campaign donations",
                        value=PAGINATED_CAMPAIGN_DONATIONS_EXAMPLE,
                        response_only=True,
                    ),
                ],
            ),
        },
    )
    @method_decorator(cache_page(60 * 2))
    def get(self, request: Request, *args, **kwargs):
        """Get paginated list of all campaign donations with optional filters"""
        queryset = CampaignDonation.objects.select_related(
            'campaign', 'donor', 'token', 'referrer'
        ).all()

        # Apply filters
        donor = request.query_params.get('donor')
        if donor:
            queryset = queryset.filter(donor__id=donor)

        campaign_id = request.query_params.get('campaign_id')
        if campaign_id:
            queryset = queryset.filter(campaign__on_chain_id=campaign_id)

        exclude_refunded = request.query_params.get('exclude_refunded')
        if exclude_refunded and exclude_refunded.lower() == 'true':
            queryset = queryset.filter(returned_at__isnull=True)

        # Paginate results
        page = self.paginate_queryset(queryset, request)
        if page is not None:
            serializer = CampaignDonationSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = CampaignDonationSerializer(queryset, many=True)
        return Response(serializer.data)


class CampaignContractConfigAPI(APIView):
    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=CampaignContractConfigSerializer,
                description=f"Returns config for {CAMPAIGN_CONTRACT}",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="Campaign contract config",
                        description="Example response for campaign contract config",
                        value={
                            "owner": "potlock.near",
                            "protocol_fee_basis_points": 250,
                            "protocol_fee_recipient_account": "impact.sputnik-dao.near",
                            "default_referral_fee_basis_points": 500,
                            "default_creator_fee_basis_points": 250,
                        },
                        response_only=True,
                    ),
                ],
            ),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    # @method_decorator(cache_page(60 * 5))
    def get(self, request: Request, *args, **kwargs):
        """Get campaign contract configuration"""
        url = f"{settings.FASTNEAR_RPC_URL}/account/{CAMPAIGN_CONTRACT}/view/get_config"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            # Remove fields we don't want to expose in the API
            # fields_to_remove = [
            #     'next_campaign_id',
            #     'next_donation_id',
            #     'total_campaigns_count',
            #     'total_donations_count',
            #     'total_donations_amount',
            #     'net_donations_amount',
            # ]
            # for field in fields_to_remove:
            #     data.pop(field, None)

            return Response(data)
        else:
            logger.error(
                f"Request for {CAMPAIGN_CONTRACT} config failed ({response.status_code}) with message: {response.text}"
            )
            return Response({"message": response.text}, status=response.status_code)
