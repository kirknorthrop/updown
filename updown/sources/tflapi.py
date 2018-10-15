import requests


from datetime import datetime

from updown import settings
from updown.utils import find_station_name, find_dates, fix_additional_info_grammar

EXPLICIT_RESOLVE = False


def check():

    StatusPageURI = 'https://api.tfl.gov.uk/StopPoint/Mode/tube,cable-car,bus,dlr,national-rail,overground,river-bus,tflrail,tram/Disruption?includeRouteBlockedStops=True&app_id=%s&app_key=%s' % (settings.TFL_API_ID, settings.TFL_API_KEY)

    problems = {}

    try:
        r = requests.get(StatusPageURI)

        if r.status_code == 200 and len(r.text) > 0:
            disruption = r.json()

            for issue in disruption:
                # All issues should now be caught with this text
                description = issue['description'].lower().replace('-', ' ')
                if 'step free access is not available' in description or 'there will be no step free access' in description:

                    try:
                        first_colon = issue['description'].find(':')

                        station_name = find_station_name(issue['commonName'])
                        status_details = issue['description'][first_colon + 1:].strip()
                        status_details = status_details.replace('No Step Free Access - ', '')

                        if issue.get('additionalInformation'):
                            additional_info = fix_additional_info_grammar(issue['additionalInformation'])
                            status_details += '<p><i>%s</i></p>' % additional_info

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
                            if ' changes ' not in status_details:
                                if (start_date and start_date < datetime.now()) or (end_date and end_date > datetime.now()):
                                    problems[station_name]['information'] = False

                    except ValueError:
                        pass

    except requests.exceptions.ConnectionError:
        pass

    return problems
