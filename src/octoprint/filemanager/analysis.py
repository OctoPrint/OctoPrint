# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import logging
try:
	import queue
except ImportError:
	import Queue as queue
import os
import threading
import collections
import time

from octoprint.events import Events, eventManager
from octoprint.settings import settings


class QueueEntry(collections.namedtuple("QueueEntry", "name, path, type, location, absolute_path, printer_profile")):
	"""
	A :class:`QueueEntry` for processing through the :class:`AnalysisQueue`. Wraps the entry's properties necessary
	for processing.

	Arguments:
	    name (str): Name of the file to analyze.
	    path (str): Storage location specific path to the file to analyze.
	    type (str): Type of file to analyze, necessary to map to the correct :class:`AbstractAnalysisQueue` sub class.
	        At the moment, only ``gcode`` is supported here.
	    location (str): Location the file is located on.
	    absolute_path (str): Absolute path on disk through which to access the file.
	    printer_profile (PrinterProfile): :class:`PrinterProfile` which to use for analysis.
	"""

	def __str__(self):
		return "{location}:{path}".format(location=self.location, path=self.path)


class AnalysisAborted(Exception):
	def __init__(self, reenqueue=True, *args, **kwargs):
		Exception.__init__(self, *args, **kwargs)
		self.reenqueue = reenqueue


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
			return False

		self._queues[entry.type].enqueue(entry, high_priority=high_priority)
		return True

	def dequeue(self, entry):
		if not entry.type in self._queues:
			return False

		self._queues[entry.type].dequeue(entry.location, entry.path)

	def dequeue_folder(self, destination, path):
		for queue in self._queues.values():
			queue.dequeue_folder(destination, path)

	def pause(self):
		for queue in self._queues.values():
			queue.pause()

	def resume(self):
		for queue in self._queues.values():
			queue.resume()

	def _analysis_finished(self, entry, result):
		for callback in self._callbacks:
			callback(entry, result)
		eventManager().fire(Events.METADATA_ANALYSIS_FINISHED, {"name": entry.name,
		                                                        "path": entry.path,
		                                                        "origin": entry.location,
		                                                        "result": result,

		                                                        # TODO: deprecated, remove in a future release
		                                                        "file": entry.path})

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

	LOW_PRIO = 100
	LOW_PRIO_ABORTED = 75
	HIGH_PRIO = 50
	HIGH_PRIO_ABORTED = 0

	def __init__(self, finished_callback):
		self._logger = logging.getLogger(__name__)

		self._finished_callback = finished_callback

		self._active = threading.Event()
		self._active.set()

		self._done = threading.Event()
		self._done.clear()

		self._currentFile = None
		self._currentProgress = None

		self._queue = queue.PriorityQueue()
		self._current = None
		self._current_highprio = False

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
			prio = self.__class__.HIGH_PRIO
		else:
			self._logger.debug("Adding entry {entry} to analysis queue with low priority".format(entry=entry))
			prio = self.__class__.LOW_PRIO

		self._queue.put((prio, entry, high_priority))
		if high_priority and self._current is not None and not self._current_highprio:
			self._logger.debug("Aborting current analysis in favor of high priority one")
			self._do_abort()

	def dequeue(self, location, path):
		if self._current is not None and self._current.location == location \
				and self._current.path == path:
			self._do_abort(reenqueue=False)
			self._done.wait()
			self._done.clear()

	def dequeue_folder(self, location, path):
		if self._current is not None and self._current.location == location \
				and self._current.path.startswith(path + "/"):
			self._do_abort(reenqueue=False)
			self._done.wait()
			self._done.clear()

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
		while True:
			(priority, entry, high_priority) = self._queue.get()
			self._logger.debug("Processing entry {} from queue (priority {})".format(entry, priority))
			self._active.wait()

			try:
				self._analyze(entry, high_priority=high_priority)
				self._queue.task_done()
				self._done.set()
			except AnalysisAborted as ex:
				if ex.reenqueue:
					self._queue.put((self.__class__.HIGH_PRIO_ABORTED if high_priority else self.__class__.LOW_PRIO_ABORTED,
					                 entry,
					                 high_priority))
				self._logger.debug("Running analysis of entry {} aborted".format(entry))
				self._queue.task_done()
				self._done.set()
			else:
				time.sleep(1.0)

	def _analyze(self, entry, high_priority=False):
		path = entry.absolute_path
		if path is None or not os.path.exists(path):
			return

		self._current = entry
		self._current_highprio = high_priority
		self._current_progress = 0

		try:
			start_time = time.time()
			self._logger.info("Starting analysis of {}".format(entry))
			eventManager().fire(Events.METADATA_ANALYSIS_STARTED, {"name": entry.name,
			                                                       "path": entry.path,
			                                                       "origin": entry.location,
			                                                       "type": entry.type,

			                                                       # TODO deprecated, remove in 1.4.0
			                                                       "file": entry.path})
			try:
				result = self._do_analysis(high_priority=high_priority)
			except TypeError:
				result = self._do_analysis()
			self._logger.info("Analysis of entry {} finished, needed {:.2f}s".format(entry, time.time() - start_time))
			self._finished_callback(self._current, result)
		finally:
			self._current = None
			self._current_progress = None

	def _do_analysis(self, high_priority=False):
		"""
		Performs the actual analysis of the current entry which can be accessed via ``self._current``. Needs to be
		overridden by sub classes.

		Arguments:
		    high_priority (bool): Whether the current entry has high priority or not.

		Returns:
		    object: The result of the analysis which will be forwarded to the ``finished_callback`` provided during
		        construction.
		"""
		return None

	def _do_abort(self, reenqueue=True):
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

	def __init__(self, finished_callback):
		AbstractAnalysisQueue.__init__(self, finished_callback)

		self._aborted = False
		self._reenqueue = False

	def _do_analysis(self, high_priority=False):
		import sarge
		import sys
		import yaml

		try:
			throttle = settings().getFloat(["gcodeAnalysis", "throttle_highprio"]) if high_priority \
				else settings().getFloat(["gcodeAnalysis", "throttle_normalprio"])
			throttle_lines = settings().getInt(["gcodeAnalysis", "throttle_lines"])
			max_extruders = settings().getInt(["gcodeAnalysis", "maxExtruders"])
			g90_extruder = settings().getBoolean(["feature", "g90InfluencesExtruder"])
			speedx = self._current.printer_profile["axes"]["x"]["speed"]
			speedy = self._current.printer_profile["axes"]["y"]["speed"]
			offsets = self._current.printer_profile["extruder"]["offsets"]

			command = [sys.executable, "-m", "octoprint", "analysis", "gcode",
			           "--speed-x={}".format(speedx), "--speed-y={}".format(speedy),
			           "--max-t={}".format(max_extruders), "--throttle={}".format(throttle),
			           "--throttle-lines={}".format(throttle_lines)]
			for offset in offsets[1:]:
				command += ["--offset", str(offset[0]), str(offset[1])]
			if g90_extruder:
				command += ["--g90-extruder"]
			command.append(self._current.absolute_path)

			self._logger.info("Invoking analysis command: {}".format(" ".join(command)))

			self._aborted = False
			p = sarge.run(command, async=True, stdout=sarge.Capture())

			while len(p.commands) == 0:
				# somewhat ugly... we can't use wait_events because
				# the events might not be all set if an exception
				# by sarge is triggered within the async process
				# thread
				time.sleep(0.01)

			# by now we should have a command, let's wait for its
			# process to have been prepared
			p.commands[0].process_ready.wait()

			if not p.commands[0].process:
				# the process might have been set to None in case of any exception
				raise RuntimeError(u"Error while trying to run command {}".format(" ".join(command)))

			try:
				# let's wait for stuff to finish
				while p.returncode is None:
					if self._aborted:
						# oh, we shall abort, let's do so!
						p.commands[0].terminate()
						raise AnalysisAborted(reenqueue=self._reenqueue)

					# else continue
					p.commands[0].poll()
			finally:
				p.close()

			output = p.stdout.text
			self._logger.debug("Got output: {!r}".format(output))

			if not "RESULTS:" in output:
				raise RuntimeError("No analysis result found")

			_, output = output.split("RESULTS:")
			analysis = yaml.safe_load(output)

			result = dict()
			result["printingArea"] = analysis["printing_area"]
			result["dimensions"] = analysis["dimensions"]
			if analysis["total_time"]:
				result["estimatedPrintTime"] = analysis["total_time"] * 60
			if analysis["extrusion_length"]:
				result["filament"] = dict()
				for i in range(len(analysis["extrusion_length"])):
					result["filament"]["tool%d" % i] = {
						"length": analysis["extrusion_length"][i],
						"volume": analysis["extrusion_volume"][i]
					}
			return result
		finally:
			self._gcode = None

	def _do_abort(self, reenqueue=True):
		self._aborted = True
		self._reenqueue = reenqueue
