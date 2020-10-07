# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import mimetypes
import os
import re
import sys

import tornado
import tornado.escape
import tornado.gen
import tornado.http1connection
import tornado.httpclient
import tornado.httpserver
import tornado.httputil
import tornado.iostream
import tornado.tcpserver
import tornado.util
import tornado.web
from past.builtins import unicode

import octoprint.util

try:
    from urllib.parse import urlparse  # py3
except ImportError:
    from urlparse import urlparse  # py2

from . import PY3


def fix_json_encode():
    """
    This makes tornado.escape.json_encode use octoprint.util.JsonEncoding.encode as fallback in order to allow
    serialization of globally registered types like frozendict and others.
    """

    import json

    from octoprint.util.json import JsonEncoding

    def fixed_json_encode(value):
        return json.dumps(value, default=JsonEncoding.encode, allow_nan=False).replace(
            "</", "<\\/"
        )

    import tornado.escape

    tornado.escape.json_encode = fixed_json_encode


def fix_websocket_check_origin():
    """
    This fixes tornado.websocket.WebSocketHandler.check_origin to do the same origin check against the Host
    header case-insensitively, as defined in RFC6454, Section 4, item 5.
    """

    scheme_translation = {"wss": "https", "ws": "http"}

    def patched_check_origin(self, origin):
        def get_check_tuple(urlstring):
            parsed = urlparse(urlstring)
            scheme = scheme_translation.get(parsed.scheme, parsed.scheme)
            return (
                scheme,
                parsed.hostname,
                parsed.port
                if parsed.port
                else 80
                if scheme == "http"
                else 443
                if scheme == "https"
                else None,
            )

        return get_check_tuple(origin) == get_check_tuple(self.request.full_url())

    import tornado.websocket

    tornado.websocket.WebSocketHandler.check_origin = patched_check_origin


# ~~ More sensible logging


class RequestlessExceptionLoggingMixin(tornado.web.RequestHandler):

    LOG_REQUEST = False

    def log_exception(self, typ, value, tb, *args, **kwargs):
        if isinstance(value, tornado.web.HTTPError):
            if value.log_message:
                format = "%d %s: " + value.log_message
                args = [value.status_code, self._request_summary()] + list(value.args)
                tornado.web.gen_log.warning(format, *args)
        else:
            if self.LOG_REQUEST:
                tornado.web.app_log.error(
                    "Uncaught exception %s\n%r",
                    self._request_summary(),
                    self.request,
                    exc_info=(typ, value, tb),
                )
            else:
                tornado.web.app_log.error(
                    "Uncaught exception %s",
                    self._request_summary(),
                    exc_info=(typ, value, tb),
                )


# ~~ CORS support


class CorsSupportMixin(tornado.web.RequestHandler):
    """
    `tornado.web.RequestHandler <http://tornado.readthedocs.org/en/branch4.0/web.html#request-handlers>`_ mixin that
    makes sure to set CORS headers similarly to the Flask backed API endpoints.
    """

    ENABLE_CORS = False

    def set_default_headers(self):
        origin = self.request.headers.get("Origin")
        if self.request.method != "OPTIONS" and origin and self.ENABLE_CORS:
            self.set_header("Access-Control-Allow-Origin", origin)

    @tornado.gen.coroutine
    def options(self, *args, **kwargs):
        if self.ENABLE_CORS:
            origin = self.request.headers.get("Origin")
            method = self.request.headers.get("Access-Control-Request-Method")

            # Allow the origin which made the XHR
            self.set_header("Access-Control-Allow-Origin", origin)
            # Allow the actual method
            self.set_header("Access-Control-Allow-Methods", method)
            # Allow for 10 seconds
            self.set_header("Access-Control-Max-Age", "10")

            # 'preflight' request contains the non-standard headers the real request will have (like X-Api-Key)
            custom_headers = self.request.headers.get("Access-Control-Request-Headers")
            if custom_headers is not None:
                self.set_header("Access-Control-Allow-Headers", custom_headers)

        self.set_status(204)
        self.finish()


# ~~ WSGI middleware


