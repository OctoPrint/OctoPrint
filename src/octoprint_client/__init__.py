# coding=utf-8
from __future__ import absolute_import

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import requests

apikey = None
baseurl = None

def prepare_request(method=None, path=None):
	url = None
	if baseurl:
		while path.startswith("/"):
			path = path[1:]
		url = baseurl + "/" + path
	return requests.Request(method=method, url=url, headers={"X-Api-Key": apikey}).prepare()

def request(method, path, data=None, files=None, encoding=None):
	s = requests.Session()
	request = prepare_request(method, path)
	if data or files:
		if encoding == "json":
			request.prepare_body(None, None, json=data)
		else:
			request.prepare_body(data, files=files)
	response = s.send(request)
	return response

def get(path):
	return request("GET", path)

def post(path, data, encoding=None):
	return request("POST", path, data=data, encoding=encoding)

def post_json(path, data):
	return post(path, data, encoding="json")

def post_command(path, command, parameters=None):
	data = dict(command=command)
	if parameters:
		data.update(parameters)
	return post_json(path, data)

def upload(path, file_path, parameters=None, file_name=None, content_type=None):
	import os

	if not os.path.isfile(file_path):
		raise ValueError("{} cannot be uploaded since it is not a file".format(file_path))

	if file_name is None:
		file_name = os.path.basename(file_path)

	with open(file_path, "rb") as fp:
		if content_type:
			files = dict(file=(file_name, fp, content_type))
		else:
			files = dict(file=(file_name, fp))

		response = request("POST", path, data=parameters, files=files)

	return response

def delete(path):
	return request("DELETE", path)

def patch(path, data, encoding=None):
	return request("PATCH", path, data=data, encoding=encoding)

def put(path, data, encoding=None):
	return request("PUT", path, data=data, encoding=encoding)
