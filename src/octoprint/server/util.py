# coding=utf-8
from tempfile import TemporaryFile
from tornado.httputil import HTTPHeaders
from octoprint.filemanager.destinations import FileDestinations

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

from flask.ext.principal import identity_changed, Identity
from tornado.web import StaticFileHandler, HTTPError, RequestHandler, asynchronous, stream_request_body, FallbackHandler
import tornado.escape, tornado.httputil
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from flask import url_for, make_response, request, current_app
from flask.ext.login import login_required, login_user, current_user
from werkzeug.utils import redirect
from sockjs.tornado import SockJSConnection

import datetime
import stat
import mimetypes
import email
import time
import os
import threading
import logging
from functools import wraps
from watchdog.events import PatternMatchingEventHandler

from octoprint.settings import settings, valid_boolean_trues
import octoprint.timelapse
import octoprint.server
from octoprint.users import ApiUser
from octoprint.events import Events
from octoprint import gcodefiles
import octoprint.util as util

def restricted_access(func, apiEnabled=True):
	"""
	If you decorate a view with this, it will ensure that first setup has been
	done for OctoPrint's Access Control plus that any conditions of the
	login_required decorator are met. It also allows to login using the masterkey or any
	of the user's apikeys if API access is enabled globally and for the decorated view.

	If OctoPrint's Access Control has not been setup yet (indicated by the "firstRun"
	flag from the settings being set to True and the userManager not indicating
	that it's user database has been customized from default), the decorator
	will cause a HTTP 403 status code to be returned by the decorated resource.

	If an API key is provided and it matches a known key, the user will be logged in and
	the view will be called directly. If the provided key doesn't match any known key,
	a HTTP 403 status code will be returned by the decorated resource.

	Otherwise the result of calling login_required will be returned.
	"""
	@wraps(func)
	def decorated_view(*args, **kwargs):
		# if OctoPrint hasn't been set up yet, abort
		if settings().getBoolean(["server", "firstRun"]) and (octoprint.server.userManager is None or not octoprint.server.userManager.hasBeenCustomized()):
			return make_response("OctoPrint isn't setup yet", 403)

		# if API is globally enabled, enabled for this request and an api key is provided that is not the current UI API key, try to use that
		apikey = getApiKey(request)
		if settings().get(["api", "enabled"]) and apiEnabled and apikey is not None and apikey != octoprint.server.UI_API_KEY:
			if apikey == settings().get(["api", "key"]):
				# master key was used
				user = ApiUser()
			else:
				# user key might have been used
				user = octoprint.server.userManager.findUser(apikey=apikey)

			if user is None:
				return make_response("Invalid API key", 401)
			if login_user(user, remember=False):
				identity_changed.send(current_app._get_current_object(), identity=Identity(user.get_id()))
				return func(*args, **kwargs)

		# call regular login_required decorator
		return login_required(func)(*args, **kwargs)
	return decorated_view


def api_access(func):
	@wraps(func)
	def decorated_view(*args, **kwargs):
		if not settings().get(["api", "enabled"]):
			make_response("API disabled", 401)
		apikey = getApiKey(request)
		if apikey is None:
			make_response("No API key provided", 401)
		if apikey != settings().get(["api", "key"]):
			make_response("Invalid API key", 403)
		return func(*args, **kwargs)
	return decorated_view


def getUserForApiKey(apikey):
	if settings().get(["api", "enabled"]) and apikey is not None:
		if apikey == settings().get(["api", "key"]):
			# master key was used
			return ApiUser()
		else:
			# user key might have been used
			return octoprint.server.userManager.findUser(apikey=apikey)
	else:
		return None


def getApiKey(request):
	# Check Flask GET/POST arguments
	if hasattr(request, "values") and "apikey" in request.values:
		return request.values["apikey"]

	# Check Tornado GET/POST arguments
	if hasattr(request, "arguments") and "apikey" in request.arguments \
		and len(request.arguments["apikey"]) > 0 and len(request.arguments["apikey"].strip()) > 0:
		return request.arguments["apikey"]

	# Check Tornado and Flask headers
	if "X-Api-Key" in request.headers.keys():
		return request.headers.get("X-Api-Key")

	return None


#~~ Printer state


