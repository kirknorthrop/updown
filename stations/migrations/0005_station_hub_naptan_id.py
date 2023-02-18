# Generated by Django 4.1.6 on 2023-02-04 15:08

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("stations", "0004_station_alternate_names"),
    ]

    operations = [
        migrations.AddField(
            model_name="station",
            name="hub_naptan_id",
            field=models.CharField(
                blank=True, max_length=32, null=True, verbose_name="Hub NaPTAN ID"
            ),
        ),
    ]