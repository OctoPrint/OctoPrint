# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import os
import datetime
import stat
import mimetypes
import email
import time
import re

import tornado
import tornado.web
import tornado.gen
import tornado.escape
import tornado.httputil
import tornado.httpserver
import tornado.httpclient
import tornado.http1connection
import tornado.iostream
import tornado.tcpserver

import octoprint.util


#~~ WSGI middleware


@tornado.web.stream_request_body
class UploadStorageFallbackHandler(tornado.web.RequestHandler):
	"""
	A `RequestHandler` similar to `tornado.web.FallbackHandler` which fetches any files contained in the request bodies
	of content type `multipart`, stores them in temporary files and supplies the `fallback` with the file's `name`,
	`content_type`, `path` and `size` instead via a rewritten body.

	Basically similar to what the nginx upload module does.

	Basic request body example:

		------WebKitFormBoundarypYiSUx63abAmhT5C
		Content-Disposition: form-data; name="file"; filename="test.gcode"
		Content-Type: application/octet-stream

		...
		------WebKitFormBoundarypYiSUx63abAmhT5C
		Content-Disposition: form-data; name="apikey"

		my_funny_apikey
		------WebKitFormBoundarypYiSUx63abAmhT5C
		Content-Disposition: form-data; name="select"

		true
		------WebKitFormBoundarypYiSUx63abAmhT5C--

	That would get turned into:

		------WebKitFormBoundarypYiSUx63abAmhT5C
		Content-Disposition: form-data; name="apikey"

		my_funny_apikey
		------WebKitFormBoundarypYiSUx63abAmhT5C
		Content-Disposition: form-data; name="select"

		true
		------WebKitFormBoundarypYiSUx63abAmhT5C
		Content-Disposition: form-data; name="file.path"

		/tmp/tmpzupkro
		------WebKitFormBoundarypYiSUx63abAmhT5C
		Content-Disposition: form-data; name="file.name"

		test.gcode
		------WebKitFormBoundarypYiSUx63abAmhT5C
		Content-Disposition: form-data; name="file.content_type"

		application/octet-stream
		------WebKitFormBoundarypYiSUx63abAmhT5C
		Content-Disposition: form-data; name="file.size"

		349182
		------WebKitFormBoundarypYiSUx63abAmhT5C--

	The underlying application can then access the contained files via their respective paths and just move them
	where necessary.
	"""

	# the request methods that may contain a request body
	BODY_METHODS = ("POST", "PATCH", "PUT")

	def initialize(self, fallback, file_prefix="tmp", file_suffix="", path=None, suffixes=None):
		if not suffixes:
			suffixes = dict()

		self._fallback = fallback
		self._file_prefix = file_prefix
		self._file_suffix = file_suffix
		self._path = path

		self._suffixes = dict((key, key) for key in ("name", "path", "content_type", "size"))
		for suffix_type, suffix in suffixes.iteritems():
			if suffix_type in self._suffixes and suffix is not None:
				self._suffixes[suffix_type] = suffix

		# Parts, files and values will be stored here
		self._parts = dict()
		self._files = []

		# Part currently being processed
		self._current_part = None

		# content type of request body
		self._content_type = None

		# bytes left to read according to content_length of request body
		self._bytes_left = 0

		# buffer needed for identifying form data parts
		self._buffer = b""

		# buffer for new body
		self._new_body = b""

		# logger
		self._logger = logging.getLogger(__name__)

	def prepare(self):
		"""
		Prepares the processing of the request. If it's a request that may contain a request body (as defined in
		`UploadStorageFallbackHandler.BODY_METHODS) prepares the multipart parsing if content type fits. If it's a
		body-less request, just calls the `fallback` with an empty body and finishes the request.
		"""
		if self.request.method in UploadStorageFallbackHandler.BODY_METHODS:
			self._bytes_left = self.request.headers.get("Content-Length", 0)
			self._content_type = self.request.headers.get("Content-Type", None)

			# request might contain a body
			if self.is_multipart():
				if not self._bytes_left:
					# we don't support requests without a content-length
					raise tornado.web.HTTPError(400, reason="No Content-Length supplied")

				# extract the multipart boundary
				fields = self._content_type.split(";")
				for field in fields:
					k, sep, v = field.strip().partition("=")
					if k == "boundary" and v:
						if v.startswith(b'"') and v.endswith(b'"'):
							self._multipart_boundary = tornado.escape.utf8(v[1:-1])
						else:
							self._multipart_boundary = tornado.escape.utf8(v)
						break
				else:
					self._multipart_boundary = None
		else:
			self._fallback(self.request, b"")
			self._finished = True

	def data_received(self, chunk):
		"""
		Called by Tornado on receiving a chunk of the request body. If request is a multipart request, takes care of
		processing the multipart data structure via `self._process_multipart_data`. If not, just adds the chunk to
		internal in-memory buffer.

		:param chunk: chunk of data received from Tornado
		"""

		data = self._buffer + chunk
		if self.is_multipart():
			self._process_multipart_data(data)
		else:
			self._buffer = data

	def is_multipart(self):
		"""Checks whether this request is a `multipart` request"""
		return self._content_type is not None and self._content_type.startswith("multipart")

	def _process_multipart_data(self, data):
		"""
		Processes the given data, parsing it for multipart definitions and calling the appropriate methods.

		:param data: the data to process as a string
		"""

		# check for boundary
		delimiter = b"--%s" % self._multipart_boundary
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
			endlen = len(self._multipart_boundary) + 4
			data, self._buffer = data[0:-endlen], data[-endlen:]

		# stream data to part handler
		if data and self._current_part:
				self._on_part_data(self._current_part, data)

		if end_of_header >= 0:
			self._on_part_header(self._buffer[delimiter_len+2:end_of_header])
			self._buffer = self._buffer[end_of_header + 4:]

		if delimiter_loc != -1 and self._buffer[delimiter_len:delimiter_len+2] == "--":
			# we saw the last boundary and are at the end of our request
			if self._current_part:
				self._on_part_finish(self._current_part)
				self._current_part = None
			self._buffer = b""
			self._on_request_body_finish()

	def _on_part_header(self, header):
		"""
		Called for a new multipart header, takes care of parsing the header and calling `self._on_part` with the
		relevant data, setting the current part in the process.

		:param header: header to parse
		"""

		# close any open parts
		if self._current_part:
			self._on_part_finish(self._current_part)
			self._current_part = None

		header_check = header.find(self._multipart_boundary)
		if header_check != -1:
			self._logger.warn("Header still contained multipart boundary, stripping it...")
			header = header[header_check:]

		# convert to dict
		header = tornado.httputil.HTTPHeaders.parse(header.decode("utf-8"))
		disp_header = header.get("Content-Disposition", "")
		disposition, disp_params = tornado.httputil._parse_header(disp_header)

		if disposition != "form-data":
			self._logger.warn("Got a multipart header without form-data content disposition, ignoring that one")
			return
		if not disp_params.get("name"):
			self._logger.warn("Got a multipart header without name, ignoring that one")
			return

		self._current_part = self._on_part_start(disp_params["name"], header.get("Content-Type", None), filename=disp_params["filename"] if "filename" in disp_params else None)

	def _on_part_start(self, name, content_type, filename=None):
		"""
		Called for new parts in the multipart stream. If `filename` is given creates new `file` part (which leads
		to storage of the data as temporary file on disk), if not creates a new `data` part (which stores
		incoming data in memory).

		Structure of `file` parts:

		* `name`: name of the part
		* `filename`: filename associated with the part
		* `path`: path to the temporary file storing the file's data
		* `content_type`: content type of the part
		* `file`: file handle for the temporary file (mode "wb", not deleted on close!)

		Structure of `data` parts:

		* `name`: name of the part
		* `content_type`: content type of the part
		* `data`: bytes of the part (initialized to "")

		:param name: name of the part
		:param content_type: content type of the part
		:param filename: filename associated with the part.
		:return: dict describing the new part
		"""
		if filename is not None:
			# this is a file
			import tempfile
			handle = tempfile.NamedTemporaryFile(mode="wb", prefix=self._file_prefix, suffix=self._file_suffix, dir=self._path, delete=False)
			return dict(name=tornado.escape.utf8(name),
						filename=tornado.escape.utf8(filename),
						path=tornado.escape.utf8(handle.name),
						content_type=tornado.escape.utf8(content_type),
						file=handle)

		else:
			return dict(name=tornado.escape.utf8(name), content_type=content_type, data=b"")

	def _on_part_data(self, part, data):
		"""
		Called when new bytes are received for the given `part`, takes care of writing them to their storage.

		:param part: part for which data was received
		:param data: data chunk which was received
		"""
		if "file" in part:
			part["file"].write(data)
		else:
			part["data"] += data

	def _on_part_finish(self, part):
		"""
		Called when a part gets closed, takes care of storing the finished part in the internal parts storage and for
		`file` parts closing the temporary file and storing the part in the internal files storage.

		:param part: part which was closed
		"""
		name = part["name"]
		self._parts[name] = part
		if "file" in part:
			self._files.append(part["path"])
			part["file"].close()
			del part["file"]

	def _on_request_body_finish(self):
		"""
		Called when the request body has been read completely. Takes care of creating the replacement body out of the
		logged parts, turning `file` parts into new
		:return:
		"""

		self._new_body = b""
		for name, part in self._parts.iteritems():
			if "filename" in part:
				# add form fields for filename, path, size and content_type for all files contained in the request
				fields = dict((self._suffixes[key], value) for (key, value) in dict(name=part["filename"], path=part["path"], size=str(os.stat(part["path"]).st_size), content_type=part["content_type"]).iteritems())
				for n, p in fields.iteritems():
					key = name + "." + n
					self._new_body += b"--%s\r\n" % self._multipart_boundary
					self._new_body += b"Content-Disposition: form-data; name=\"%s\"\r\n" % key
					self._new_body += b"\r\n"
					self._new_body += p + b"\r\n"
			elif "data" in part:
				self._new_body += b"--%s\r\n" % self._multipart_boundary
				value = part["data"]
				self._new_body += b"Content-Disposition: form-data; name=\"%s\"\r\n" % name
				if "content_type" in part and part["content_type"] is not None:
					self._new_body += b"Content-Type: %s\r\n" % part["content_type"]
				self._new_body += b"\r\n"
				self._new_body += value
		self._new_body += b"--%s--\r\n" % self._multipart_boundary

	def _handle_method(self, *args, **kwargs):
		"""
		Handler for any request method, takes care of defining the new request body if necessary and forwarding
		the current request and changed body to the `fallback`.
		"""

		# determine which body to supply
		body = b""
		if self.is_multipart():
			# make sure we really processed all data in the buffer
			while len(self._buffer):
				self._process_multipart_data(self._buffer)

			# use rewritten body
			body = self._new_body

		elif self.request.method in UploadStorageFallbackHandler.BODY_METHODS:
			# directly use data from buffer
			body = self._buffer

		# rewrite content length
		self.request.headers["Content-Length"] = len(body)

		try:
			# call the configured fallback with request and body to use
			self._fallback(self.request, body)
			self._headers_written = True
		finally:
			# make sure the temporary files are removed again
			for f in self._files:
				octoprint.util.silentRemove(f)

	# make all http methods trigger _handle_method
	get = _handle_method
	post = _handle_method
	put = _handle_method
	patch = _handle_method
	delete = _handle_method
	head = _handle_method
	options = _handle_method


