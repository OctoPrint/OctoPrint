# -*- coding: utf-8 -*-
"""
    sockjs.tornado.transports.rawwebsocket
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Raw websocket transport implementation
"""
import logging
import socket

from octoprint.vendor.sockjs.tornado import websocket, session
from octoprint.vendor.sockjs.tornado.transports import base
from tornado.websocket import WebSocketError
from tornado.ioloop import IOLoop

LOG = logging.getLogger("tornado.general")

class RawSession(session.BaseSession):
    """Raw session without any sockjs protocol encoding/decoding. Simply
    works as a proxy between `SockJSConnection` class and `RawWebSocketTransport`."""
    def send_message(self, msg, stats=True, binary=False):
        self.handler.send_pack(msg, binary)

    def on_message(self, msg):
        self.conn.on_message(msg)


class RawWebSocketTransport(websocket.SockJSWebSocketHandler, base.BaseTransportMixin):
    """Raw Websocket transport"""
    name = 'rawwebsocket'

    def initialize(self, server):
        self.server = server
        self.session = None
        self.active = True

    def open(self):
        # Stats
        self.server.stats.on_conn_opened()

        # Disable nagle if needed
        if self.server.settings['disable_nagle']:
            self.stream.socket.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)

        # Create and attach to session
        self.session = RawSession(self.server.get_connection_class(), self.server)
        self.session.set_handler(self)
        self.session.verify_state()

    def _detach(self):
        if self.session is not None:
            self.session.remove_handler(self)
            self.session = None

    def on_message(self, message):
        # SockJS requires that empty messages should be ignored
        if not message or not self.session:
            return

        try:
            self.session.on_message(message)
        except Exception:
            LOG.exception('RawWebSocket')

            # Close running connection
            self.abort_connection()

    def on_close(self):
        # Close session if websocket connection was closed
        if self.session is not None:
            # Stats
            self.server.stats.on_conn_closed()

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
        try:
            self.close(*self.session.get_close_reason())
        except IOError:
            pass
        finally:
            self._detach()

    # Websocket overrides
    def allow_draft76(self):
        return True
