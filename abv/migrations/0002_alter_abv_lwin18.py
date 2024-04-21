# Generated by Django 4.2.3 on 2023-07-19 14:22

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('abv', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='abv',
            name='lwin18',
            field=models.CharField(max_length=11, validators=[django.core.validators.RegexValidator('^\\d{11}$')]),
        ),
    ]