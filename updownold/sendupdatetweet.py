from datetime import datetime

from updownold.utils import (
    get_problem_stations,
    get_problems_dict,
    send_tweet,
)


def get_salutation():
    if datetime.now().hour < 12:
        return "Good morning!"
    elif datetime.now().hour >= 12 and datetime.now().hour < 19:
        return "Good afternoon!"
    elif datetime.now().hour >= 19:
        return "Good evening!"
    else:
        return "Hello!"


if __name__ == "__main__":
    problems = get_problem_stations(get_problems_dict())
    tweets = []

    salutation = get_salutation()

    if len(problems) == 0:
        tweets.append(
            salutation
            + " There are currently no reported step free access issues \
            on the Transport for London network."
        )
    else:
        tweet_string = salutation + " There are step free access issues at: "

        # So see if the tweet is too long
        # Bear in mind we will be adding 'and' between the last two
        # and (1/2) if there is more than one tweet.
        # So a single tweet can be 275, multiple 270 each.
        if len(tweet_string + ", ".join(problems)) < 275:
            tweet_string += ", ".join(problems[0:-1])
            if len(problems) > 1:
                tweet_string += " and "
            tweet_string += problems[-1]
            tweets.append(tweet_string)
        else:
            # Too long, split it up!
            for i, station in enumerate(problems):
                if len(tweet_string + station + " ") > 270:
                    if tweet_string[-2:] == ", ":
                        tweet_string = tweet_string[0:-2] + "..."
                    tweets.append(tweet_string)
                    tweet_string = "... "

                tweet_string += station

                if i == len(problems) - 2:
                    tweet_string += " and "
                elif i < len(problems) - 2:
                    tweet_string += ", "

            if tweet_string:
                tweets.append(tweet_string)

            if len(tweets) > 1:
                for i in range(len(tweets)):
                    tweets[i] = tweets[i] + " (%d/%d)" % (i + 1, len(tweets))

    for tweet in tweets:
        send_tweet(tweet)
