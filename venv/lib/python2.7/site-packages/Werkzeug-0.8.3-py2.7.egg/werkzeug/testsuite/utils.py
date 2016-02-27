# -*- coding: utf-8 -*-
"""
    werkzeug.testsuite.utils
    ~~~~~~~~~~~~~~~~~~~~~~~~

    General utilities.

    :copyright: (c) 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""

from __future__ import with_statement

import unittest
from datetime import datetime

from werkzeug.testsuite import WerkzeugTestCase

from werkzeug import utils
from werkzeug.datastructures import Headers
from werkzeug.http import parse_date, http_date
from werkzeug.wrappers import BaseResponse
from werkzeug.test import Client, run_wsgi_app


class GeneralUtilityTestCase(WerkzeugTestCase):

    def test_redirect(self):
        resp = utils.redirect(u'/füübär')
        assert '/f%C3%BC%C3%BCb%C3%A4r' in resp.data
        assert resp.headers['Location'] == '/f%C3%BC%C3%BCb%C3%A4r'
        assert resp.status_code == 302

        resp = utils.redirect(u'http://☃.net/', 307)
        assert 'http://xn--n3h.net/' in resp.data
        assert resp.headers['Location'] == 'http://xn--n3h.net/'
        assert resp.status_code == 307

        resp = utils.redirect('http://example.com/', 305)
        assert resp.headers['Location'] == 'http://example.com/'
        assert resp.status_code == 305

    def test_redirect_xss(self):
        location = 'http://example.com/?xss="><script>alert(1)</script>'
        resp = utils.redirect(location)
        assert '<script>alert(1)</script>' not in resp.data

        location = 'http://example.com/?xss="onmouseover="alert(1)'
        resp = utils.redirect(location)
        assert 'href="http://example.com/?xss="onmouseover="alert(1)"' not in resp.data

    def test_cached_property(self):
        foo = []
        class A(object):
            def prop(self):
                foo.append(42)
                return 42
            prop = utils.cached_property(prop)

        a = A()
        p = a.prop
        q = a.prop
        assert p == q == 42
        assert foo == [42]

        foo = []
        class A(object):
            def _prop(self):
                foo.append(42)
                return 42
            prop = utils.cached_property(_prop, name='prop')
            del _prop

        a = A()
        p = a.prop
        q = a.prop
        assert p == q == 42
        assert foo == [42]

    def test_environ_property(self):
        class A(object):
            environ = {'string': 'abc', 'number': '42'}

            string = utils.environ_property('string')
            missing = utils.environ_property('missing', 'spam')
            read_only = utils.environ_property('number')
            number = utils.environ_property('number', load_func=int)
            broken_number = utils.environ_property('broken_number', load_func=int)
            date = utils.environ_property('date', None, parse_date, http_date,
                                    read_only=False)
            foo = utils.environ_property('foo')

        a = A()
        assert a.string == 'abc'
        assert a.missing == 'spam'
        def test_assign():
            a.read_only = 'something'
        self.assert_raises(AttributeError, test_assign)
        assert a.number == 42
        assert a.broken_number == None
        assert a.date is None
        a.date = datetime(2008, 1, 22, 10, 0, 0, 0)
        assert a.environ['date'] == 'Tue, 22 Jan 2008 10:00:00 GMT'

    def test_escape(self):
        class Foo(str):
            def __html__(self):
                return unicode(self)
        assert utils.escape(None) == ''
        assert utils.escape(42) == '42'
        assert utils.escape('<>') == '&lt;&gt;'
        assert utils.escape('"foo"') == '"foo"'
        assert utils.escape('"foo"', True) == '&quot;foo&quot;'
        assert utils.escape(Foo('<foo>')) == '<foo>'

    def test_unescape(self):
        assert utils.unescape('&lt;&auml;&gt;') == u'<ä>'

    def test_run_wsgi_app(self):
        def foo(environ, start_response):
            start_response('200 OK', [('Content-Type', 'text/plain')])
            yield '1'
            yield '2'
            yield '3'

        app_iter, status, headers = run_wsgi_app(foo, {})
        assert status == '200 OK'
        assert headers == [('Content-Type', 'text/plain')]
        assert app_iter.next() == '1'
        assert app_iter.next() == '2'
        assert app_iter.next() == '3'
        self.assert_raises(StopIteration, app_iter.next)

        got_close = []
        class CloseIter(object):
            def __init__(self):
                self.iterated = False
            def __iter__(self):
                return self
            def close(self):
                got_close.append(None)
            def next(self):
                if self.iterated:
                    raise StopIteration()
                self.iterated = True
                return 'bar'

        def bar(environ, start_response):
            start_response('200 OK', [('Content-Type', 'text/plain')])
            return CloseIter()

        app_iter, status, headers = run_wsgi_app(bar, {})
        assert status == '200 OK'
        assert headers == [('Content-Type', 'text/plain')]
        assert app_iter.next() == 'bar'
        self.assert_raises(StopIteration, app_iter.next)
        app_iter.close()

        assert run_wsgi_app(bar, {}, True)[0] == ['bar']

        assert len(got_close) == 2

    def test_import_string(self):
        import cgi
        from werkzeug.debug import DebuggedApplication
        assert utils.import_string('cgi.escape') is cgi.escape
        assert utils.import_string(u'cgi.escape') is cgi.escape
        assert utils.import_string('cgi:escape') is cgi.escape
        assert utils.import_string('XXXXXXXXXXXX', True) is None
        assert utils.import_string('cgi.XXXXXXXXXXXX', True) is None
        assert utils.import_string(u'cgi.escape') is cgi.escape
        assert utils.import_string(u'werkzeug.debug.DebuggedApplication') is DebuggedApplication
        self.assert_raises(ImportError, utils.import_string, 'XXXXXXXXXXXXXXXX')
        self.assert_raises(ImportError, utils.import_string, 'cgi.XXXXXXXXXX')

    def test_find_modules(self):
        assert list(utils.find_modules('werkzeug.debug')) == \
            ['werkzeug.debug.console', 'werkzeug.debug.repr',
             'werkzeug.debug.tbtools']

    def test_html_builder(self):
        html = utils.html
        xhtml = utils.xhtml
        assert html.p('Hello World') == '<p>Hello World</p>'
        assert html.a('Test', href='#') == '<a href="#">Test</a>'
        assert html.br() == '<br>'
        assert xhtml.br() == '<br />'
        assert html.img(src='foo') == '<img src="foo">'
        assert xhtml.img(src='foo') == '<img src="foo" />'
        assert html.html(
            html.head(
                html.title('foo'),
                html.script(type='text/javascript')
            )
        ) == '<html><head><title>foo</title><script type="text/javascript">' \
             '</script></head></html>'
        assert html('<foo>') == '&lt;foo&gt;'
        assert html.input(disabled=True) == '<input disabled>'
        assert xhtml.input(disabled=True) == '<input disabled="disabled" />'
        assert html.input(disabled='') == '<input>'
        assert xhtml.input(disabled='') == '<input />'
        assert html.input(disabled=None) == '<input>'
        assert xhtml.input(disabled=None) == '<input />'
        assert html.script('alert("Hello World");') == '<script>' \
            'alert("Hello World");</script>'
        assert xhtml.script('alert("Hello World");') == '<script>' \
            '/*<![CDATA[*/alert("Hello World");/*]]>*/</script>'

    def test_validate_arguments(self):
        take_none = lambda: None
        take_two = lambda a, b: None
        take_two_one_default = lambda a, b=0: None

        assert utils.validate_arguments(take_two, (1, 2,), {}) == ((1, 2), {})
        assert utils.validate_arguments(take_two, (1,), {'b': 2}) == ((1, 2), {})
        assert utils.validate_arguments(take_two_one_default, (1,), {}) == ((1, 0), {})
        assert utils.validate_arguments(take_two_one_default, (1, 2), {}) == ((1, 2), {})

        self.assert_raises(utils.ArgumentValidationError,
            utils.validate_arguments, take_two, (), {})

        assert utils.validate_arguments(take_none, (1, 2,), {'c': 3}) == ((), {})
        self.assert_raises(utils.ArgumentValidationError,
               utils.validate_arguments, take_none, (1,), {}, drop_extra=False)
        self.assert_raises(utils.ArgumentValidationError,
               utils.validate_arguments, take_none, (), {'a': 1}, drop_extra=False)

    def test_header_set_duplication_bug(self):
        headers = Headers([
            ('Content-Type', 'text/html'),
            ('Foo', 'bar'),
            ('Blub', 'blah')
        ])
        headers['blub'] = 'hehe'
        headers['blafasel'] = 'humm'
        assert headers == Headers([
            ('Content-Type', 'text/html'),
            ('Foo', 'bar'),
            ('blub', 'hehe'),
            ('blafasel', 'humm')
        ])

    def test_append_slash_redirect(self):
        def app(env, sr):
            return utils.append_slash_redirect(env)(env, sr)
        client = Client(app, BaseResponse)
        response = client.get('foo', base_url='http://example.org/app')
        assert response.status_code == 301
        assert response.headers['Location'] == 'http://example.org/app/foo/'

    def test_cached_property_doc(self):
        @utils.cached_property
        def foo():
            """testing"""
            return 42
        assert foo.__doc__ == 'testing'
        assert foo.__name__ == 'foo'
        assert foo.__module__ == __name__


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(GeneralUtilityTestCase))
    return suite
