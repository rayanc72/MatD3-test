# Generated by Django 2.0.1 on 2018-01-26 22:18

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('materials', '0016_bandstructure_band_structure'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='bandstructure',
            name='band_structure',
        ),
    ]