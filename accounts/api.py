from django.db.models import Exists, OuterRef
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from donations.models import Donation
from pots.models import Pot, PotApplication, PotApplicationStatus
from pots.serializers import PotSerializer

from .models import Account
from .serializers import AccountSerializer


class DonorsAPI(APIView, LimitOffsetPagination):
    def dispatch(self, request, *args, **kwargs):
        return super(DonorsAPI, self).dispatch(request, *args, **kwargs)

    @method_decorator(cache_page(60 * 15))  # Cache for 15 mins
    def get(self, request: Request, *args, **kwargs):
        # Return all donors
        donations_subquery = Donation.objects.filter(donor_id=OuterRef("pk"))
        donor_accounts = Account.objects.filter(Exists(donations_subquery))
        sort = request.query_params.get("sort", None)
        if sort == "most_donated_usd":
            donor_accounts = donor_accounts.order_by(
                "-total_donations_out_usd"
            )  # TODO: this field name might be changing
        # TODO: add more sort options
        results = self.paginate_queryset(donor_accounts, request, view=self)
        serializer = AccountSerializer(results, many=True)
        return self.get_paginated_response(serializer.data)


class AccountsAPI(APIView, LimitOffsetPagination):
    def dispatch(self, request, *args, **kwargs):
        return super(AccountsAPI, self).dispatch(request, *args, **kwargs)

    #@method_decorator(cache_page(60 * 15))  # Cache for 15 mins
    def get(self, request: Request, *args, **kwargs):
        account_id = kwargs.get("account_id", None)
        action = kwargs.get("action", None)
        if account_id:
            # Request pertaining to a specific account_id
            try:
                account = Account.objects.get(id=account_id)
            except Account.DoesNotExist:
                return Response(
                    {"message": f"Account with ID {account_id} not found."}, status=404
                )
            if action:
                # Handle action if present; only valid option currently is "active_pots"
                if action == "active_pots":
                    # Return active pots for account_id
                    now = timezone.now()
                    applications = PotApplication.objects.filter(
                        applicant=account, status=PotApplicationStatus.APPROVED
                    )
                    pot_ids = applications.values_list("pot_id", flat=True)
                    pots = Pot.objects.filter(id__in=pot_ids)
                    if request.query_params.get("status") == "live":
                        pots = pots.filter(
                            matching_round_start__lte=now, matching_round_end__gte=now
                        )
                    results = self.paginate_queryset(pots, request, view=self)
                    serializer = PotSerializer(results, many=True)
                    return self.get_paginated_response(serializer.data)
                return Response({"message": f"Invalid action {action}."}, status=400)
            # If no action, return account by account_id
            else:
                serializer = AccountSerializer(account)
                return Response(serializer.data)
        else:
            # No account_id specified; return all accounts
            accounts = Account.objects.all()
            results = self.paginate_queryset(accounts, request, view=self)
            serializer = AccountSerializer(results, many=True)
            return self.get_paginated_response(serializer.data)
