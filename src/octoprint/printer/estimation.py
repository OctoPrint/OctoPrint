# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


class TimeEstimationHelper(object):

	STABLE_THRESHOLD = 0.1
	STABLE_COUNTDOWN = 250
	STABLE_ROLLING_WINDOW = 250

	def __init__(self):
		import collections
		self._distances = collections.deque([], self.__class__.STABLE_ROLLING_WINDOW)
		self._totals = collections.deque([], self.__class__.STABLE_ROLLING_WINDOW)
		self._sum_total = 0
		self._count = 0
		self._stable_counter = None

	def is_stable(self):
		return self._stable_counter is not None and self._stable_counter >= self.__class__.STABLE_COUNTDOWN

	def update(self, newEstimate):
			old_average_total = self.average_total

			self._sum_total += newEstimate
			self._totals.append(newEstimate)
			self._count += 1

			if old_average_total:
				self._distances.append(abs(self.average_total - old_average_total))

			if -1.0 * self.__class__.STABLE_THRESHOLD < self.average_distance < self.__class__.STABLE_THRESHOLD:
				if self._stable_counter is None:
					self._stable_counter = 0
				else:
					self._stable_counter += 1
			else:
				self._stable_counter = None

	@property
	def average_total(self):
		if not self._count:
			return None
		else:
			return self._sum_total / self._count

	@property
	def average_total_rolling(self):
		if not self._count or self._count < self.__class__.STABLE_ROLLING_WINDOW:
			return None
		else:
			return sum(self._totals) / len(self._totals)

	@property
	def average_distance(self):
		if not self._count or self._count < self.__class__.STABLE_ROLLING_WINDOW + 1:
			return None
		else:
			return sum(self._distances) / len(self._distances)