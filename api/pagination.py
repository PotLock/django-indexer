from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter
from rest_framework.pagination import PageNumberPagination



# ovveeride PageNumberPagination to add page_size_query_param alias
class CustomSizePageNumberPagination(PageNumberPagination):
    page_size_query_param = 'page_size'
    max_page_size = 100

pagination_parameters = [
    OpenApiParameter(
        "page",
        OpenApiTypes.INT,
        OpenApiParameter.QUERY,
        description="Page number for pagination",
    ),
    OpenApiParameter(
        "page_size",
        OpenApiTypes.INT,
        OpenApiParameter.QUERY,
        description="Number of results per page",
    ),
]
