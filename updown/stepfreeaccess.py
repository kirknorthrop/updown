import jsondate as json
import pytz

from pytz import timezone
from datetime import datetime, timedelta

from twython import Twython
from twython.exceptions import TwythonAuthError

from mako.template import Template

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


def set_problem_for_station(station, problem):

    problems = get_problems_dict()

    problems[station] = problem

    set_problems_dict(problems)

    return True

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

    problems = utils.get_problem_stations(problems_dict)

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

    resolutions = []

    for source in SOURCE_RELIABILITY_ORDER:
        if problem.get(source):
            if not text:
                text = problem[source]['text']

            if (time is None and problem[source]['time']) or \
                    (problem[source]['time'] and problem[source]['time'] < time):
                time = problem[source]['time']

            if problem[source]['information'] is not None:
                information = problem[source]['information']

            if (work_start is None and problem[source]['work_start']) or \
                    (problem[source]['work_start'] and problem[source]['work_start'] < work_start):
                work_start = problem[source]['work_start']

            if (work_end is None and problem[source]['work_end']) or \
                    (problem[source]['work_end'] and problem[source]['work_end'] < work_end):
                work_end = problem[source]['work_end']

            # Because of persistent problems, we now only mark resolved if all sources agree
            # We gather them here and process them below.
            resolutions.append(problem[source].get('resolved'))

    if all(resolutions):
        # Get the last resolution
        resolved = sorted(resolutions)[-1]
    else:
        resolved = None

    return text, time, resolved, information, work_start, work_end


def check_for_resolved(problems_dict, source_id, source):
    # See if anything is missing from the sources that is in the x
    # problems dict. This is only where they don't have an explicit
    # resolve which is pretty much only Twitter.
    if not getattr(scs, source_id).EXPLICIT_RESOLVE:
        missing_for_source = [x for x in problems_dict.keys() if x not in source.keys()]
        for station in missing_for_source:
            if problems_dict[station].get(source_id):
                problems_dict[station][source_id]['resolved'] = datetime.now()


def update_problems_from_source(source_id, source, problems):
    for station, problem in source.items():
        if station not in problems:
            problems[station] = {
                'resolved': False,
                'time-to-resolve': None,
                'new-problem': True,
            }

        problems[station][source_id] = problem


def blah():

    problems_dict = get_problems_dict()

    sources = {
        'tflapi': tflapi.check(),
        'trackernet': trackernet.check(),
    }

    for source in sources:
        check_for_resolved(problems_dict, source, sources[source])

    # So then let's go through the new problems and add them in.
    for source, problems in sources.items():
        update_problems_from_source(source, problems, problems_dict)

    # Then get the preferred, updated data, and put that at the top level
    for station, problem in problems_dict.items():
        text, time, resolved, information, work_start, work_end = get_preferred_data(problem)

        problem['text'] = utils.remove_tfl_specifics(text)
        problem['time'] = time
        problem['resolved'] = resolved
        problem['information'] = information
        problem['work_start'] = work_start
        problem['work_end'] = work_end

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
