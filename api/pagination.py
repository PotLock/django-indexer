from rest_framework.pagination import PageNumberPagination

class ResultPagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = 'limit'
    max_page_size = 200
