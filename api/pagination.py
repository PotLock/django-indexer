from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter

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
