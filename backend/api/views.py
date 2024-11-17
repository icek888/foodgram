from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import HttpResponse
from django.contrib.auth import get_user_model

from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from djoser.views import UserViewSet

from recipes.models import (
    Tag,
    Ingredient,
    Recipe,
    ShoppingCart,
    Favorite,
    Subscription
)
from api.pagination import PageLimitPagination, SubRecipeLimitPagination
from api.utils import create_object, delete_object
from api.filters import RecipeFilter
from api.permissions import IsOwnerOrReadOnly
from api.serializers import (
    AvatarSerializer,
    TagSerializer,
    CustomUserSerializer,
    IngredientSerializer,
    RecipeGetSerializer,
    RecipeSerializer,
    RecipeFavoriteSerializer,
    FavoriteSerializer,
    ShoppingCartSerializer,
    SubscriptionReadSerializer,
    SubscriptionSerializer
)

CustomUser = get_user_model()


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Контроллер для работы с тегами,
    поддерживающий только операции чтения."""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """Позволяет выполнять фильтрацию тегов по части названия,
        если передан параметр 'name'.
        """
        queryset = self.queryset
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Контроллер для работы с ингредиентами,
    доступен только просмотр данных."""
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    permission_classes = [IsOwnerOrReadOnly]

    def get_queryset(self):
        """Возвращает список ингредиентов с возможностью фильтрации
        по названию, если указан параметр 'name'.
        """
        queryset = Ingredient.objects.all()
        ingredients = self.request.query_params.get('name')
        if ingredients is not None:
            queryset = queryset.filter(name__istartswith=ingredients)
        return queryset


class RecipeViewSet(viewsets.ModelViewSet):
    """Контроллер для взаимодействия с рецептами,
    поддерживает полные CRUD-операции."""
    pagination_class = PageLimitPagination
    permission_classes = [
        IsOwnerOrReadOnly,
        permissions.IsAuthenticatedOrReadOnly
    ]
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_queryset(self):
        """Подготавливает набор данных с предзагрузкой тегов и ингредиентов
        для оптимизации запросов.
        """
        return Recipe.objects.prefetch_related(
            'amount_ingredients__ingredient', 'tags'
        ).all()

    def perform_create(self, serializer):
        """Сохраняет рецепт,
        автоматически привязывая его к текущему пользователю."""
        serializer.save(author=self.request.user)

    def get_serializer_class(self):
        """Выбирает соответствующий сериализатор в зависимости от типа запроса
        (безопасный или изменяющий данные).
        """
        if self.request.method in permissions.SAFE_METHODS:
            return RecipeGetSerializer
        return RecipeSerializer

    @action(detail=True, methods=['post', 'delete'])
    def favorite(self, request, pk):
        """Добавляет или удаляет рецепт из списка 'Избранное'
        для текущего пользователя.
        """
        if request.method == 'POST':
            serializer = create_object(
                request,
                pk,
                FavoriteSerializer,
                RecipeFavoriteSerializer,
                Recipe
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        try:
            recipe = Recipe.objects.get(pk=pk)
        except Recipe.DoesNotExist:
            return Response(
                {"detail": "Рецепт не найден."},
                status=status.HTTP_404_NOT_FOUND
                )

        if not Favorite.objects.filter(user=request.user,
                                       recipe=recipe).exists():
            return Response(
                {"detail": "Рецепт не был добавлен в избранное."},
                status=status.HTTP_400_BAD_REQUEST
            )

        delete_object(request, pk, Recipe, Favorite)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'])
    def shopping_cart(self, request, pk):
        """Добавляет или удаляет рецепт из 'Корзины покупок'
        для текущего пользователя.
        """
        if request.method == 'POST':
            serializer = create_object(
                request,
                pk,
                ShoppingCartSerializer,
                RecipeFavoriteSerializer,
                Recipe
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        try:
            recipe = Recipe.objects.get(pk=pk)
        except Recipe.DoesNotExist:
            return Response(
                {"detail": "Рецепт не найден."},
                status=status.HTTP_404_NOT_FOUND
            )

        if not ShoppingCart.objects.filter(user=request.user,
                                           recipe=recipe).exists():
            return Response(
                {"detail": "Рецепт не был добавлен в корзину."},
                status=status.HTTP_400_BAD_REQUEST
            )

        delete_object(request, pk, Recipe, ShoppingCart)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        """Генерирует файл со списком покупок на основе рецептов,
        добавленных в корзину.
        """
        ingredient_lst = ShoppingCart.objects.filter(
            user=request.user
        ).values_list(
            'recipe__ingredients__name',
            'recipe__ingredients__measurement_unit',
            Sum('recipe__amount_ingredients__amount')
        )

        shopping_list = ['Список покупок:']
        ingredient_lst = set(ingredient_lst)

        for ingredient in ingredient_lst:
            shopping_list.append('{} ({}) - {}'.format(*ingredient))

        response = HttpResponse(
            '\n'.join(shopping_list),
            content_type='text/plain'
        )
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_short_link(self, request, pk=None):
        """
        Возвращает короткую ссылку на рецепт.
        """
        recipe = self.get_object()
        short_link = f"https://example.com/{recipe.id}-shortlink"

        return Response({"short-link": short_link}, status=status.HTTP_200_OK)


class CustomUserViewSet(UserViewSet):
    """Контроллер для модели пользователя,
    с дополнительными действиями для управления подписками и загрузки аватара.
    """
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    pagination_class = PageLimitPagination
    permission_classes = [permissions.AllowAny]

    @action(detail=False,
            methods=['get'],
            permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """Возвращает данные текущего пользователя
        (только для авторизованных).
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[permissions.IsAuthenticated])
    def subscribe(self, request, id):
        """Создает или удаляет подписку текущего пользователя
        на выбранного автора.
        """
        if request.user.id == int(id):
            raise ValidationError("Вы не можете подписаться на самого себя.")

        try:
            author = CustomUser.objects.get(pk=id)
        except CustomUser.DoesNotExist:
            return Response(
                {"detail": "Автор не найден."},
                status=status.HTTP_404_NOT_FOUND
            )

        if request.method == 'POST':
            serializer = create_object(
                request,
                id,
                SubscriptionSerializer,
                SubscriptionReadSerializer,
                CustomUser
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if not Subscription.objects.filter(user=request.user,
                                           author=author).exists():
            return Response(
                {"detail": "Подписка на данного автора отсутствует."},
                status=status.HTTP_400_BAD_REQUEST
            )

        delete_object(request, id, CustomUser, Subscription)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False,
            permission_classes=[permissions.IsAuthenticated],
            methods=['get'])
    def subscriptions(self, request):
        """
        Возвращает список всех авторов, 
        на которых подписан текущий пользователь,
        с учетом параметра `limit`.
        """
        user = request.user
        authors = CustomUser.objects.filter(subscribing__user=user)

        limit = request.query_params.get('limit')
        if limit and limit.isdigit():
            authors = authors[:int(limit)]

        serializer = SubscriptionReadSerializer(
            authors,
            context={'request': request},
            many=True
        )
        return Response(serializer.data)

    @action(methods=['PUT', 'DELETE'], detail=False,
            permission_classes=[permissions.IsAuthenticated],
            serializer_class=AvatarSerializer,
            url_path='me/avatar')
    def avatar(self, request):
        user = self.request.user
        if request.method == 'DELETE':
            CustomUser.objects.filter(pk=user.pk).update(avatar='')

            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = AvatarSerializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        file = serializer.validated_data['avatar']
        user.avatar.save(file.name, content=file)

        return Response(serializer.data)
