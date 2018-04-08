import requests

from bs4 import BeautifulSoup
from datetime import datetime

from updown.utils import find_station_name

EXPLICIT_RESOLVE = False


# Do everything we need to check trackernet
def check():

    StationIncidentsURI = "http://cloud.tfl.gov.uk/TrackerNet/StationStatus/IncidentsOnly"

    problems = {}

    try:
        r = requests.get(StationIncidentsURI)
        xml = r.text

        if r.status_code == 200 and len(xml) > 0:
            soup = BeautifulSoup(xml)

            for station in soup.find_all('stationstatus'):
                if station.status['id'] == 'NS':
                    print('**%s**' % station.station['name'])
                    station_name = find_station_name(station.station['name'])

                    problems[station_name] = {
                        'text': station['statusdetails'],
                        'time': datetime.now(),
                        'resolved': None,
                        'information': False,
                        'work_start': None,
                        'work_end': None,
                    }

    except requests.exceptions.ConnectionError:
        pass

    return problems
