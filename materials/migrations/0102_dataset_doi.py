# Generated by Django 2.2.5 on 2019-11-15 16:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('materials', '0101_auto_20190905_1702'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='doi',
            field=models.CharField(blank=True, max_length=50),
        ),
    ]