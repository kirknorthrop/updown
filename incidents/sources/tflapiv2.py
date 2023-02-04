from datetime import datetime

import requests
from django.conf import settings
from incidents.models import Report
from stations.utils import find_station

from stations.utils import find_station_from_naptan

EXPLICIT_RESOLVE = False


def check():
    StatusPageURI = f"https://api.tfl.gov.uk/Disruptions/Lifts/v2?app_id={settings.TFL_API_ID}&app_key={settings.TFL_API_KEY}"

    try:
        r = requests.get(StatusPageURI)

        if r.status_code == 200 and len(r.text) > 0:
            disruption = r.json()

            for issue in disruption:
                try:
                    station = find_station_from_naptan(issue["stationUniqueId"])

                    first_colon = issue["message"].find(":")
                    status_details = issue["message"][first_colon + 1 :].strip()
                    status_details = status_details.replace(
                        "No Step Free Access - ", ""
                    )

                    report, created = Report.objects.get_or_create(
                        station=station,
                        text=status_details,
                        source=Report.SOURCE_TFLAPI_V2,
                        information=False,
                    )

                except ValueError:
                    pass

    except requests.exceptions.ConnectionError:
        pass
