# Generated by Django 4.2.16 on 2024-11-12 11:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recipe',
            name='image',
            field=models.ImageField(default=None, upload_to='recipes/images', verbose_name='Изображение рецепта'),
        ),
    ]