class PrinterStateConnection(SockJSConnection):
	EVENTS = [Events.UPDATED_FILES, Events.METADATA_ANALYSIS_FINISHED, Events.MOVIE_RENDERING, Events.MOVIE_DONE,
			  Events.MOVIE_FAILED, Events.SLICING_STARTED, Events.SLICING_DONE, Events.SLICING_FAILED,
			  Events.TRANSFER_STARTED, Events.TRANSFER_DONE]

	def __init__(self, printer, gcodeManager, userManager, eventManager, session):
		SockJSConnection.__init__(self, session)

		self._logger = logging.getLogger(__name__)

		self._temperatureBacklog = []
		self._temperatureBacklogMutex = threading.Lock()
		self._logBacklog = []
		self._logBacklogMutex = threading.Lock()
		self._messageBacklog = []
		self._messageBacklogMutex = threading.Lock()

		self._printer = printer
		self._gcodeManager = gcodeManager
		self._userManager = userManager
		self._eventManager = eventManager

	def _getRemoteAddress(self, info):
		forwardedFor = info.headers.get("X-Forwarded-For")
		if forwardedFor is not None:
			return forwardedFor.split(",")[0]
		return info.ip

	def on_open(self, info):
		remoteAddress = self._getRemoteAddress(info)
		self._logger.info("New connection from client: %s" % remoteAddress)

		# connected => update the API key, might be necessary if the client was left open while the server restarted
		self._emit("connected", {"apikey": octoprint.server.UI_API_KEY, "version": octoprint.server.VERSION})

		self._printer.registerCallback(self)
		self._gcodeManager.registerCallback(self)
		octoprint.timelapse.registerCallback(self)

		self._eventManager.fire(Events.CLIENT_OPENED, {"remoteAddress": remoteAddress})
		for event in PrinterStateConnection.EVENTS:
			self._eventManager.subscribe(event, self._onEvent)

		octoprint.timelapse.notifyCallbacks(octoprint.timelapse.current)

	def on_close(self):
		self._logger.info("Client connection closed")
		self._printer.unregisterCallback(self)
		self._gcodeManager.unregisterCallback(self)
		octoprint.timelapse.unregisterCallback(self)

		self._eventManager.fire(Events.CLIENT_CLOSED)
		for event in PrinterStateConnection.EVENTS:
			self._eventManager.unsubscribe(event, self._onEvent)

	def on_message(self, message):
		pass

	def sendCurrentData(self, data):
		# add current temperature, log and message backlogs to sent data
		with self._temperatureBacklogMutex:
			temperatures = self._temperatureBacklog
			self._temperatureBacklog = []

		with self._logBacklogMutex:
			logs = self._logBacklog
			self._logBacklog = []

		with self._messageBacklogMutex:
			messages = self._messageBacklog
			self._messageBacklog = []

		data.update({
			"temps": temperatures,
			"logs": logs,
			"messages": messages
		})
		self._emit("current", data)

	def sendHistoryData(self, data):
		self._emit("history", data)

	def sendEvent(self, type, payload=None):
		self._emit("event", {"type": type, "payload": payload})

	def sendFeedbackCommandOutput(self, name, output):
		self._emit("feedbackCommandOutput", {"name": name, "output": output})

	def sendTimelapseConfig(self, timelapseConfig):
		self._emit("timelapse", timelapseConfig)

	def addLog(self, data):
		with self._logBacklogMutex:
			self._logBacklog.append(data)

	def addMessage(self, data):
		with self._messageBacklogMutex:
			self._messageBacklog.append(data)

	def addTemperature(self, data):
		with self._temperatureBacklogMutex:
			self._temperatureBacklog.append(data)

	def _onEvent(self, event, payload):
		self.sendEvent(event, payload)

	def _emit(self, type, payload):
		self.send({type: payload})


@stream_request_body
class UploadStorageFallbackHandler(RequestHandler):

	def initialize(self, delegate, folder):
		self.delegate = delegate
		self.folder = folder

		# Parts information will be stored here
		self.parts = dict()

		# files will be stored here
		self.files = dict()

		# values will be stored here
		self.values = dict()

		# Part currently being processed
		self._current_part = None
		# buffer needed for identifying form data parts
		self._buffer = b""

		# we only support multipart/form-data content, so check for that
		self._bytes_left = self.request.headers.get("Content-Length", 0)
		content_type = self.request.headers.get("Content-Type", "")
		if not self._bytes_left or not content_type.startswith("multipart"):
			raise HTTPError(405)

		# extract the multipart boundary
		fields = content_type.split(";")
		for field in fields:
			k, sep, v = field.strip().partition("=")
			if k == "boundary" and v:
				if v.startswith(b'"') and v.endswith(b'"'):
					self.boundary = tornado.escape.utf8(v[1:-1])
				else:
					self.boundary = tornado.escape.utf8(v)
				break
		else:
			raise HTTPError(400)



