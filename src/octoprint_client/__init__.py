# coding=utf-8
from __future__ import absolute_import

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import requests
import time
import collections

apikey = None
baseurl = None


class SocketTimeout(BaseException):
	pass

class SocketClient(object):
	def __init__(self, url, use_ssl=False, daemon=True, **kwargs):
		self._url = url
		self._use_ssl = use_ssl
		self._daemon = daemon
		self._ws_kwargs = kwargs

		self._seen_open = False
		self._seen_close = False
		self._waiting_for_reconnect = False

		self._ws = None
		self._thread = None

		# hello world

	def _prepare(self):
		"""Prepares socket and thread for a new connection."""

		# close the socket if it's currently open
		if self._ws is not None:
			try:
				self._ws.close()
			except:
				# we can't handle that in any meaningful way right now
				pass

		# prepare a bunch of callback methods
		import functools
		callbacks = dict()
		for callback in ("on_open", "on_message", "on_error", "on_close"):
			# now, normally we could just use functools.partial for something like
			# this, but websocket does a type check against a python function type
			# which the use of partial makes fail, so we have to use a lambda
			# wrapper here, and since we need to pick the current value of
			# callback from the current scope we need a factory method for that...
			def factory(cb):
				return lambda *fargs, **fkwargs: functools.partial(self._on_callback, cb)(*fargs, **fkwargs)
			callbacks[callback] = factory(callback)

		# initialize socket instance with url and callbacks
		import websocket
		kwargs = dict(self._ws_kwargs)
		kwargs.update(callbacks)
		self._ws = websocket.WebSocketApp(self._url, **kwargs)

		# initialize thread
		import threading
		self._thread = threading.Thread(target=self._on_thread_run)
		self._thread.daemon = self._daemon

	def _on_thread_run(self):
		"""Has the socket run forever (aka until closed...)."""
		self._ws.run_forever()

	def _on_callback(self, cb, *args, **kwargs):
		"""
		Callback for socket events.

		Will call any callback method defined on ``self`` that matches ``cb``
		prefixed with an ``_ws_``, then will call any callback method provided in
		the socket keyword arguments (``self._ws_kwargs``) that matches ``cb``.

		Calling args and kwargs will be the ones passed to ``_on_callback``.

		Arguments:
		    cb (str): the callback type
		"""
		internal = "_ws_" + cb
		if hasattr(self, internal):
			cb_func = getattr(self, internal)
			if isinstance(cb_func, collections.Callable):
				cb_func(*args, **kwargs)

		cb_func = self._ws_kwargs.get(cb, None)
		if isinstance(cb_func, collections.Callable):
			cb_func(*args, **kwargs)

	def _ws_on_open(self, ws):
		"""
		Callback for socket on_open event.

		Used only to track active reconnection attempts.
		"""

		if not self._waiting_for_reconnect:
			return
		if ws != self._ws:
			return
		self._seen_open = True

	def _ws_on_close(self, ws):
		"""
		Callback for socket on_close event.

		Used only to track active reconnection attempts.
		"""

		if not self._waiting_for_reconnect:
			return
		if ws != self._ws:
			return
		self._seen_close = True

	def connect(self):
		"""Connects the socket."""
		self._prepare()
		self._thread.start()

	def wait(self, timeout=None):
		"""Waits for the closing of the socket or the timeout."""
		start = None

		def test_condition():
			if timeout and start and start + timeout > time.time():
				raise SocketTimeout()

		start = time.time()
		while self._thread.is_alive():
			test_condition()
			self._thread.join(timeout=1.0)

	@property
	def is_connected(self):
		"""Whether the web socket is connected or not."""
		return self._thread and self._ws and self._thread.is_alive()

	def disconnect(self):
		"""Disconnect the web socket."""
		if self._ws:
			self._ws.close()

	def reconnect(self, timeout=None, disconnect=True):
		"""
		Tries to reconnect to the web socket.

		If timeout is set will try to reconnect over the specified timeout in seconds
		and return False if the connection could not be re-established.

		If no timeout is provided, the method will block until the connection could
		be re-established.

		If disconnect is set to ``True`` will disconnect the socket explictly
		first if it is currently connected.

		Arguments:
		    timeout (number): timeout in seconds to wait for the reconnect to happen.
		    disconnect (bool): Whether to disconnect explicitly from the socket if
		       a connection is currently established (True, default) or not (False).

		Returns:
		    bool - True if the reconnect was successful, False otherwise.
		"""

		self._seen_close = False
		self._seen_open = False
		self._waiting_for_reconnect = True

		if not self.is_connected:
			# not connected, so we are already closed
			self._seen_close = True
		elif disconnect:
			# connected and disconnect is True, so we disconnect
			self.disconnect()

		start = None
		if timeout:
			timeout_condition = lambda: start is not None and time.time() > start + timeout
		else:
			timeout_condition = lambda: False

		start = time.time()
		while not timeout_condition():
			if self._seen_close and self._seen_open:
				# we saw a connection close and open, so a reconnect, success!
				return True
			else:
				# try to connect
				self.connect()

			# sleep a bit
			time.sleep(1.0)

		# if we land here the timeout condition became True without us seeing
		# a reconnect, that's a failure
		return False


