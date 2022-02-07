__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

import time
import unittest
from unittest import mock

from octoprint.util import ResettableTimer


class ResettableTimerTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_function(self):
        timer_task = mock.MagicMock()

        timer = ResettableTimer(10, timer_task)
        timer.start()

        # wait for it
        timer.join()

        self.assertEqual(1, timer_task.call_count)

    def test_reset_callback(self):
        timer_task = mock.MagicMock()
        on_reset_cb = mock.MagicMock()

        timer = ResettableTimer(10, timer_task, on_reset=on_reset_cb)
        timer.start()

        timer.reset()

        # wait for it
        timer.join()

        self.assertEqual(1, timer_task.call_count)
        self.assertEqual(1, on_reset_cb.call_count)

    def test_canceled_callback(self):
        timer_task = mock.MagicMock()
        on_cancelled_cb = mock.MagicMock()

        timer = ResettableTimer(10, timer_task, on_cancelled=on_cancelled_cb)
        timer.start()

        time.sleep(5)

        timer.cancel()

        time.sleep(10)

        self.assertEqual(0, timer_task.call_count)
        self.assertEqual(1, on_cancelled_cb.call_count)
