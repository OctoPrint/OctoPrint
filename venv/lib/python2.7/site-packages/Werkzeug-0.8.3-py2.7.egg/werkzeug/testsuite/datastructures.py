# -*- coding: utf-8 -*-
"""
    werkzeug.testsuite.datastructures
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Tests the functionality of the provided Werkzeug
    datastructures.

    TODO:

    -   FileMultiDict
    -   convert to proper asserts
    -   Immutable types undertested
    -   Split up dict tests

    :copyright: (c) 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""

from __future__ import with_statement

import unittest
import pickle
from copy import copy
from werkzeug.testsuite import WerkzeugTestCase

from werkzeug import datastructures
from werkzeug.exceptions import BadRequestKeyError


class MutableMultiDictBaseTestCase(WerkzeugTestCase):
    storage_class = None

    def test_pickle(self):
        cls = self.storage_class

        for protocol in xrange(pickle.HIGHEST_PROTOCOL + 1):
            d = cls()
            d.setlist('foo', [1, 2, 3, 4])
            d.setlist('bar', 'foo bar baz'.split())
            s = pickle.dumps(d, protocol)
            ud = pickle.loads(s)
            self.assert_equal(type(ud), type(d))
            self.assert_equal(ud, d)
            self.assert_equal(pickle.loads(
                s.replace('werkzeug.datastructures', 'werkzeug')), d)
            ud['newkey'] = 'bla'
            self.assert_not_equal(ud, d)

    def test_basic_interface(self):
        md = self.storage_class()
        assert isinstance(md, dict)

        mapping = [('a', 1), ('b', 2), ('a', 2), ('d', 3),
                   ('a', 1), ('a', 3), ('d', 4), ('c', 3)]
        md = self.storage_class(mapping)

        # simple getitem gives the first value
        assert md['a'] == 1
        assert md['c'] == 3
        with self.assert_raises(KeyError):
            md['e']
        assert md.get('a') == 1

        # list getitem
        assert md.getlist('a') == [1, 2, 1, 3]
        assert md.getlist('d') == [3, 4]
        # do not raise if key not found
        assert md.getlist('x') == []

        # simple setitem overwrites all values
        md['a'] = 42
        assert md.getlist('a') == [42]

        # list setitem
        md.setlist('a', [1, 2, 3])
        assert md['a'] == 1
        assert md.getlist('a') == [1, 2, 3]

        # verify that it does not change original lists
        l1 = [1, 2, 3]
        md.setlist('a', l1)
        del l1[:]
        assert md['a'] == 1

        # setdefault, setlistdefault
        assert md.setdefault('u', 23) == 23
        assert md.getlist('u') == [23]
        del md['u']

        md.setlist('u', [-1, -2])

        # delitem
        del md['u']
        with self.assert_raises(KeyError):
            md['u']
        del md['d']
        assert md.getlist('d') == []

        # keys, values, items, lists
        assert list(sorted(md.keys())) == ['a', 'b', 'c']
        assert list(sorted(md.iterkeys())) == ['a', 'b', 'c']

        assert list(sorted(md.values())) == [1, 2, 3]
        assert list(sorted(md.itervalues())) == [1, 2, 3]

        assert list(sorted(md.items())) == [('a', 1), ('b', 2), ('c', 3)]
        assert list(sorted(md.items(multi=True))) == \
               [('a', 1), ('a', 2), ('a', 3), ('b', 2), ('c', 3)]
        assert list(sorted(md.iteritems())) == [('a', 1), ('b', 2), ('c', 3)]
        assert list(sorted(md.iteritems(multi=True))) == \
               [('a', 1), ('a', 2), ('a', 3), ('b', 2), ('c', 3)]

        assert list(sorted(md.lists())) == [('a', [1, 2, 3]), ('b', [2]), ('c', [3])]
        assert list(sorted(md.iterlists())) == [('a', [1, 2, 3]), ('b', [2]), ('c', [3])]

        # copy method
        c = md.copy()
        assert c['a'] == 1
        assert c.getlist('a') == [1, 2, 3]

        # copy method 2
        c = copy(md)
        assert c['a'] == 1
        assert c.getlist('a') == [1, 2, 3]

        # update with a multidict
        od = self.storage_class([('a', 4), ('a', 5), ('y', 0)])
        md.update(od)
        assert md.getlist('a') == [1, 2, 3, 4, 5]
        assert md.getlist('y') == [0]

        # update with a regular dict
        md = c
        od = {'a': 4, 'y': 0}
        md.update(od)
        assert md.getlist('a') == [1, 2, 3, 4]
        assert md.getlist('y') == [0]

        # pop, poplist, popitem, popitemlist
        assert md.pop('y') == 0
        assert 'y' not in md
        assert md.poplist('a') == [1, 2, 3, 4]
        assert 'a' not in md
        assert md.poplist('missing') == []

        # remaining: b=2, c=3
        popped = md.popitem()
        assert popped in [('b', 2), ('c', 3)]
        popped = md.popitemlist()
        assert popped in [('b', [2]), ('c', [3])]

        # type conversion
        md = self.storage_class({'a': '4', 'b': ['2', '3']})
        assert md.get('a', type=int) == 4
        assert md.getlist('b', type=int) == [2, 3]

        # repr
        md = self.storage_class([('a', 1), ('a', 2), ('b', 3)])
        assert "('a', 1)" in repr(md)
        assert "('a', 2)" in repr(md)
        assert "('b', 3)" in repr(md)

        # add and getlist
        md.add('c', '42')
        md.add('c', '23')
        assert md.getlist('c') == ['42', '23']
        md.add('c', 'blah')
        assert md.getlist('c', type=int) == [42, 23]

        # setdefault
        md = self.storage_class()
        md.setdefault('x', []).append(42)
        md.setdefault('x', []).append(23)
        assert md['x'] == [42, 23]

        # to dict
        md = self.storage_class()
        md['foo'] = 42
        md.add('bar', 1)
        md.add('bar', 2)
        assert md.to_dict() == {'foo': 42, 'bar': 1}
        assert md.to_dict(flat=False) == {'foo': [42], 'bar': [1, 2]}

        # popitem from empty dict
        with self.assert_raises(KeyError):
            self.storage_class().popitem()

        with self.assert_raises(KeyError):
            self.storage_class().popitemlist()

        # key errors are of a special type
        with self.assert_raises(BadRequestKeyError):
            self.storage_class()[42]

        # setlist works
        md = self.storage_class()
        md['foo'] = 42
        md.setlist('foo', [1, 2])
        assert md.getlist('foo') == [1, 2]


class ImmutableDictBaseTestCase(WerkzeugTestCase):
    storage_class = None

    def test_follows_dict_interface(self):
        cls = self.storage_class

        data = {'foo': 1, 'bar': 2, 'baz': 3}
        d = cls(data)

        self.assert_equal(d['foo'], 1)
        self.assert_equal(d['bar'], 2)
        self.assert_equal(d['baz'], 3)
        self.assert_equal(sorted(d.keys()), ['bar', 'baz', 'foo'])
        self.assert_('foo' in d)
        self.assert_('foox' not in d)
        self.assert_equal(len(d), 3)

    def test_copies_are_mutable(self):
        cls = self.storage_class
        immutable = cls({'a': 1})
        with self.assert_raises(TypeError):
            immutable.pop('a')

        mutable = immutable.copy()
        mutable.pop('a')
        self.assert_('a' in immutable)
        self.assert_(mutable is not immutable)
        self.assert_(copy(immutable) is immutable)

    def test_dict_is_hashable(self):
        cls = self.storage_class
        immutable = cls({'a': 1, 'b': 2})
        immutable2 = cls({'a': 2, 'b': 2})
        x = set([immutable])
        self.assert_(immutable in x)
        self.assert_(immutable2 not in x)
        x.discard(immutable)
        self.assert_(immutable not in x)
        self.assert_(immutable2 not in x)
        x.add(immutable2)
        self.assert_(immutable not in x)
        self.assert_(immutable2 in x)
        x.add(immutable)
        self.assert_(immutable in x)
        self.assert_(immutable2 in x)


class ImmutableTypeConversionDictTestCase(ImmutableDictBaseTestCase):
    storage_class = datastructures.ImmutableTypeConversionDict


class ImmutableMultiDictTestCase(ImmutableDictBaseTestCase):
    storage_class = datastructures.ImmutableMultiDict

    def test_multidict_is_hashable(self):
        cls = self.storage_class
        immutable = cls({'a': [1, 2], 'b': 2})
        immutable2 = cls({'a': [1], 'b': 2})
        x = set([immutable])
        self.assert_(immutable in x)
        self.assert_(immutable2 not in x)
        x.discard(immutable)
        self.assert_(immutable not in x)
        self.assert_(immutable2 not in x)
        x.add(immutable2)
        self.assert_(immutable not in x)
        self.assert_(immutable2 in x)
        x.add(immutable)
        self.assert_(immutable in x)
        self.assert_(immutable2 in x)


class ImmutableDictTestCase(ImmutableDictBaseTestCase):
    storage_class = datastructures.ImmutableDict


class ImmutableOrderedMultiDictTestCase(ImmutableDictBaseTestCase):
    storage_class = datastructures.ImmutableOrderedMultiDict

    def test_ordered_multidict_is_hashable(self):
        a = self.storage_class([('a', 1), ('b', 1), ('a', 2)])
        b = self.storage_class([('a', 1), ('a', 2), ('b', 1)])
        self.assert_not_equal(hash(a), hash(b))


class MultiDictTestCase(MutableMultiDictBaseTestCase):
    storage_class = datastructures.MultiDict

    def test_multidict_pop(self):
        make_d = lambda: self.storage_class({'foo': [1, 2, 3, 4]})
        d = make_d()
        assert d.pop('foo') == 1
        assert not d
        d = make_d()
        assert d.pop('foo', 32) == 1
        assert not d
        d = make_d()
        assert d.pop('foos', 32) == 32
        assert d

        with self.assert_raises(KeyError):
            d.pop('foos')

    def test_setlistdefault(self):
        md = self.storage_class()
        assert md.setlistdefault('u', [-1, -2]) == [-1, -2]
        assert md.getlist('u') == [-1, -2]
        assert md['u'] == -1

    def test_iter_interfaces(self):
        mapping = [('a', 1), ('b', 2), ('a', 2), ('d', 3),
                   ('a', 1), ('a', 3), ('d', 4), ('c', 3)]
        md = self.storage_class(mapping)
        assert list(zip(md.keys(), md.listvalues())) == list(md.lists())
        assert list(zip(md, md.iterlistvalues())) == list(md.iterlists())
        assert list(zip(md.iterkeys(), md.iterlistvalues())) == list(md.iterlists())


class OrderedMultiDictTestCase(MutableMultiDictBaseTestCase):
    storage_class = datastructures.OrderedMultiDict

    def test_ordered_interface(self):
        cls = self.storage_class

        d = cls()
        assert not d
        d.add('foo', 'bar')
        assert len(d) == 1
        d.add('foo', 'baz')
        assert len(d) == 1
        assert d.items() == [('foo', 'bar')]
        assert list(d) == ['foo']
        assert d.items(multi=True) == [('foo', 'bar'),
                                       ('foo', 'baz')]
        del d['foo']
        assert not d
        assert len(d) == 0
        assert list(d) == []

        d.update([('foo', 1), ('foo', 2), ('bar', 42)])
        d.add('foo', 3)
        assert d.getlist('foo') == [1, 2, 3]
        assert d.getlist('bar') == [42]
        assert d.items() == [('foo', 1), ('bar', 42)]
        assert d.keys() == list(d) == list(d.iterkeys()) == ['foo', 'bar']
        assert d.items(multi=True) == [('foo', 1), ('foo', 2),
                                       ('bar', 42), ('foo', 3)]
        assert len(d) == 2

        assert d.pop('foo') == 1
        assert d.pop('blafasel', None) is None
        assert d.pop('blafasel', 42) == 42
        assert len(d) == 1
        assert d.poplist('bar') == [42]
        assert not d

        d.get('missingkey') is None

        d.add('foo', 42)
        d.add('foo', 23)
        d.add('bar', 2)
        d.add('foo', 42)
        assert d == datastructures.MultiDict(d)
        id = self.storage_class(d)
        assert d == id
        d.add('foo', 2)
        assert d != id

        d.update({'blah': [1, 2, 3]})
        assert d['blah'] == 1
        assert d.getlist('blah') == [1, 2, 3]

        # setlist works
        d = self.storage_class()
        d['foo'] = 42
        d.setlist('foo', [1, 2])
        assert d.getlist('foo') == [1, 2]

        with self.assert_raises(BadRequestKeyError):
            d.pop('missing')
        with self.assert_raises(BadRequestKeyError):
            d['missing']

        # popping
        d = self.storage_class()
        d.add('foo', 23)
        d.add('foo', 42)
        d.add('foo', 1)
        assert d.popitem() == ('foo', 23)
        with self.assert_raises(BadRequestKeyError):
            d.popitem()
        assert not d

        d.add('foo', 23)
        d.add('foo', 42)
        d.add('foo', 1)
        assert d.popitemlist() == ('foo', [23, 42, 1])

        with self.assert_raises(BadRequestKeyError):
            d.popitemlist()


class CombinedMultiDictTestCase(WerkzeugTestCase):
    storage_class = datastructures.CombinedMultiDict

    def test_basic_interface(self):
        d1 = datastructures.MultiDict([('foo', '1')])
        d2 = datastructures.MultiDict([('bar', '2'), ('bar', '3')])
        d = self.storage_class([d1, d2])

        # lookup
        assert d['foo'] == '1'
        assert d['bar'] == '2'
        assert d.getlist('bar') == ['2', '3']

        assert sorted(d.items()) == [('bar', '2'), ('foo', '1')], d.items()
        assert sorted(d.items(multi=True)) == [('bar', '2'), ('bar', '3'), ('foo', '1')]
        assert 'missingkey' not in d
        assert 'foo' in d

        # type lookup
        assert d.get('foo', type=int) == 1
        assert d.getlist('bar', type=int) == [2, 3]

        # get key errors for missing stuff
        with self.assert_raises(KeyError):
            d['missing']

        # make sure that they are immutable
        with self.assert_raises(TypeError):
            d['foo'] = 'blub'

        # copies are immutable
        d = d.copy()
        with self.assert_raises(TypeError):
            d['foo'] = 'blub'

        # make sure lists merges
        md1 = datastructures.MultiDict((("foo", "bar"),))
        md2 = datastructures.MultiDict((("foo", "blafasel"),))
        x = self.storage_class((md1, md2))
        assert x.lists() == [('foo', ['bar', 'blafasel'])]


class HeadersTestCase(WerkzeugTestCase):
    storage_class = datastructures.Headers

    def test_basic_interface(self):
        headers = self.storage_class()
        headers.add('Content-Type', 'text/plain')
        headers.add('X-Foo', 'bar')
        assert 'x-Foo' in headers
        assert 'Content-type' in headers

        headers['Content-Type'] = 'foo/bar'
        assert headers['Content-Type'] == 'foo/bar'
        assert len(headers.getlist('Content-Type')) == 1

        # list conversion
        assert headers.to_list() == [
            ('Content-Type', 'foo/bar'),
            ('X-Foo', 'bar')
        ]
        assert str(headers) == (
            "Content-Type: foo/bar\r\n"
            "X-Foo: bar\r\n"
            "\r\n")
        assert str(self.storage_class()) == "\r\n"

        # extended add
        headers.add('Content-Disposition', 'attachment', filename='foo')
        assert headers['Content-Disposition'] == 'attachment; filename=foo'

        headers.add('x', 'y', z='"')
        assert headers['x'] == r'y; z="\""'

    def test_defaults_and_conversion(self):
        # defaults
        headers = self.storage_class([
            ('Content-Type', 'text/plain'),
            ('X-Foo',        'bar'),
            ('X-Bar',        '1'),
            ('X-Bar',        '2')
        ])
        assert headers.getlist('x-bar') == ['1', '2']
        assert headers.get('x-Bar') == '1'
        assert headers.get('Content-Type') == 'text/plain'

        assert headers.setdefault('X-Foo', 'nope') == 'bar'
        assert headers.setdefault('X-Bar', 'nope') == '1'
        assert headers.setdefault('X-Baz', 'quux') == 'quux'
        assert headers.setdefault('X-Baz', 'nope') == 'quux'
        headers.pop('X-Baz')

        # type conversion
        assert headers.get('x-bar', type=int) == 1
        assert headers.getlist('x-bar', type=int) == [1, 2]

        # list like operations
        assert headers[0] == ('Content-Type', 'text/plain')
        assert headers[:1] == self.storage_class([('Content-Type', 'text/plain')])
        del headers[:2]
        del headers[-1]
        assert headers == self.storage_class([('X-Bar', '1')])

    def test_copying(self):
        a = self.storage_class([('foo', 'bar')])
        b = a.copy()
        a.add('foo', 'baz')
        assert a.getlist('foo') == ['bar', 'baz']
        assert b.getlist('foo') == ['bar']

    def test_popping(self):
        headers = self.storage_class([('a', 1)])
        assert headers.pop('a') == 1
        assert headers.pop('b', 2) == 2

        with self.assert_raises(KeyError):
            headers.pop('c')

    def test_set_arguments(self):
        a = self.storage_class()
        a.set('Content-Disposition', 'useless')
        a.set('Content-Disposition', 'attachment', filename='foo')
        assert a['Content-Disposition'] == 'attachment; filename=foo'

    def test_reject_newlines(self):
        h = self.storage_class()

        for variation in 'foo\nbar', 'foo\r\nbar', 'foo\rbar':
            with self.assert_raises(ValueError):
                h['foo'] = variation
            with self.assert_raises(ValueError):
                h.add('foo', variation)
            with self.assert_raises(ValueError):
                h.add('foo', 'test', option=variation)
            with self.assert_raises(ValueError):
                h.set('foo', variation)
            with self.assert_raises(ValueError):
                h.set('foo', 'test', option=variation)


class EnvironHeadersTestCase(WerkzeugTestCase):
    storage_class = datastructures.EnvironHeaders

    def test_basic_interface(self):
        # this happens in multiple WSGI servers because they
        # use a vary naive way to convert the headers;
        broken_env = {
            'HTTP_CONTENT_TYPE':        'text/html',
            'CONTENT_TYPE':             'text/html',
            'HTTP_CONTENT_LENGTH':      '0',
            'CONTENT_LENGTH':           '0',
            'HTTP_ACCEPT':              '*',
            'wsgi.version':             (1, 0)
        }
        headers = self.storage_class(broken_env)
        assert headers
        assert len(headers) == 3
        assert sorted(headers) == [
            ('Accept', '*'),
            ('Content-Length', '0'),
            ('Content-Type', 'text/html')
        ]
        assert not self.storage_class({'wsgi.version': (1, 0)})
        assert len(self.storage_class({'wsgi.version': (1, 0)})) == 0


class HeaderSetTestCase(WerkzeugTestCase):
    storage_class = datastructures.HeaderSet

    def test_basic_interface(self):
        hs = self.storage_class()
        hs.add('foo')
        hs.add('bar')
        assert 'Bar' in hs
        assert hs.find('foo') == 0
        assert hs.find('BAR') == 1
        assert hs.find('baz') < 0
        hs.discard('missing')
        hs.discard('foo')
        assert hs.find('foo') < 0
        assert hs.find('bar') == 0

        with self.assert_raises(IndexError):
            hs.index('missing')

        assert hs.index('bar') == 0
        assert hs
        hs.clear()
        assert not hs


class ImmutableListTestCase(WerkzeugTestCase):
    storage_class = datastructures.ImmutableList

    def test_list_hashable(self):
        t = (1, 2, 3, 4)
        l = self.storage_class(t)
        self.assert_equal(hash(t), hash(l))
        self.assert_not_equal(t, l)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(MultiDictTestCase))
    suite.addTest(unittest.makeSuite(OrderedMultiDictTestCase))
    suite.addTest(unittest.makeSuite(CombinedMultiDictTestCase))
    suite.addTest(unittest.makeSuite(ImmutableTypeConversionDictTestCase))
    suite.addTest(unittest.makeSuite(ImmutableMultiDictTestCase))
    suite.addTest(unittest.makeSuite(ImmutableDictTestCase))
    suite.addTest(unittest.makeSuite(ImmutableOrderedMultiDictTestCase))
    suite.addTest(unittest.makeSuite(HeadersTestCase))
    suite.addTest(unittest.makeSuite(EnvironHeadersTestCase))
    suite.addTest(unittest.makeSuite(HeaderSetTestCase))
    return suite
