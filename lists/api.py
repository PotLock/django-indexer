from django.db.models import Exists, OuterRef
from django.utils import timezone
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import List
from .serializers import ListRegistrationSerializer, ListSerializer


class ListsAPI(APIView, LimitOffsetPagination):
    def dispatch(self, request, *args, **kwargs):
        return super(ListsAPI, self).dispatch(request, *args, **kwargs)

    def get(self, request: Request, *args, **kwargs):
        list_id = kwargs.get("list_id", None)
        action = kwargs.get("action", None)
        if list_id:
            # Request pertaining to a specific list_id
            try:
                list = List.objects.get(id=list_id)
            except List.DoesNotExist:
                return Response(
                    {"message": f"List with ID {list_id} not found."}, status=404
                )
            if action:
                # Handle action if present; only valid option currently is "registrations"
                if action == "registrations":
                    # Return registrations for list_id
                    registrations = list.registrations.all()
                    results = self.paginate_queryset(registrations, request, view=self)
                    serializer = ListRegistrationSerializer(results, many=True)
                    return self.get_paginated_response(serializer.data)
                else:
                    return Response(
                        {"error": f"Invalid action: {action}"},
                        status=400,
                    )
            else:
                # Return list
                serializer = ListSerializer(list)
                return Response(serializer.data)
        else:
            # Return all lists
            lists = List.objects.all()
            results = self.paginate_queryset(lists, request, view=self)
            serializer = ListSerializer(results, many=True)
            return self.get_paginated_response(serializer.data)