@stream_request_body
class StreamingFallbackHandler(FallbackHandler):
	"""A `RequestHandler` that wraps another HTTP server callback.

	The fallback is a callable object that accepts an
	`~.httputil.HTTPServerRequest`, such as an `Application` or
	`octoprint.server.util.StreamedWSGIContainer`.  This is most useful to use both
	Tornado ``RequestHandlers`` and WSGI in the same server.  Typical
	usage::

		wsgi_app = octoprint.server.util.StreamedWSGIContainer(
			django.core.handlers.wsgi.WSGIHandler())
		application = tornado.web.Application([
			(r"/foo", FooHandler),
			(r".*", StreamingFallbackHandler, dict(fallback=wsgi_app),
		])
	"""
	def initialize(self, fallback):
		self.fallback = fallback

	def data_received(self, chunk):
		self._tmpfile.write(chunk)
		self._length_left -= len(chunk)
		if self._length_left <= 0:
			self.finished_body()

	def finished_body(self):
		self._tmpfile.seek(0)

	def prepare(self):
		self._length_left = int(self.request.headers.get("Content-Length", 0))
		self._tmpfile = TemporaryFile()

	def __getattribute__(self, name):
		if name in ("get", "post", "put", "patch"):
			try:
				body_stream = self._tmpfile
				self.fallback(self.request, body_stream)
			finally:
				self._tmpfile.close()
			return lambda *args, **kwargs: None
		return object.__getattribute__(self, name)


class StreamedWsgiContainer(object):

	def __init__(self, wsgi_application):
		self.wsgi_application = wsgi_application

	def __call__(self, request, body_stream):
		data = {}
		response = []

		def start_response(status, response_headers, exc_info=None):
			data["status"] = status
			data["headers"] = response_headers
			return response.append
		app_response = self.wsgi_application(
			StreamedWsgiContainer.environ(request, body_stream), start_response)
		try:
			response.extend(app_response)
			body = b"".join(response)
		finally:
			if hasattr(app_response, "close"):
				app_response.close()
		if not data:
			raise Exception("WSGI app did not call start_response")

		status_code = int(data["status"].split()[0])
		headers = data["headers"]
		header_set = set(k.lower() for (k, v) in headers)
		body = tornado.escape.utf8(body)
		if status_code != 304:
			if "content-length" not in header_set:
				headers.append(("Content-Length", str(len(body))))
			if "content-type" not in header_set:
				headers.append(("Content-Type", "text/html; charset=UTF-8"))
		if "server" not in header_set:
			headers.append(("Server", "TornadoServer/%s" % tornado.version))

		parts = [tornado.escape.utf8("HTTP/1.1 " + data["status"] + "\r\n")]
		for key, value in headers:
			parts.append(tornado.escape.utf8(key) + b": " + tornado.escape.utf8(value) + b"\r\n")
		parts.append(b"\r\n")
		parts.append(body)
		request.write(b"".join(parts))
		request.finish()
		self._log(status_code, request)

	@staticmethod
	def environ(request, body_stream):
		"""Converts a `tornado.httputil.HTTPServerRequest` to a WSGI environment.
		"""
		from tornado.wsgi import to_wsgi_str
		import sys
		import io

		hostport = request.host.split(":")
		if len(hostport) == 2:
			host = hostport[0]
			port = int(hostport[1])
		else:
			host = request.host
			port = 443 if request.protocol == "https" else 80
		environ = {
			"REQUEST_METHOD": request.method,
			"SCRIPT_NAME": "",
			"PATH_INFO": to_wsgi_str(tornado.escape.url_unescape(
				request.path, encoding=None, plus=False)),
			"QUERY_STRING": request.query,
			"REMOTE_ADDR": request.remote_ip,
			"SERVER_NAME": host,
			"SERVER_PORT": str(port),
			"SERVER_PROTOCOL": request.version,
			"wsgi.version": (1, 0),
			"wsgi.url_scheme": request.protocol,
			"wsgi.input": body_stream,
			"wsgi.errors": sys.stderr,
			"wsgi.multithread": False,
			"wsgi.multiprocess": True,
			"wsgi.run_once": False,
			}
		if "Content-Type" in request.headers:
			environ["CONTENT_TYPE"] = request.headers.pop("Content-Type")
		if "Content-Length" in request.headers:
			environ["CONTENT_LENGTH"] = request.headers.pop("Content-Length")
		for key, value in request.headers.items():
			environ["HTTP_" + key.replace("-", "_").upper()] = value
		return environ

	def _log(self, status_code, request):
		access_log = logging.getLogger("tornado.access")

		if status_code < 400:
			log_method = access_log.info
		elif status_code < 500:
			log_method = access_log.warning
		else:
			log_method = access_log.error
		request_time = 1000.0 * request.request_time()
		summary = request.method + " " + request.uri + " (" + \
				  request.remote_ip + ")"
		log_method("%d %s %.2fms", status_code, summary, request_time)


