from django.db.models import Count, Exists, OuterRef, Sum
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Account
from donations.models import Donation
from pots.models import PotPayout


class StatsAPI(APIView):
    def dispatch(self, request, *args, **kwargs):
        return super(StatsAPI, self).dispatch(request, *args, **kwargs)

    @method_decorator(
        cache_page(60 * 5)
    )  # Cache for 5 mins (using page-level caching for now for simplicity, but can move to data-level caching if desired)
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
            Account.objects.filter(received_donations__is_null=False).distinct().count()
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
