# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

"""
    sockjs.tornado.transports.websocket
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Websocket transport implementation
"""
import logging
import socket

from octoprint.vendor.sockjs.tornado import proto, websocket
from octoprint.vendor.sockjs.tornado.transports import base
from octoprint.vendor.sockjs.tornado.util import bytes_to_str
from tornado.websocket import WebSocketError
from tornado.ioloop import IOLoop

LOG = logging.getLogger("tornado.general")

class WebSocketTransport(websocket.SockJSWebSocketHandler, base.BaseTransportMixin):
    """Websocket transport"""
    name = 'websocket'

    def initialize(self, server):
        self.server = server
        self.session = None
        self.active = True

    def open(self, session_id):
        # Stats
        self.server.stats.on_conn_opened()

        # Disable nagle
        if self.server.settings['disable_nagle']:
            if hasattr(self, 'ws_connection'):
                self.ws_connection.stream.set_nodelay(True)
            else:
                self.stream.set_nodelay(True)

        # Handle session
        self.session = self.server.create_session(session_id, register=False)

        if not self.session.set_handler(self):
            self.close()
            return

        self.session.verify_state()

        if self.session:
            self.session.flush()

    def _detach(self):
        if self.session is not None:
            self.session.remove_handler(self)
            self.session = None

    def on_message(self, message):
        # SockJS requires that empty messages should be ignored
        if not message or not self.session:
            return

        try:
            msg = proto.json_decode(bytes_to_str(message))

            if isinstance(msg, list):
                self.session.on_messages(msg)
            else:
                self.session.on_messages((msg,))
        except Exception:
            LOG.exception('WebSocket')

            # Close session on exception
            #self.session.close()

            # Close running connection
            self.abort_connection()

    def on_close(self):
        # Close session if websocket connection was closed
        if self.session is not None:
            # Stats
            self.server.stats.on_conn_closed()

            # Detach before closing session
            session = self.session
            self._detach()
            session.close()

    def send_pack(self, message, binary=False):
        if IOLoop.current(False) == self.server.io_loop:
            # Running in Main Thread
            # Send message
            try:
                self.write_message(message, binary)
            except (IOError, WebSocketError):
                self.server.io_loop.add_callback(self.on_close)
        else:
            # Not running in Main Thread so use proper thread to send message
            self.server.io_loop.add_callback(lambda: self.send_pack(message, binary))

    def session_closed(self):
        # If session was closed by the application, terminate websocket
        # connection as well.
        try:
            self.close()
        except IOError:
            pass
        finally:
            self._detach()

    # Websocket overrides
    def allow_draft76(self):
        return True

    def auto_decode(self):
        return False