def access_validation_factory(app, login_manager, validator):
	"""
	Creates an access validation wrapper using the supplied validator.

	:param validator: the access validator to use inside the validation wrapper
	:return: an access validation wrapper taking a request as parameter and performing the request validation
	"""
	def f(request):
		"""
		Creates a custom wsgi and Flask request context in order to be able to process user information
		stored in the current session.

		:param request: The Tornado request for which to create the environment and context
		"""
		import flask
		import tornado.wsgi

		wsgi_environ = tornado.wsgi.WSGIContainer.environ(request)
		with app.request_context(wsgi_environ):
			app.session_interface.open_session(app, flask.request)
			login_manager.reload_user()
			validator(flask.request)
	return f


@stream_request_body
class PrintableFilesUploadHandler(RequestHandler):

	def initialize(self, path, postfix=".tmp", files_only=False, access_validation=None):
		self._path = path
		self._postfix = postfix
		self._files_only = files_only
		self._access_validation = access_validation

		# Parts information will be stored here
		self.parts = dict()

		# files will be stored here
		self.files = dict()

		# values will be stored here
		self.values = dict()

		# Part currently being processed
		self._current_part = None
		# buffer needed for identifying form data parts
		self._buffer = b""

		# we only support multipart/form-data content, so check for that
		bytes_left = self.request.headers.get("Content-Length", 0)
		content_type = self.request.headers.get("Content-Type", "")
		if not bytes_left or not content_type.startswith("multipart"):
			raise HTTPError(405)

		# extract the multipart boundary
		fields = content_type.split(";")
		for field in fields:
			k, sep, v = field.strip().partition("=")
			if k == "boundary" and v:
				if v.startswith(b'"') and v.endswith(b'"'):
					self.boundary = tornado.escape.utf8(v[1:-1])
				else:
					self.boundary = tornado.escape.utf8(v)
				break
		else:
			raise HTTPError(400)

	def data_received(self, chunk):
		data = self._buffer + chunk
		self.process_data(data)

	def process_data(self, data):
		# check for boundary
		delimiter = b"--%s" % self.boundary
		delimiter_loc = data.find(delimiter)
		delimiter_len = len(delimiter)
		end_of_header = None
		if delimiter_loc != -1:
			# found the delimiter in the currently available data
			data, self._buffer = data[0:delimiter_loc], data[delimiter_loc:]
			end_of_header = self._buffer.find("\r\n\r\n")
		else:
			# make sure any boundary (with single or double ==) contained at the end of chunk does not get
			# truncated by this processing round => save it to the buffer for next round
			endlen = len(self.boundary) + 4
			data, self._buffer = data[0:-endlen], data[-endlen:]

		# stream data to part handler
		if data:
			if self._current_part:
				self.ondata(self._current_part, data)

		if end_of_header >= 0:
			self._header(self._buffer[delimiter_len+2:end_of_header])
			self._buffer = self._buffer[end_of_header + 4:]

		if delimiter_loc != -1 and self._buffer[delimiter_len:delimiter_len+2] == "--":
			# we saw the last boundary and are at the end of our request
			if self._current_part:
				self.onclose(self._current_part)
				self._current_part = None
			self._buffer = b""
			self.onfinish()

	def _header(self, header):
		# close any open parts
		if self._current_part:
			self.onclose(self._current_part)
			self._current_part = None

		header_check = header.find(self.boundary)
		if header_check != -1:
			# TODO log warning
			header = header[header_check:]

		# convert to dict
		header = HTTPHeaders.parse(header.decode("utf-8"))
		disp_header = header.get("Content-Disposition", "")
		disposition, disp_params = tornado.httputil._parse_header(disp_header)

		if disposition != "form-data":
			# TODO log warning
			return
		if not disp_params.get("name"):
			# TODO log warning
			return

		if self._files_only and "filename" not in disp_params:
			# TODO log warning
			return
		else:
			self._current_part = self.onpart(disp_params["name"], header.get("Content-Type", None), filename=disp_params["filename"] if "filename" in disp_params else None)

	def onpart(self, name, content_type, filename=None):
		from octoprint.server import gcodeManager

		if content_type is None:
			# we got a key-value-pair
			return dict(name=name, value=b"")
		elif filename is not None:
			# this is a file
			upload = Object()
			upload.filename = filename

			sane_filename = gcodeManager.getFutureFilename(upload)
			if sane_filename is None:
				return dict()

			local_path = os.path.join(self._path, sane_filename + self._postfix)
			handle = open(local_path, "wb")
			return dict(name=name, filename=filename, sane_filename=sane_filename, content_type=content_type, local_path=local_path, file=handle)
		else:
			return dict()

	def ondata(self, part, data):
		if "value" in part:
			part["value"] += data
		elif "file" in part:
			part["file"].write(data)

	def onclose(self, part):
		escaped_name = tornado.escape.utf8(part["name"])

		self.parts[escaped_name] = part
		if "file" in part:
			part["file"].close()
			del part["file"]
			self.files[escaped_name] = part
		elif "value" in part:
			escaped_value = tornado.escape.utf8(part["value"])
			self.values[escaped_name] = escaped_value
			self.request.body_arguments.setdefault(escaped_name, []).append(escaped_value)

	def onfinish(self):
		# we now do something horrible and replace the body by a version stripped of all files. Yes, I feel bad for this
		import io
		new_body = b""
		for name, value in self.values.iteritems():
			new_body += b"--%s\r\n" % self.boundary
			new_body += b"Content-Disposition: form-data; name=\"%s\"\r\n\r\n" % name
			new_body += value
		new_body += b"--%s--\r\n" % self.boundary
		self.request.body = new_body
		self.request.headers["Content-Length"] = len(new_body)

	def post(self, *args, **kwargs):
		while len(self._buffer):
			self.process_data(self._buffer)

		from octoprint.server import gcodeManager, printer, eventManager

		if self._access_validation is not None:
			self._access_validation(self.request)

		target = self.request.path.split("/")[-1]

		if not target in [FileDestinations.LOCAL, FileDestinations.SDCARD]:
			self.set_status(404, reason="Unknown target: %s" % target)
			return

		if not "file" in self.files:
			self.set_status(400, reason="No file included")
			return

		if target == FileDestinations.SDCARD and not settings().getBoolean(["feature", "sdSupport"]):
			self.set_status(404, reason="SD card support is disabled")
			return

		import octoprint.util

		upload = Object()
		upload.filename = self.files["file"]["filename"]
		upload.sane_filename = self.files["file"]["sane_filename"]
		upload.save = lambda new_name: octoprint.util.safeRename(self.files["file"]["local_path"], new_name)

		sd = target == FileDestinations.SDCARD
		selectAfterUpload = "select" in self.values and self.values["select"] in valid_boolean_trues
		printAfterSelect = "print" in self.values and self.values["print"] in valid_boolean_trues

		if sd:
			# validate that all preconditions for SD upload are met before attempting it
			if not (printer.isOperational() and not (printer.isPrinting() or printer.isPaused())):
				self.set_status(409, reason="Can not upload to SD card, printer is either not operational or already busy")
				return
			if not printer.isSdReady():
				self.set_status(409, "Can not upload to SD card, not yet initialized")
				return

		# determine current job
		currentFilename = None
		currentOrigin = None
		currentJob = printer.getCurrentJob()
		if currentJob is not None and "file" in currentJob.keys():
			currentJobFile = currentJob["file"]
			if "name" in currentJobFile.keys() and "origin" in currentJobFile.keys():
				currentFilename = currentJobFile["name"]
				currentOrigin = currentJobFile["origin"]

		# determine future filename of file to be uploaded, abort if it can't be uploaded
		futureFilename = upload.sane_filename
		if futureFilename is None or (not settings().getBoolean(["cura", "enabled"]) and not gcodefiles.isGcodeFileName(futureFilename)):
			self.set_status(415, reason="Can not upload file %s, wrong format?" % upload.filename)
			return

		# prohibit overwriting currently selected file while it's being printed
		if futureFilename == currentFilename and target == currentOrigin and printer.isPrinting() or printer.isPaused():
			self.set_status(409, reason="Trying to overwrite file that is currently being printed: %s" % currentFilename)
			return

		def fileProcessingFinished(filename, absFilename, destination):
			"""
			Callback for when the file processing (upload, optional slicing, addition to analysis queue) has
			finished.

			Depending on the file's destination triggers either streaming to SD card or directly calls selectAndOrPrint.
			"""
			if destination == FileDestinations.SDCARD:
				return filename, printer.addSdFile(filename, absFilename, selectAndOrPrint)
			else:
				selectAndOrPrint(filename, absFilename, destination)
				return filename

		def selectAndOrPrint(filename, absFilename, destination):
			"""
			Callback for when the file is ready to be selected and optionally printed. For SD file uploads this is only
			the case after they have finished streaming to the printer, which is why this callback is also used
			for the corresponding call to addSdFile.

			Selects the just uploaded file if either selectAfterUpload or printAfterSelect are True, or if the
			exact file is already selected, such reloading it.
			"""
			if selectAfterUpload or printAfterSelect or (currentFilename == filename and currentOrigin == destination):
				printer.selectFile(absFilename, destination == FileDestinations.SDCARD, printAfterSelect)

		filename, done = gcodeManager.addFile(upload, target, fileProcessingFinished)
		if filename is None:
			return make_response("Could not upload the file %s" % upload.filename, 500)

		sdFilename = None
		if isinstance(filename, tuple):
			filename, sdFilename = filename

		eventManager.fire(Events.UPLOAD, {"file": filename, "target": target})

		"""
		files = {}
		location = url_for(".readGcodeFile", target=FileDestinations.LOCAL, filename=filename, _external=True)
		files.update({
			FileDestinations.LOCAL: {
				"name": filename,
				"origin": FileDestinations.LOCAL,
				"refs": {
				"resource": location,
					"download": url_for("index", _external=True) + "downloads/files/" + FileDestinations.LOCAL + "/" + filename
				}
			}
		})

		if sd and sdFilename:
			location = url_for(".readGcodeFile", target=FileDestinations.SDCARD, filename=sdFilename, _external=True)
			files.update({
				FileDestinations.SDCARD: {
					"name": sdFilename,
					"origin": FileDestinations.SDCARD,
					"refs": {
						"resource": location
					}
				}
			})
		"""

		import tornado.escape

		self.set_status(201)
		#self.set_header("Location", location)
		self.finish(tornado.escape.json_encode(dict(files={}, done=done)))


