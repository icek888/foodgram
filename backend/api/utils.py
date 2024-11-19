from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework import status

from recipes.models import Recipe, Subscription


def create_object(request, pk, serializer_in, serializer_out, model):
    """
    Функция для создания объектов связи в моделях.
    Проверяет, является ли пользователь авторизованным, и создаёт связь.
    """
    if request.user.is_anonymous:
        return Response(status=status.HTTP_401_UNAUTHORIZED)

    user_id = request.user.id
    target_obj = get_object_or_404(model, id=pk)

    # Подготавливаем данные в зависимости от типа модели
    data = (
        {'user': user_id, 'recipe': target_obj.id}
        if model is Recipe
        else {'user': user_id, 'author': target_obj.id}
    )

    serializer = serializer_in(data=data)
    serializer.is_valid(raise_exception=True)
    serializer.save()

    # Используем выходной сериализатор для создания ответа
    response_serializer = serializer_out(target_obj,
                                         context={'request': request})
    return response_serializer


def delete_object(request, pk, main_model, relation_model):
    """
    Функция для удаления объектов связи в моделях.
    Проверяет авторизацию пользователя и удаляет связь.
    """
    if request.user.is_anonymous:
        return Response(status=status.HTTP_401_UNAUTHORIZED)

    user = request.user

    # Получаем объект связи в зависимости от модели
    if relation_model is Subscription:
        obj_to_delete = get_object_or_404(relation_model, user=user, author=pk)
    else:
        recipe_obj = get_object_or_404(main_model, id=pk)
        obj_to_delete = get_object_or_404(relation_model, user=user,
                                          recipe=recipe_obj)

    obj_to_delete.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
