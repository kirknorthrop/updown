from django.contrib import admin
from stations.models import Station


class StationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "naptan_id",
        "hub_naptan_id",
        "tube",
        "dlr",
        "national_rail",
        "crossrail",
        "overground",
    )
    list_filter = ["tube", "dlr", "national_rail", "crossrail", "overground"]
    ordering = ("name",)
    search_fields = ["name"]


admin.site.register(Station, StationAdmin)
