from django.db.models import Exists, OuterRef
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from donations.models import Donation

from .models import Account
from .serializers import AccountSerializer


class DonorsAPI(APIView, LimitOffsetPagination):
    def dispatch(self, request, *args, **kwargs):
        return super(DonorsAPI, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # Return all donors
        # TODO: NB: this has not yet been tested, simply provided as a starting point using pagination
        # TODO: add optional query params for filtering, sorting, etc
        donations_subquery = Donation.objects.filter(donor_id=OuterRef("pk"))
        donor_accounts = Account.objects.filter(Exists(donations_subquery))
        results = self.paginate_queryset(donor_accounts, request, view=self)
        serializer = AccountSerializer(results, many=True)
        return self.get_paginated_response(serializer.data)


class AccountsAPI(APIView, LimitOffsetPagination):
    def dispatch(self, request, *args, **kwargs):
        return super(AccountsAPI, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # Return all accounts
        accounts = Account.objects.all()
        results = self.paginate_queryset(accounts, request, view=self)
        serializer = AccountSerializer(results, many=True)
        return self.get_paginated_response(serializer.data)