#~~ customized large response handler


class LargeResponseHandler(StaticFileHandler):

	CHUNK_SIZE = 16 * 1024

	def initialize(self, path, default_filename=None, as_attachment=False, access_validation=None):
		StaticFileHandler.initialize(self, path, default_filename)
		self._as_attachment = as_attachment
		self._access_validation = access_validation

	def get(self, path, include_body=True):
		if self._access_validation is not None:
			self._access_validation(self.request)

		path = self.parse_url_path(path)
		abspath = os.path.abspath(os.path.join(self.root, path))
		# os.path.abspath strips a trailing /
		# it needs to be temporarily added back for requests to root/
		if not (abspath + os.path.sep).startswith(self.root):
			raise HTTPError(403, "%s is not in root static directory", path)
		if os.path.isdir(abspath) and self.default_filename is not None:
			# need to look at the request.path here for when path is empty
			# but there is some prefix to the path that was already
			# trimmed by the routing
			if not self.request.path.endswith("/"):
				self.redirect(self.request.path + "/")
				return
			abspath = os.path.join(abspath, self.default_filename)
		if not os.path.exists(abspath):
			raise HTTPError(404)
		if not os.path.isfile(abspath):
			raise HTTPError(403, "%s is not a file", path)

		stat_result = os.stat(abspath)
		modified = datetime.datetime.fromtimestamp(stat_result[stat.ST_MTIME])

		self.set_header("Last-Modified", modified)

		mime_type, encoding = mimetypes.guess_type(abspath)
		if mime_type:
			self.set_header("Content-Type", mime_type)

		cache_time = self.get_cache_time(path, modified, mime_type)

		if cache_time > 0:
			self.set_header("Expires", datetime.datetime.utcnow() +
									   datetime.timedelta(seconds=cache_time))
			self.set_header("Cache-Control", "max-age=" + str(cache_time))

		self.set_extra_headers(path)

		# Check the If-Modified-Since, and don't send the result if the
		# content has not been modified
		ims_value = self.request.headers.get("If-Modified-Since")
		if ims_value is not None:
			date_tuple = email.utils.parsedate(ims_value)
			if_since = datetime.datetime.fromtimestamp(time.mktime(date_tuple))
			if if_since >= modified:
				self.set_status(304)
				return

		if not include_body:
			assert self.request.method == "HEAD"
			self.set_header("Content-Length", stat_result[stat.ST_SIZE])
		else:
			with open(abspath, "rb") as file:
				while True:
					data = file.read(LargeResponseHandler.CHUNK_SIZE)
					if not data:
						break
					self.write(data)
					self.flush()

	def set_extra_headers(self, path):
		if self._as_attachment:
			self.set_header("Content-Disposition", "attachment")