@tornado.web.stream_request_body
class UploadStorageFallbackHandler(RequestlessExceptionLoggingMixin, CorsSupportMixin):
    """
    A ``RequestHandler`` similar to ``tornado.web.FallbackHandler`` which fetches any files contained in the request bodies
    of content type ``multipart``, stores them in temporary files and supplies the ``fallback`` with the file's ``name``,
    ``content_type``, ``path`` and ``size`` instead via a rewritten body.

    Basically similar to what the nginx upload module does.

    Basic request body example:

    .. code-block:: none

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

    .. code-block:: none

        ------WebKitFormBoundarypYiSUx63abAmhT5C
        Content-Disposition: form-data; name="apikey"

        my_funny_apikey
        ------WebKitFormBoundarypYiSUx63abAmhT5C
        Content-Disposition: form-data; name="select"

        true
        ------WebKitFormBoundarypYiSUx63abAmhT5C
        Content-Disposition: form-data; name="file.path"
        Content-Type: text/plain; charset=utf-8

        /tmp/tmpzupkro
        ------WebKitFormBoundarypYiSUx63abAmhT5C
        Content-Disposition: form-data; name="file.name"
        Content-Type: text/plain; charset=utf-8

        test.gcode
        ------WebKitFormBoundarypYiSUx63abAmhT5C
        Content-Disposition: form-data; name="file.content_type"
        Content-Type: text/plain; charset=utf-8

        application/octet-stream
        ------WebKitFormBoundarypYiSUx63abAmhT5C
        Content-Disposition: form-data; name="file.size"
        Content-Type: text/plain; charset=utf-8

        349182
        ------WebKitFormBoundarypYiSUx63abAmhT5C--

    The underlying application can then access the contained files via their respective paths and just move them
    where necessary.
    """

    BODY_METHODS = ("POST", "PATCH", "PUT")
    """ The request methods that may contain a request body. """

    def initialize(
        self, fallback, file_prefix="tmp", file_suffix="", path=None, suffixes=None
    ):
        if not suffixes:
            suffixes = {}

        self._fallback = fallback
        self._file_prefix = file_prefix
        self._file_suffix = file_suffix
        self._path = path

        self._suffixes = dict(
            (key, key) for key in ("name", "path", "content_type", "size")
        )
        for suffix_type, suffix in suffixes.items():
            if suffix_type in self._suffixes and suffix is not None:
                self._suffixes[suffix_type] = suffix

        # multipart boundary
        self._multipart_boundary = None

        # Parts, files and values will be stored here
        self._parts = {}
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
        :attr:`UploadStorageFallbackHandler.BODY_METHODS`) prepares the multipart parsing if content type fits. If it's a
        body-less request, just calls the ``fallback`` with an empty body and finishes the request.
        """
        if self.request.method in UploadStorageFallbackHandler.BODY_METHODS:
            self._bytes_left = self.request.headers.get("Content-Length", 0)
            self._content_type = self.request.headers.get("Content-Type", None)

            # request might contain a body
            if self.is_multipart():
                if not self._bytes_left:
                    # we don't support requests without a content-length
                    raise tornado.web.HTTPError(
                        411, log_message="No Content-Length supplied"
                    )

                # extract the multipart boundary
                fields = self._content_type.split(";")
                for field in fields:
                    k, sep, v = field.strip().partition("=")
                    if k == "boundary" and v:
                        if v.startswith('"') and v.endswith('"'):
                            self._multipart_boundary = tornado.escape.utf8(v[1:-1])
                        else:
                            self._multipart_boundary = tornado.escape.utf8(v)
                        break
                else:
                    # RFC2046 section 5.1 (as referred to from RFC 7578) defines the boundary
                    # parameter as mandatory for multipart requests:
                    #
                    #     The only mandatory global parameter for the "multipart" media type is
                    #     the boundary parameter, which consists of 1 to 70 characters [...]
                    #
                    # So no boundary? 400 Bad Request
                    raise tornado.web.HTTPError(
                        400, log_message="No multipart boundary supplied"
                    )
        else:
            self._fallback(self.request, b"")
            self._finished = True

    def data_received(self, chunk):
        """
        Called by Tornado on receiving a chunk of the request body. If request is a multipart request, takes care of
        processing the multipart data structure via :func:`_process_multipart_data`. If not, just adds the chunk to
        internal in-memory buffer.

        :param chunk: chunk of data received from Tornado
        """

        data = self._buffer + chunk
        if self.is_multipart():
            self._process_multipart_data(data)
        else:
            self._buffer = data

    def is_multipart(self):
        """Checks whether this request is a ``multipart`` request"""
        return self._content_type is not None and self._content_type.startswith(
            "multipart"
        )

    def _process_multipart_data(self, data):
        """
        Processes the given data, parsing it for multipart definitions and calling the appropriate methods.

        :param data: the data to process as a string
        """

        # check for boundary
        delimiter = b"--%s" % self._multipart_boundary
        delimiter_loc = data.find(delimiter)
        delimiter_len = len(delimiter)
        end_of_header = -1
        if delimiter_loc != -1:
            # found the delimiter in the currently available data
            delimiter_data_end = 0 if delimiter_loc == 0 else delimiter_loc - 2
            data, self._buffer = data[0:delimiter_data_end], data[delimiter_loc:]
            end_of_header = self._buffer.find(b"\r\n\r\n")
        else:
            # make sure any boundary (with single or double ==) contained at the end of chunk does not get
            # truncated by this processing round => save it to the buffer for next round
            endlen = len(self._multipart_boundary) + 4
            data, self._buffer = data[0:-endlen], data[-endlen:]

        # stream data to part handler
        if data and self._current_part:
            self._on_part_data(self._current_part, data)

        if end_of_header >= 0:
            self._on_part_header(self._buffer[delimiter_len + 2 : end_of_header])
            self._buffer = self._buffer[end_of_header + 4 :]

        if delimiter_loc != -1 and self._buffer.strip() == delimiter + b"--":
            # we saw the last boundary and are at the end of our request
            if self._current_part:
                self._on_part_finish(self._current_part)
                self._current_part = None
            self._buffer = b""
            self._on_request_body_finish()

    def _on_part_header(self, header):
        """
        Called for a new multipart header, takes care of parsing the header and calling :func:`_on_part` with the
        relevant data, setting the current part in the process.

        :param header: header to parse
        """

        # close any open parts
        if self._current_part:
            self._on_part_finish(self._current_part)
            self._current_part = None

        header_check = header.find(self._multipart_boundary)
        if header_check != -1:
            self._logger.warning(
                "Header still contained multipart boundary, stripping it..."
            )
            header = header[header_check:]

        # convert to dict
        try:
            header = tornado.httputil.HTTPHeaders.parse(header.decode("utf-8"))
        except UnicodeDecodeError:
            try:
                header = tornado.httputil.HTTPHeaders.parse(header.decode("iso-8859-1"))
            except Exception:
                # looks like we couldn't decode something here neither as UTF-8 nor ISO-8859-1
                self._logger.warning(
                    "Could not decode multipart headers in request, should be either UTF-8 or ISO-8859-1"
                )
                self.send_error(400)
                return

        disp_header = header.get("Content-Disposition", "")
        disposition, disp_params = _parse_header(disp_header, strip_quotes=False)

        if disposition != "form-data":
            self._logger.warning(
                "Got a multipart header without form-data content disposition, ignoring that one"
            )
            return
        if not disp_params.get("name"):
            self._logger.warning("Got a multipart header without name, ignoring that one")
            return

        filename = disp_params.get("filename*", None)  # RFC 5987 header present?
        if filename is not None:
            try:
                filename = _extended_header_value(filename)
            except Exception:
                # parse error, this is not RFC 5987 compliant after all
                self._logger.warning(
                    "extended filename* value {!r} is not RFC 5987 compliant".format(
                        filename
                    )
                )
                self.send_error(400)
                return
        else:
            # no filename* header, just strip quotes from filename header then and be done
            filename = _strip_value_quotes(disp_params.get("filename", None))

        self._current_part = self._on_part_start(
            _strip_value_quotes(disp_params["name"]),
            header.get("Content-Type", None),
            filename=filename,
        )

    def _on_part_start(self, name, content_type, filename=None):
        """
        Called for new parts in the multipart stream. If ``filename`` is given creates new ``file`` part (which leads
        to storage of the data as temporary file on disk), if not creates a new ``data`` part (which stores
        incoming data in memory).

        Structure of ``file`` parts:

        * ``name``: name of the part
        * ``filename``: filename associated with the part
        * ``path``: path to the temporary file storing the file's data
        * ``content_type``: content type of the part
        * ``file``: file handle for the temporary file (mode "wb", not deleted on close, will be deleted however after
          handling of the request has finished in :func:`_handle_method`)

        Structure of ``data`` parts:

        * ``name``: name of the part
        * ``content_type``: content type of the part
        * ``data``: bytes of the part (initialized to an empty string)

        :param name: name of the part
        :param content_type: content type of the part
        :param filename: filename associated with the part.
        :return: dict describing the new part
        """
        if filename is not None:
            # this is a file
            import tempfile

            handle = tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=self._file_prefix,
                suffix=self._file_suffix,
                dir=self._path,
                delete=False,
            )
            return {
                "name": tornado.escape.utf8(name),
                "filename": tornado.escape.utf8(filename),
                "path": tornado.escape.utf8(handle.name),
                "content_type": tornado.escape.utf8(content_type),
                "file": handle,
            }

        else:
            return {
                "name": tornado.escape.utf8(name),
                "content_type": tornado.escape.utf8(content_type),
                "data": b"",
            }

    def _on_part_data(self, part, data):
        """
        Called when new bytes are received for the given ``part``, takes care of writing them to their storage.

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
        ``file`` parts closing the temporary file and storing the part in the internal files storage.

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
        logged parts, turning ``file`` parts into new ``data`` parts.
        """

        self._new_body = b""
        for name, part in self._parts.items():
            if "filename" in part:
                # add form fields for filename, path, size and content_type for all files contained in the request
                if "path" not in part:
                    continue

                parameters = {
                    "name": part["filename"],
                    "path": part["path"],
                    "size": str(os.stat(part["path"]).st_size),
                }
                if "content_type" in part:
                    parameters["content_type"] = part["content_type"]

                fields = dict(
                    (self._suffixes[key], value) for (key, value) in parameters.items()
                )
                for n, p in fields.items():
                    if n is None or p is None:
                        continue
                    key = name + b"." + octoprint.util.to_bytes(n)
                    self._new_body += b"--%s\r\n" % self._multipart_boundary
                    self._new_body += (
                        b'Content-Disposition: form-data; name="%s"\r\n' % key
                    )
                    self._new_body += b"Content-Type: text/plain; charset=utf-8\r\n"
                    self._new_body += b"\r\n"
                    self._new_body += octoprint.util.to_bytes(p) + b"\r\n"
            elif "data" in part:
                self._new_body += b"--%s\r\n" % self._multipart_boundary
                value = part["data"]
                self._new_body += b'Content-Disposition: form-data; name="%s"\r\n' % name
                if "content_type" in part and part["content_type"] is not None:
                    self._new_body += b"Content-Type: %s\r\n" % part["content_type"]
                self._new_body += b"\r\n"
                self._new_body += value + b"\r\n"
        self._new_body += b"--%s--\r\n" % self._multipart_boundary

    def _handle_method(self, *args, **kwargs):
        """
        Takes care of defining the new request body if necessary and forwarding
        the current request and changed body to the ``fallback``.
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
                octoprint.util.silent_remove(f)

    # make all http methods trigger _handle_method
    get = _handle_method
    post = _handle_method
    put = _handle_method
    patch = _handle_method
    delete = _handle_method
    head = _handle_method
    options = _handle_method


