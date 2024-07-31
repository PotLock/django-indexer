import requests
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

from .serializers import DonationContractConfigSerializer

DONATE_CONTRACT = "donate." + settings.POTLOCK_TLA


class DonationContractConfigAPI(APIView, CustomSizePageNumberPagination):

    @extend_schema(
        parameters=[
            *pagination_parameters,
        ],
        responses={
            200: OpenApiResponse(
                response=DonationContractConfigSerializer,
                description=f"Returns config for {DONATE_CONTRACT}",
                examples=[
                    OpenApiExample(
                        "example-1",
                        summary="Simple example",
                        description="Example response for donate contract config",
                        value={
                            "owner": "potlock.near",
                            "protocol_fee_basis_points": 250,
                            "referral_fee_basis_points": 1500,
                            "protocol_fee_recipient_account": "impact.sputnik-dao.near",
                        },
                        response_only=True,
                    ),
                ],
            ),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    @method_decorator(cache_page(60 * 5))
    def get(self, request: Request, *args, **kwargs):
        url = f"{settings.FASTNEAR_RPC_URL}/account/{DONATE_CONTRACT}/view/get_config"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            data.pop("total_donations_amount")
            data.pop("net_donations_amount")
            data.pop("total_donations_count")
            data.pop("total_protocol_fees")
            data.pop("total_referrer_fees")

            return Response(data)
        else:
            logger.error(
                f"Request for {DONATE_CONTRACT} config failed ({response.status_code}) with message: {response.text}"
            )
            return Response({"message": response.text}, status=response.status_code)