##~~ URL Forward Handler for forwarding requests to a preconfigured static URL


class UrlForwardHandler(RequestHandler):

	def initialize(self, url=None, as_attachment=False, basename=None, access_validation=None):
		RequestHandler.initialize(self)
		self._url = url
		self._as_attachment = as_attachment
		self._basename = basename
		self._access_validation = access_validation

	@asynchronous
	def get(self, *args, **kwargs):
		if self._access_validation is not None:
			self._access_validation(self.request)

		if self._url is None:
			raise HTTPError(404)

		client = AsyncHTTPClient()
		r = HTTPRequest(url=self._url, method=self.request.method, body=self.request.body, headers=self.request.headers, follow_redirects=False, allow_nonstandard_methods=True)

		try:
			return client.fetch(r, self.handle_response)
		except HTTPError as e:
			if hasattr(e, "response") and e.response:
				self.handle_response(e.response)
			else:
				raise HTTPError(500)

	def handle_response(self, response):
		if response.error and not isinstance(response.error, HTTPError):
			raise HTTPError(500)

		filename = None

		self.set_status(response.code)
		for name in ("Date", "Cache-Control", "Server", "Content-Type", "Location"):
			value = response.headers.get(name)
			if value:
				self.set_header(name, value)

				if name == "Content-Type":
					filename = self.get_filename(value)

		if self._as_attachment:
			if filename is not None:
				self.set_header("Content-Disposition", "attachment; filename=%s" % filename)
			else:
				self.set_header("Content-Disposition", "attachment")

		if response.body:
			self.write(response.body)
		self.finish()

	def get_filename(self, content_type):
		if not self._basename:
			return None

		typeValue = map(str.strip, content_type.split(";"))
		if len(typeValue) == 0:
			return None

		extension = mimetypes.guess_extension(typeValue[0])
		if not extension:
			return None

		return "%s%s" % (self._basename, extension)


