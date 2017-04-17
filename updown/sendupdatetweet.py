import jsondate as json
import re
import string

from pytz import timezone
from datetime import datetime, timedelta

from twython import Twython
from twython.exceptions import TwythonAuthError

import settings

# Some "constants" and globals
APP_KEY = settings.app_key
APP_SECRET = settings.app_secret

access_token = None
problems_dict = None
twitter = None


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

    blank_problems_dict = {'_last_updated' : datetime.now().isoformat(), '_twitter_update' : '2000-01-01T00:00:00.000000', '_trackernet_update' : '2000-01-01T00:00:00.000000'}

    with open(settings.template_file_location + 'problems.json', 'w') as f:
        f.write(json.dumps(blank_problems_dict))

    return blank_problems_dict


def get_problems_dict():

    global problems_dict

    if problems_dict is None:
        try:
            with open(settings.template_file_location + 'problems.json', 'r') as f:
                problems_dict = json.loads(f.read())
        except IOError:
            problems_dict = create_problems_dict()

    return problems_dict


# Get a twitter object
def get_twitter():

    global twitter

    if twitter is None:
        try:
            twitter = Twython(APP_KEY, access_token = get_twitter_access_token())
            twitter.get_user_timeline(screen_name='TFLOfficial')
        except TwythonAuthError:
            twitter = Twython(APP_KEY, access_token = create_twitter_access_token())

    return twitter


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


def get_salutation():

    if datetime.now().hour < 12:
        return "Good morning!"
    elif datetime.now().hour >= 12 and datetime.now().hour < 19:
        return "Good afternoon!"
    elif datetime.now().hour >= 19:
        return "Good evening!"
    else:
        return "Hello!"


if __name__ == '__main__':

    problems = []
    tweets = []

    for problem in get_problems_dict().keys():
        if problem[0:1] != '_':
            if not get_problems_dict()[problem]['resolved'] and \
                    not get_problems_dict()[problem]['information']:
                problems.append(problem)

    problems = sorted(problems)

    salutation = get_salutation()

    if len(problems) == 0:
        tweets.append(salutation + ' There are currently no reported step free access issues on the Transport for London network.')
    else:
        tweet_string = salutation + ' There are step free access issues at: '

        # So see if the tweet is too long
        # Bear in mind we will be adding 'and' between the last two
        # and (1/2) if there is more than one tweet.
        # So a single tweet can be 135, multiple 130 each.
        if len(tweet_string + ', '.join(problems)) < 135:
            tweet_string += ', '.join(problems[0:-1])
            if len(problems) > 1:
                tweet_string += ' and '
            tweet_string += problems[-1]
            tweets.append(tweet_string)
        else:
            # Too long, split it up!
            for i, station in enumerate(problems):
                if len(tweet_string + station + ' ') > 130:
                    if tweet_string[-2:] == ', ':
                        tweet_string = tweet_string[0:-2] + '...'
                    tweets.append(tweet_string)
                    tweet_string = '... '

                tweet_string += station

                if i == len(problems) - 2:
                    tweet_string += ' and '
                elif i < len(problems) - 2:
                    tweet_string += ', '

            if tweet_string:
                tweets.append(tweet_string)

            if len(tweets) > 1:
                for i in range(len(tweets)):
                    tweets[i] = tweets[i] + " (%d/%d)" % (i + 1, len(tweets))

    for tweet in tweets:
        send_tweet(tweet)
