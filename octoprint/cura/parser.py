import logging


def process_profile_ini(filename):
	"""Builds the array that needs to be sent to the subprocess call.
	
	:param filename: :class: `str`

	:note: The filename should be the full path to the profile.ini
	"""


	profile = open(filename, 'r')
	data = {}

	for line in profile:

		if _is_multi_start(line):
			
			multi_line = line

			while(not _is_multi_end(line)):
				line = profile.readline()
				multi_line += next_line

			data = process_multi_setting_line(data, multi_line)

		if _is_single(line):
			data = process_setting_line(data, setting_line)

	profile.close()

	return format_data_for_command(data)


def _is_multi_start(line):
	pass


def _is_multi_end(line):
	pass


def _is_single(line):
	pass


def process_setting_line(data, setting_line):
	"""Adds to the data dictionary a converted to camel case version of the 
	variable name as the  key and the value as the parameter's value.

	:param data: :class: `dict`
	:param setting_line: :class: `str`
	"""

	if not data:
		data = {}

	if not setting_line:
		return data

	# TODO: Make this more fault tolerant

	split = setting_line.split("=")
	variable_parts = split[0].split("_")
	end_variable_parts = ''.join(word.title() for word in variable_parts[1:])

	new_name = str(variable_parts[0]) + end_variable_parts

	data[new_name] = split[1].strip()

	return data


def format_data_for_command(data):
	"""Takes the data parsed from the file and formats it for the command line
    
	:param data: :class: `dict`

	:returns: :class: `list` of :class: `str`
	"""

	if not data:
		raise ValueError("Data not found")

	result = []

	for key, value in data.iteritems():
		result.extend(['-s', '%s=%s' %  (key, str(value))])

	return result
