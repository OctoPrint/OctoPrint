# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


from octoprint.settings import settings


class PrintTimeEstimator(object):
	"""
	Estimator implementation.

	Subclass this and register via the octoprint.printer.estimation.factory hook to provide your own implementation.
	"""

	def __init__(self, job_type):
		self.stats_weighing_until = settings().getFloat(["estimation", "printTime", "statsWeighingUntil"])
		self.validity_range = settings().getFloat(["estimation", "printTime", "validityRange"])
		self.force_dumb_from_percent = settings().getFloat(["estimation", "printTime", "forceDumbFromPercent"])
		self.force_dumb_after_min = settings().getFloat(["estimation", "printTime", "forceDumbAfterMin"])

		threshold = None
		rolling_window = None
		countdown = None

		if job_type == "local" or job_type == "sdcard":
			# we are happy if the average of the estimates stays within 60s of the prior one
			threshold = settings().getFloat(["estimation", "printTime", "stableThreshold"])

			if job_type == "sdcard":
				# we are interesting in a rolling window of roughly the last 15s, so the number of entries has to be derived
				# by that divided by the sd status polling interval
				interval = settings().getFloat(["serial", "timeout", "sdStatus"])
				if interval <= 0:
					interval = 1.0
				rolling_window = int(15 // interval)
				if rolling_window < 1:
					rolling_window = 1

				# we are happy when one rolling window has been stable
				countdown = rolling_window

		self._data = TimeEstimationHelper(rolling_window=rolling_window, countdown=countdown, threshold=threshold)

	def estimate(self, progress, printTime, cleanedPrintTime, statisticalTotalPrintTime, statisticalTotalPrintTimeType):
		"""
		Tries to estimate the print time left for the print job

		This is somewhat horrible since accurate print time estimation is pretty much impossible to
		achieve, considering that we basically have only two data points (current progress in file and
		time needed for that so far - former prints or a file analysis might not have happened or simply
		be completely impossible e.g. if the file is stored on the printer's SD card) and
		hence can only do a linear estimation of a completely non-linear process. That's a recipe
		for inaccurate predictions right there. Yay.

		Anyhow, here's how this implementation works. This method gets the current progress in the
		printed file (percentage based on bytes read vs total bytes), the print time that elapsed,
		the same print time with the heat up times subtracted (if possible) and if available also
		some statistical total print time (former prints or a result from the GCODE analysis).

		  1. First get an "intelligent" estimate based on the :class:`~octoprint.printer.estimation.TimeEstimationHelper`.
		     That thing tries to detect if the estimation based on our progress and time needed for that becomes
		     stable over time through a rolling window and only returns a result once that appears to be the
		     case.
		  2. If we have any statistical data (former prints or a result from the GCODE analysis)
		     but no intelligent estimate yet, we'll use that for the next step. Otherwise, up to a certain percentage
		     in the print we do a percentage based weighing of the statistical data and the intelligent
		     estimate - the closer to the beginning of the print, the more precedence for the statistical
		     data, the closer to the cut off point, the more precedence for the intelligent estimate. This
		     is our preliminary total print time.
		  3. If the total print time is set, we do a sanity check for it. Based on the total print time
		     estimate and the time we already spent printing, we calculate at what percentage we SHOULD be
		     and compare that to the percentage at which we actually ARE. If it's too far off, our total
		     can't be trusted and we fall back on the dumb estimate. Same if the time we spent printing is
		     already higher than our total estimate.
		  4. If we do NOT have a total print time estimate yet but we've been printing for longer than
		     a configured amount of minutes or are further in the file than a configured percentage, we
		     also use the dumb estimate for now.

		Yes, all this still produces horribly inaccurate results. But we have to do this live during the print and
		hence can't produce to much computational overhead, we do not have any insight into the firmware implementation
		with regards to planner setup and acceleration settings, we might not even have access to the printed file's
		contents and such we need to find something that works "mostly" all of the time without costing too many
		resources. Feel free to propose a better solution within the above limitations (and I mean that, this solution
		here makes me unhappy).

		Args:
		    progress (float or None): Current percentage in the printed file
		    printTime (float or None): Print time elapsed so far
		    cleanedPrintTime (float or None): Print time elapsed minus the time needed for getting up to temperature
		        (if detectable).
		    statisticalTotalPrintTime (float or None): Total print time of past prints against same printer profile,
		        or estimated total print time from GCODE analysis.
		    statisticalTotalPrintTimeType (str or None): Type of statistical print time, either "average" (total time
		        of former prints) or "analysis"

		Returns:
		    (2-tuple) estimated print time left or None if not proper estimate could be made at all, origin of estimation
		"""

		if progress is None or progress == 0 or printTime is None or cleanedPrintTime is None:
			return None, None

		dumbTotalPrintTime = printTime / progress
		estimatedTotalPrintTime = self.estimate_total(progress, cleanedPrintTime)
		totalPrintTime = estimatedTotalPrintTime

		printTimeLeftOrigin = "estimate"
		if statisticalTotalPrintTime is not None:
			if estimatedTotalPrintTime is None:
				# no estimate yet, we'll use the statistical total
				totalPrintTime = statisticalTotalPrintTime
				printTimeLeftOrigin = statisticalTotalPrintTimeType

			else:
				if progress < self.stats_weighing_until:
					# still inside weighing range, use part stats, part current estimate
					sub_progress = progress * (1 / self.stats_weighing_until)
					if sub_progress > 1.0:
						sub_progress = 1.0
					printTimeLeftOrigin = "mixed-" + statisticalTotalPrintTimeType
				else:
					# use only the current estimate
					sub_progress = 1.0
					printTimeLeftOrigin = "estimate"

				# combine
				totalPrintTime = - sub_progress * statisticalTotalPrintTime \
				                 + sub_progress * estimatedTotalPrintTime

		printTimeLeft = None
		if totalPrintTime is not None:
			# sanity check current total print time estimate
			assumed_progress = cleanedPrintTime / totalPrintTime
			min_progress = progress - self.validity_range
			max_progress = progress + self.validity_range

			if min_progress <= assumed_progress <= max_progress and totalPrintTime > cleanedPrintTime:
				# appears sane, we'll use it
				printTimeLeft = totalPrintTime - cleanedPrintTime

			else:
				# too far from the actual progress or negative,
				# we use the dumb print time instead
				printTimeLeft = dumbTotalPrintTime - cleanedPrintTime
				printTimeLeftOrigin = "linear"

		else:
			printTimeLeftOrigin = "linear"
			if progress > self.force_dumb_from_percent or \
					cleanedPrintTime >= self.force_dumb_after_min * 60:
				# more than x% or y min printed and still no real estimate, ok, we'll use the dumb variant :/
				printTimeLeft = dumbTotalPrintTime - cleanedPrintTime

		if printTimeLeft is not None and printTimeLeft < 0:
			# shouldn't actually happen, but let's make sure
			printTimeLeft = None

		return printTimeLeft, printTimeLeftOrigin

	def estimate_total(self, progress, printTime):
		if not progress or not printTime or not self._data:
			return None
		else:
			return self._data.update(printTime / progress)


class TimeEstimationHelper(object):

	STABLE_THRESHOLD = 0.1
	STABLE_COUNTDOWN = 250
	STABLE_ROLLING_WINDOW = 250

	def __init__(self, rolling_window=None, countdown=None, threshold=None):
		if rolling_window is None:
			rolling_window = self.__class__.STABLE_ROLLING_WINDOW
		if countdown is None:
			countdown = self.__class__.STABLE_COUNTDOWN
		if threshold is None:
			threshold = self.__class__.STABLE_THRESHOLD

		self._rolling_window = rolling_window
		self._countdown = countdown
		self._threshold = threshold

		import collections
		self._distances = collections.deque([], self._rolling_window)
		self._totals = collections.deque([], self._rolling_window)
		self._sum_total = 0
		self._count = 0
		self._stable_counter = -1

	def is_stable(self):
		return self._stable_counter >= self._countdown

	def update(self, new_estimate):
		old_average_total = self.average_total

		self._sum_total += new_estimate
		self._totals.append(new_estimate)
		self._count += 1

		if old_average_total:
			self._distances.append(abs(self.average_total - old_average_total))

		if -self._threshold < self.average_distance < self._threshold:
			self._stable_counter += 1
		else:
			self._stable_counter = -1

		if self.is_stable():
			return self.average_total_rolling
		else:
			return None

	@property
	def average_total(self):
		if not self._count:
			return 0
		else:
			return self._sum_total / self._count

	@property
	def average_total_rolling(self):
		if not self._count or self._count < self._rolling_window or not len(self._totals):
			return -1
		else:
			return sum(self._totals) / len(self._totals)

	@property
	def average_distance(self):
		if not self._count or self._count < self._rolling_window + 1 or not len(self._distances):
			return -1
		else:
			return sum(self._distances) / len(self._distances)
