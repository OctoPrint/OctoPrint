# -*- coding: utf-8 -*-
"""
    werkzeug.testsuite.serving
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Added serving tests.

    :copyright: (c) 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import sys
import time
import urllib
import unittest
from functools import update_wrapper
from StringIO import StringIO

from werkzeug.testsuite import WerkzeugTestCase

from werkzeug import __version__ as version, serving
from werkzeug.testapp import test_app
from threading import Thread


real_make_server = serving.make_server


def silencestderr(f):
    def new_func(*args, **kwargs):
        old_stderr = sys.stderr
        sys.stderr = StringIO()
        try:
            return f(*args, **kwargs)
        finally:
            sys.stderr = old_stderr
    return update_wrapper(new_func, f)


def run_dev_server(application):
    servers = []
    def tracking_make_server(*args, **kwargs):
        srv = real_make_server(*args, **kwargs)
        servers.append(srv)
        return srv
    serving.make_server = tracking_make_server
    try:
        t = Thread(target=serving.run_simple, args=('localhost', 0, application))
        t.setDaemon(True)
        t.start()
        time.sleep(0.25)
    finally:
        serving.make_server = real_make_server
    if not servers:
        return None, None
    server ,= servers
    ip, port = server.socket.getsockname()[:2]
    if ':' in ip:
        ip = '[%s]' % ip
    return server, '%s:%d'  % (ip, port)


class ServingTestCase(WerkzeugTestCase):

    @silencestderr
    def test_serving(self):
        server, addr = run_dev_server(test_app)
        rv = urllib.urlopen('http://%s/?foo=bar&baz=blah' % addr).read()
        assert 'WSGI Information' in rv
        assert 'foo=bar&amp;baz=blah' in rv
        assert ('Werkzeug/%s' % version) in rv

    @silencestderr
    def test_broken_app(self):
        def broken_app(environ, start_response):
            1/0
        server, addr = run_dev_server(broken_app)
        rv = urllib.urlopen('http://%s/?foo=bar&baz=blah' % addr).read()
        assert 'Internal Server Error' in rv


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ServingTestCase))
    return suite