#~~ admin access validator for use with tornado


def admin_validator(request):
	"""
	Validates that the given request is made by an admin user, identified either by API key or existing Flask
	session.

	Must be executed in an existing Flask request context!

	:param request: The Flask request object
	"""

	apikey = getApiKey(request)
	if settings().get(["api", "enabled"]) and apikey is not None:
		user = getUserForApiKey(apikey)
	else:
		user = current_user

	if user is None or not user.is_authenticated() or not user.is_admin():
		raise HTTPError(403)


#~~ user access validator for use with tornado


def user_validator(request):
	"""
	Validates that the given request is made by an authenticated user, identified either by API key or existing Flask
	session.

	Must be executed in an existing Flask request context!

	:param request: The Flask request object
	"""

	apikey = getApiKey(request)
	if settings().get(["api", "enabled"]) and apikey is not None:
		user = getUserForApiKey(apikey)
	else:
		user = current_user

	if user is None or not user.is_authenticated():
		raise HTTPError(403)


#~~ reverse proxy compatible wsgi middleware


class ReverseProxied(object):
	"""
	Wrap the application in this middleware and configure the
	front-end server to add these headers, to let you quietly bind
	this to a URL other than / and to an HTTP scheme that is
	different than what is used locally.

	In nginx:
		location /myprefix {
			proxy_pass http://192.168.0.1:5001;
			proxy_set_header Host $host;
			proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
			proxy_set_header X-Scheme $scheme;
			proxy_set_header X-Script-Name /myprefix;
		}

	Alternatively define prefix and scheme via config.yaml:
		server:
			baseUrl: /myprefix
			scheme: http

	:param app: the WSGI application
	"""

	def __init__(self, app):
		self.app = app

	def __call__(self, environ, start_response):
		script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
		if not script_name:
			script_name = settings().get(["server", "baseUrl"])

		if script_name:
			environ['SCRIPT_NAME'] = script_name
			path_info = environ['PATH_INFO']
			if path_info.startswith(script_name):
				environ['PATH_INFO'] = path_info[len(script_name):]

		scheme = environ.get('HTTP_X_SCHEME', '')
		if not scheme:
			scheme = settings().get(["server", "scheme"])

		if scheme:
			environ['wsgi.url_scheme'] = scheme
		return self.app(environ, start_response)