class WsgiInputContainer(object):
	"""
	A WSGI container for use with Tornado that allows supplying the request body to be used for `wsgi.input` in the
	generated WSGI environment upon call.

	A `RequestHandler` can thus provide the WSGI application with a stream for the request body, or a modified body.

	Example usage:

		wsgi_app = octoprint.server.util.WsgiInputContainer(octoprint_app)
		application = tornado.web.Application([
			(r".*", UploadStorageFallbackHandler, dict(fallback=wsgi_app),
		])

	The implementation logic is basically the same as `tornado.wsgi.WSGIContainer` but the `__call__` and `environ`
	methods have been adjusted to for an optionally supplied `body` argument which is then used for `wsgi.input`.
	"""

	def __init__(self, wsgi_application):
		self.wsgi_application = wsgi_application

	def __call__(self, request, body=None):
		"""
		Wraps the call against the WSGI app, deriving the WSGI environment from the supplied Tornado `HTTPServerRequest`.

		:param request: the `tornado.httpserver.HTTPServerRequest` to derive the WSGI environment from
		:param body: an optional body  to use as `wsgi.input` instead of `request.body`, can be a string or a stream
		"""

		data = {}
		response = []

		def start_response(status, response_headers, exc_info=None):
			data["status"] = status
			data["headers"] = response_headers
			return response.append
		app_response = self.wsgi_application(
			WsgiInputContainer.environ(request, body), start_response)
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
	def environ(request, body=None):
		"""
		Converts a `tornado.httputil.HTTPServerRequest` to a WSGI environment.

		An optional `body` to be used for populating `wsgi.input` can be supplied (either a string or a stream). If not
		supplied, `request.body` will be wrapped into a `io.BytesIO` stream and used instead.

		:param request: the `tornado.httpserver.HTTPServerRequest` to derive the WSGI environment from
		:param body: an optional body  to use as `wsgi.input` instead of `request.body`, can be a string or a stream
		"""
		from tornado.wsgi import to_wsgi_str
		import sys
		import io

		# determine the request_body to supply as wsgi.input
		if body is not None:
			if isinstance(body, (bytes, str)):
				request_body = io.BytesIO(tornado.escape.utf8(body))
			else:
				request_body = body
		else:
			request_body = io.BytesIO(tornado.escape.utf8(request.body))

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
		"wsgi.input": request_body,
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


