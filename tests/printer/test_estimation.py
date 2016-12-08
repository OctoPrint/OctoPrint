# coding=utf-8
from __future__ import absolute_import, division, print_function
from octoprint.printer.estimation import TimeEstimationHelper

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import unittest
from ddt import ddt, data, unpack

import octoprint.printer

@ddt
class EstimationTestCase(unittest.TestCase):

	def setUp(self):
		self.estimation_helper = type(TimeEstimationHelper)(TimeEstimationHelper.__name__, (TimeEstimationHelper,), {
			'STABLE_THRESHOLD': 0.1,
			'STABLE_ROLLING_WINDOW': 3,
			'STABLE_COUNTDOWN': 1
		})()

	@data(
		((1.0, 2.0, 3.0, 4.0, 5.0), 3.0),
		((1.0, 2.0, 0.0, 1.0, 2.0), 1.2),
		((1.0, -2.0, -1.0, -2.0, 3.0), -0.2)
	)
	@unpack
	def test_average_total(self, estimates, expected):
		for estimate in estimates:
			self.estimation_helper.update(estimate)

		self.assertEqual(self.estimation_helper.average_total, expected)

	@data(
		((1.0, 2.0), None),                    # not enough values, have 1, need 3
		((1.0, 2.0, 3.0), None),               # not enough values, have 2, need 3
		((1.0, 2.0, 3.0, 4.0), 0.5),           # average totals: 1.0, 1.5, 2.0, 2.5 => (3 * 0.5 / 3 = 0.5
		((1.0, 2.0, 3.0, 4.0, 5.0), 0.5),      # average totals: 1.0, 1.5, 2.0, 2.5, 3.0 => (0.5 + 0.5 + 0.5) / 3 = 0.5
		((1.0, 2.0, 0.0, 1.0, 2.0), 0.7 / 3)   # average totals: 1.0, 1.5, 1.0, 1.0, 1.2 => (0.5 + 0.0 + 0.2) / 3 = 0.7 / 3
	)
	@unpack
	def test_average_distance(self, estimates, expected):
		for estimate in estimates:
			self.estimation_helper.update(estimate)

		self.assertEqual(self.estimation_helper.average_distance, expected)

	@data(
		((1.0, 1.0), None),
		((1.0, 1.0, 1.0), 1.0),
		((1.0, 2.0, 3.0, 4.0, 5.0), 4.0),
	)
	@unpack
	def test_average_total_rolling(self, estimates, expected):
		for estimate in estimates:
			self.estimation_helper.update(estimate)

		self.assertEqual(self.estimation_helper.average_total_rolling, expected)

	@data(
		((1.0, 1.0, 1.0, 1.0), False),         # average totals: 1.0, 1.0, 1.0, 1.0 => 3.0 / 3 = 1.0
		((1.0, 1.0, 1.0, 1.0, 1.0), True),     # average totals: 1.0, 1.0, 1.0, 1.0, 1.0 => 0.0 / 3 = 0.0
		((1.0, 2.0, 3.0, 4.0, 5.0), False),    # average totals: 1.0, 1.5, 2.0, 2.5, 3.0 => 1.5 / 3 = 0.5
		((0.0, 0.09, 0.18, 0.27, 0.36), True)  # average totals: 0.0, 0.045, 0.09, 0.135, 0.18 => (0.045 + 0.045 + 0.045) / 3 = 0.045
	)
	@unpack
	def test_is_stable(self, estimates, expected):
		for estimate in estimates:
			self.estimation_helper.update(estimate)

		self.assertEqual(self.estimation_helper.is_stable(), expected)

