EXPLICIT_RESOLVE = True

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
