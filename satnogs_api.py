# Matthew Menten
# August Black
# ATLS 4519 - Studio: Space Fall 2018

# SatNOGS API Tool



# Example API Request
# https://network.satnogs.org/api/observations/?ground_station=13&page=33&start=2018-08-01T00%3A00%3A00Z&format=json

# Example error message
# {'detail': 'Invalid page.'}



import argparse
import pprint
import requests
import re
import os

from urllib.error import HTTPError
from urllib.parse import quote


def request_dates(station_id, start_date, end_date, page):
	"""
	:param station_id:      <int>
	:param start_date:      <str>
	:param end_date:        <str>
	:param page:            <int>
	:return response.json() <dict>
	"""

	# set up parameters for the API call
	# these will be the variables in the url (e.g. /?ground_station=13&format=json)
	url_params = {
		'ground_station': str(station_id),
		'start': start_date+'T00:00:00Z',
		'end': end_date+'T00:00:00Z',
		'format': 'json',
		'page': str(page)
	}

	# host url of the API
	host = "https://network.satnogs.org"
	# path for the 'observations' endpoint
	observation_path = "/api/observations/"

	# combine host and path into complete url
	url = '{0}{1}'.format(host, quote(observation_path.encode('utf8')))

	# print(u'Querying {0} ...'.format(url))

	# make a GET request to the API
	response = requests.request('GET', url, params=url_params)

	# return the JSON response from the request
	return response.json()


def request_observation(station_id, obs_id):
	"""
	:param station_id:      <int>
	:param obs_id:          <int>
	:return response.json() <dict>
	"""

	# procedure the same as request_dates, see comments there

	url_params = {
		'ground_station': str(station_id),
		'format': 'json',
	}

	host = "https://network.satnogs.org"
	specific_observation_path = "/api/observations/"+str(obs_id)+"/"

	url = '{0}{1}'.format(host, quote(specific_observation_path.encode('utf8')))

	# print(u'Querying {0} ...'.format(url))

	response = requests.request('GET', url, params=url_params)

	return response.json()


def download_data_file(link, obs_id):
	"""
	:param link:   <int>
	:param obs_id: <int>
	:return:
	"""

	# the file name is the thing after the last '/' in the link (e.g. blahblah.blah/data_file.png)
	fName = link.split("/")[-1]

	# create a name for the relative path where the data file will be saved (<observation_id>/<filename>)
	fPath = "{}/{}".format(obs_id, fName)

	# make the directory for fPath if it does not already exist
	os.makedirs(os.path.dirname(fPath), exist_ok=True)

	# make a request to the link of the datafile, this returns binary data for the file
	r = requests.get(link, allow_redirects=True)

	# write the content of the request to the file specified by fPath
	open(fPath, 'wb').write(r.content)


