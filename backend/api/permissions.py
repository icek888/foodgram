from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Разрешает редактирование объекта только его автору,
    остальные могут только читать."""

    def has_permission(self, request, view):
        """Проверяет доступ на уровне запроса: чтение разрешено всем,
        изменение — только авторизованным."""
        return (
            request.method in permissions.SAFE_METHODS
            or request.user.is_authenticated
        )

    def has_object_permission(self, request, view, obj):
        """Проверяет доступ на уровне объекта:
        редактирование разрешено только автору объекта."""
        return (
            request.method in permissions.SAFE_METHODS
            or obj.author == request.user
        )
