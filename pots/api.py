from django.db.models import Q
from django.utils import timezone
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Pot, PotApplication, PotApplicationStatus
from .serializers import PotSerializer


class ActivePotsAPIView(APIView, LimitOffsetPagination):
    def get(self, request: Request, *args, **kwargs):
        now = timezone.now()
        account_id = kwargs.get("account_id")

        # If account_id, get only those Pots with approved applications for this account_id
        if account_id:
            applications = PotApplication.objects.filter(
                applicant_id=account_id, status=PotApplicationStatus.APPROVED
            )
            pot_ids = applications.values_list("pot_id", flat=True)
            pots = Pot.objects.filter(id__in=pot_ids)
        else:
            # If no account_id provided, get all pots
            pots = Pot.objects.all()

        # Apply filter for 'status=live' query parameter
        if request.query_params.get("status") == "live":
            pots = pots.filter(
                matching_round_start__lte=now, matching_round_end__gte=now
            )

        # Pagination
        results = self.paginate_queryset(pots, request, view=self)
        serializer = PotSerializer(results, many=True)
        return self.get_paginated_response(serializer.data)
