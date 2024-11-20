import base64
from django.core.files.base import ContentFile
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from djoser.serializers import UserSerializer
from django.conf import settings

from users.models import CustomUser
from recipes.models import (
    Tag,
    Ingredient,
    Recipe,
    IngredientRecipe,
    ShoppingCart,
    Favorite,
    Subscription
)

AMOUNT_MIN = 1
AMOUNT_MAX = 32000
COOKING_TIME_MIN = 1
COOKING_TIME_MAX = 32000


class Base64ImageField(serializers.Field):
    """Кастомное поле для обработки изображений в формате Base64."""
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return data

    def to_representation(self, value):
        if not value:
            return None
        return value.url


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True)

    class Meta:
        model = CustomUser
        fields = ['avatar']


class ProfileSerializer(UserSerializer):
    """Сериализатор для модели пользователя с полем is_subscribed."""
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'is_subscribed',
            'avatar',
        )

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return obj.subscribing.filter(user=user).exists()

    def validate_email(self, value):
        if not value:
            raise serializers.ValidationError('Email is required.')
        return value

    def validate_username(self, value):
        if not value:
            raise serializers.ValidationError('Username is required.')
        return value


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Ingredient."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')
        read_only_fields = ('id', 'name', 'measurement_unit')


class IngredientRecipeGetSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения ингредиентов в рецепте (GET запросы)."""
    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name')
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit')

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class IngredientRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и обновления ингредиентов в рецепте."""
    id = serializers.IntegerField()
    amount = serializers.IntegerField(
        min_value=AMOUNT_MIN,
        max_value=AMOUNT_MAX,
        error_messages={
            'min_value': f'Количество должно быть не менее {AMOUNT_MIN}.',
            'max_value': f'Количество должно быть не более {AMOUNT_MAX}.'
        }
    )

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'amount')


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для Tag."""

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class RecipeGetSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения рецептов (GET запросы)."""
    tags = TagSerializer(many=True, read_only=True)
    author = ProfileSerializer(read_only=True)
    ingredients = IngredientRecipeGetSerializer(many=True,
                                                source='amount_ingredients')
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time',
        )

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and obj.favorites.filter(user=user
                                                              ).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and obj.cart.filter(user=user
                                                         ).exists()


class RecipeSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания и обновления рецептов.
    """
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )
    author = ProfileSerializer(read_only=True)
    ingredients = IngredientRecipeSerializer(many=True)
    image = Base64ImageField(required=True)
    cooking_time = serializers.IntegerField(
        min_value=COOKING_TIME_MIN,
        max_value=COOKING_TIME_MAX,
        error_messages={
            'min_value': (
                f'Время приготовления должно быть не менее '
                f'{COOKING_TIME_MIN} минут.'
            ),
            'max_value': (
                f'Время приготовления должно быть не более '
                f'{COOKING_TIME_MAX} минут.'
            )
        }
    )

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def validate(self, data):
        ingredients = data.get('ingredients')
        if not ingredients:
            raise serializers.ValidationError(
                {'ingredients': 'Необходимо указать хотя бы один ингредиент.'}
            )

        for ingredient in ingredients:
            try:
                Ingredient.objects.get(id=ingredient['id'])
            except Ingredient.DoesNotExist:
                raise serializers.ValidationError(
                    {f'Ингредиент с id {ingredient["id"]} не существует.'}
                )

        tags = data.get('tags')
        if not tags:
            raise serializers.ValidationError(
                {'tags': 'Необходимо указать хотя бы один тег.'}
            )

        unique_tags = set()
        for tag in tags:
            if tag in unique_tags:
                raise serializers.ValidationError(
                    {'tags': 'Теги не могут повторяться.'})
            unique_tags.add(tag)

        unique_ingredients = set()
        for ingredient in ingredients:
            ingredient_id = ingredient.get('id')
            if ingredient_id in unique_ingredients:
                raise serializers.ValidationError(
                    {'ingredients': 'Ингредиенты должны быть уникальными.'}
                )
            unique_ingredients.add(ingredient_id)

        image = data.get('image')
        if not image:
            raise serializers.ValidationError(
                {'image': 'Поле "image" не может быть пустым.'}
            )

        return data

    def create_ingredients(self, ingredients, recipe):
        IngredientRecipe.objects.bulk_create([
            IngredientRecipe(
                recipe=recipe,
                ingredient_id=ingredient['id'],
                amount=ingredient['amount'],
            ) for ingredient in ingredients
        ])

    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.create_ingredients(ingredients, recipe)
        return recipe

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        instance.tags.set(tags)
        instance.amount_ingredients.all().delete()
        self.create_ingredients(ingredients, instance)
        super().update(instance, validated_data)
        return instance

    def to_representation(self, instance):
        context = {'request': self.context.get('request')}
        return RecipeGetSerializer(instance, context=context).data


class RecipeFavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для избранного и корзины."""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для избранного."""

    class Meta:
        model = Favorite
        fields = ('user', 'recipe')
        validators = [
            UniqueTogetherValidator(
                queryset=Favorite.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже в избранном.'
            )
        ]


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Сериализатор для корзины покупок."""

    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже в корзине покупок.'
            )
        ]


class SubscriptionSerializer(serializers.ModelSerializer):
    """Сериализатор для подписок на авторов."""

    class Meta:
        model = Subscription
        fields = ('user', 'author')
        validators = [
            UniqueTogetherValidator(
                queryset=Subscription.objects.all(),
                fields=('user', 'author'),
                message='Вы уже подписаны на этого пользователя.'
            )
        ]

    def validate(self, attrs):
        """Проверяет, что пользователь не подписывается на самого себя."""
        if attrs['user'] == attrs['author']:
            raise serializers.ValidationError(
                'Вы не можете подписаться на самого себя.'
            )
        return attrs


class SubscriptionReadSerializer(ProfileSerializer):
    """
    Сериализатор для отображения подписок
    с поддержкой ограничения на количество рецептов.
    """
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = CustomUser
        fields = ProfileSerializer.Meta.fields + ('recipes', 'recipes_count')

    def get_recipes(self, obj):
        """
        Возвращает рецепты автора с учетом параметра `recipes_limit`.
        """
        request = self.context.get('request')
        recipes_limit = request.query_params.get(
            'recipes_limit', settings.REST_FRAMEWORK['PAGE_SIZE']
        )

        recipes = obj.recipes.all()
        if recipes_limit and recipes_limit.isdigit():
            recipes = recipes[:int(recipes_limit)]

        return RecipeFavoriteSerializer(
            recipes,
            many=True,
            context={'request': request}
        ).data
