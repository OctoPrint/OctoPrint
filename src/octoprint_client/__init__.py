# coding=utf-8
from __future__ import absolute_import

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import requests

apikey = None
baseurl = None

def build_base_url(https=False, httpuser=None, httppass=None, host=None, port=None, prefix=None):
	protocol = "https" if https else "http"
	httpauth = "{}:{}@".format(httpuser, httppass) if httpuser and httppass else ""
	host = host if host else "127.0.0.1"
	port = ":{}".format(port) if port else ":5000"
	prefix = prefix if prefix else ""

	return "{}://{}{}{}{}".format(protocol, httpauth, host, port, prefix)


def init_client(settings, https=False, httpuser=None, httppass=None, host=None, port=None, prefix=None):
	settings_host = settings.get(["server", "host"])
	settings_port = settings.getInt(["server", "port"])
	settings_apikey = settings.get(["api", "key"])

	global apikey, baseurl
	apikey = settings_apikey
	baseurl = build_base_url(https=https,
	                                          httpuser=httpuser,
	                                          httppass=httppass,
	                                          host=host or settings_host if settings_host != "0.0.0.0" else "127.0.0.1",
	                                          port=port or settings_port,
	                                          prefix=prefix)

def prepare_request(method=None, path=None, params=None):
	url = None
	if baseurl:
		while path.startswith("/"):
			path = path[1:]
		url = baseurl + "/" + path
	return requests.Request(method=method, url=url, params=params, headers={"X-Api-Key": apikey}).prepare()

def request(method, path, data=None, files=None, encoding=None, params=None):
	s = requests.Session()
	request = prepare_request(method, path, params=params)
	if data or files:
		if encoding == "json":
			request.prepare_body(None, None, json=data)
		else:
			request.prepare_body(data, files=files)
	response = s.send(request)
	return response

def get(path, params=None):
	return request("GET", path, params=params)

def post(path, data, encoding=None, params=None):
	return request("POST", path, data=data, encoding=encoding, params=params)

def post_json(path, data, params=None):
	return post(path, data, encoding="json", params=params)

def post_command(path, command, additional=None):
	data = dict(command=command)
	if additional:
		data.update(additional)
	return post_json(path, data, params=params)

def upload(path, file_path, additional=None, file_name=None, content_type=None, params=None):
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

		response = request("POST", path, data=additional, files=files, params=params)

	return response

def delete(path, params=None):
	return request("DELETE", path, params=params)

def patch(path, data, encoding=None, params=None):
	return request("PATCH", path, data=data, encoding=encoding, params=params)

def put(path, data, encoding=None, params=None):
	return request("PUT", path, data=data, encoding=encoding, params=params)

def connect_socket(**kwargs):
	import uuid
	import random
	import threading
	import websocket
	import json

	url = "ws://{}/sockjs/{:0>3d}/{}/websocket".format(baseurl[baseurl.find("//") + 2:], random.randrange(0, stop=999), uuid.uuid4())

	on_message_cb = kwargs.get("on_message", None)
	on_close_cb = kwargs.get("on_close", None)
	on_error_cb = kwargs.get("on_error", None)

	def on_message(ws, message):
		if not callable(on_message_cb):
			return

		if message.startswith(u"a["):
			data = json.loads(message[2:-1])
			for msg_type, msg in data.items():
				on_message_cb(ws, msg_type, msg)

	def on_close(ws):
		if callable(on_close_cb):
			on_close_cb(ws)

	def on_error(ws, error):
		if callable(on_error_cb):
			on_error_cb(ws, error)

	ws = websocket.WebSocketApp(url,
	                            on_message=on_message,
	                            on_close=on_close,
	                            on_error=on_error)

	class WebSocketThread(threading.Thread):
		def __init__(self, ws):
			threading.Thread.__init__(self)
			self.ws = ws

		def run(self):
			self.ws.run_forever()

	thread = WebSocketThread(ws)
	thread.start()

	return thread
