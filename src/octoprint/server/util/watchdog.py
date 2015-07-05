# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import watchdog.events

import octoprint.filemanager
import octoprint.filemanager.util
import octoprint.util


class GcodeWatchdogHandler(watchdog.events.PatternMatchingEventHandler):
	"""
	Takes care of automatically "uploading" files that get added to the watched folder.
	"""

	def __init__(self, file_manager, printer):
		watchdog.events.PatternMatchingEventHandler.__init__(self, patterns=map(lambda x: "*.%s" % x, octoprint.filemanager.get_all_extensions()))

		self._logger = logging.getLogger(__name__)

		self._file_manager = file_manager
		self._printer = printer

	def _upload(self, path):
		import os
		file_wrapper = octoprint.filemanager.util.DiskFileWrapper(os.path.basename(path), path)

		# determine current job
		currentFilename = None
		currentOrigin = None
		currentJob = self._printer.get_current_job()
		if currentJob is not None and "file" in currentJob.keys():
			currentJobFile = currentJob["file"]
			if "name" in currentJobFile.keys() and "origin" in currentJobFile.keys():
				currentFilename = currentJobFile["name"]
				currentOrigin = currentJobFile["origin"]

		# determine future filename of file to be uploaded, abort if it can't be uploaded
		try:
			futureFilename = self._file_manager.sanitize_name(octoprint.filemanager.FileDestinations.LOCAL, file_wrapper.filename)
		except:
			futureFilename = None
		if futureFilename is None or (len(self._file_manager.registered_slicers) == 0 and not octoprint.filemanager.valid_file_type(futureFilename)):
			return

		# prohibit overwriting currently selected file while it's being printed
		if futureFilename == currentFilename and currentOrigin == octoprint.filemanager.FileDestinations.LOCAL and self._printer.is_printing() or self._printer.is_paused():
			return

		self._file_manager.add_file(octoprint.filemanager.FileDestinations.LOCAL,
		                            file_wrapper.filename,
		                            file_wrapper,
		                            allow_overwrite=True)
		if os.path.exists(path):
			try:
				os.remove(path)
			except:
				self._logger.exception("Error while trying to clear a file from the watched folder")

	def on_created(self, event):
		self._upload(event.src_path)