def main():

	# set a description for the script
	description = "A script to get observation data from the SatNOGS Network"

	parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawTextHelpFormatter)

	# add argument for station id. This argument is required and does not have a flag
	parser.add_argument("station_id", help="ID of ground station to gather observation data from", type=int)

	# add a mutually exclusive group for specifying either a specific observation or a set of observations (via dates)
	obs_group = parser.add_mutually_exclusive_group(required=True)

	obs_group.add_argument("-o", "--observation-id", help="Observation ID for a specific observation", type=int)

	obs_group.add_argument("-d", "--date-range", help="Date range for a set of observations."
												  "\nFormat (start/end): yyyy-mm-dd/yyyy-mm-dd", type=str)

	# add a mutually exclusive group for suppressing output of the script
	# it's mutually exclusive so you can't suppress all output, making the script do nothing
	opt_group = parser.add_mutually_exclusive_group()

	opt_group.add_argument("-q", "--quiet", help="Suppress printing of observation info "
												 "(files will still be saved).", action="store_true", default=False)

	opt_group.add_argument("-n", "--no-download", help="Do not download data files for the observations.", action="store_true", default=False)

	# parse cmd args and set their values to variables (e.g. args.station_id)
	args = parser.parse_args()

	# define constants for API errors
	INVALID_PAGE_ERROR = {'detail': 'Invalid page.'}
	NOT_FOUND_ERROR = {'detail': 'Not found.'}

	# check if date query
	if args.date_range:
		# RegEX pattern match to ensure dates are formatted correctly (yyyy-mm-dd/yyyy-mm-dd)
		format_check = re.search("\d{4}-\d{2}-\d{2}/\d{4}-\d{2}-\d{2}", args.date_range)

		# checks if pattern was matched successfully
		if format_check is not None:
			# date pattern is good

			# get the matched string and split on '/' to get each individual date
			format_check = format_check.group(0)
			format_check = format_check.split("/")

			date_start = format_check[0]
			date_end = format_check[-1]

			# print("Start Date Range", date_start)
			# print("End Date Range", date_end)

			# set page counter, used to get new data from the API if the result of the query does not fit on one page
			page = 1

			# make the initial API call
			api_response_json = request_dates(args.station_id, date_start, date_end, page)

			# check for errors in the response
			if api_response_json == [] or api_response_json == INVALID_PAGE_ERROR:
				print("There was an error in the query. Make sure the ground station id exists and the dates are correct.")
				exit(-1)

			# print("Number of observations in this range (page 1):", len(api_response_json))

			# set limit to None so there's no 'reference before assignment' error later
			limit = None

			# check number of observations in the first page of the response, if it's over 10, notify the user
			if len(api_response_json) > 10:
				print("WARNING: There are over 10 observations in this range and there may be many more than that.\n")

				if not args.no_download:
					print("Audio and image files will be downloaded for EACH observation.\n")
					print("**You can suppress file downloads with the --no-download flag**\n")

				# loop infinitely until the user selects a valid option
				while True:
					print("Input y to proceed, n to quit, or give an integer to limit observations to that number.")

					usrInp = input("Select an option: ")

					if usrInp == "y":
						break
					elif usrInp == "n":
						exit(0)
					else:
						# test to see if input is a valid int
						try:
							limit = int(usrInp)
							if limit <= 0:
								print(">>> Please enter a positive integer.")
							else:
								break
						except ValueError:
							print(">>> INVALID OPTION")

			# counter for number of observations handled so far, used to determine when to stop if limit is given
			num_observations = 0

			# loop until there are no more pages of data
			while api_response_json != INVALID_PAGE_ERROR:

				# for each observation in the page
				for obs in api_response_json:

					# print observation data
					if not args.quiet:
						print("------------------------------------")
						print("Observation ID:  ", obs['id'])
						print("Start Time:      ", obs['start'])
						print("End Time:        ", obs['end'])
						print("Station ID:      ", obs['ground_station'])
						print("Station Name:    ", obs['station_name'])
						print("Lat, Long:       ", str(obs['station_lat'])+","+str(obs['station_lng']))
						print("Station Altitude:", obs['station_alt'])
						print("Transmitter:     ", obs['transmitter'])
						print("NORAD CAT ID:    ", obs['norad_cat_id'])
						print("Rise Azimuth:    ", obs['rise_azimuth'])
						print("Set Azimuth:     ", obs['set_azimuth'])
						print("Max Altitude:    ", obs['max_altitude'])
						print("TLE:             ", obs['tle'])


					# downloading files
					if not args.no_download:
						print("\n>>> Downloading data files, please be patient...\n")

						if obs['payload']:

							download_data_file(obs['payload'], obs['id'])

						elif obs['archive_url']:

							download_data_file(obs['archive_url'], obs['id'])

						if obs['waterfall']:

							download_data_file(obs['waterfall'], obs['id'])

						# demoddata is a list of dicts -> each with a single key called 'payload_demod'
						# each payload_demod is a link to a png file
						if obs['demoddata'] != []:
							for elem in obs['demoddata']:
								download_data_file(elem['payload_demod'], obs['id'])

					num_observations += 1

					if limit:
						if num_observations >= limit:
							exit(0)

				# increment page and get new data
				page += 1
				api_response_json = request_dates(args.station_id, date_start, date_end, page)

			# exit successfully
			exit(0)

		else:
			# if date format check fails, notify user and exit with error code
			print("Invalid format for date range. Use [-h] for help.")
			exit(-1)

	elif args.observation_id:

		# make API call for specific observation
		api_response_json = request_observation(args.station_id, args.observation_id)

		# check for errors in the response
		if api_response_json == [] or api_response_json == INVALID_PAGE_ERROR or api_response_json == NOT_FOUND_ERROR:
			print("There was an error in the query. Make sure the ground station id and observation id are valid.")
			exit(-1)

		# pprint.pprint(api_response_json)

		# reassign api_response_json so I can just paste my code from above
		obs = api_response_json

		# print observation info
		if not args.quiet:
			print("------------------------------------")
			print("Observation ID:  ", obs['id'])
			print("Start Time:      ", obs['start'])
			print("End Time:        ", obs['end'])
			print("Station ID:      ", obs['ground_station'])
			print("Station Name:    ", obs['station_name'])
			print("Lat, Long:       ", str(obs['station_lat']) + "," + str(obs['station_lng']))
			print("Station Altitude:", obs['station_alt'])
			print("Transmitter:     ", obs['transmitter'])
			print("NORAD CAT ID:    ", obs['norad_cat_id'])
			print("Rise Azimuth:    ", obs['rise_azimuth'])
			print("Set Azimuth:     ", obs['set_azimuth'])
			print("Max Altitude:    ", obs['max_altitude'])
			print("TLE:             ", obs['tle'])

		# downloading files
		if not args.no_download:

			print("\n>>> Downloading data files, please be patient...\n")

			if obs['payload']:

				download_data_file(obs['payload'], obs['id'])

			elif obs['archive_url']:

				download_data_file(obs['archive_url'], obs['id'])

			if obs['waterfall']:

				download_data_file(obs['waterfall'], obs['id'])

			if obs['demoddata'] != []:
				for elem in obs['demoddata']:
					download_data_file(elem['payload_demod'], obs['id'])

		exit(0)

	else:
		print("Catch all case. If you see this, something weird happened.\n"
			  "Check that all required parameters are correct and try again.")

		exit(-1)



if __name__ == '__main__':
	main()