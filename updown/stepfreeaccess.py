# import requests

# import HTMLParser
import jsondate as json
import pytz
import re

from copy import deepcopy
from pytz import timezone
from datetime import datetime, timedelta

from twython import Twython
from twython.exceptions import TwythonAuthError

from mako.template import Template

# from bs4 import BeautifulSoup

from updown import sources as scs
from sources import tflapi, trackernet
import settings
import utils

# Some "constants" and globals
APP_KEY = settings.app_key
APP_SECRET = settings.app_secret

access_token = None
twitter_last_statuses = None
station_list = None
problems_dict = None
twitter = None

SOURCE_RELIABILITY_ORDER = ['trackernet', 'tflapi', 'twitter']

DEFAULT_EXCUSE = 'There are step free access issues at this station.'


# Getter, Setter, Creator and Saver for twitter accounts and last statuses
def get_twitter_last_statuses():

    global twitter_last_statuses

    if twitter_last_statuses is None:
        try:
            with open(settings.template_file_location + 'twitter_laststatuses.json', 'r') as f:
                twitter_last_statuses = json.loads(f.read())
        except IOError:
            twitter_last_statuses = {
                'bakerlooline': 1,
                'centralline': 1,
                'circleline': 1,
                'districtline': 1,
                'hamandcityline': 1,
                'jubileeline': 1,
                'metline': 1,
                'northernline': 1,
                'piccadillyline': 1,
                'victorialine': 1,
                'wlooandcityline': 1,
                'LondonDLR': 1,
                'LDNOverground': 1,
            }

    return twitter_last_statuses


def set_twitter_last_statuses(last_statuses):

    global twitter_last_statuses

    twitter_last_statuses = last_statuses
    with open(settings.template_file_location + 'twitter_laststatuses.json', 'w') as f:
        f.write(json.dumps(last_statuses))

    return True


# Getter and Creator for twitter Access Token
def create_twitter_access_token():

    twitter = Twython(APP_KEY, APP_SECRET, oauth_version=2)
    token = twitter.obtain_access_token()

    with open(settings.template_file_location + 'twitter_access_token', 'w') as f:
        f.write(token)

    return token


def get_twitter_access_token():

    global access_token

    if access_token is None:
        try:
            with open(settings.template_file_location + 'twitter_access_token', 'r') as f:
                access_token = f.read()
        except IOError:
            access_token = create_twitter_access_token()

    return access_token


# Getter, Setter and Creator and Saver for Problems file
def create_problems_dict():

    blank_problems_dict = {
        # '_last_updated': datetime.now().isoformat(),
        # '_twitter_update': '2000-01-01T00:00:00.000000',
        # '_trackernet_update': '2000-01-01T00:00:00.000000',
        # '_tflwebsite_update': '2000-01-01T00:00:00.000000'
    }

    with open(settings.template_file_location + 'problems.json', 'w') as f:
        f.write(json.dumps(blank_problems_dict))

    return blank_problems_dict


def get_problems_dict():

    global problems_dict

    if problems_dict is None:
        try:
            with open(settings.template_file_location + 'problems.json', 'r') as f:
                problems_dict = json.loads(f.read())
                if '_last_updated' in problems_dict:
                    del problems_dict['_last_updated']
        except IOError:
            problems_dict = create_problems_dict()

    return problems_dict


def set_problems_dict(problems):

    global problems_dict

    problems['_last_updated'] = datetime.now()

    problems_dict = problems

    save_problems_dict()

    return True


def save_problems_dict():

    with open(settings.template_file_location + 'problems.json', 'w') as f:
        f.write(json.dumps(get_problems_dict()))

    return True


# Getter and Setter for problems at a station
def get_problem_for_station(problems, station):

    # problems = get_problems_dict()

    if problems.get(station, None) is not None:
        # Then we already have a problem at this station
        return problems[station]

    else:
        # Send a blank problem
        return {
            'sources': {
            },
            'resolved': False,
            'time-to-resolve': None,
            'new-problem': True,
        }


def set_problem_for_station(station, problem):

    problems = get_problems_dict()

    problems[station] = problem

    set_problems_dict(problems)

    return True


# Convert the odd time that comes from twython to a sensible one
def convert_tweet_time(time):
    # Format: Fri Sep 13 15:23:01 +0000 2013 - python seems to dislike %z so we're using +0000
    naive_tweet_time = datetime.strptime(time, '%a %b %d %H:%M:%S +0000 %Y')
    utc_tweet_time = pytz.utc.localize(naive_tweet_time)
    return utc_tweet_time.astimezone(timezone('Europe/London'))


