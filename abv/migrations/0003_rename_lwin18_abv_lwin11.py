# Generated by Django 4.2.3 on 2023-07-19 14:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('abv', '0002_alter_abv_lwin18'),
    ]

    operations = [
        migrations.RenameField(
            model_name='abv',
            old_name='lwin18',
            new_name='lwin11',
        ),
    ]