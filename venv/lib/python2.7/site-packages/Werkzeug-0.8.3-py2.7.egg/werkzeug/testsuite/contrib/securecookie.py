# -*- coding: utf-8 -*-
"""
    werkzeug.testsuite.securecookie
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Tests the secure cookie.

    :copyright: (c) 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import unittest

from werkzeug.testsuite import WerkzeugTestCase

from werkzeug.utils import parse_cookie
from werkzeug.wrappers import Request, Response
from werkzeug.contrib.securecookie import SecureCookie


class SecureCookieTestCase(WerkzeugTestCase):

    def test_basic_support(self):
        c = SecureCookie(secret_key='foo')
        assert c.new
        print c.modified, c.should_save
        assert not c.modified
        assert not c.should_save
        c['x'] = 42
        assert c.modified
        assert c.should_save
        s = c.serialize()

        c2 = SecureCookie.unserialize(s, 'foo')
        assert c is not c2
        assert not c2.new
        assert not c2.modified
        assert not c2.should_save
        assert c2 == c

        c3 = SecureCookie.unserialize(s, 'wrong foo')
        assert not c3.modified
        assert not c3.new
        assert c3 == {}

    def test_wrapper_support(self):
        req = Request.from_values()
        resp = Response()
        c = SecureCookie.load_cookie(req, secret_key='foo')
        assert c.new
        c['foo'] = 42
        assert c.secret_key == 'foo'
        c.save_cookie(resp)

        req = Request.from_values(headers={
            'Cookie':  'session="%s"' % parse_cookie(resp.headers['set-cookie'])['session']
        })
        c2 = SecureCookie.load_cookie(req, secret_key='foo')
        assert not c2.new
        assert c2 == c


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SecureCookieTestCase))
    return suite