# Get a twitter object
def get_twitter():

    global twitter

    if twitter is None:
        try:
            twitter = Twython(APP_KEY, access_token=get_twitter_access_token())
            twitter.get_user_timeline(screen_name='TFLOfficial')
        except TwythonAuthError:
            twitter = Twython(APP_KEY, access_token=create_twitter_access_token())

    return twitter


# Do we need to update twitter again yet?
def twitter_needs_update():

    last_twitter = datetime.strptime(get_problems_dict()['_twitter_update'], '%Y-%m-%dT%H:%M:%S')

    return last_twitter + timedelta(minutes=2) < datetime.now()


# Send a tweet
def send_tweet(tweet_text):
    if settings.production:
        try:
            twitter_sending = Twython(settings.app_key, settings.app_secret, settings.tubelifts_oauth_token, settings.tubelifts_oauth_token_secret)

            twitter_sending.update_status(status=tweet_text)
        # Except everything. TODO: Look into some of twitters annoying foibles
        except:
            pass
    else:
        print "Should have tweeted: " + tweet_text


# Update the problems, delete old ones etc
def update_problems():
    problems = get_problems_dict()

    problems_to_remove = []

    for problem in problems.keys():
        if problem and problem[0:1] != '_':

            tweet = None

            if problems[problem].get('new-problem', False) and problem:
                # Longest station name is Cutty Sark for Maritime Greenwich at 34 chars. This leaves 106
                for source in SOURCE_RELIABILITY_ORDER:
                    if problems[problem].get(source) and problems[problem][source]['text']:
                        tweet = problem + ': ' + problems[problem][source]['text']
                        break

                if not tweet or len(tweet) > 140:
                    if problems[problem]['information']:
                        tweet = 'New information on step free access at ' + problem
                    else:
                        tweet = 'Step free access issues reported at ' + problem

                send_tweet(tweet)

            problems[problem]['new-problem'] = False

            if problems[problem]['resolved']:
                # If it's resolved, see if it's old enough to delete
                if problems[problem]['resolved'] + timedelta(hours=12) < datetime.now():
                    problems_to_remove.append(problem)
                    break

                # Work out how long it took them to resolve
                start_time = problems[problem]['time']
                end_time = problems[problem]['resolved']

                problems[problem]['time-to-resolve'] = int((end_time - start_time).seconds)

                # Longest station name is Cutty Sark for Maritime Greenwich at 34 chars. This leaves 106
                tweet = 'Step free access has been restored at ' + problem
                send_tweet(tweet)

                # # If is was something that was only put on twitter and never resolved - time out after 6 hours
                # elif problems[problem]['twitter']['time'] and problems[problem]['trackernet']['time'] is None and problems[problem]['trackernet']['resolved'] is None and problems[problem]['twitter']['resolved'] is None:
                #     twitter_time = datetime.strptime(problems[problem]['twitter']['time'][0:19], '%Y-%m-%dT%H:%M:%S')

                #     if twitter_time + timedelta(hours=6) < datetime.now():
                #         problems[problem]['trackernet']['resolved'] = datetime.now().isoformat()
                #         problems[problem]['trackernet']['text'] = "This issue was mentioned on Twitter but never resolved. Therefore we have marked it as resolved after 6 hours."
                #         problems[problem]['resolved'] = True

                #         # Longest station name is Cutty Sark for Maritime Greenwich at 34 chars. This leaves 106
                #         tweet = 'There is no further news on step free access at ' + problem
                #         send_tweet(tweet)

    for problem in list(set(problems_to_remove)):
        if problem in problems:
            del(problems[problem])

    set_problems_dict(problems)


def publish_alexa_file(problems_dict):

    problems = []

    for problem in problems_dict:
        if problem and problem[0:1] != '_':
            if not problems_dict[problem]['resolved'] and \
                    not problems_dict[problem]['information']:
                problems.append(problem)

    if len(problems) == 0:
        tweet_string = "There are currently no reported step free access issues on the Transport for London network."
    else:
        tweet_string = "There are step free access issues at: "
        tweet_string += ', '.join(problems[0:-1])
        if len(problems) > 1:
            tweet_string += ' and '
        tweet_string += problems[-1]

    with open(settings.output_file_location + 'problems.txt', 'w') as f:
        f.write(tweet_string)


