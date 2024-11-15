import csv
import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from recipes.models import Ingredient

# Настраиваем логирование для записи событий в файл
logging.basicConfig(
    level=logging.INFO,
    filename='ingredient_import.log',
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class Command(BaseCommand):
    """
    Команда для импорта ингредиентов из CSV-файла.
    Для запуска: python manage.py importcsv.
    Базу следует заполнять только на чистую. Чтобы повторно заполнить базу,
    удалите файл базы данных и примените миграции.
    """
    help = 'Заполняет таблицу ингредиентов из CSV-файла'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Начинаем импорт ингредиентов...'))
        file_path = f'{settings.BASE_DIR}/data/ingredients.csv'

        try:
            with open(file_path, mode='r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)

                # Подготовка объектов для массового создания
                ingredients = [
                    Ingredient(name=row['name'],
                               unit=row['unit']) for row in csv_reader
                ]

                # Создание записей в базе данных
                Ingredient.objects.bulk_create(ingredients,
                                               ignore_conflicts=True)

            self.stdout.write(self.style.SUCCESS(
                'Импорт ингредиентов завершён успешно!'
                )
                              )

        except FileNotFoundError:
            logging.error(f'Файл {file_path} не найден.')
            self.stdout.write(self.style.ERROR(
                f'Ошибка: Файл {file_path} не найден.'))

        except Exception as e:
            logging.error(f'Ошибка при импорте: {str(e)}')
            self.stdout.write(
                self.style.ERROR(
                    'Ошибка при выполнении импорта. Подробности в логах.'
                    )
                )
