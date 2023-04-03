import re

import arrow

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
    text = re.sub(
        "Call 0343 222 1234 if you need further help\.?", "", text, re.IGNORECASE
    )

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


def fix_additional_info_grammar(text):
    # It appears that full stops and spaces aren't always used...
    text = re.sub(r"\.([A-Z<])", r". \1", text)
    text = re.sub(r"[^ \.](Please allow extra time for your journey.)", r". \1", text)

    return text
