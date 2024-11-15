from django.contrib.auth.models import AbstractUser
from django.db import models

from users.validators import validate_username


class CustomUser(AbstractUser):
    """Переопределяем модель User с дополнительными полями"""

    username = models.CharField(
        'Пользователь',
        max_length=150,
        unique=True,
        validators=[validate_username],
        help_text='Обязательное поле. Должно содержать только буквы и цифры.'
    )
    email = models.EmailField(
        'Электронная почта',
        unique=True,
        max_length=254,
        help_text='Обязательное поле. Укажите действующий адрес почты.'
    )
    first_name = models.CharField(
        'Имя',
        max_length=150,
        help_text='Обязательное поле. Укажите ваше имя.'
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=150,
        help_text='Обязательное поле. Укажите вашу фамилию.'
    )
    bio = models.TextField(
        'О себе',
        blank=True,
        help_text='Необязательное поле. Краткая информация о себе.'
    )
    avatar = models.ImageField(
        'Аватар',
        upload_to='avatar/',
        blank=True,
        null=True,
        help_text='Необязательное поле. Загрузите изображение профиля.'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = (
        'username',
        'first_name',
        'last_name',
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)

    def __str__(self) -> str:
        """Строковое представление объекта модели."""
        return self.username
