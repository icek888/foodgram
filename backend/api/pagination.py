from rest_framework.pagination import PageNumberPagination


class PageLimitPagination(PageNumberPagination):
    page_size_query_param = 'limit'
    page_size = 10


class SubRecipeLimitPagination(PageNumberPagination):
    page_size_query_param = 'recipes_limit'
    page_size = 10