def build_base_url(https=False, httpuser=None, httppass=None, host=None, port=None, prefix=None):
	protocol = "https" if https else "http"
	httpauth = "{}:{}@".format(httpuser, httppass) if httpuser and httppass else ""
	host = host if host else "127.0.0.1"
	port = ":{}".format(port) if port else ":5000"
	prefix = prefix if prefix else ""

	return "{}://{}{}{}{}".format(protocol, httpauth, host, port, prefix)


def init_client(settings, https=False, httpuser=None, httppass=None, host=None, port=None, prefix=None):
	"""
	Initializes the API client with the provided settings.

	Basically a convenience method to set ``apikey`` and ``baseurl`` from settings
	and/or command line arguments.

	Arguments:
	    settings (octoprint.settings.Settings): A :class:`~octoprint.settings.Settings` instance to use
	        for client configuration
	    https (bool): Whether to connect via HTTPS (True) or not (False, default)
	    httpuser (str or None): HTTP Basic Auth username to use. No Basic Auth will be
	        used if unset.
	    httppass (str or None): HTTP Basic Auth password to use. No Basic Auth will be
	        used if unset.
	    host (str or None): Host to connect to, overrides data from settings if set.
	    port (int or None): Port to connect to, overrides data from settings if set.
	    prefix (str or None): Path prefix, overrides data from settings if set.
	"""
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
	return post_json(path, data, params=data)

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
	import json

	# creates websocket URL for SockJS according to
	# - http://sockjs.github.io/sockjs-protocol/sockjs-protocol-0.3.3.html#section-37
	# - http://sockjs.github.io/sockjs-protocol/sockjs-protocol-0.3.3.html#section-50
	url = "ws://{}/sockjs/{:0>3d}/{}/websocket".format(
		baseurl[baseurl.find("//") + 2:], # host + port + prefix, but no protocol
		random.randrange(0, stop=999),    # server_id
		uuid.uuid4()                      # session_id
	)
	use_ssl = baseurl.startswith("https:")

	on_open_cb = kwargs.get("on_open", None)
	on_heartbeat_cb = kwargs.get("on_heartbeat", None)
	on_message_cb = kwargs.get("on_message", None)
	on_close_cb = kwargs.get("on_close", None)
	on_error_cb = kwargs.get("on_error", None)
	daemon = kwargs.get("daemon", True)

	def on_message(ws, message):
		message_type = message[0]

		if message_type == "h":
			# "heartbeat" message
			if isinstance(on_heartbeat_cb, collections.Callable):
				on_heartbeat_cb(ws)
				return
		elif message_type == "o":
			# "open" message
			return
		elif message_type == "c":
			# "close" message
			return

		if not isinstance(on_message_cb, collections.Callable):
			return

		message_body = message[1:]
		if not message_body:
			return

		data = json.loads(message_body)

		if message_type == "m":
			data = [data,]

		for d in data:
			for internal_type, internal_message in d.items():
				on_message_cb(ws, internal_type, internal_message)

	def on_open(ws):
		if isinstance(on_open_cb, collections.Callable):
			on_open_cb(ws)

	def on_close(ws):
		if isinstance(on_close_cb, collections.Callable):
			on_close_cb(ws)

	def on_error(ws, error):
		if isinstance(on_error_cb, collections.Callable):
			on_error_cb(ws, error)

	socket = SocketClient(url,
	                      use_ssl=use_ssl,
	                      daemon=daemon,
	                      on_open=on_open,
	                      on_message=on_message,
	                      on_close=on_close,
	                      on_error=on_error)
	socket.connect()

	return socket
