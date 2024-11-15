import base64
from django.core.files.base import ContentFile
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from djoser.serializers import UserSerializer

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


class CustomUserSerializer(UserSerializer):
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
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return Subscription.objects.filter(user=user, author=obj).exists()

    def validate_email(self, value):
        if not value:
            raise serializers.ValidationError("Email is required.")
        return value

    def validate_username(self, value):
        if not value:
            raise serializers.ValidationError("Username is required.")
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
        source='ingredient.measurement_unit'
        )

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class IngredientRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и обновления ингредиентов в рецепте."""
    id = serializers.IntegerField()

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
    author = CustomUserSerializer(read_only=True)
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
        user = self.context.get('request').user
        return user.is_authenticated and Favorite.objects.filter(user=user,
                                                                 recipe=obj
                                                                 ).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        return user.is_authenticated and ShoppingCart.objects.filter(user=user,
                                                                     recipe=obj
                                                                     ).exists()


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и обновления рецептов."""
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(),
                                              many=True)
    author = CustomUserSerializer(read_only=True)
    ingredients = IngredientRecipeSerializer(many=True)
    image = Base64ImageField(required=True)

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
                    {f'Ингредиент с id{ingredient["id"]} не существует.'}
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
                    {'tags': 'Теги не могут повторяться.'}
                    )
            unique_tags.add(tag)

        unique_ingredients = set()
        for ingredient in ingredients:
            ingredient_id = ingredient.get('id')
            if ingredient_id in unique_ingredients:
                raise serializers.ValidationError(
                    {'ingredients': 'Ингредиенты должны быть уникальными.'}
                )
            unique_ingredients.add(ingredient_id)
            amount = ingredient.get('amount')
            if amount is None or int(amount) <= 0:
                raise serializers.ValidationError({
                    'Количество ингредиента должно быть больше 0.'
                })

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
        IngredientRecipe.objects.filter(recipe=instance).delete()
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


class SubscriptionReadSerializer(CustomUserSerializer):
    """Сериализатор для отображения подписок."""
    recipes = RecipeFavoriteSerializer(many=True, read_only=True)
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = CustomUserSerializer.Meta.fields + ('recipes',
                                                     'recipes_count')

    def get_recipes_count(self, obj):
        return obj.recipes.count()
