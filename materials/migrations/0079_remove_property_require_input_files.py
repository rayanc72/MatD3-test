# Generated by Django 2.1.7 on 2019-05-03 02:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('materials', '0078_auto_20190501_1418'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='property',
            name='require_input_files',
        ),
    ]