import requests
from django.conf import settings

from stations.models import Station


def cleanup_station_name(station_name):
    to_remove = [
        "Rail Station",
        "Underground Station",
        "Underground Stn",
        "Overground Station",
        "DLR Station",
        "Station",
        "(London)",
        "(",
        ")",
        "Dist&Picc Line",
        "Circle Line",
        "Bakerloo Line",
        "Central Line",
        "H&C Line-Underground",
        "Crossrail",
    ]

    for item in to_remove:
        station_name = station_name.replace(item, "")

    # Kensington (Olympia) is the only station with parentheses in its name on the tube map.
    if station_name == "Kensington Olympia":
        station_name = "Kensington (Olympia)"

    return station_name.strip()


def update_station_list():
    modes = ["tube", "dlr", "overground", "tflrail", "elizabeth-line"]

    station_status_uri = "https://api.tfl.gov.uk/StopPoint/Mode/%s?app_id=%s&app_key=%s"

    MODE_TRANSFORM = {
        "tube": "tube",
        "dlr": "dlr",
        "": "national_rail",
        "elizabeth-line": "crossrail",
        "overground": "overground",
    }

    for mode in modes:
        url = station_status_uri % (mode, settings.TFL_API_ID, settings.TFL_API_KEY)

        r = requests.get(url)

        for stop_point in r.json().get("stopPoints", []):
            station_name = cleanup_station_name(stop_point["commonName"])

            station, _ = Station.objects.get_or_create(
                name=station_name,
                naptan_id=stop_point.get("stationNaptan"),
                hub_naptan_id=stop_point.get("hubNaptanCode"),
            )
            setattr(station, MODE_TRANSFORM[mode], True)
            station.save()
