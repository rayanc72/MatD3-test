# Generated by Django 4.1 on 2022-09-24 16:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('materials', '0125_alter_system_message'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='notice',
            field=models.CharField(blank=True, default='', max_length=1000),
        ),
    ]