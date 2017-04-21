import requests

from datetime import datetime

from updown import settings
from updown.utils import find_station_name, find_dates

EXPLICIT_RESOLVE = False


def check():

    StatusPageURI = 'https://api.tfl.gov.uk/StopPoint/Mode/tube,cable-car,bus,dlr,national-rail,overground,river-bus,tflrail,tram/Disruption?includeRouteBlockedStops=True&app_id=%s&app_key=%s' % (settings.tfl_api_id, settings.tfl_api_key)

    problems = {}

    try:
        r = requests.get(StatusPageURI)

        if r.status_code == 200 and len(r.text) > 0:
            disruption = r.json()

            for issue in disruption:
                if 'step free' in issue['description'].lower() or \
                        'step-free' in issue['description'].lower() or \
                        'no lift service' in issue['description'].lower():

                    try:
                        first_colon = issue['description'].index(':')

                        station_name = find_station_name(issue['commonName'])
                        status_details = issue['description'][first_colon + 1:].strip()
                        status_details = status_details.replace('No Step Free Access - ', '')

                        problems[station_name] = {
                            'text': status_details,
                            'time': datetime.now(),
                            'resolved': None,
                            'information': issue['appearance'] != 'RealTime',
                            'work_start': None,
                            'work_end': None,
                        }

                        if issue['appearance'] == 'PlannedWork':
                            start_date, end_date = find_dates(status_details)
                            problems[station_name]['work_start'] = start_date
                            problems[station_name]['work_end'] = end_date

                            if (start_date and start_date < datetime.now()) or (end_date and end_date > datetime.now()):
                                problems[station_name]['information'] = False

                    except ValueError:
                        pass

    except requests.exceptions.ConnectionError:
        pass

    return problems