def _parse_header(line, strip_quotes=True):
    parts = tornado.httputil._parseparam(";" + line)
    key = next(parts)
    pdict = {}
    for p in parts:
        i = p.find("=")
        if i >= 0:
            name = p[:i].strip().lower()
            value = p[i + 1 :].strip()
            if strip_quotes:
                value = _strip_value_quotes(value)
            pdict[name] = value
    return key, pdict


def _strip_value_quotes(value):
    if not value:
        return value

    if len(value) >= 2 and value[0] == value[-1] == '"':
        value = value[1:-1]
        value = value.replace("\\\\", "\\").replace('\\"', '"')

    return value


def _extended_header_value(value):
    if not value:
        return value

    if value.lower().startswith("iso-8859-1'") or value.lower().startswith("utf-8'"):
        # RFC 5987 section 3.2
        try:
            from urllib import unquote
        except ImportError:
            from urllib.parse import unquote
        encoding, _, value = value.split("'", 2)
        if PY3:
            return unquote(value, encoding=encoding)
        else:
            return unquote(octoprint.util.to_bytes(value, encoding="iso-8859-1")).decode(
                encoding
            )
    else:
        # no encoding provided, strip potentially present quotes and call it a day
        return octoprint.util.to_unicode(_strip_value_quotes(value), encoding="utf-8")


