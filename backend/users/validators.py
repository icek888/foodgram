import re
from django.core.exceptions import ValidationError


def validate_username(value):
    if value.lower() == 'me':
        raise ValidationError('Недопустимое имя пользователя.')

    if not re.match(r'^[a-zA-Z][a-zA-Z0-9._-]{1,20}$', value):
        raise ValidationError('Недопустимые символы в имени пользователя.')
    return value


def validate_password(value):
    if len(value) < 8:
        raise ValidationError('Пароль слишком короткий. Минимум 8 символов.')
    return value
