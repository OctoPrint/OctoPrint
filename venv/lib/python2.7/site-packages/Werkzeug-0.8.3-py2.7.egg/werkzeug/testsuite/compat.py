# -*- coding: utf-8 -*-
"""
    werkzeug.testsuite.compat
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Ensure that old stuff does not break on update.

    :copyright: (c) 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import unittest
import warnings
from werkzeug.testsuite import WerkzeugTestCase

from werkzeug.wrappers import Response
from werkzeug.test import create_environ


class CompatTestCase(WerkzeugTestCase):

    def test_old_imports(self):
        from werkzeug.utils import Headers, MultiDict, CombinedMultiDict, \
             Headers, EnvironHeaders
        from werkzeug.http import Accept, MIMEAccept, CharsetAccept, \
             LanguageAccept, ETags, HeaderSet, WWWAuthenticate, \
             Authorization

    def test_exposed_werkzeug_mod(self):
        import werkzeug
        for key in werkzeug.__all__:
            # deprecated, skip it
            if key in ('templates', 'Template'):
                continue
            getattr(werkzeug, key)

    def test_fix_headers_in_response(self):
        # ignore some warnings werkzeug emits for backwards compat
        for msg in ['called into deprecated fix_headers',
                    'fix_headers changed behavior']:
            warnings.filterwarnings('ignore', message=msg,
                                    category=DeprecationWarning)

        class MyResponse(Response):
            def fix_headers(self, environ):
                Response.fix_headers(self, environ)
                self.headers['x-foo'] = "meh"
        myresp = MyResponse('Foo')
        resp = Response.from_app(myresp, create_environ(method='GET'))
        assert resp.headers['x-foo'] == 'meh'
        assert resp.data == 'Foo'

        warnings.resetwarnings()


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(CompatTestCase))
    return suite
