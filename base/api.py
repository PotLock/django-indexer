from datetime import timedelta

from django.db.models import Sum
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
)
from django.conf import settings
from asgiref.sync import async_to_sync
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from accounts.models import Account
from campaigns.models import Campaign
from donations.models import Donation
from pots.models import PotPayout


class StatsResponseSerializer(serializers.Serializer):
    total_donations_usd = serializers.FloatField()
    total_payouts_usd = serializers.FloatField()
    total_donations_count = serializers.IntegerField()
    total_donors_count = serializers.IntegerField()
    total_recipients_count = serializers.IntegerField()

class ReclaimProofRequestConfigSerializer(serializers.Serializer):
    reclaimProofRequestConfig = serializers.CharField()

class StatsAPI(APIView):
    def dispatch(self, request, *args, **kwargs):
        return super(StatsAPI, self).dispatch(request, *args, **kwargs)

    @method_decorator(
        cache_page(60 * 5)
    )  # Cache for 5 mins (using page-level caching for now for simplicity, but can move to data-level caching if desired)
    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=StatsResponseSerializer,
                description="Returns statistics data",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="Simple example",
                        description="Example response for statistics data",
                        value={
                            "total_donations_usd": 12345.67,
                            "total_payouts_usd": 8901.23,
                            "total_donations_count": 456,
                            "total_donors_count": 789,
                            "total_recipients_count": 321,
                        },
                        response_only=True,
                    ),
                ],
            ),
            500: OpenApiResponse(description="Internal server error"),
        }
    )
    def get(self, request: Request, *args, **kwargs):
        total_donations_usd = (
            Donation.objects.all().aggregate(Sum("total_amount_usd"))[
                "total_amount_usd__sum"
            ]
            or 0
        )
        total_payouts_usd = (
            PotPayout.objects.filter(paid_at__isnull=False).aggregate(
                Sum("amount_paid_usd")
            )["amount_paid_usd__sum"]
            or 0
        )
        total_donations_count = Donation.objects.count()
        total_donors_count = (
            Account.objects.filter(donations__isnull=False).distinct().count()
        )
        total_recipients_count = (
            Account.objects.filter(received_donations__isnull=False).distinct().count()
        )

        return Response(
            {
                "total_donations_usd": total_donations_usd,
                "total_payouts_usd": total_payouts_usd,
                "total_donations_count": total_donations_count,
                "total_donors_count": total_donors_count,
                "total_recipients_count": total_recipients_count,
            }
        )


def _campaign_window_stats(window_filter=None):
    qs = Campaign.objects.all() if window_filter is None else Campaign.objects.filter(**window_filter)
    return {
        "count": qs.count(),
        "raised_usd": float(qs.aggregate(s=Sum("total_raised_amount_usd"))["s"] or 0),
    }


def _build_campaign_stats():
    """Campaign aggregates for today / last 7 days / all-time.

    Windows are based on `Campaign.created_at`; `raised_usd` sums each campaign's
    `total_raised_amount_usd`. Consumed by the prod deployment's daily Signal
    message (prod has no campaigns app, so it pulls this over HTTP)."""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    seven_days_ago = now - timedelta(days=7)
    return {
        "today": _campaign_window_stats({"created_at__gte": today_start}),
        "last_7_days": _campaign_window_stats({"created_at__gte": seven_days_ago}),
        "all_time": _campaign_window_stats(),
    }


class CampaignStatsAPI(APIView):
    """Campaign aggregates (count + raised USD) for today / last 7 days / all-time.

    Used by the prod deployment to merge campaign data into its daily stats
    message, since the campaigns app only lives on this (dev) deployment."""

    @method_decorator(cache_page(60 * 5))
    @extend_schema(
        responses={
            200: OpenApiResponse(description="Campaign stats per window"),
            500: OpenApiResponse(description="Internal server error"),
        }
    )
    def get(self, request: Request, *args, **kwargs):
        return Response(_build_campaign_stats())


class ReclaimProofRequestView(APIView):

    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=ReclaimProofRequestConfigSerializer,
                description="Returns Reclaim proof request configuration",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="Simple example",
                        description="Example response for Reclaim proof request config",
                        value={
                            "reclaimProofRequestConfig": "{}"
                        },
                        response_only=True,
                    ),
                ],
            ),
            500: OpenApiResponse(description="Internal server error"),
        }
    )
    def post(self, request: Request, *args, **kwargs):
        from reclaim_python_sdk import ReclaimProofRequest

        APP_ID = settings.RECLAIM_APP_ID
        APP_SECRET = settings.RECLAIM_APP_SECRET
        PROVIDER_ID = settings.RECLAIM_TWITTER_PROVIDER_ID

        platform = request.query_params.get("platform")
        handle = request.query_params.get("handle")

        try:
            reclaim_proof_func = async_to_sync(ReclaimProofRequest.init)
            reclaim_proof_request = reclaim_proof_func(APP_ID, APP_SECRET, PROVIDER_ID, {"context": {"handle": handle}})
            # reclaim_proof_request.set_app_callback_url("https://your-backend.com/receive-proofs")
            reclaim_proof_request_config = reclaim_proof_request.to_json_string()

            return JsonResponse({"reclaimProofRequestConfig": reclaim_proof_request_config})
        except Exception as error:
            print(f"Error generating request config: {error}")
            return JsonResponse({"error": "Failed to generate request config"}, status=500)
