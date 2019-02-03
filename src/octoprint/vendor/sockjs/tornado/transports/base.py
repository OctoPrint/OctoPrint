# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from octoprint.vendor.sockjs.tornado import session


class BaseTransportMixin(object):
    """Base transport.

    Implements few methods that session expects to see in each transport.
    """

    name = 'override_me_please'

    def get_conn_info(self):
        """Return `ConnectionInfo` object from current transport"""
        return session.ConnectionInfo(self.request.remote_ip,
                                      self.request.cookies,
                                      self.request.arguments,
                                      self.request.headers,
                                      self.request.path)

    def session_closed(self):
        """Called by the session, when it gets closed"""
        pass
