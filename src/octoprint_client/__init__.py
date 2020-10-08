# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

import io
import json
import time

import requests
import websocket


def build_base_url(
    https=False, httpuser=None, httppass=None, host=None, port=None, prefix=None
):
    protocol = "https" if https else "http"
    httpauth = "{}:{}@".format(httpuser, httppass) if httpuser and httppass else ""
    host = host if host else "127.0.0.1"
    port = ":{}".format(port) if port else ":5000"
    prefix = prefix if prefix else ""

    return "{}://{}{}{}{}".format(protocol, httpauth, host, port, prefix)


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
            except Exception:
                # we can't handle that in any meaningful way right now
                pass

        # prepare a bunch of callback methods
        import functools

        callbacks = {}
        for callback in ("on_open", "on_message", "on_error", "on_close"):
            # now, normally we could just use functools.partial for something like
            # this, but websocket does a type check against a python function type
            # which the use of partial makes fail, so we have to use a lambda
            # wrapper here, and since we need to pick the current value of
            # callback from the current scope we need a factory method for that...
            def factory(cb):
                return lambda *fargs, **fkwargs: functools.partial(self._on_callback, cb)(
                    *fargs, **fkwargs
                )

            callbacks[callback] = factory(callback)

        # initialize socket instance with url and callbacks
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
            if callable(cb_func):
                cb_func(*args, **kwargs)

        cb_func = self._ws_kwargs.get(cb, None)
        if callable(cb_func):
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

        If disconnect is set to ``True`` will disconnect the socket explicitly
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
            timeout_condition = (
                lambda: start is not None and time.time() > start + timeout
            )
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


class Client(object):
    def __init__(self, baseurl, apikey):
        self.baseurl = baseurl
        self.apikey = apikey

    def prepare_request(self, method=None, path=None, params=None):
        url = None
        if self.baseurl:
            while path.startswith("/"):
                path = path[1:]
            url = self.baseurl + "/" + path
        return requests.Request(
            method=method, url=url, params=params, headers={"X-Api-Key": self.apikey}
        ).prepare()

    def request(
        self,
        method,
        path,
        data=None,
        files=None,
        encoding=None,
        params=None,
        timeout=None,
    ):
        if timeout is None:
            timeout = 30

        s = requests.Session()
        request = self.prepare_request(method, path, params=params)
        if data or files:
            if encoding == "json":
                request.prepare_body(None, None, json=data)
            else:
                request.prepare_body(data, files=files)
        response = s.send(request, timeout=timeout)
        return response

    def get(self, path, params=None, timeout=None):
        return self.request("GET", path, params=params, timeout=timeout)

    def post(self, path, data, encoding=None, params=None, timeout=None):
        return self.request(
            "POST", path, data=data, encoding=encoding, params=params, timeout=timeout
        )

    def post_json(self, path, data, params=None, timeout=None):
        return self.post(path, data, encoding="json", params=params, timeout=timeout)

    def post_command(self, path, command, additional=None, timeout=None):
        data = {"command": command}
        if additional:
            data.update(additional)
        return self.post_json(path, data, params=data, timeout=timeout)

    def upload(
        self,
        path,
        file_path,
        additional=None,
        file_name=None,
        content_type=None,
        params=None,
        timeout=None,
    ):
        import os

        if not os.path.isfile(file_path):
            raise ValueError(
                "{} cannot be uploaded since it is not a file".format(file_path)
            )

        if file_name is None:
            file_name = os.path.basename(file_path)

        with io.open(file_path, "rb") as fp:
            if content_type:
                files = {"file": (file_name, fp, content_type)}
            else:
                files = {"file": (file_name, fp)}

            response = self.request(
                "POST", path, data=additional, files=files, params=params, timeout=timeout
            )

        return response

    def delete(self, path, params=None, timeout=None):
        return self.request("DELETE", path, params=params, timeout=timeout)

    def patch(self, path, data, encoding=None, params=None, timeout=None):
        return self.request(
            "PATCH", path, data=data, encoding=encoding, params=params, timeout=timeout
        )

    def put(self, path, data, encoding=None, params=None, timeout=None):
        return self.request(
            "PUT", path, data=data, encoding=encoding, params=params, timeout=timeout
        )

    def create_socket(self, **kwargs):
        import random
        import uuid

        # creates websocket URL for SockJS according to
        # - http://sockjs.github.io/sockjs-protocol/sockjs-protocol-0.3.3.html#section-37
        # - http://sockjs.github.io/sockjs-protocol/sockjs-protocol-0.3.3.html#section-50
        url = "ws://{}/sockjs/{:0>3d}/{}/websocket".format(
            self.baseurl[
                self.baseurl.find("//") + 2 :
            ],  # host + port + prefix, but no protocol
            random.randrange(0, stop=999),  # server_id
            uuid.uuid4(),  # session_id
        )
        use_ssl = self.baseurl.startswith("https:")

        on_open_cb = kwargs.get("on_open", None)
        on_heartbeat_cb = kwargs.get("on_heartbeat", None)
        on_message_cb = kwargs.get("on_message", None)
        on_close_cb = kwargs.get("on_close", None)
        on_error_cb = kwargs.get("on_error", None)
        on_sent_cb = kwargs.get("on_sent", None)
        daemon = kwargs.get("daemon", True)

        def send(ws, data):
            payload = '["' + json.dumps(data).replace('"', '\\"') + '"]'
            ws.send(payload)
            if callable(on_sent_cb):
                on_sent_cb(ws, data)

        def authenticate(ws):
            # perform passive login to retrieve username and session key for API key
            response = self.post("/api/login", {"passive": True})
            response.raise_for_status()
            data = response.json()

            # prepare auth payload
            auth_message = {"auth": "{name}:{session}".format(**data)}

            # send it
            send(ws, auth_message)

        def on_message(ws, message):
            message_type = message[0]

            if message_type == "h":
                # "heartbeat" message
                if callable(on_heartbeat_cb):
                    on_heartbeat_cb(ws)
                    return
            elif message_type == "o":
                # "open" message
                return
            elif message_type == "c":
                # "close" message
                return

            if not callable(on_message_cb):
                return

            message_body = message[1:]
            if not message_body:
                return

            data = json.loads(message_body)

            if message_type == "m":
                data = [
                    data,
                ]

            for d in data:
                for internal_type, internal_message in d.items():
                    on_message_cb(ws, internal_type, internal_message)
                    if internal_type == "connected":
                        # we just got connected to the server, authenticate
                        authenticate(ws)

        def on_open(ws):
            if callable(on_open_cb):
                on_open_cb(ws)

        def on_close(ws):
            if callable(on_close_cb):
                on_close_cb(ws)

        def on_error(ws, error):
            if callable(on_error_cb):
                on_error_cb(ws, error)

        class CustomSocketClient(SocketClient):
            def auth(self, username, key):
                self.send({"auth": "{}:{}".format(username, key)})

            def throttle(self, factor):
                self.send({"throttle": factor})

            def send(self, data):
                send(self._ws, data)

        socket = CustomSocketClient(
            url,
            use_ssl=use_ssl,
            daemon=daemon,
            on_open=on_open,
            on_message=on_message,
            on_close=on_close,
            on_error=on_error,
        )
        socket.connect()

        return socket