#~~ customized HTTP1Connection implementation


class CustomHTTPServer(tornado.httpserver.HTTPServer):
	"""
	Custom implementation of `tornado.httpserver.HTTPServer` that allows defining max body sizes depending on path and
	method.

	The implementation is mostly taken from `tornado.httpserver.HTTPServer`, the only difference is the creation
	of a `CustomHTTP1ConnectionParameters` instance instead of `tornado.http1connection.HTTP1ConnectionParameters`
	which is supplied with the two new constructor arguments `max_body_sizes` and `max_default_body_size` and the
	creation of a `CustomHTTP1ServerConnection` instead of a `tornado.http1connection.HTTP1ServerConnection` upon
	connection by a client.

	`max_body_sizes` is expected to be an iterable containing tuples of the form (method, path regex, maximum body size),
	with method and path regex having to match in order for maximum body size to take affect.

	`default_max_body_size` is the default maximum body size to apply if no specific one from `max_body_sizes` matches.
	"""

	def __init__(self, request_callback, no_keep_alive=False, io_loop=None,
				 xheaders=False, ssl_options=None, protocol=None,
				 decompress_request=False,
				 chunk_size=None, max_header_size=None,
				 idle_connection_timeout=None, body_timeout=None,
				 max_body_sizes=None, default_max_body_size=None, max_buffer_size=None):
		self.request_callback = request_callback
		self.no_keep_alive = no_keep_alive
		self.xheaders = xheaders
		self.protocol = protocol
		self.conn_params = CustomHTTP1ConnectionParameters(
			decompress=decompress_request,
			chunk_size=chunk_size,
			max_header_size=max_header_size,
			header_timeout=idle_connection_timeout or 3600,
			max_body_sizes=max_body_sizes,
			default_max_body_size=default_max_body_size,
			body_timeout=body_timeout)
		tornado.tcpserver.TCPServer.__init__(self, io_loop=io_loop, ssl_options=ssl_options,
						   max_buffer_size=max_buffer_size,
						   read_chunk_size=chunk_size)
		self._connections = set()


	def handle_stream(self, stream, address):
		context = tornado.httpserver._HTTPRequestContext(stream, address,
									  self.protocol)
		conn = CustomHTTP1ServerConnection(
			stream, self.conn_params, context)
		self._connections.add(conn)
		conn.start_serving(self)


