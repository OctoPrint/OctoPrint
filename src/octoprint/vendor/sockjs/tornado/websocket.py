# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import tornado
from tornado import escape, gen, websocket

try:
    from urllib.parse import urlparse # py3
except ImportError:
    from urlparse import urlparse # py2


class SockJSWebSocketHandler(websocket.WebSocketHandler):
    if tornado.version_info[0] == 4 and tornado.version_info[1] > 1:
        def get_compression_options(self):
            # let tornado use compression when Sec-WebSocket-Extensions:permessage-deflate is provided
            return {}

    SUPPORTED_METHODS = ('GET',)

    def check_origin(self, origin):
        # let tornado first check if connection from the same domain
        same_domain = super(SockJSWebSocketHandler, self).check_origin(origin)
        if same_domain:
            return True

        # this is cross-origin connection - check using SockJS server settings
        allow_origin = self.server.settings.get("websocket_allow_origin", "*")
        if allow_origin == "":
            return False
        elif allow_origin == "*":
            return True
        else:
            parsed_origin = urlparse(origin)
            origin = parsed_origin.netloc
            origin = origin.lower()
            return origin in allow_origin

    def abort_connection(self):
        if self.ws_connection:
            self.ws_connection._abort()