class WsgiInputContainer(object):
    """
    A WSGI container for use with Tornado that allows supplying the request body to be used for ``wsgi.input`` in the
    generated WSGI environment upon call.

    A ``RequestHandler`` can thus provide the WSGI application with a stream for the request body, or a modified body.

    Example usage:

    .. code-block:: python

       wsgi_app = octoprint.server.util.WsgiInputContainer(octoprint_app)
       application = tornado.web.Application([
           (r".*", UploadStorageFallbackHandler, dict(fallback=wsgi_app),
       ])

    The implementation logic is basically the same as ``tornado.wsgi.WSGIContainer`` but the ``__call__`` and ``environ``
    methods have been adjusted to allow for an optionally supplied ``body`` argument which is then used for ``wsgi.input``.
    """

    def __init__(
        self, wsgi_application, headers=None, forced_headers=None, removed_headers=None
    ):
        self.wsgi_application = wsgi_application

        if headers is None:
            headers = {}
        if forced_headers is None:
            forced_headers = {}
        if removed_headers is None:
            removed_headers = []

        self.headers = headers
        self.forced_headers = forced_headers
        self.removed_headers = removed_headers

    def __call__(self, request, body=None):
        """
        Wraps the call against the WSGI app, deriving the WSGI environment from the supplied Tornado ``HTTPServerRequest``.

        :param request: the ``tornado.httpserver.HTTPServerRequest`` to derive the WSGI environment from
        :param body: an optional body  to use as ``wsgi.input`` instead of ``request.body``, can be a string or a stream
        """

        data = {}
        response = []

        def start_response(status, response_headers, exc_info=None):
            data["status"] = status
            data["headers"] = response_headers
            return response.append

        app_response = self.wsgi_application(
            WsgiInputContainer.environ(request, body), start_response
        )
        try:
            response.extend(app_response)
            body = b"".join(response)
        finally:
            if hasattr(app_response, "close"):
                app_response.close()
        if not data:
            raise Exception("WSGI app did not call start_response")

        status_code, reason = data["status"].split(" ", 1)
        status_code = int(status_code)
        headers = data["headers"]
        header_set = {k.lower() for (k, v) in headers}
        body = tornado.escape.utf8(body)
        if status_code != 304:
            if "content-length" not in header_set:
                headers.append(("Content-Length", str(len(body))))
            if "content-type" not in header_set:
                headers.append(("Content-Type", "text/html; charset=UTF-8"))

        header_set = {k.lower() for (k, v) in headers}
        for header, value in self.headers.items():
            if header.lower() not in header_set:
                headers.append((header, value))
        for header, value in self.forced_headers.items():
            headers.append((header, value))
        headers = [
            (header, value)
            for header, value in headers
            if header.lower() not in self.removed_headers
        ]

        start_line = tornado.httputil.ResponseStartLine("HTTP/1.1", status_code, reason)
        header_obj = tornado.httputil.HTTPHeaders()
        for key, value in headers:
            header_obj.add(key, value)
        request.connection.write_headers(start_line, header_obj, chunk=body)
        request.connection.finish()
        self._log(status_code, request)

    @staticmethod
    def environ(request, body=None):
        """
        Converts a ``tornado.httputil.HTTPServerRequest`` to a WSGI environment.

        An optional ``body`` to be used for populating ``wsgi.input`` can be supplied (either a string or a stream). If not
        supplied, ``request.body`` will be wrapped into a ``io.BytesIO`` stream and used instead.

        :param request: the ``tornado.httpserver.HTTPServerRequest`` to derive the WSGI environment from
        :param body: an optional body  to use as ``wsgi.input`` instead of ``request.body``, can be a string or a stream
        """
        import io

        from tornado.wsgi import to_wsgi_str

        # determine the request_body to supply as wsgi.input
        if body is not None:
            if isinstance(body, (bytes, str, unicode)):
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
            "PATH_INFO": to_wsgi_str(
                tornado.escape.url_unescape(request.path, encoding=None, plus=False)
            ),
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
        summary = request.method + " " + request.uri + " (" + request.remote_ip + ")"
        log_method("%d %s %.2fms", status_code, summary, request_time)


# ~~ customized HTTP1Connection implementation


