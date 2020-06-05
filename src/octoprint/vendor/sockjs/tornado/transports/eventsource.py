# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

"""
    sockjs.tornado.transports.eventsource
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    EventSource transport implementation.
"""

from octoprint.vendor.sockjs.tornado.transports import streamingbase
from octoprint.vendor.sockjs.tornado.util import no_auto_finish


class EventSourceTransport(streamingbase.StreamingTransportBase):
    name = 'eventsource'

    @no_auto_finish
    def get(self, session_id):
        # Start response
        self.preflight()
        self.handle_session_cookie()
        self.disable_cache()

        self.set_header('Content-Type', 'text/event-stream; charset=UTF-8')
        self.write('\r\n')
        self.flush()

        if not self._attach_session(session_id):
            self.finish()
            return

        if self.session:
            self.session.flush()

    def send_pack(self, message, binary=False):
        if binary:
            raise Exception('binary not supported for EventSourceTransport')

        msg = 'data: %s\r\n\r\n' % message

        self.active = False

        try:
            self.notify_sent(len(msg))

            self.write(msg)
            self.flush().add_done_callback(self.send_complete)
        except IOError:
            # If connection dropped, make sure we close offending session instead
            # of propagating error all way up.
            self.session.delayed_close()
            self._detach()
