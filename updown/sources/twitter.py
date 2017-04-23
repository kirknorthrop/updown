import settings
from twython import Twython

EXPLICIT_RESOLVE = True

from twython.exceptions import TwythonAuthError
import os

###########################################
# Lots of currently unused Twitter stuff. #
###########################################

def get_twitter_access_token(regenerate=False):

    TOKEN_FILE_LOCATION = settings.TEMPLATE_FILE_LOCATION + 'twitter_access_token'

    if not regenerate and os.path.isfile(TOKEN_FILE_LOCATION):
        with open(TOKEN_FILE_LOCATION, 'r') as f:
            token = f.read()
    else:
        twitter = Twython(settings.TWITTER_KEY, settings.TWITTER_SECRET, oauth_version=2)
        token = twitter.obtain_access_token()

        with open(TOKEN_FILE_LOCATION, 'w') as f:
            f.write(token)

    return token


def get_twitter():

    try:
        twitter = Twython(settings.TWITTER_KEY, access_token=get_twitter_access_token())
        twitter.get_user_timeline(screen_name='TfL')
    except TwythonAuthError:
        twitter = Twython(settings.TWITTER_KEY, access_token=get_twitter_access_token(True))

    return twitter

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


# Get a twitter object
def get_twitter():

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


# Convert the odd time that comes from twython to a sensible one
def convert_tweet_time(time):
    # Format: Fri Sep 13 15:23:01 +0000 2013 - python seems to dislike %z so we're using +0000
    naive_tweet_time = datetime.strptime(time, '%a %b %d %H:%M:%S +0000 %Y')
    utc_tweet_time = pytz.utc.localize(naive_tweet_time)
    return utc_tweet_time.astimezone(timezone('Europe/London'))


# Getter, Setter, Creator and Saver for twitter accounts and last statuses
def get_twitter_last_statuses():

    if twitter_last_statuses is None:
        try:
            with open(settings.TEMPLATE_FILE_LOCATION + 'twitter_laststatuses.json', 'r') as f:
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

    twitter_last_statuses = last_statuses
    with open(settings.TEMPLATE_FILE_LOCATION + 'twitter_laststatuses.json', 'w') as f:
        f.write(json.dumps(last_statuses))

    return True


# Do everything we need to check twitter
def check_twitter():

    h = HTMLParser.HTMLParser()

    twitter = get_twitter()

    for account in get_twitter_last_statuses().keys():
        user_timeline = twitter.get_user_timeline(screen_name=account, since_id=get_twitter_last_statuses()[account])

        for tweet in user_timeline:
            tweet_text = h.unescape(tweet['text'])

            if 'no step free access' in tweet_text.lower():
                station_name = find_station_name(h.unescape(tweet_text))
                if station_name:
                    problem = get_problem_for_station(global_problems, station_name)

                    problem['twitter-id'] = tweet['id']
                    problem['twitter-text'] = tweet['text']
                    problem['twitter-time'] = convert_tweet_time(tweet['created_at']).isoformat()
                    problem['twitter-resolved'] = None

                    if problem.get('new-problem', False):
                        # Longest station name is Cutty Sark for Maritime Greenwich at 34 chars. This leaves 106
                        tweet = 'No step free access reported at ' + station_name
                        send_tweet(tweet)

                    problem['new-problem'] = False

                    set_problem_for_station(station_name, problem)

            elif 'step free access' in tweet_text.lower() and 'restored' in tweet_text.lower():
                station_name = find_station_name(h.unescape(tweet_text))

                problem = get_problem_for_station(global_problems, station_name)

                problem['twitter-resolved'] = convert_tweet_time(tweet['created_at']).isoformat()

                set_problem_for_station(station_name, problem)

        if len(user_timeline):
            last_statuses = get_twitter_last_statuses()

            last_statuses[account] = user_timeline[0]['id']

            set_twitter_last_statuses(last_statuses)

    # And update the last time we saw twitter
    problems = get_problems_dict()
    problems['_twitter_update'] = datetime.now().isoformat()
    set_problems_dict(problems)
