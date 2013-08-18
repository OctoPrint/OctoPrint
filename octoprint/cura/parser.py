import logging
from StringIO import StringIO


def process_profile_ini(filename):
	"""Builds the array that needs to be sent to the subprocess call.
	
	:param filename: :class: `str`

	:note: The filename should be the full path to the profile.ini
	"""

	if not filename:
		raise ValueError("No file name to process")

	# This made it easier to mock and test
	profile = read_filename(filename)
	data = {}

	logging.info("Processing %s" % filename)
	for line in profile:
		if _is_multi_start(line):
			read_multi_line(line, profile, data)
			
		if _is_single(line):
			data = process_setting_line(data, line)

	return format_data_for_command(data)

def read_multi_line(line, profile, data):

	multi_line = line

	line = profile.readline()
	if _is_multi_continue(line):
		multi_line += line
	
	if _is_single(line):
		data = process_setting_line(data, multi_line)
		data = process_setting_line(data, line)
		return

	while(_is_multi_continue(line)):

		line = profile.readline()
		if not line:
			break

		if _is_single(line):
			data = process_setting_line(data, line)
			break

		if _is_multi_start(line):
			read_multi_line(line, profile, data)
			break

		multi_line += line

	data = process_multi_setting_line(data, multi_line)




def process_multi_setting_line(data, multi_line):

	data = process_setting_line(data, multi_line)
	return data


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

	# Changes var_with_underscore to varWithUnderscore
	split = setting_line.split("=")
	variable_parts = split[0].split("_")
	end_variable_parts = ''.join(word.title() for word in variable_parts[1:])

	new_name = (str(variable_parts[0]) + end_variable_parts).strip()
	new_value = split[1].strip()

	if '.gcode' in new_name:
		new_name = new_name.replace('.gcode', 'Code')

		# might need to surround the value in quotes?
		#new_value = "'" + new_value + "'"

	data[new_name] = new_value

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


def read_filename(filename):
	
	lines = open(filename, 'r').read()
	return StringIO(lines)

def _is_multi_start(line):

	if '.gcode' in line or "=" in line and "(lp" in line:
		return True

def _is_multi_continue(line):

	if '=' not in line:
		return True
		
	if '.gcode' not in line and '=' not in line:
		return True

def _is_single(line):
	
	if '=' in line and '.gcode' not in line:
		return True


