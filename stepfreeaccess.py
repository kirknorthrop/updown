import requests

import HTMLParser
import json
import pytz
import re

from pytz import timezone
from datetime import datetime, timedelta

from twython import Twython
from twython.exceptions import TwythonAuthError

from mako.template import Template

from bs4 import BeautifulSoup

import settings

# Some "constants" and globals
APP_KEY = settings.app_key
APP_SECRET = settings.app_secret

TFL_NAME_CORRECTIONS = {'King\'s Cross' : 'King\'s Cross St. Pancras'}

access_token = None
twitter_last_statuses = None
station_list = None
problems_dict = None
twitter = None


# Getter, Setter, Creator and Saver for twitter accounts and last statuses
def create_twitter_last_statuses():

	twitter_laststatuses = {
		'bakerlooline' : 1,
		'centralline' : 1,
		'circleline' : 1,
		'districtline' : 1,
		'hamandcityline' : 1,
		'jubileeline' : 1,
		'metline' : 1,
		'northernline' : 1,
		'piccadillyline' : 1,
		'victorialine' : 1,
		'wlooandcityline': 1,
		'LondonDLR' : 1,
		'LDNOverground' : 1,
	}

	with open(settings.template_file_location + 'twitter_laststatuses.json', 'w') as f:
		f.write(json.dumps(twitter_laststatuses))

	return twitter_laststatuses

def get_twitter_last_statuses():
	
	global twitter_last_statuses

	if twitter_last_statuses is None:
		try:
			with open(settings.template_file_location + 'twitter_laststatuses.json', 'r') as f:
				twitter_last_statuses = json.loads(f.read())
		except IOError:
			twitter_last_statuses = create_twitter_last_statuses()

	return twitter_last_statuses

def set_twitter_last_statuses(last_statuses):

	global twitter_last_statuses

	twitter_last_statuses = last_statuses

	return True

def save_twitter_last_statuses():
	
	with open(settings.template_file_location + 'twitter_laststatuses.json', 'w') as f:
		f.write(json.dumps(get_twitter_last_statuses()))

	return True


# Getter and Creator for twitter Access Token
def create_twitter_access_token():

	twitter = Twython(APP_KEY, APP_SECRET, oauth_version = 2)
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


# Getter and Creator for Station List
def create_station_list():
	# TODO: Save this and replace once a day
	StationStatusURI = "http://cloud.tfl.gov.uk/TrackerNet/StationStatus"

	r = requests.get(StationStatusURI)
	xml = r.text
	# CHECK RESPONSE CODE 200!
	soup = BeautifulSoup(xml)

	return [station['name'] for station in soup.find_all('station')]


def get_station_list():

	global station_list

	if station_list is None:
		station_list = create_station_list()

	return station_list


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

def set_problems_dict(problems):

	global problems_dict

	problems['_last_updated'] = datetime.now().isoformat()

	problems_dict = problems

	return True

def save_problems_dict():
	
	with open(settings.template_file_location + 'problems.json', 'w') as f:
		f.write(json.dumps(get_problems_dict()))

	return True


# Getter and Setter for problems at a station
def get_problem_for_station(station):

	problems = get_problems_dict()

	if problems.get(station, None) is not None:
		# Then we already have a problem at this station
		return problems[station]

	else:
		# Send a blank problem
		return {
			'trackernet-text' : None,
			'trackernet-time' : None,
			'trackernet-resolved' : None,
			'twitter-id' : None,
			'twitter-text' : None,
			'twitter-time' : None,
			'twitter-resolved' : None,
			'resolved' : False,
			'time-to-resolve' : None,
			'new-problem': True,
		}

def set_problem_for_station(station, problem):

	problems = get_problems_dict()

	problems[station] = problem

	set_problems_dict(problems)

	return True


# Correlate a name from a tweet/trackernet with one we expect to find
def find_station_name(possible_name):
	
	for station_name in get_station_list():
		if station_name in possible_name:
			return station_name

	# If we don't find it in the proper list, we have to look in our corrections list
	for station_name in TFL_NAME_CORRECTIONS.keys():
		if station_name in possible_name:
			return TFL_NAME_CORRECTIONS[station_name]
	

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
		 	twitter = Twython(APP_KEY, access_token = get_twitter_access_token())
		 	twitter.get_user_timeline(screen_name='TFLOfficial')
		except TwythonAuthError:
		 	twitter = Twython(APP_KEY, access_token = create_twitter_access_token())

	return twitter