class CustomHTTPServer(tornado.httpserver.HTTPServer):
    """
    Custom implementation of ``tornado.httpserver.HTTPServer`` that allows defining max body sizes depending on path and
    method.

    The implementation is mostly taken from ``tornado.httpserver.HTTPServer``, the only difference is the creation
    of a ``CustomHTTP1ConnectionParameters`` instance instead of ``tornado.http1connection.HTTP1ConnectionParameters``
    which is supplied with the two new constructor arguments ``max_body_sizes`` and ``max_default_body_size`` and the
    creation of a ``CustomHTTP1ServerConnection`` instead of a ``tornado.http1connection.HTTP1ServerConnection`` upon
    connection by a client.

    ``max_body_sizes`` is expected to be an iterable containing tuples of the form (method, path regex, maximum body size),
    with method and path regex having to match in order for maximum body size to take affect.

    ``default_max_body_size`` is the default maximum body size to apply if no specific one from ``max_body_sizes`` matches.
    """

    def __init__(self, *args, **kwargs):
        pass

    def initialize(self, *args, **kwargs):
        default_max_body_size = kwargs.pop("default_max_body_size", None)
        max_body_sizes = kwargs.pop("max_body_sizes", None)

        tornado.httpserver.HTTPServer.initialize(self, *args, **kwargs)

        additional = {
            "default_max_body_size": default_max_body_size,
            "max_body_sizes": max_body_sizes,
        }
        self.conn_params = CustomHTTP1ConnectionParameters.from_stock_params(
            self.conn_params, **additional
        )

    def handle_stream(self, stream, address):
        context = tornado.httpserver._HTTPRequestContext(
            stream, address, self.protocol, self.trusted_downstream
        )
        conn = CustomHTTP1ServerConnection(stream, self.conn_params, context)
        self._connections.add(conn)
        conn.start_serving(self)


class CustomHTTP1ServerConnection(tornado.http1connection.HTTP1ServerConnection):
    """
    A custom implementation of ``tornado.http1connection.HTTP1ServerConnection`` which utilizes a ``CustomHTTP1Connection``
    instead of a ``tornado.http1connection.HTTP1Connection`` in ``_server_request_loop``. The implementation logic is
    otherwise the same as ``tornado.http1connection.HTTP1ServerConnection``.
    """

    @tornado.gen.coroutine
    def _server_request_loop(self, delegate):
        try:
            while True:
                conn = CustomHTTP1Connection(
                    self.stream, False, self.params, self.context
                )
                request_delegate = delegate.start_request(self, conn)
                try:
                    ret = yield conn.read_response(request_delegate)
                except (
                    tornado.iostream.StreamClosedError,
                    tornado.iostream.UnsatisfiableReadError,
                ):
                    return
                except tornado.http1connection._QuietException:
                    # This exception was already logged.
                    conn.close()
                    return
                except Exception:
                    tornado.http1connection.gen_log.error(
                        "Uncaught exception", exc_info=True
                    )
                    conn.close()
                    return
                if not ret:
                    return
                yield tornado.gen.moment
        finally:
            delegate.on_close(self)


