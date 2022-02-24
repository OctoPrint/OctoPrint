__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

import time
import unittest
from unittest import mock

from octoprint.util import RepeatedTimer


class Countdown:
    def __init__(self, start):
        self._counter = start

    def step(self):
        self._counter -= 1

    @property
    def counter(self):
        return self._counter


class IncreasingInterval(Countdown):
    def __init__(self, start, factor):
        Countdown.__init__(self, start)
        self._start = start
        self._factor = factor

    def interval(self):
        result = (self._start - self._counter + 1) * self._factor
        return result


class RepeatedTimerTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_condition(self):
        countdown = Countdown(5)
        timer_task = mock.MagicMock()
        timer_task.side_effect = countdown.step

        timer = RepeatedTimer(0.1, timer_task, condition=lambda: countdown.counter > 0)
        timer.start()

        # wait for it
        timer.join()

        self.assertEqual(5, timer_task.call_count)

    def test_finished_callback(self):
        countdown = Countdown(5)
        timer_task = mock.MagicMock()
        timer_task.side_effect = countdown.step

        on_finished = mock.MagicMock()

        timer = RepeatedTimer(
            0.1,
            timer_task,
            condition=lambda: countdown.counter > 0,
            on_finish=on_finished,
        )
        timer.start()

        # wait for it
        timer.join()

        self.assertEqual(1, on_finished.call_count)

    def test_condition_callback(self):
        countdown = Countdown(5)
        timer_task = mock.MagicMock()
        timer_task.side_effect = countdown.step

        on_cancelled = mock.MagicMock()
        on_condition_false = mock.MagicMock()

        timer = RepeatedTimer(
            0.1,
            timer_task,
            condition=lambda: countdown.counter > 0,
            on_condition_false=on_condition_false,
            on_cancelled=on_cancelled,
        )
        timer.start()

        # wait for it
        timer.join()

        self.assertEqual(1, on_condition_false.call_count)
        self.assertEqual(0, on_cancelled.call_count)

    def test_cancelled_callback(self):
        countdown = Countdown(5)
        timer_task = mock.MagicMock()
        timer_task.side_effect = countdown.step

        on_cancelled = mock.MagicMock()
        on_condition_false = mock.MagicMock()

        timer = RepeatedTimer(
            10,
            timer_task,
            condition=lambda: countdown.counter > 0,
            on_condition_false=on_condition_false,
            on_cancelled=on_cancelled,
        )
        timer.start()

        # give it some time to run
        time.sleep(1)

        # then cancel it and wait for the thread to really finish
        timer.cancel()
        timer.join()

        self.assertEqual(0, on_condition_false.call_count)
        self.assertEqual(1, on_cancelled.call_count)

    def test_run_first(self):
        timer_task = mock.MagicMock()

        timer = RepeatedTimer(60, timer_task, run_first=True)
        timer.start()

        # give it some time to run
        time.sleep(1)

        # then cancel it and wait for the thread to really finish
        timer.cancel()
        timer.join()

        # should have run once
        self.assertEqual(1, timer_task.call_count)

    def test_not_run_first(self):
        timer_task = mock.MagicMock()

        timer = RepeatedTimer(60, timer_task)
        timer.start()

        # give it some time to run - should hang in the sleep phase though
        time.sleep(1)

        # then cancel it and wait for the thread to really finish
        timer.cancel()
        timer.join()

        self.assertEqual(0, timer_task.call_count)

    def test_adjusted_interval(self):
        increasing_interval = IncreasingInterval(3, 1)

        timer_task = mock.MagicMock()
        timer_task.side_effect = increasing_interval.step

        timer = RepeatedTimer(
            increasing_interval.interval,
            timer_task,
            condition=lambda: increasing_interval.counter > 0,
        )

        # this should take 1 + 2 + 3 = 6s
        start_time = time.time()
        timer.start()
        timer.join()
        duration = time.time() - start_time

        self.assertEqual(3, timer_task.call_count)
        self.assertGreaterEqual(duration, 6)
        self.assertLess(duration, 7)

    def test_condition_change_during_task(self):
        def sleep():
            time.sleep(2)

        timer_task = mock.MagicMock()
        timer_task.side_effect = sleep

        timer = RepeatedTimer(0.1, timer_task, run_first=True)
        timer.start()

        time.sleep(1)
        timer.condition = lambda: False
        timer.join()

        self.assertEqual(1, timer_task.call_count)