# Do we need to update twitter again yet?
def twitter_needs_update():

	last_twitter = datetime.strptime(get_problems_dict()['_twitter_update'], '%Y-%m-%dT%H:%M:%S.%f')

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




# Do everything we need to check trackernet
def check_trackernet():

	StationIncidentsURI = "http://cloud.tfl.gov.uk/TrackerNet/StationStatus/IncidentsOnly"

	r = requests.get(StationIncidentsURI)
	xml = r.text
	# CHECK RESPONSE CODE 200!
	soup = BeautifulSoup(xml)

	stations_in_trackernet = []

	for station in soup.find_all('stationstatus'):
		if station.status['id'] == 'NS':
			station_name = find_station_name(station.station['name'])

			problem = get_problem_for_station(station_name)

			if problem['trackernet-text'] is None:
				problem['trackernet-time'] = datetime.now().isoformat()
				problem['trackernet-resolved'] = None

			# We always reset this just in case there is an update
			matches = re.sub('[Cc]all.*0[38]43 ?222 ?1234.*journey\.?', '', station['statusdetails'])
			problem['trackernet-text'] = matches

			if problem.get('new-problem', False):
				# Longest station name is Cutty Sark for Maritime Greenwich at 34 chars. This leaves 106
				tweet = station_name + ': ' + problem['trackernet-text']
				if len(tweet) > 140:
					tweet = 'No step free access reported at ' + station_name
				
				send_tweet(tweet)

			problem['new-problem'] = False

			set_problem_for_station(station_name, problem)

			stations_in_trackernet.append(station_name)


	for problem_station in get_problems_dict().keys():
		if problem_station[0:1] != '_':
			# If we set a problem via trackernet but haven't resolved it, and it's not in the current issues list, mark it as resolved now.
			if get_problems_dict()[problem_station]['trackernet-time'] is not None and get_problems_dict()[problem_station]['trackernet-resolved'] is None and problem_station not in stations_in_trackernet:
				problem = get_problem_for_station(problem_station)

				problem['trackernet-resolved'] = datetime.now().isoformat()

				set_problem_for_station(problem_station, problem)

	# And update the last time we saw trackernet
	problems = get_problems_dict()
	problems['_trackernet_update'] = datetime.now().isoformat()
	set_problems_dict(problems)


# Do everything we need to check twitter
def check_twitter():

	h = HTMLParser.HTMLParser()

	twitter = get_twitter()

	for account in get_twitter_last_statuses().keys():
		user_timeline = twitter.get_user_timeline(screen_name = account, since_id = get_twitter_last_statuses()[account])

		for tweet in user_timeline:
			tweet_text = h.unescape(tweet['text'])

		 	if 'no step free access' in tweet_text.lower():
				station_name = find_station_name(h.unescape(tweet_text))

				problem = get_problem_for_station(station_name)

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

				problem = get_problem_for_station(station_name)

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


