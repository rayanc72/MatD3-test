# Generated by Django 3.1.14 on 2022-07-15 15:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('materials', '0120_subset_space_group_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='system',
            name='iupac',
            field=models.CharField(blank=True, max_length=500),
        ),
    ]
