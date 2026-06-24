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
from lists.models import List, ListRegistration
from pots.models import Pot, PotPayout

logger = logging.getLogger("jobs")

# A "project" on POTLOCK is an approved registrant on the Public Goods Registry
# list (PUBLIC_GOODS_REGISTRY_LIST_ID = 1 on the frontend). The homepage project
# discovery defaults to this list + "Approved" status.
REGISTRY_LIST_ON_CHAIN_ID = 1


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


def _sum_usd_count(qs):
    """(count, total USD) for a donation-like queryset with a total_amount_usd field."""
    agg = qs.aggregate(usd=Sum("total_amount_usd"), count=Count("id"))
    return agg["count"] or 0, float(agg["usd"] or 0)


def _registry_registrations(start=None):
    """Approved registrants on the Public Goods Registry list = POTLOCK 'projects'."""
    qs = ListRegistration.objects.filter(
        list__on_chain_id=REGISTRY_LIST_ON_CHAIN_ID, status="Approved"
    )
    if start is not None:
        qs = qs.filter(submitted_at__gte=start)
    return qs


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
    daily-stats message. The env var is optional: it falls back to the canonical
    dev endpoint so a dropped/missing var can't silently strip campaign lines
    from the message. Returns a dict with `today`/`last_7_days`/`all_time` keys,
    or `None` if the request fails — in which case the message omits campaigns.
    """
    url = os.environ.get(
        "DEV_CAMPAIGN_STATS_URL", "https://dev.potlock.io/api/v1/stats/campaigns"
    )
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("Failed to fetch campaign stats from dev (%s): %s", url, e)
        return None


def _window_stats(start, campaign_window):
    """Build one window (start=None means all-time). `campaign_window` is the
    matching slice of the dev campaign-stats payload (or None when unavailable)."""
    dqs = Donation.objects.all() if start is None else Donation.objects.filter(donated_at__gte=start)
    direct_count, direct_usd = _sum_usd_count(dqs.filter(pot__isnull=True))
    pot_count, pot_usd = _sum_usd_count(dqs.filter(pot__isnull=False))

    if campaign_window is not None:
        camp_don_count = campaign_window.get("donation_count", 0)
        camp_near = campaign_window.get("donation_near", 0) or 0
        # stored USD (priced/FT donations) + approx USD of the NEAR portion
        camp_don_usd = (campaign_window.get("donation_usd", 0) or 0) + (
            campaign_window.get("donation_near_usd", 0) or 0
        )
        new_campaigns = campaign_window.get("count")
    else:
        camp_don_count, camp_near, camp_don_usd, new_campaigns = 0, 0, 0, None

    people = dqs.aggregate(
        donors=Count("donor", distinct=True),
        recipients=Count("recipient", distinct=True),
    )
    fees = dqs.aggregate(
        protocol=Sum("protocol_fee_usd"),
        referrer=Sum("referrer_fee_usd"),
        chef=Sum("chef_fee_usd"),
    )

    payout_qs = PotPayout.objects.all() if start is None else PotPayout.objects.filter(paid_at__gte=start)
    pots = (Pot.objects.all() if start is None else Pot.objects.filter(deployed_at__gte=start)).count()
    lists = (List.objects.all() if start is None else List.objects.filter(created_at__gte=start)).count()

    return {
        "donations": {
            "count": direct_count + pot_count + camp_don_count,
            "usd": direct_usd + pot_usd + camp_don_usd,
            "direct_count": direct_count,
            "direct_usd": direct_usd,
            "pot_count": pot_count,
            "pot_usd": pot_usd,
            "campaign_count": camp_don_count,
            "campaign_usd": camp_don_usd,
            "campaign_near": camp_near,
            "has_campaigns": campaign_window is not None,
        },
        "donors": people["donors"] or 0,
        "recipients": people["recipients"] or 0,
        "fees": {
            "protocol": fees["protocol"] or 0,
            "referrer": fees["referrer"] or 0,
            "chef": fees["chef"] or 0,
        },
        "payouts": _payout_stats(payout_qs),
        "projects": _registry_registrations(start).count(),
        "pots": pots,
        "lists": lists,
        "campaigns": new_campaigns,
    }


def _build_daily_stats():
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    seven_days_ago = now - timedelta(days=7)

    campaign_stats = _fetch_campaign_stats_from_dev() or {}

    return {
        "date": now.strftime("%Y-%m-%d"),
        "today": _window_stats(today_start, campaign_stats.get("today")),
        "last_7_days": _window_stats(seven_days_ago, campaign_stats.get("last_7_days")),
        "all_time": _window_stats(None, campaign_stats.get("all_time")),
        "signups_total": Account.objects.count(),
    }


def _format_window(label: str, window: dict, *, all_time: bool = False) -> str:
    d = window["donations"]
    f = window["fees"]
    fees_total = f["protocol"] + f["referrer"] + f["chef"]

    lines = [
        label,
        f"Donations: {d['count']} ({_money(d['usd'])})",
        f"  - direct: {d['direct_count']} ({_money(d['direct_usd'])})",
        f"  - pots (matching): {d['pot_count']} ({_money(d['pot_usd'])})",
    ]
    if d["has_campaigns"]:
        lines.append(
            f"  - campaigns: {d['campaign_count']} ({d['campaign_near']:,.2f} NEAR / ~{_money(d['campaign_usd'])})"
        )

    lines.append(f"Donors: {window['donors']}")
    lines.append(f"Recipients: {window['recipients']}")
    lines.append(
        f"Fees: {_money(fees_total)} (protocol {_money(f['protocol'])}"
        f" + referrer {_money(f['referrer'])} + chef {_money(f['chef'])})"
    )

    p = window["payouts"]
    lines.append(f"Payouts: {_money(p['paid_usd'])} ({p['paid_count']})")
    lines.append(f"Pending payouts: {p['pending_count']}")

    proj_label = "Projects" if all_time else "New projects"
    pot_label = "Pots" if all_time else "New pots"
    camp_label = "Campaigns" if all_time else "New campaigns"
    list_label = "Lists" if all_time else "New lists"

    lines.append(f"{proj_label}: {window['projects']}")
    lines.append(f"{pot_label}: {window['pots']}")
    if window["campaigns"] is not None:
        lines.append(f"{camp_label}: {window['campaigns']}")
    lines.append(f"{list_label}: {window['lists']}")
    return "\n".join(lines)


def format_daily_stats_text(stats: dict) -> str:
    divider = "-" * 20
    parts = [
        "POTLOCK metrics - Global",
        f"Date: {stats['date']}",
        divider,
        _format_window("TODAY", stats["today"]),
        divider,
        _format_window("LAST 7 DAYS", stats["last_7_days"]),
        divider,
        _format_window("ALL-TIME", stats["all_time"], all_time=True),
        f"Signups (total accounts): {stats['signups_total']:,}",
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