# Update the problems, delete old ones etc
def update_problems():
	problems = get_problems_dict()

	problems_to_remove = []

	for problem in problems.keys():
		if problem[0:1] != '_':
			if problems[problem]['resolved']:
				# If it's resolved, see if it's old enough to delete
				if problems[problem]['twitter-resolved']:
					twitter_resolved = datetime.strptime(problems[problem]['twitter-resolved'][0:19], '%Y-%m-%dT%H:%M:%S')
					if twitter_resolved + timedelta(hours = 12) < datetime.now():
						problems_to_remove.append(problem)	
				
				if problems[problem]['trackernet-resolved']:
					trackernet_resolved = datetime.strptime(problems[problem]['trackernet-resolved'], '%Y-%m-%dT%H:%M:%S.%f')
					if trackernet_resolved + timedelta(hours = 12) < datetime.now():
						problems_to_remove.append(problem)

			else:
				# See if it should be resolved!
				if problems[problem]['twitter-resolved'] or problems[problem]['trackernet-resolved']:
					problems[problem]['resolved'] = True
					# Work out how long it took them to resolve
					start_time = datetime.strptime(problems[problem]['trackernet-time'], '%Y-%m-%dT%H:%M:%S.%f') or datetime.strptime(problems[problem]['twitter-time'][0:19], '%Y-%m-%dT%H:%M:%S')
					end_time = datetime.strptime(problems[problem]['trackernet-resolved'], '%Y-%m-%dT%H:%M:%S.%f') or datetime.strptime(problems[problem]['twitter-resolved'][0:19], '%Y-%m-%dT%H:%M:%S')
					problems[problem]['time-to-resolve'] = int((end_time - start_time).seconds)

					# Longest station name is Cutty Sark for Maritime Greenwich at 34 chars. This leaves 106
					tweet = 'Step free access has been restored at ' + problem
					send_tweet(tweet)

				# If is was something that was only put on twitter and never resolved - time out after 6 hours
				elif problems[problem]['twitter-time'] and problems[problem]['trackernet-time'] is None and problems[problem]['trackernet-resolved'] is None and problems[problem]['twitter-resolved'] is None:
					twitter_time = datetime.strptime(problems[problem]['twitter-time'][0:19], '%Y-%m-%dT%H:%M:%S')

					if twitter_time + timedelta(hours = 6) < datetime.now():
						problems[problem]['trackernet-resolved'] = datetime.now().isoformat()
						problems[problem]['trackernet-text'] = "This issue was mentioned on Twitter but never resolved. Therefore we have marked it as resolved after 6 hours."
						problems[problem]['resolved'] = True

						# Longest station name is Cutty Sark for Maritime Greenwich at 34 chars. This leaves 106
						tweet = 'There is no further news on step free access at ' + problem
						send_tweet(tweet)

	for problem in problems_to_remove:
		del(problems[problem])

	set_problems_dict(problems)



if __name__ == '__main__':

	check_trackernet()
	
	if twitter_needs_update():
		check_twitter()
		save_twitter_last_statuses()

	# Then we need to see what's been resolved or whatever
	update_problems()

	save_problems_dict()
	
	# Then split them into two dicts
	problems = {}
	resolved = {}

	for problem in get_problems_dict().keys():
		if problem[0:1] != '_':
			# Make the times look readable
			if get_problems_dict()[problem]['twitter-time']:
				get_problems_dict()[problem]['twitter-time'] = datetime.strptime(get_problems_dict()[problem]['twitter-time'][0:19], '%Y-%m-%dT%H:%M:%S').strftime('%H:%M %d %b')
			if get_problems_dict()[problem]['twitter-resolved']:
				get_problems_dict()[problem]['twitter-resolved'] = datetime.strptime(get_problems_dict()[problem]['twitter-resolved'][0:19], '%Y-%m-%dT%H:%M:%S').strftime('%H:%M %d %b')
			if get_problems_dict()[problem]['trackernet-time']:
				get_problems_dict()[problem]['trackernet-time'] = datetime.strptime(get_problems_dict()[problem]['trackernet-time'], '%Y-%m-%dT%H:%M:%S.%f').strftime('%H:%M %d %b')
			if get_problems_dict()[problem]['trackernet-resolved']:
				get_problems_dict()[problem]['trackernet-resolved'] = datetime.strptime(get_problems_dict()[problem]['trackernet-resolved'], '%Y-%m-%dT%H:%M:%S.%f').strftime('%H:%M %d %b')	

			if get_problems_dict()[problem]['time-to-resolve']:
				hours = str(get_problems_dict()[problem]['time-to-resolve'] / (60 * 60))
				minutes = str((get_problems_dict()[problem]['time-to-resolve'] / 60) % 60)
				get_problems_dict()[problem]['time-to-resolve'] = hours + ":" + minutes

			if get_problems_dict()[problem]['resolved']:
				resolved[problem] = get_problems_dict()[problem]
			else:
				problems[problem] = get_problems_dict()[problem]

	# Then create the HTML file.
	mytemplate = Template(filename=settings.template_file_location + 'index.tmpl')
	rendered_page = mytemplate.render(problems = problems, problems_sort = sorted(problems), resolved = resolved, resolved_sort = sorted(resolved), last_updated = datetime.strptime(get_problems_dict()['_last_updated'], '%Y-%m-%dT%H:%M:%S.%f').strftime('%H:%M %d %b'), production = settings.production)

	with open(settings.output_file_location + 'index.html', 'w') as f:
		f.write(rendered_page)



