# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import logging
import Queue as queue
import os
import threading
import collections

from octoprint.events import Events, eventManager

import octoprint.util.gcodeInterpreter as gcodeInterpreter


class QueueEntry(collections.namedtuple("QueueEntry", "path, type, location, absolute_path, printer_profile")):
	"""
	A :class:`QueueEntry` for processing through the :class:`AnalysisQueue`. Wraps the entry's properties necessary
	for processing.

	Arguments:
	    path (str): Storage location specific path to the file to analyze.
	    type (str): Type of file to analyze, necessary to map to the correct :class:`AbstractAnalysisQueue` sub class.
	        At the moment, only ``gcode`` is supported here.
	    location (str): Location the file is located on.
	    absolute_path (str): Absolute path on disk through which to access the file.
	    printer_profile (PrinterProfile): :class:`PrinterProfile` which to use for analysis.
	"""

	def __str__(self):
		return "{location}:{path}".format(location=self.location, path=self.path)


class AnalysisQueue(object):
	"""
	OctoPrint's :class:`AnalysisQueue` can manage various :class:`AbstractAnalysisQueue` implementations, mapped
	by their machine code type.

	At the moment, only the analysis of GCODE files for 3D printing is supported, through :class:`GcodeAnalysisQueue`.

	By invoking :meth:`register_finish_callback` it is possible to register oneself as a callback to be invoked each
	time the analysis of a queue entry finishes. The call parameters will be the finished queue entry as the first
	and the analysis result as the second parameter. It is also possible to remove the registration again by invoking
	:meth:`unregister_finish_callback`.

	:meth:`enqueue` allows enqueuing :class:`QueueEntry` instances to analyze. If the :attr:`QueueEntry.type` is unknown
	(no specific child class of :class:`AbstractAnalysisQueue` is registered for it), nothing will happen. Otherwise the
	entry will be enqueued with the type specific analysis queue.
	"""

	def __init__(self):
		self._logger = logging.getLogger(__name__)
		self._callbacks = []
		self._queues = dict(
			gcode=GcodeAnalysisQueue(self._analysis_finished)
		)

	def register_finish_callback(self, callback):
		self._callbacks.append(callback)

	def unregister_finish_callback(self, callback):
		self._callbacks.remove(callback)

	def enqueue(self, entry, high_priority=False):
		if not entry.type in self._queues:
			return

		self._queues[entry.type].enqueue(entry, high_priority=high_priority)

	def pause(self):
		for queue in self._queues.values():
			queue.pause()

	def resume(self):
		for queue in self._queues.values():
			queue.resume()

	def _analysis_finished(self, entry, result):
		for callback in self._callbacks:
			callback(entry, result)
		eventManager().fire(Events.METADATA_ANALYSIS_FINISHED, {"file": entry.path, "result": result})

