from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from users.models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('id', 'email', 'username', 'first_name', 'last_name')
    search_fields = ('username', 'email')
    list_filter = ('is_active', 'is_staff')
    ordering = ('email',)
