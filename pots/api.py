from django.db.models import Q
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Account
from accounts.serializers import AccountSerializer
from donations.models import Donation
from donations.serializers import DonationSerializer

from .models import Pot, PotApplication, PotApplicationStatus
from .serializers import PotApplicationSerializer, PotPayoutSerializer, PotSerializer


class PotsAPI(APIView, LimitOffsetPagination):
    def dispatch(self, request, *args, **kwargs):
        return super(PotsAPI, self).dispatch(request, *args, **kwargs)

    @method_decorator(cache_page(60 * 15))  # Cache for 15 mins
    def get(self, request: Request, *args, **kwargs):
        pot_id = kwargs.get("pot_id", None)
        action = kwargs.get("action", None)
        if pot_id:
            # Request pertaining to a specific pot_id
            try:
                pot = Pot.objects.get(id=pot_id)
            except Pot.DoesNotExist:
                return Response(
                    {"message": f"Pot with ID {pot_id} not found."}, status=404
                )
            if action:
                # Handle action if present; only valid option currently is "applications"
                if action == "applications":
                    # Return applications for pot_id
                    applications = pot.applications.all()
                    results = self.paginate_queryset(applications, request, view=self)
                    serializer = PotApplicationSerializer(results, many=True)
                    return self.get_paginated_response(serializer.data)
                elif action == "donations":
                    # Return donations for pot_id
                    donations = pot.donations.all()
                    results = self.paginate_queryset(donations, request, view=self)
                    serializer = DonationSerializer(results, many=True)
                    return self.get_paginated_response(serializer.data)
                elif action == "sponsors":
                    # Return sponsors for pot_id
                    sponsor_ids = (
                        Donation.objects.filter(pot=pot, matching_pool=True)
                        .values_list("donor", flat=True)
                        .distinct()
                    )
                    sponsors = Account.objects.filter(id__in=sponsor_ids)
                    results = self.paginate_queryset(sponsors, request, view=self)
                    serializer = AccountSerializer(results, many=True)
                    return self.get_paginated_response(serializer.data)
                elif action == "payouts":
                    # Return payouts for pot_id
                    payouts = pot.payouts.all()
                    results = self.paginate_queryset(payouts, request, view=self)
                    serializer = PotPayoutSerializer(results, many=True)
                    return self.get_paginated_response(serializer.data)
                else:
                    return Response(
                        {"error": f"Invalid action: {action}"},
                        status=400,
                    )
            else:
                # Return pot
                serializer = PotSerializer(pot)
                return Response(serializer.data)
        else:
            # Return all pots
            pots = Pot.objects.all()
            results = self.paginate_queryset(pots, request, view=self)
            serializer = PotSerializer(results, many=True)
            return self.get_paginated_response(serializer.data)