class CustomHTTP1ServerConnection(tornado.http1connection.HTTP1ServerConnection):
	"""
	A custom implementation of `tornado.http1connection.HTTP1ServerConnection` which utilizes a `CustomHTTP1Connection`
	instead of a `tornado.http1connection.HTTP1Connection` in `_server_request_loop`. The implementation logic is
	otherwise the same as `tornado.http1connection.HTTP1ServerConnection`.
	"""

	@tornado.gen.coroutine
	def _server_request_loop(self, delegate):
		try:
			while True:
				conn = CustomHTTP1Connection(self.stream, False,
									   self.params, self.context)
				request_delegate = delegate.start_request(self, conn)
				try:
					ret = yield conn.read_response(request_delegate)
				except (tornado.iostream.StreamClosedError,
						tornado.iostream.UnsatisfiableReadError):
					return
				except tornado.http1connection._QuietException:
					# This exception was already logged.
					conn.close()
					return
				except Exception:
					tornado.http1connection.gen_log.error("Uncaught exception", exc_info=True)
					conn.close()
					return
				if not ret:
					return
				yield tornado.gen.moment
		finally:
			delegate.on_close(self)


class CustomHTTP1Connection(tornado.http1connection.HTTP1Connection):
	"""
	A custom implementation of `tornado.http1connection.HTTP1Connection` which upon checking the `Content-Length` of
	the request against the configured maximum utilizes `max_body_sizes` and `default_max_body_size` as a fallback.
	"""

	def __init__(self, stream, is_client, params=None, context=None):
		tornado.http1connection.HTTP1Connection.__init__(self, stream, is_client, params=params, context=context)

		import re
		self._max_body_sizes = map(lambda x: (x[0], re.compile(x[1]), x[2]), self.params.max_body_sizes or dict())
		self._default_max_body_size = self.params.default_max_body_size or self.stream.max_buffer_size

	def _read_body(self, code, headers, delegate):
		"""
		Basically the same as `tornado.http1connection.HTTP1Connection._read_body`, but determines the maximum
		content length individually for the request (utilizing `._get_max_content_length`).

		If the individual max content length is 0 or smaller no content length is checked. If the content length of the
		current request exceeds the individual max content length, the request processing is aborted and an
		`HTTPInputError` is raised.
		"""
		content_length = headers.get("Content-Length")
		if "Content-Length" in headers:
			if "," in headers["Content-Length"]:
				# Proxies sometimes cause Content-Length headers to get
				# duplicated.  If all the values are identical then we can
				# use them but if they differ it's an error.
				pieces = re.split(r',\s*', headers["Content-Length"])
				if any(i != pieces[0] for i in pieces):
					raise tornado.httputil.HTTPInputError(
						"Multiple unequal Content-Lengths: %r" %
						headers["Content-Length"])
				headers["Content-Length"] = pieces[0]
			content_length = int(headers["Content-Length"])

			content_length = int(content_length)
			max_content_length = self._get_max_content_length(self._request_start_line.method, self._request_start_line.path)
			if 0 <= max_content_length < content_length:
				raise tornado.httputil.HTTPInputError("Content-Length too long")
		else:
			content_length = None

		if code == 204:
			# This response code is not allowed to have a non-empty body,
			# and has an implicit length of zero instead of read-until-close.
			# http://www.w3.org/Protocols/rfc2616/rfc2616-sec4.html#sec4.3
			if ("Transfer-Encoding" in headers or
						content_length not in (None, 0)):
				raise tornado.httputil.HTTPInputError(
					"Response with code %d should not have body" % code)
			content_length = 0

		if content_length is not None:
			return self._read_fixed_body(content_length, delegate)
		if headers.get("Transfer-Encoding") == "chunked":
			return self._read_chunked_body(delegate)
		if self.is_client:
			return self._read_body_until_close(delegate)
		return None

	def _get_max_content_length(self, method, path):
		"""
		Gets the max content length for the given method and path. Checks whether method and path match against any
		of the specific maximum content lengths supplied in `max_body_sizes` and returns that as the maximum content
		length if available, otherwise returns `default_max_body_size`.

		:param method: method of the request to match against
		:param path: path od the request to match against
		:return: determine maximum content length to apply to this request, max return 0 for unlimited allowed content
		         length
		"""

		for m, p, s in self._max_body_sizes:
			if method == m and p.match(path):
				return s
		return self._default_max_body_size