class AbstractAnalysisQueue(object):
	"""
	The :class:`AbstractAnalysisQueue` is the parent class of all specific analysis queues such as the
	:class:`GcodeAnalysisQueue`. It offers methods to enqueue new entries to analyze and pausing and resuming analysis
	processing.

	Arguments:
	    finished_callback (callable): Callback that will be called upon finishing analysis of an entry in the queue.
	        The callback will be called with the analyzed entry as the first argument and the analysis result as
	        returned from the queue implementation as the second parameter.

	.. automethod:: _do_analysis

	.. automethod:: _do_abort
	"""

	def __init__(self, finished_callback):
		self._logger = logging.getLogger(__name__)

		self._finished_callback = finished_callback

		self._active = threading.Event()
		self._active.set()

		self._currentFile = None
		self._currentProgress = None

		self._queue = queue.PriorityQueue()
		self._current = None

		self._worker = threading.Thread(target=self._work)
		self._worker.daemon = True
		self._worker.start()

	def enqueue(self, entry, high_priority=False):
		"""
		Enqueues an ``entry`` for analysis by the queue.

		If ``high_priority`` is True (defaults to False), the entry will be prioritized and hence processed before
		other entries in the queue with normal priority.

		Arguments:
		    entry (QueueEntry): The :class:`QueueEntry` to analyze.
		    high_priority (boolean): Whether to process the provided entry with high priority (True) or not
		        (False, default)
		"""

		if high_priority:
			self._logger.debug("Adding entry {entry} to analysis queue with high priority".format(entry=entry))
			prio = 0
		else:
			self._logger.debug("Adding entry {entry} to analysis queue with low priority".format(entry=entry))
			prio = 100

		self._queue.put((prio, entry))

	def pause(self):
		"""
		Pauses processing of the queue, e.g. when a print is active.
		"""

		self._logger.debug("Pausing analysis")
		self._active.clear()
		if self._current is not None:
			self._logger.debug("Aborting running analysis, will restart when analyzer is resumed")
			self._do_abort()

	def resume(self):
		"""
		Resumes processing of the queue, e.g. when a print has finished.
		"""

		self._logger.debug("Resuming analyzer")
		self._active.set()

	def _work(self):
		aborted = None
		while True:
			if aborted is not None:
				entry = aborted
				aborted = None
				self._logger.debug("Got an aborted analysis job for entry {entry}, processing this instead of first item in queue".format(**locals()))
			else:
				(priority, entry) = self._queue.get()
				self._logger.debug("Processing entry {entry} from queue (priority {priority})".format(**locals()))

			self._active.wait()

			try:
				self._analyze(entry)
				self._queue.task_done()
			except gcodeInterpreter.AnalysisAborted:
				aborted = entry
				self._logger.debug("Running analysis of entry {entry} aborted".format(**locals()))

	def _analyze(self, entry):
		path = entry.absolute_path
		if path is None or not os.path.exists(path):
			return

		self._current = entry
		self._current_progress = 0

		try:
			self._logger.debug("Starting analysis of {entry}".format(**locals()))
			eventManager().fire(Events.METADATA_ANALYSIS_STARTED, {"file": entry.path, "type": entry.type})
			result = self._do_analysis()
			self._logger.debug("Analysis of entry {entry} finished, notifying callback".format(**locals()))
			self._finished_callback(self._current, result)
		finally:
			self._current = None
			self._current_progress = None

	def _do_analysis(self):
		"""
		Performs the actual analysis of the current entry which can be accessed via ``self._current``. Needs to be
		overridden by sub classes.

		Returns:
		    object: The result of the analysis which will be forwarded to the ``finished_callback`` provided during
		        construction.
		"""
		return None

	def _do_abort(self):
		"""
		Aborts analysis of the current entry. Needs to be overridden by sub classes.
		"""
		pass


class GcodeAnalysisQueue(AbstractAnalysisQueue):
	"""
	A queue to analyze GCODE files. Analysis results are :class:`dict` instances structured as follows:

	.. list-table::
	   :widths: 25 70

	   - * **Key**
	     * **Description**
	   - * ``estimatedPrintTime``
	     * Estimated time the file take to print, in minutes
	   - * ``filament``
	     * Substructure describing estimated filament usage. Keys are ``tool0`` for the first extruder, ``tool1`` for
	       the second and so on. For each tool extruded length and volume (based on diameter) are provided.
	   - * ``filament.toolX.length``
	     * The extruded length in mm
	   - * ``filament.toolX.volume``
	     * The extruded volume in cm³
	"""

	def _do_analysis(self):
		try:
			self._gcode = gcodeInterpreter.gcode()
			self._gcode.load(self._current.absolute_path, self._current.printer_profile)

			result = dict()
			if self._gcode.totalMoveTimeMinute:
				result["estimatedPrintTime"] = self._gcode.totalMoveTimeMinute * 60
			if self._gcode.extrusionAmount:
				result["filament"] = dict()
				for i in range(len(self._gcode.extrusionAmount)):
					result["filament"]["tool%d" % i] = {
						"length": self._gcode.extrusionAmount[i],
						"volume": self._gcode.extrusionVolume[i]
					}
			return result
		finally:
			self._gcode = None

	def _do_abort(self):
		if self._gcode:
			self._gcode.abort()