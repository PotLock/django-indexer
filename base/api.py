import logging
import os
from datetime import timedelta

import requests
from django.db.models import Count, Sum
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
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
from donations.models import Donation
from pots.models import Pot, PotPayout

logger = logging.getLogger("jobs")


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


def _money(value) -> str:
    return f"${(value or 0):,.2f}"


def _aggregate_donations(qs):
    agg = qs.aggregate(
        volume=Sum("total_amount_usd"),
        protocol_fees=Sum("protocol_fee_usd"),
        referrer_fees=Sum("referrer_fee_usd"),
        chef_fees=Sum("chef_fee_usd"),
        count=Count("id"),
        donors=Count("donor", distinct=True),
        recipients=Count("recipient", distinct=True),
    )
    matching_pool_volume = (
        qs.filter(matching_pool=True).aggregate(s=Sum("total_amount_usd"))["s"] or 0
    )
    direct_volume = (agg["volume"] or 0) - matching_pool_volume
    return {
        "volume": agg["volume"] or 0,
        "direct_volume": direct_volume,
        "matching_pool_volume": matching_pool_volume,
        "protocol_fees": agg["protocol_fees"] or 0,
        "referrer_fees": agg["referrer_fees"] or 0,
        "chef_fees": agg["chef_fees"] or 0,
        "count": agg["count"] or 0,
        "donors": agg["donors"] or 0,
        "recipients": agg["recipients"] or 0,
    }


def _payout_stats(qs):
    paid = qs.filter(paid_at__isnull=False)
    pending = qs.filter(paid_at__isnull=True)
    return {
        "paid_usd": paid.aggregate(s=Sum("amount_paid_usd"))["s"] or 0,
        "paid_count": paid.count(),
        "pending_count": pending.count(),
    }


def _fetch_campaign_stats_from_dev():
    """Fetch campaign stats from the dev deployment (which has the campaigns app
    installed and indexes campaign data with USD computed).

    The prod deployment does not have the campaigns app, so campaign data is
    pulled over HTTP from `DEV_CAMPAIGN_STATS_URL` and merged into the same
    daily-stats message. Returns a dict with `today`/`last_7_days`/`all_time`
    keys (each `{"count", "raised_usd"}`), or `None` if the URL is unset or the
    request fails — in which case the message simply omits campaign lines.
    """
    url = os.environ.get("DEV_CAMPAIGN_STATS_URL")
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("Failed to fetch campaign stats from dev (%s): %s", url, e)
        return None


def _build_daily_stats():
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    seven_days_ago = now - timedelta(days=7)

    donations_today = _aggregate_donations(Donation.objects.filter(donated_at__gte=today_start))
    donations_7d = _aggregate_donations(Donation.objects.filter(donated_at__gte=seven_days_ago))
    donations_all = _aggregate_donations(Donation.objects.all())

    payouts_today = _payout_stats(PotPayout.objects.filter(paid_at__gte=today_start))
    payouts_7d = _payout_stats(PotPayout.objects.filter(paid_at__gte=seven_days_ago))
    payouts_all = _payout_stats(PotPayout.objects.all())

    pots_today = Pot.objects.filter(deployed_at__gte=today_start).count()
    pots_7d = Pot.objects.filter(deployed_at__gte=seven_days_ago).count()
    pots_all = Pot.objects.count()

    campaign_stats = _fetch_campaign_stats_from_dev() or {}
    campaigns_today = campaign_stats.get("today")
    campaigns_7d = campaign_stats.get("last_7_days")
    campaigns_all = campaign_stats.get("all_time")

    return {
        "date": now.strftime("%Y-%m-%d"),
        "today": {
            "donations": donations_today,
            "payouts": payouts_today,
            "new_pots": pots_today,
            "campaigns": campaigns_today,
        },
        "last_7_days": {
            "donations": donations_7d,
            "payouts": payouts_7d,
            "new_pots": pots_7d,
            "campaigns": campaigns_7d,
        },
        "all_time": {
            "donations": donations_all,
            "payouts": payouts_all,
            "pots": pots_all,
            "campaigns": campaigns_all,
        },
    }


def _format_window(label: str, window: dict, *, include_new_label: bool, all_time: bool = False) -> str:
    d = window["donations"]
    p = window["payouts"]
    lines = [
        label,
        f"Volume: {_money(d['volume'])} (direct {_money(d['direct_volume'])} + matching {_money(d['matching_pool_volume'])})",
        f"Fees: {_money(d['protocol_fees'] + d['referrer_fees'] + d['chef_fees'])}"
        f" (protocol {_money(d['protocol_fees'])} + referrer {_money(d['referrer_fees'])} + chef {_money(d['chef_fees'])})",
        f"Donations: {d['count']}",
        f"Unique donors: {d['donors']}",
        f"Unique recipients: {d['recipients']}",
        f"Payouts: {_money(p['paid_usd'])} ({p['paid_count']})",
        f"Pending payouts: {p['pending_count']}",
    ]
    pot_label = "Pots" if all_time else ("New pots" if include_new_label else "Pots")
    if all_time:
        lines.append(f"{pot_label}: {window['pots']}")
    else:
        lines.append(f"{pot_label}: {window['new_pots']}")

    campaigns = window["campaigns"]
    if campaigns is not None:
        camp_label = "Campaigns" if all_time else ("New campaigns" if include_new_label else "Campaigns")
        lines.append(f"{camp_label}: {campaigns['count']} (raised {_money(campaigns['raised_usd'])})")
    return "\n".join(lines)


def format_daily_stats_text(stats: dict) -> str:
    divider = "-" * 20
    parts = [
        "POTLOCK metrics - Global",
        f"Date: {stats['date']}",
        divider,
        _format_window("TODAY", stats["today"], include_new_label=True),
        divider,
        _format_window("LAST 7 DAYS", stats["last_7_days"], include_new_label=True),
        divider,
        _format_window("ALL-TIME", stats["all_time"], include_new_label=False, all_time=True),
    ]
    return "\n".join(parts)


class DailyStatsAPI(APIView):
    """Daily aggregated stats for POTLOCK. Default response is pre-formatted text
    suitable for posting directly to Signal. Pass `?format=json` for raw numbers."""

    @method_decorator(cache_page(60 * 5))
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="format",
                description="`text` (default) or `json`",
                required=False,
                type=str,
            ),
        ],
        responses={
            200: OpenApiResponse(description="Daily stats (text/plain or application/json)"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def get(self, request: Request, *args, **kwargs):
        stats = _build_daily_stats()
        if request.query_params.get("format", "text").lower() == "json":
            return Response(stats)
        return HttpResponse(format_daily_stats_text(stats), content_type="text/plain; charset=utf-8")


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