class CustomHTTP1ConnectionParameters(tornado.http1connection.HTTP1ConnectionParameters):
	"""
	An implementation of `tornado.http1connection.HTTP1ConnectionParameters` that adds to new parameters
	`max_body_sizes` and `default_max_body_size`.

	For a description of these please see the documentation of `CustomHTTPServer` above.
	"""

	def __init__(self, *args, **kwargs):
		tornado.http1connection.HTTP1ConnectionParameters.__init__(self, args, kwargs)
		self.max_body_sizes = kwargs["max_body_sizes"] if "max_body_sizes" in kwargs else dict()
		self.default_max_body_size = kwargs["default_max_body_size"] if "default_max_body_size" in kwargs else dict()

#~~ customized large response handler


class LargeResponseHandler(tornado.web.StaticFileHandler):

	CHUNK_SIZE = 16 * 1024

	def initialize(self, path, default_filename=None, as_attachment=False, access_validation=None):
		tornado.web.StaticFileHandler.initialize(self, os.path.abspath(path), default_filename)
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
			raise tornado.web.HTTPError(403, "%s is not in root static directory", path)
		if os.path.isdir(abspath) and self.default_filename is not None:
			# need to look at the request.path here for when path is empty
			# but there is some prefix to the path that was already
			# trimmed by the routing
			if not self.request.path.endswith("/"):
				self.redirect(self.request.path + "/")
				return
			abspath = os.path.join(abspath, self.default_filename)
		if not os.path.exists(abspath):
			raise tornado.web.HTTPError(404)
		if not os.path.isfile(abspath):
			raise tornado.web.HTTPError(403, "%s is not a file", path)

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


