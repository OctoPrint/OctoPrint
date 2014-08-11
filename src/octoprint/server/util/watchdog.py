# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import os
import watchdog.events

import octoprint.gcodefiles
import octoprint.util
from octoprint.settings import settings


class UploadCleanupWatchdogHandler(watchdog.events.PatternMatchingEventHandler):
	"""
	Takes care of automatically deleting metadata entries for files that get deleted from the uploads folder
	"""

	patterns = map(lambda x: "*.%s" % x, octoprint.gcodefiles.GCODE_EXTENSIONS)

	def __init__(self, gcode_manager):
		watchdog.events.PatternMatchingEventHandler.__init__(self)
		self._gcode_manager = gcode_manager

	def on_deleted(self, event):
		filename = self._gcode_manager._getBasicFilename(event.src_path)
		if not filename:
			return

		self._gcode_manager.removeFileFromMetadata(filename)


class GcodeWatchdogHandler(watchdog.events.PatternMatchingEventHandler):
	"""
	Takes care of automatically "uploading" files that get added to the watched folder.
	"""

	patterns = map(lambda x: "*.%s" % x, octoprint.gcodefiles.SUPPORTED_EXTENSIONS)

	def __init__(self, gcodeManager, printer):
		watchdog.events.PatternMatchingEventHandler.__init__(self)

		self._logger = logging.getLogger(__name__)

		self._gcodeManager = gcodeManager
		self._printer = printer

	def _upload(self, path):
		class WatchdogFileWrapper(object):

			def __init__(self, path):
				self._path = path
				self.filename = os.path.basename(self._path)

			def save(self, target):
				octoprint.util.safeRename(self._path, target)

		fileWrapper = WatchdogFileWrapper(path)

		# determine current job
		currentFilename = None
		currentOrigin = None
		currentJob = self._printer.getCurrentJob()
		if currentJob is not None and "file" in currentJob.keys():
			currentJobFile = currentJob["file"]
			if "name" in currentJobFile.keys() and "origin" in currentJobFile.keys():
				currentFilename = currentJobFile["name"]
				currentOrigin = currentJobFile["origin"]

		# determine future filename of file to be uploaded, abort if it can't be uploaded
		futureFilename = self._gcodeManager.getFutureFilename(fileWrapper)
		if futureFilename is None or (not settings().getBoolean(["cura", "enabled"]) and not octoprint.gcodefiles.isGcodeFileName(futureFilename)):
			self._logger.warn("Could not add %s: Invalid file" % fileWrapper.filename)
			return

		# prohibit overwriting currently selected file while it's being printed
		if futureFilename == currentFilename and not currentOrigin == octoprint.gcodefiles.FileDestinations.SDCARD and self._printer.isPrinting() or self._printer.isPaused():
			self._logger.warn("Could not add %s: Trying to overwrite file that is currently being printed" % fileWrapper.filename)
			return

		self._gcodeManager.addFile(fileWrapper, octoprint.gcodefiles.FileDestinations.LOCAL)

	def on_created(self, event):
		self._upload(event.src_path)