class CustomHTTP1Connection(tornado.http1connection.HTTP1Connection):
    """
    A custom implementation of ``tornado.http1connection.HTTP1Connection`` which upon checking the ``Content-Length`` of
    the request against the configured maximum utilizes ``max_body_sizes`` and ``default_max_body_size`` as a fallback.
    """

    def __init__(self, stream, is_client, params=None, context=None):
        if params is None:
            params = CustomHTTP1ConnectionParameters()

        tornado.http1connection.HTTP1Connection.__init__(
            self, stream, is_client, params=params, context=context
        )

        import re

        self._max_body_sizes = list(
            map(
                lambda x: (x[0], re.compile(x[1]), x[2]),
                self.params.max_body_sizes or list(),
            )
        )
        self._default_max_body_size = (
            self.params.default_max_body_size or self.stream.max_buffer_size
        )

    def _read_body(self, code, headers, delegate):
        """
        Basically the same as ``tornado.http1connection.HTTP1Connection._read_body``, but determines the maximum
        content length individually for the request (utilizing ``._get_max_content_length``).

        If the individual max content length is 0 or smaller no content length is checked. If the content length of the
        current request exceeds the individual max content length, the request processing is aborted and an
        ``HTTPInputError`` is raised.
        """
        if "Content-Length" in headers:
            if "Transfer-Encoding" in headers:
                # Response cannot contain both Content-Length and
                # Transfer-Encoding headers.
                # http://tools.ietf.org/html/rfc7230#section-3.3.3
                raise tornado.httputil.HTTPInputError(
                    "Response with both Transfer-Encoding and Content-Length"
                )
            if "," in headers["Content-Length"]:
                # Proxies sometimes cause Content-Length headers to get
                # duplicated.  If all the values are identical then we can
                # use them but if they differ it's an error.
                pieces = re.split(r",\s*", headers["Content-Length"])
                if any(i != pieces[0] for i in pieces):
                    raise tornado.httputil.HTTPInputError(
                        "Multiple unequal Content-Lengths: %r" % headers["Content-Length"]
                    )
                headers["Content-Length"] = pieces[0]

            try:
                content_length = int(headers["Content-Length"])
            except ValueError:
                # Handles non-integer Content-Length value.
                raise tornado.httputil.HTTPInputError(
                    "Only integer Content-Length is allowed: %s"
                    % headers["Content-Length"]
                )

            max_content_length = self._get_max_content_length(
                self._request_start_line.method, self._request_start_line.path
            )
            if (
                max_content_length is not None
                and 0 <= max_content_length < content_length
            ):
                raise tornado.httputil.HTTPInputError("Content-Length too long")
        else:
            content_length = None

        if code == 204:
            # This response code is not allowed to have a non-empty body,
            # and has an implicit length of zero instead of read-until-close.
            # http://www.w3.org/Protocols/rfc2616/rfc2616-sec4.html#sec4.3
            if "Transfer-Encoding" in headers or content_length not in (None, 0):
                raise tornado.httputil.HTTPInputError(
                    "Response with code %d should not have body" % code
                )
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
        of the specific maximum content lengths supplied in ``max_body_sizes`` and returns that as the maximum content
        length if available, otherwise returns ``default_max_body_size``.

        :param method: method of the request to match against
        :param path: path of the request to match against
        :return: determine maximum content length to apply to this request, max return 0 for unlimited allowed content
                 length
        """

        for m, p, s in self._max_body_sizes:
            if method == m and p.match(path):
                return s
        return self._default_max_body_size


class CustomHTTP1ConnectionParameters(tornado.http1connection.HTTP1ConnectionParameters):
    """
    An implementation of ``tornado.http1connection.HTTP1ConnectionParameters`` that adds two new parameters
    ``max_body_sizes`` and ``default_max_body_size``.

    For a description of these please see the documentation of ``CustomHTTPServer`` above.
    """

    def __init__(self, *args, **kwargs):
        max_body_sizes = kwargs.pop("max_body_sizes", list())
        default_max_body_size = kwargs.pop("default_max_body_size", None)

        tornado.http1connection.HTTP1ConnectionParameters.__init__(self, *args, **kwargs)

        self.max_body_sizes = max_body_sizes
        self.default_max_body_size = default_max_body_size

    @classmethod
    def from_stock_params(cls, other, **additional):
        kwargs = dict(other.__dict__)
        for key, value in additional.items():
            kwargs[key] = value
        return cls(**kwargs)


# ~~ customized large response handler


class LargeResponseHandler(
    RequestlessExceptionLoggingMixin, CorsSupportMixin, tornado.web.StaticFileHandler
):
    """
    Customized `tornado.web.StaticFileHandler <http://tornado.readthedocs.org/en/branch4.0/web.html#tornado.web.StaticFileHandler>`_
    that allows delivery of the requested resource as attachment and access and request path validation through
    optional callbacks. Note that access validation takes place before path validation.

    Arguments:
       path (str): The system path from which to serve files (this will be forwarded to the ``initialize`` method of
           :class:``~tornado.web.StaticFileHandler``)
       default_filename (str): The default filename to serve if none is explicitly specified and the request references
           a subdirectory of the served path (this will be forwarded to the ``initialize`` method of
           :class:``~tornado.web.StaticFileHandler`` as the ``default_filename`` keyword parameter). Defaults to ``None``.
       as_attachment (bool): Whether to serve requested files with ``Content-Disposition: attachment`` header (``True``)
           or not. Defaults to ``False``.
       allow_client_caching (bool): Whether to allow the client to cache (by not setting any ``Cache-Control`` or
           ``Expires`` headers on the response) or not.
       access_validation (function): Callback to call in the ``get`` method to validate access to the resource. Will
           be called with ``self.request`` as parameter which contains the full tornado request object. Should raise
           a ``tornado.web.HTTPError`` if access is not allowed in which case the request will not be further processed.
           Defaults to ``None`` and hence no access validation being performed.
       path_validation (function): Callback to call in the ``get`` method to validate the requested path. Will be called
           with the requested path as parameter. Should raise a ``tornado.web.HTTPError`` (e.g. an 404) if the requested
           path does not pass validation in which case the request will not be further processed.
           Defaults to ``None`` and hence no path validation being performed.
       etag_generator (function): Callback to call for generating the value of the ETag response header. Will be
           called with the response handler as parameter. May return ``None`` to prevent the ETag response header
           from being set. If not provided the last modified time of the file in question will be used as returned
           by ``get_content_version``.
       name_generator (function): Callback to call for generating the value of the attachment file name header. Will be
           called with the requested path as parameter.
       mime_type_guesser (function): Callback to guess the mime type to use for the content type encoding of the
           response. Will be called with the requested path on disk as parameter.
       is_pre_compressed (bool): if the file is expected to be pre-compressed, i.e, if there is a file in the same
           directory with the same name, but with '.gz' appended and gzip-encoded
    """

    def initialize(
        self,
        path,
        default_filename=None,
        as_attachment=False,
        allow_client_caching=True,
        access_validation=None,
        path_validation=None,
        etag_generator=None,
        name_generator=None,
        mime_type_guesser=None,
        is_pre_compressed=False,
        stream_body=False,
    ):
        tornado.web.StaticFileHandler.initialize(
            self, os.path.abspath(path), default_filename
        )
        self._as_attachment = as_attachment
        self._allow_client_caching = allow_client_caching
        self._access_validation = access_validation
        self._path_validation = path_validation
        self._etag_generator = etag_generator
        self._name_generator = name_generator
        self._mime_type_guesser = mime_type_guesser
        self._is_pre_compressed = is_pre_compressed
        self._stream_body = stream_body

    def should_use_precompressed(self):
        return self._is_pre_compressed and "gzip" in self.request.headers.get(
            "Accept-Encoding", ""
        )

    def get(self, path, include_body=True):
        if self._access_validation is not None:
            self._access_validation(self.request)
        if self._path_validation is not None:
            self._path_validation(path)

        if "cookie" in self.request.arguments:
            self.set_cookie(self.request.arguments["cookie"][0], "true", path="/")

        if self.should_use_precompressed():
            if os.path.exists(os.path.join(self.root, path + ".gz")):
                self.set_header("Content-Encoding", "gzip")
                path = path + ".gz"
            else:
                logging.getLogger(__name__).warning(
                    "Precompressed assets expected but {}.gz does not exist "
                    "in {}, using plain file instead.".format(path, self.root)
                )

        if self._stream_body:
            return self.streamed_get(path, include_body=include_body)
        else:
            return tornado.web.StaticFileHandler.get(
                self, path, include_body=include_body
            )

    @tornado.gen.coroutine
    def streamed_get(self, path, include_body=True):
        """
        Version of StaticFileHandler.get that doesn't support ranges or ETag but streams the content. Helpful for files
        that might still change while being transmitted (e.g. log files)
        """

        # Set up our path instance variables.
        self.path = self.parse_url_path(path)
        del path  # make sure we don't refer to path instead of self.path again
        absolute_path = self.get_absolute_path(self.root, self.path)
        self.absolute_path = self.validate_absolute_path(self.root, absolute_path)
        if self.absolute_path is None:
            return

        content_type = self.get_content_type()
        if content_type:
            self.set_header("Content-Type", content_type)
        self.set_extra_headers(self.path)

        if include_body:
            content = self.get_content(self.absolute_path)
            if isinstance(content, bytes):
                content = [content]
            for chunk in content:
                try:
                    self.write(chunk)
                    yield self.flush()
                except tornado.iostream.StreamClosedError:
                    return
        else:
            assert self.request.method == "HEAD"

    def set_extra_headers(self, path):
        if self._as_attachment:
            filename = None
            if callable(self._name_generator):
                filename = self._name_generator(path)
            if filename is None:
                filename = os.path.basename(path)

            filename = tornado.escape.url_escape(filename, plus=False)
            self.set_header(
                "Content-Disposition",
                "attachment; filename=\"{}\"; filename*=UTF-8''{}".format(
                    filename, filename
                ),
            )

        if not self._allow_client_caching:
            self.set_header("Cache-Control", "max-age=0, must-revalidate, private")
            self.set_header("Expires", "-1")

    @property
    def original_absolute_path(self):
        """The path of the uncompressed file corresponding to the compressed file"""
        if self._is_pre_compressed:
            return self.absolute_path.rstrip(".gz")
        return self.absolute_path

    def compute_etag(self):
        if self._etag_generator is not None:
            return self._etag_generator(self)
        else:
            return self.get_content_version(self.absolute_path)

    # noinspection PyAttributeOutsideInit
    def get_content_type(self):
        if self._mime_type_guesser is not None:
            type = self._mime_type_guesser(self.original_absolute_path)
            if type is not None:
                return type

        correct_absolute_path = None
        try:
            # reset self.absolute_path temporarily
            if self.should_use_precompressed():
                correct_absolute_path = self.absolute_path
                self.absolute_path = self.original_absolute_path
            return tornado.web.StaticFileHandler.get_content_type(self)
        finally:
            # restore self.absolute_path
            if self.should_use_precompressed() and correct_absolute_path is not None:
                self.absolute_path = correct_absolute_path

    @classmethod
    def get_content_version(cls, abspath):
        import os
        import stat

        return os.stat(abspath)[stat.ST_MTIME]


##~~ URL Forward Handler for forwarding requests to a preconfigured static URL


class UrlProxyHandler(
    RequestlessExceptionLoggingMixin, CorsSupportMixin, tornado.web.RequestHandler
):
    """
    `tornado.web.RequestHandler <http://tornado.readthedocs.org/en/branch4.0/web.html#request-handlers>`_ that proxies
    requests to a preconfigured url and returns the response. Allows delivery of the requested content as attachment
    and access validation through an optional callback.

    This will use `tornado.httpclient.AsyncHTTPClient <http://tornado.readthedocs.org/en/branch4.0/httpclient.html#tornado.httpclient.AsyncHTTPClient>`_
    for making the request to the configured endpoint and return the body of the client response with the status code
    from the client response and the following headers:

      * ``Date``, ``Cache-Control``, ``Expires``, ``ETag``, ``Server``, ``Content-Type`` and ``Location`` will be copied over.
      * If ``as_attachment`` is set to True, ``Content-Disposition`` will be set to ``attachment``. If ``basename`` is
        set including the attachment's ``filename`` attribute will be set to the base name followed by the extension
        guessed based on the MIME type from the ``Content-Type`` header of the response. If no extension can be guessed
        no ``filename`` attribute will be set.

    Arguments:
       url (str): URL to forward any requests to. A 404 response will be returned if this is not set. Defaults to ``None``.
       as_attachment (bool): Whether to serve files with ``Content-Disposition: attachment`` header (``True``)
           or not. Defaults to ``False``.
       basename (str): base name of file names to return as part of the attachment header, see above. Defaults to ``None``.
       access_validation (function): Callback to call in the ``get`` method to validate access to the resource. Will
           be called with ``self.request`` as parameter which contains the full tornado request object. Should raise
           a ``tornado.web.HTTPError`` if access is not allowed in which case the request will not be further processed.
           Defaults to ``None`` and hence no access validation being performed.
    """

    def initialize(
        self, url=None, as_attachment=False, basename=None, access_validation=None
    ):
        tornado.web.RequestHandler.initialize(self)
        self._url = url
        self._as_attachment = as_attachment
        self._basename = basename
        self._access_validation = access_validation

    @tornado.gen.coroutine
    def get(self, *args, **kwargs):
        if self._access_validation is not None:
            self._access_validation(self.request)

        if self._url is None:
            raise tornado.web.HTTPError(404)

        client = tornado.httpclient.AsyncHTTPClient()
        r = tornado.httpclient.HTTPRequest(
            url=self._url,
            method=self.request.method,
            body=self.request.body,
            headers=self.request.headers,
            follow_redirects=False,
            allow_nonstandard_methods=True,
        )

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
        for name in (
            "Date",
            "Cache-Control",
            "Server",
            "Content-Type",
            "Location",
            "Expires",
            "ETag",
        ):
            value = response.headers.get(name)
            if value:
                self.set_header(name, value)

                if name == "Content-Type":
                    filename = self.get_filename(value)

        if self._as_attachment:
            if filename is not None:
                self.set_header(
                    "Content-Disposition", "attachment; filename=%s" % filename
                )
            else:
                self.set_header("Content-Disposition", "attachment")

        if response.body:
            self.write(response.body)
        self.finish()

    def get_filename(self, content_type):
        if not self._basename:
            return None

        typeValue = list(x.strip() for x in content_type.split(";"))
        if len(typeValue) == 0:
            return None

        extension = mimetypes.guess_extension(typeValue[0])
        if not extension:
            return None

        return "%s%s" % (self._basename, extension)


class StaticDataHandler(
    RequestlessExceptionLoggingMixin, CorsSupportMixin, tornado.web.RequestHandler
):
    """
    `tornado.web.RequestHandler <http://tornado.readthedocs.org/en/branch4.0/web.html#request-handlers>`_ that returns
    static ``data`` of a configured ``content_type``.

    Arguments:
       data (str): The data with which to respond
       content_type (str): The content type with which to respond. Defaults to ``text/plain``
    """

    def initialize(self, data="", content_type="text/plain"):
        self.data = data
        self.content_type = content_type

    def get(self, *args, **kwargs):
        self.set_status(200)
        self.set_header("Content-Type", self.content_type)
        self.write(self.data)
        self.flush()
        self.finish()


class DeprecatedEndpointHandler(CorsSupportMixin, tornado.web.RequestHandler):
    """
    `tornado.web.RequestHandler <http://tornado.readthedocs.org/en/branch4.0/web.html#request-handlers>`_ that redirects
    to another ``url`` and logs a deprecation warning.

    Arguments:
       url (str): URL to which to redirect
    """

    def initialize(self, url):
        self._url = url
        self._logger = logging.getLogger(__name__)

    def _handle_method(self, *args, **kwargs):
        to_url = self._url.format(*args)
        self._logger.info(
            "Redirecting deprecated endpoint {} to {}".format(self.request.path, to_url)
        )
        self.redirect(to_url, permanent=True)

    # make all http methods trigger _handle_method
    get = _handle_method
    post = _handle_method
    put = _handle_method
    patch = _handle_method
    delete = _handle_method
    head = _handle_method
    options = _handle_method


class GlobalHeaderTransform(tornado.web.OutputTransform):

    HEADERS = {}
    FORCED_HEADERS = {}
    REMOVED_HEADERS = []

    @classmethod
    def for_headers(cls, name, headers=None, forced_headers=None, removed_headers=None):
        if headers is None:
            headers = {}
        if forced_headers is None:
            forced_headers = {}
        if removed_headers is None:
            removed_headers = []

        return type(
            octoprint.util.to_native_str(name),
            (GlobalHeaderTransform,),
            {
                "HEADERS": headers,
                "FORCED_HEADERS": forced_headers,
                "REMOVED_HEADERS": removed_headers,
            },
        )

    def __init__(self, request):
        tornado.web.OutputTransform.__init__(self, request)

    def transform_first_chunk(self, status_code, headers, chunk, finishing):
        for header, value in self.HEADERS.items():
            if header not in headers:
                headers[header] = value
        for header, value in self.FORCED_HEADERS.items():
            headers[header] = value
        for header in self.REMOVED_HEADERS:
            del headers[header]
        return status_code, headers, chunk


# ~~ Factory method for creating Flask access validation wrappers from the Tornado request context


def access_validation_factory(app, validator, *args):
    """
    Creates an access validation wrapper using the supplied validator.

    :param validator: the access validator to use inside the validation wrapper
    :return: an access validator taking a request as parameter and performing the request validation
    """

    # noinspection PyProtectedMember
    def f(request):
        """
        Creates a custom wsgi and Flask request context in order to be able to process user information
        stored in the current session.

        :param request: The Tornado request for which to create the environment and context
        """
        import flask

        wsgi_environ = WsgiInputContainer.environ(request)
        with app.request_context(wsgi_environ):
            session = app.session_interface.open_session(app, flask.request)
            user_id = session.get("_user_id")
            user = None

            # Yes, using protected methods is ugly. But these used to be publicly available in former versions
            # of flask-login, there are no replacements, and seeing them renamed & hidden in a minor version release
            # without any mention in the changelog means the public API ain't strictly stable either, so we might
            # as well make our life easier here and just use them...
            if user_id is not None and app.login_manager._user_callback is not None:
                user = app.login_manager._user_callback(user_id)
            app.login_manager._update_request_context_with_user(user)

            validator(flask.request, *args)

    return f


def path_validation_factory(path_filter, status_code=404):
    """
    Creates a request path validation wrapper returning the defined status code if the supplied path_filter returns False.

    :param path_filter: the path filter to use on the requested path, should return False for requests that should
       be responded with the provided error code.
    :return: a request path validator taking a request path as parameter and performing the request validation
    """

    def f(path):
        if not path_filter(path):
            raise tornado.web.HTTPError(status_code)

    return f


def validation_chain(*validators):
    def f(request):
        for validator in validators:
            validator(request)

    return f
