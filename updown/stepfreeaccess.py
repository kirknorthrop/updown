import os
import yaml

from datetime import datetime, timedelta

from updown.utils import (
    get_problems_dict,
    remove_tfl_specifics,
    send_tweet,
    set_problems_dict,
)

from updown.sources import tflapi, trackernet
from updown import sources as scs
from updown.outputs import website, alexa

from updown import settings


# Some "constants" and globals
station_list = None
twitter = None

SOURCE_RELIABILITY_ORDER = ["trackernet", "tflapi"]

DEFAULT_EXCUSE = "There are step free access issues at this station."


def set_problem_for_station(station, problem):

    problems = get_problems_dict()

    problems[station] = problem

    set_problems_dict(problems)

    return True


# Update the problems, delete old ones etc
def update_problems(problems):
    problems_to_remove = []

    for problem in problems.keys():
        if problem and problem[0:1] != "_":

            tweet = None

            if problems[problem].get("new-problem", False) and problem:
                # Longest station name is Cutty Sark for Maritime Greenwich at 34 chars. This leaves 246
                for source in SOURCE_RELIABILITY_ORDER:
                    if (
                        problems[problem].get(source)
                        and problems[problem][source]["text"]
                    ):
                        tweet = problem + ": " + problems[problem][source]["text"]
                        break

                if not tweet or len(tweet) > 280:
                    if problems[problem]["information"]:
                        tweet = "New information on step free access at " + problem
                    elif problem != "null":
                        tweet = "Step free access issues reported at " + problem

                send_tweet(tweet)

            problems[problem]["new-problem"] = False

            if problems[problem]["resolved"]:
                # If it's resolved, see if it's old enough to delete
                if problems[problem]["resolved"] + timedelta(hours=12) < datetime.now():
                    problems_to_remove.append(problem)
                    break

                if problems[problem]["resolved"] > datetime.now() - timedelta(
                    minutes=1
                ):
                    # Work out how long it took them to resolve
                    start_time = problems[problem]["time"]
                    end_time = problems[problem]["resolved"]

                    problems[problem]["time-to-resolve"] = int(
                        (end_time - start_time).seconds
                    )

                    # Longest station name is Cutty Sark for Maritime Greenwich at 34 chars. This leaves 106
                    if problem != "null":
                        tweet = "Step free access has been restored at " + problem
                    send_tweet(tweet)

    for problem in list(set(problems_to_remove)):
        if problem in problems:
            del problems[problem]

    set_problems_dict(problems)


def get_preferred_data(problem):
    text = problem.get("text", None)
    time = problem.get("time", None)
    resolved = problem.get("resolved", None)
    information = problem.get("information", None)
    work_start = problem.get("work_start", None)
    work_end = problem.get("work_end", None)

    resolutions = []
    new_text = None

    for source in SOURCE_RELIABILITY_ORDER:
        if problem.get(source):
            if not new_text:
                new_text = problem[source]["text"]

            if (time is None and problem[source]["time"]) or (
                problem[source]["time"] and problem[source]["time"] < time
            ):
                time = problem[source]["time"]

            if problem[source]["information"] is not None:
                information = problem[source]["information"]

            if (work_start is None and problem[source]["work_start"]) or (
                problem[source]["work_start"]
                and problem[source]["work_start"] < work_start
            ):
                work_start = problem[source]["work_start"]

            if (work_end is None and problem[source]["work_end"]) or (
                problem[source]["work_end"] and problem[source]["work_end"] < work_end
            ):
                work_end = problem[source]["work_end"]

            # Because of persistent problems, we now only mark resolved if all sources agree
            # We gather them here and process them below.
            resolutions.append(problem[source].get("resolved"))

    if all(resolutions):
        # Get the last resolution
        resolved = sorted(resolutions)[-1]
    else:
        resolved = None

    if not resolved:
        text = new_text

    return text, time, resolved, information, work_start, work_end


def check_for_resolved(problems_dict, source_id, source):
    # See if anything is missing from the sources that is in the x
    # problems dict. This is only where they don't have an explicit
    # resolve which is pretty much only Twitter.
    if not getattr(scs, source_id).EXPLICIT_RESOLVE:
        missing_for_source = [x for x in problems_dict.keys() if x not in source.keys()]
        for station in missing_for_source:
            if (
                problems_dict[station].get(source_id)
                and problems_dict[station][source_id].get("resolved") is None
            ):
                problems_dict[station][source_id]["resolved"] = datetime.now()


def update_problems_from_source(source_id, source, problems):
    for station, problem in source.items():
        if station not in problems:
            problems[station] = {
                "resolved": False,
                "time-to-resolve": None,
                "new-problem": True,
            }

        problems[station][source_id] = problem


def update_site():

    problems_dict = get_problems_dict()

    sources = {
        "tflapi": tflapi.check(),
        # 'trackernet': trackernet.check(),
    }

    with open(
        os.path.join(
            settings.UPDATE_FILE_DIR,
            "%s.yaml" % datetime.now().strftime("%Y-%m-%d-%H-%M"),
        ),
        "w",
    ) as f:
        f.write(yaml.dump(sources))

    for source in sources:
        check_for_resolved(problems_dict, source, sources[source])

    # So then let's go through the new problems and add them in.
    for source, problems in sources.items():
        update_problems_from_source(source, problems, problems_dict)

    # Then get the preferred, updated data, and put that at the top level
    for station, problem in problems_dict.items():
        text, time, resolved, information, work_start, work_end = get_preferred_data(
            problem
        )

        problem["text"] = remove_tfl_specifics(text)
        problem["time"] = time
        problem["resolved"] = resolved
        problem["information"] = information
        problem["work_start"] = work_start
        problem["work_end"] = work_end

    # Then we need to see what's been resolved and tweet about it
    update_problems(problems_dict)

    set_problems_dict(problems_dict)

    # Then split them into two dicts
    problems = {}
    resolved = {}
    information = {}

    for problem in problems_dict.keys():
        if problem and problem[0:1] != "_":
            problems_dict[problem]["time"] = problems_dict[problem]["time"].strftime(
                "%H:%M %d %b"
            )
            if problems_dict[problem]["resolved"]:
                problems_dict[problem]["resolved"] = problems_dict[problem][
                    "resolved"
                ].strftime("%H:%M %d %b")

            if problems_dict[problem].get("time-to-resolve"):
                hours = str(problems_dict[problem]["time-to-resolve"] / (60 * 60))
                minutes = str((problems_dict[problem]["time-to-resolve"] / 60) % 60)
                problems_dict[problem]["time-to-resolve"] = hours + ":" + minutes

            if problems_dict[problem]["information"]:
                information[problem] = problems_dict[problem]
            elif (
                problems_dict[problem]["work_start"]
                and problems_dict[problem]["work_start"] < datetime.now()
            ) or (
                problems_dict[problem]["work_end"]
                and problems_dict[problem]["work_end"] > datetime.now()
            ):
                problems[problem] = problems_dict[problem]
            elif problems_dict[problem]["resolved"]:
                resolved[problem] = problems_dict[problem]
            else:
                problems[problem] = problems_dict[problem]

    last_updated = datetime.now()  # get_problems_dict()['_last_updated']

    alexa.generate(problems, resolved, information, last_updated)
    website.generate(problems, resolved, information, last_updated)
