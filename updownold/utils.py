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

from updownold import settings

A_DAY_IN_SECONDS = 60 * 60 * 24

TFL_NAME_CORRECTIONS = {
    "King's Cross": "King's Cross St. Pancras",
    "Cutty Sark": "Cutty Sark for Maritime Greenwich",
    "London Liverpool Street": "Liverpool Street",
}







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
