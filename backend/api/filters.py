from django_filters import rest_framework as filters
from recipes.models import Recipe, Tag


class RecipeFilter(filters.FilterSet):
    """Настраивает фильтрацию для рецептов по разным параметрам."""
    author = filters.NumberFilter(
        field_name='author__id',
        label='Фильтр по автору'
    )
    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
        label='Фильтр по тегам'
    )
    is_favorited = filters.BooleanFilter(
        method='filter_is_favorited',
        label='Фильтр по избранному'
    )
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_is_in_shopping_cart',
        label='Фильтр по корзине покупок'
    )

    class Meta:
        model = Recipe
        fields = [
            'author',
            'tags',
            'is_favorited',
            'is_in_shopping_cart',
        ]