def get_preferred_data(problem):
    text = problem.get('text', None)
    time = problem.get('time', None)
    resolved = problem.get('resolved', None)
    information = problem.get('information', None)
    work_start = problem.get('work_start', None)
    work_end = problem.get('work_end', None)

    for source in SOURCE_RELIABILITY_ORDER:
        if problem.get(source):
            if not text:
                text = problem[source]['text']

            if (time is None and problem[source]['time']) or \
                    (problem[source]['time'] and problem[source]['time'] < time):
                time = problem[source]['time']

            if (not resolved and problem[source]['resolved']) or \
                    (problem[source]['resolved'] and problem[source]['resolved'] < resolved):
                resolved = problem[source]['resolved']

            if problem[source]['information'] is not None:
                information = problem[source]['information']

            if (work_start is None and problem[source]['work_start']) or \
                    (problem[source]['work_start'] and problem[source]['work_start'] < work_start):
                work_start = problem[source]['work_start']

            if (work_end is None and problem[source]['work_end']) or \
                    (problem[source]['work_end'] and problem[source]['work_end'] < work_end):
                work_end = problem[source]['work_end']

    return text, time, resolved, information, work_start, work_end


def blah():

    problems_dict = get_problems_dict()

    sources = {
        'tflapi': tflapi.check(),
        'trackernet': trackernet.check(),
    }

    # See if anything is missing from the sources that is in the x
    # problems dictThis is only where they don't have an explicit
    # resolve which is pretty much only Twitter.
    for source in sources.keys():
        if not getattr(scs, source).EXPLICIT_RESOLVE:
            missing_for_source = [x for x in problems_dict.keys() if x not in sources[source].keys()]
            for station in missing_for_source:
                if problems_dict[station].get(source):
                    problems_dict[station][source]['resolved'] = datetime.now()

    # So then let's go through the new problems and add them in.
    for source, problems in sources.items():
        for station, problem in problems.items():
            if station not in problems_dict:
                problems_dict[station] = get_problem_for_station(problems_dict, station)

            problems_dict[station][source] = problem

    # Then get the preferred, updated data, and put that at the top level
    for station, problem in problems_dict.items():
        text, time, resolved, information, work_start, work_end = get_preferred_data(problem)

        problem['text'] = utils.remove_tfl_specifics(text)
        problem['time'] = time
        problem['resolved'] = resolved
        problem['information'] = information
        problem['work_start'] = work_start
        problem['work_end'] = work_end

    #

    # Then we need to see what's been resolved and tweet about it
    update_problems()

    set_problems_dict(problems_dict)

    # save_problems_dict()

    # # Publish service JSONs
    # # # #publish_android_json(get_problems_dict())
    publish_alexa_file(problems_dict)

    # Then split them into two dicts
    problems = {}
    resolved = {}
    information = {}

    for problem in problems_dict.keys():
        if problem and problem[0:1] != '_':
            # print problem, problems_dict[problem], type(problems_dict[problem]['time']), problems_dict[problem]['time']
            problems_dict[problem]['time'] = problems_dict[problem]['time'].strftime('%H:%M %d %b')
            if problems_dict[problem]['resolved']:
                problems_dict[problem]['resolved'] = problems_dict[problem]['resolved'].strftime('%H:%M %d %b')

            if problems_dict[problem].get('time-to-resolve'):
                hours = str(problems_dict[problem]['time-to-resolve'] / (60 * 60))
                minutes = str((problems_dict[problem]['time-to-resolve'] / 60) % 60)
                problems_dict[problem]['time-to-resolve'] = hours + ":" + minutes

            if (problems_dict[problem]['work_start'] and problems_dict[problem]['work_start'] < datetime.now()) or (problems_dict[problem]['work_end'] and problems_dict[problem]['work_end'] > datetime.now()):
                problems[problem] = problems_dict[problem]
            elif problems_dict[problem]['information']:
                information[problem] = problems_dict[problem]
            elif problems_dict[problem]['resolved']:
                resolved[problem] = problems_dict[problem]
            else:
                problems[problem] = problems_dict[problem]

    # Then create the HTML file.
    mytemplate = Template(filename=settings.template_file_location + 'index.tmpl')
    rendered_page = mytemplate.render(problems=problems, problems_sort=sorted(problems), resolved=resolved, resolved_sort=sorted(resolved), information=information, information_sort=sorted(information), last_updated=get_problems_dict()['_last_updated'].strftime('%H:%M %d %b'), production=settings.production)

    with open(settings.output_file_location + 'index.html', 'w') as f:
        f.write(rendered_page)
