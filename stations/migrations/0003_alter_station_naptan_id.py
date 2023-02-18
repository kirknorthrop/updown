# Generated by Django 4.1.6 on 2023-02-04 14:25

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("stations", "0002_alter_station_crossrail_alter_station_dlr_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="station",
            name="naptan_id",
            field=models.CharField(
                blank=True, max_length=32, null=True, verbose_name="NaPTAN ID"
            ),
        ),
    ]