class UrlForwardHandler(tornado.web.RequestHandler):

	def initialize(self, url=None, as_attachment=False, basename=None, access_validation=None):
		tornado.web.RequestHandler.initialize(self)
		self._url = url
		self._as_attachment = as_attachment
		self._basename = basename
		self._access_validation = access_validation

	@tornado.web.asynchronous
	def get(self, *args, **kwargs):
		if self._access_validation is not None:
			self._access_validation(self.request)

		if self._url is None:
			raise tornado.web.HTTPError(404)

		client = tornado.httpclient.AsyncHTTPClient()
		r = tornado.httpclient.HTTPRequest(url=self._url, method=self.request.method, body=self.request.body, headers=self.request.headers, follow_redirects=False, allow_nonstandard_methods=True)

		try:
			return client.fetch(r, self.handle_response)
		except tornado.web.HTTPError as e:
			if hasattr(e, "response") and e.response:
				self.handle_response(e.response)
			else:
				raise tornado.web.HTTPError(500)

	def handle_response(self, response):
		if response.error and not isinstance(response.error, tornado.web.HTTPError):
			raise tornado.web.HTTPError(500)

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


#~~ Factory method for creating Flask access validation wrappers from the Tornado request context


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

		wsgi_environ = WsgiInputContainer.environ(request)
		with app.request_context(wsgi_environ):
			app.session_interface.open_session(app, flask.request)
			login_manager.reload_user()
			validator(flask.request)
	return f
