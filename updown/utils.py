import json
import os
import re
import stat

from datetime import datetime
from time import time

import arrow
import requests
import yaml

from twython import Twython

from updown import settings

A_DAY_IN_SECONDS = 60 * 60 * 24

TFL_NAME_CORRECTIONS = {
    "King's Cross": "King's Cross St. Pancras",
    "Cutty Sark": "Cutty Sark for Maritime Greenwich",
    "London Liverpool Street": "Liverpool Street",
}


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
    ]

    for item in to_remove:
        station_name = station_name.replace(item, "")

    # Kensington (Olympia) is the only station with parentheses in its name on the tube map.
    if station_name == "Kensington Olympia":
        station_name = "Kensington (Olympia)"

    return station_name.strip()


# Getter and Creator for Station List
def create_station_list():
    # TODO: Save this and replace once a day

    modes = ["tube", "dlr", "overground", "tflrail", "elizabeth-line"]

    station_status_URI = "https://api.tfl.gov.uk/StopPoint/Mode/%s?app_id=%s&app_key=%s"

    stations = []

    for mode in modes:
        url = station_status_URI % (mode, settings.TFL_API_ID, settings.TFL_API_KEY)

        r = requests.get(url)

        for station in r.json().get("stopPoints", []):
            stations.append(cleanup_station_name(station["commonName"]))

        stations = list(reversed(sorted(set(stations), key=len)))

        with open("stations.yaml", "w") as f:
            f.write(yaml.dump(stations))

    return stations


def get_station_list():

    if os.path.isfile("stations.yaml"):
        stations_file_time = os.stat("stations.yaml")[stat.ST_MTIME]

        if (int(time()) - stations_file_time) < A_DAY_IN_SECONDS:
            with open("stations.yaml") as f:
                return yaml.safe_load(f.read())

    return create_station_list()


def find_station_name(possible_name):

    clean_station_name = cleanup_station_name(possible_name).lower()

    # Correlate a name from a tweet/trackernet with one we expect to find
    for station_name in get_station_list():
        if station_name.lower() in clean_station_name:
            return station_name

    # If we don't find it in the proper list, we have to look in our corrections list
    for station_name in TFL_NAME_CORRECTIONS.keys():
        if station_name.lower() in clean_station_name:
            return TFL_NAME_CORRECTIONS[station_name]

    print(possible_name, "not found")
    return clean_station_name


def remove_tfl_specifics(text):
    # We always reset this just in case there is an update
    text = re.sub("(Please )?[Cc]all.*0[38]43 ?222 ?1234.*journey\.?", "", text)
    text = re.sub("we ", "TfL ", text, re.IGNORECASE)
    text = re.sub("member of staff", "member of TfL staff", text, re.IGNORECASE)
    text = re.sub(
        "Call our Travel Information Centre on 0343 222 1234 if you need more help\.?",
        "",
        text,
        re.IGNORECASE,
    )
    text = re.sub(
        "Call our Travel Information Centre on 0343 222 1234 for further help\.?",
        "",
        text,
        re.IGNORECASE,
    )
    text = re.sub(
        "Call our Travel Information Centre on 0343 222 1234 for help planning your journey\.?",
        "",
        text,
        re.IGNORECASE,
    )
    text = re.sub(
        "Call us on 0343 222 1234 if you need more help\.?", "", text, re.IGNORECASE
    )
    text = re.sub("Call 0343 222 1234 for further help\.?", "", text, re.IGNORECASE)

    return text


def fix_additional_info_grammar(text):
    # It appears that full stops and spaces aren't always used...
    text = re.sub(r"\.([A-Z<])", r". \1", text)
    text = re.sub(r"[^ \.](Please allow extra time for your journey.)", r". \1", text)

    return text


def parse_date(text):
    possible_formats = ["D MMMM YYYY", "D MMMM", "MMMM YYYY", "MMMM"]

    try:
        date_ = arrow.get(text, possible_formats)
        if "early" in text:
            date_ = date_.replace(day=10)
        if "mid" in text:
            date_ = date_.replace(day=20)
        if "late" in text:
            date_ = date_.ceil("month")

        if date_.year == 1:
            date_ = date_.replace(year=arrow.utcnow().year)

        date_ = date_.naive

    except:
        date_ = None

    return date_


def find_dates(text):
    start_and_end = re.search("From (.*?) until (.*?)(,|there|due)", text, flags=re.I)

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
        if problem and problem[0:1] != "_":
            if (
                not problems_dict[problem]["resolved"]
                and not problems_dict[problem]["information"]
            ):
                problems.append(problem)

    return sorted(problems)


def send_tweet(tweet_text):
    """Send a tweet"""
    if settings.PRODUCTION:
        try:
            twitter = Twython(
                settings.TWITTER_KEY,
                settings.TWITTER_SECRET,
                settings.TUBELIFTS_OAUTH_TOKEN,
                settings.TUBELIFTS_OAUTH_TOKEN_SECRET,
            )

            twitter.update_status(status=remove_tfl_specifics(tweet_text))
        # Except everything. TODO: Look into some of twitters annoying foibles
        except:
            pass
    else:
        print("Should have tweeted: " + tweet_text)


def get_problems_dict():
    try:
        with open(settings.TEMPLATE_FILE_LOCATION + "problems.yaml", "r") as f:
            problems_dict = yaml.safe_load(f.read())
            if "_last_updated" in problems_dict:
                del problems_dict["_last_updated"]
    except IOError:
        with open(settings.TEMPLATE_FILE_LOCATION + "problems.yaml", "w") as f:
            problems_dict = {}
            f.write(yaml.dump(problems_dict))

    return problems_dict


def set_problems_dict(problems):

    problems["_last_updated"] = datetime.now()

    with open(settings.TEMPLATE_FILE_LOCATION + "problems.yaml", "w") as f:
        f.write(yaml.dump(problems))

    return True
