# Generated by Django 2.1.7 on 2019-03-29 14:18

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('materials', '0057_auto_20190328_2245'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='bondangle',
            name='idinfo_ptr',
        ),
        migrations.RemoveField(
            model_name='bondangle',
            name='system',
        ),
        migrations.RemoveField(
            model_name='bondlength',
            name='idinfo_ptr',
        ),
        migrations.RemoveField(
            model_name='bondlength',
            name='system',
        ),
        migrations.DeleteModel(
            name='BondAngle',
        ),
        migrations.DeleteModel(
            name='BondLength',
        ),
    ]
