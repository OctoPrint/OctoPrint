# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import unittest
from ddt import ddt, data, unpack

import octoprint.printer

@ddt
class EstimationTestCase(unittest.TestCase):

	def setUp(self):
		self.estimation_helper = octoprint.printer.TimeEstimationHelper()

	@data(
		((1.0, 2.0, 3.0, 4.0, 5.0), 3.0),
		((1.0, 2.0, 0.0, 1.0, 2.0), 1.2),
		((1.0, -2.0, -1.0, -2.0, 3.0), -0.2)
	)
	@unpack
	def test_average_total(self, estimates, expected):
		for estimate in estimates:
			self.estimation_helper.update(estimate)

		self.assertEquals(self.estimation_helper.average_total, expected)

	@data(
		((1.0, 2.0, 3.0, 4.0, 5.0), 0.5), # average totals: 1.0, 1.5, 2.0, 2.5, 3.0
		((1.0, 2.0, 0.0, 1.0, 2.0), 0.3) # average totals: 1.0, 1.5, 1.0, 1.0, 1.2
	)
	@unpack
	def test_average_distance(self, estimates, expected):
		for estimate in estimates:
			self.estimation_helper.update(estimate)

		self.assertEquals(self.estimation_helper.average_distance, expected)

