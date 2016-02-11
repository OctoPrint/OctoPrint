# -*- coding: utf-8 -*-
"""
    werkzeug.testsuite.iterio
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Tests the iterio object.

    :copyright: (c) 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import unittest

from werkzeug.testsuite import WerkzeugTestCase
from werkzeug.contrib.iterio import IterIO, greenlet


class IterOTestSuite(WerkzeugTestCase):

    def test_basic(self):
        io = IterIO(["Hello", "World", "1", "2", "3"])
        assert io.tell() == 0
        assert io.read(2) == "He"
        assert io.tell() == 2
        assert io.read(3) == "llo"
        assert io.tell() == 5
        io.seek(0)
        assert io.read(5) == "Hello"
        assert io.tell() == 5
        assert io._buf == "Hello"
        assert io.read() == "World123"
        assert io.tell() == 13
        io.close()
        assert io.closed

        io = IterIO(["Hello\n", "World!"])
        assert io.readline() == 'Hello\n'
        assert io._buf == 'Hello\n'
        assert io.read() == 'World!'
        assert io._buf == 'Hello\nWorld!'
        assert io.tell() == 12
        io.seek(0)
        assert io.readlines() == ['Hello\n', 'World!']

        io = IterIO(["foo\n", "bar"])
        io.seek(-4, 2)
        assert io.read(4) == '\nbar'

        self.assert_raises(IOError, io.seek, 2, 100)
        io.close()
        self.assert_raises(ValueError, io.read)


class IterITestSuite(WerkzeugTestCase):

    def test_basic(self):
        def producer(out):
            out.write('1\n')
            out.write('2\n')
            out.flush()
            out.write('3\n')
        iterable = IterIO(producer)
        self.assert_equal(iterable.next(), '1\n2\n')
        self.assert_equal(iterable.next(), '3\n')
        self.assert_raises(StopIteration, iterable.next)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(IterOTestSuite))
    if greenlet is not None:
        suite.addTest(unittest.makeSuite(IterITestSuite))
    return suite
