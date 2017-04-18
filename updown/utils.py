import re

import arrow
import requests

from bs4 import BeautifulSoup


TFL_NAME_CORRECTIONS = {
    'King\'s Cross': 'King\'s Cross St. Pancras',
    'Cutty Sark': 'Cutty Sark for Maritime Greenwich'
}


# Getter and Creator for Station List
def create_station_list():
    # TODO: Save this and replace once a day
    station_status_URI = "http://cloud.tfl.gov.uk/TrackerNet/StationStatus"

    r = requests.get(station_status_URI)
    xml = r.text
    # CHECK RESPONSE CODE 200!
    soup = BeautifulSoup(xml)

    return list(reversed(sorted([station['name'] for station in soup.find_all('station')], key=len)))


def get_station_list():

    station_list = create_station_list()

    return station_list


def find_station_name(possible_name):

    # Correlate a name from a tweet/trackernet with one we expect to find

    for station_name in get_station_list():
        if station_name.lower() in possible_name.lower():
            return station_name

    # If we don't find it in the proper list, we have to look in our corrections list
    for station_name in TFL_NAME_CORRECTIONS.keys():
        if station_name.lower() in possible_name.lower():
            return TFL_NAME_CORRECTIONS[station_name]

    print station_name, 'not found'


def remove_tfl_specifics(text):
    # We always reset this just in case there is an update
    text = re.sub('(Please )?[Cc]all.*0[38]43 ?222 ?1234.*journey\.?', '', text)
    text = re.sub('we ', 'TfL ', text, re.IGNORECASE)
    text = re.sub('member of staff', 'member of TfL staff', text, re.IGNORECASE)

    return text


def parse_date(text):
    possible_formats = [
        'D MMMM YYYY', 'D MMMM', 'MMMM YYYY', 'MMMM'
    ]

    try:
        date_ = arrow.get(text, possible_formats)
        if 'early' in text:
            date_ = date_.replace(day=10)
        if 'mid' in text:
            date_ = date_.replace(day=20)
        if 'late' in text:
            date_ = date_.ceil('month')

        if date_.year == 1:
            date_ = date_.replace(year=arrow.utcnow().year)

        date_ = date_.naive

    except:
        date_ = None

    return date_


def find_dates(text):
    start_and_end = re.search('From (.*?) until (.*?)(,|there|due)', text, flags=re.I)

    start_date = None
    end_date = None

    if start_and_end:
        start_date = parse_date(start_and_end.groups()[0])
        end_date = parse_date(start_and_end.groups()[1])

        while start_date and end_date and end_date < start_date:
            start_date = start_date.replace(year=start_date.year - 1)

    return start_date, end_date


def get_problem_stations(problems_dict):
    problems = []

    for problem in problems_dict:
        if problem and problem[0:1] != '_':
            if not problems_dict[problem]['resolved'] and \
                    not problems_dict[problem]['information']:
                problems.append(problem)

    return sorted(problems)