def redirectToTornado(request, target, code=302):
	requestUrl = request.url
	appBaseUrl = requestUrl[:requestUrl.find(url_for("index") + "api")]

	redirectUrl = appBaseUrl + target
	if "?" in requestUrl:
		fragment = requestUrl[requestUrl.rfind("?"):]
		redirectUrl += fragment
	return redirect(redirectUrl, code=code)


class UploadCleanupWatchdogHandler(PatternMatchingEventHandler):
	"""
	Takes care of automatically deleting metadata entries for files that get deleted from the uploads folder
	"""

	patterns = map(lambda x: "*.%s" % x, gcodefiles.GCODE_EXTENSIONS)

	def __init__(self, gcode_manager):
		PatternMatchingEventHandler.__init__(self)
		self._gcode_manager = gcode_manager

	def on_deleted(self, event):
		filename = self._gcode_manager._getBasicFilename(event.src_path)
		if not filename:
			return

		self._gcode_manager.removeFileFromMetadata(filename)


class GcodeWatchdogHandler(PatternMatchingEventHandler):
	"""
	Takes care of automatically "uploading" files that get added to the watched folder.
	"""

	patterns = map(lambda x: "*.%s" % x, gcodefiles.SUPPORTED_EXTENSIONS)

	def __init__(self, gcodeManager, printer):
		PatternMatchingEventHandler.__init__(self)

		self._logger = logging.getLogger(__name__)

		self._gcodeManager = gcodeManager
		self._printer = printer

	def _upload(self, path):
		class WatchdogFileWrapper(object):

			def __init__(self, path):
				self._path = path
				self.filename = os.path.basename(self._path)

			def save(self, target):
				util.safeRename(self._path, target)

		fileWrapper = WatchdogFileWrapper(path)

		# determine current job
		currentFilename = None
		currentOrigin = None
		currentJob = self._printer.getCurrentJob()
		if currentJob is not None and "file" in currentJob.keys():
			currentJobFile = currentJob["file"]
			if "name" in currentJobFile.keys() and "origin" in currentJobFile.keys():
				currentFilename = currentJobFile["name"]
				currentOrigin = currentJobFile["origin"]

		# determine future filename of file to be uploaded, abort if it can't be uploaded
		futureFilename = self._gcodeManager.getFutureFilename(fileWrapper)
		if futureFilename is None or (not settings().getBoolean(["cura", "enabled"]) and not gcodefiles.isGcodeFileName(futureFilename)):
			self._logger.warn("Could not add %s: Invalid file" % fileWrapper.filename)
			return

		# prohibit overwriting currently selected file while it's being printed
		if futureFilename == currentFilename and not currentOrigin == FileDestinations.SDCARD and self._printer.isPrinting() or self._printer.isPaused():
			self._logger.warn("Could not add %s: Trying to overwrite file that is currently being printed" % fileWrapper.filename)
			return

		self._gcodeManager.addFile(fileWrapper, FileDestinations.LOCAL)

	def on_created(self, event):
		self._upload(event.src_path)


class Object(object):
	pass