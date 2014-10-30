# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import watchdog.events

import octoprint.filemanager
import octoprint.util


class GcodeWatchdogHandler(watchdog.events.PatternMatchingEventHandler):
	"""
	Takes care of automatically "uploading" files that get added to the watched folder.
	"""

	patterns = map(lambda x: "*.%s" % x, octoprint.filemanager.get_all_extensions())

	def __init__(self, file_manager, printer):
		watchdog.events.PatternMatchingEventHandler.__init__(self)

		self._logger = logging.getLogger(__name__)

		self._file_manager = file_manager
		self._printer = printer

	def _upload(self, path):
		class WatchdogFileWrapper(object):

			def __init__(self, path):
				import os
				self._path = path
				self.filename = os.path.basename(self._path)

			def save(self, target):
				octoprint.util.safeRename(self._path, target)

		file_wrapper = WatchdogFileWrapper(path)

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
		try:
			futureFilename = self._file_manager.sanitize_name(octoprint.filemanager.FileDestinations.LOCAL, file_wrapper.filename)
		except:
			futureFilename = None
		if futureFilename is None or (len(self._file_manager.registered_slicers) == 0 and not octoprint.filemanager.valid_file_type(futureFilename, type="gcode")):
			return

		# prohibit overwriting currently selected file while it's being printed
		if futureFilename == currentFilename and currentOrigin == octoprint.filemanager.FileDestinations.LOCAL and self._printer.isPrinting() or self._printer.isPaused():
			return

		added_file = self._file_manager.add_file(octoprint.filemanager.FileDestinations.LOCAL,
		                                         file_wrapper.filename,
		                                         file_wrapper,
		                                         allow_overwrite=True)
		if added_file is None:
			return

		slicer_name = self._file_manager.default_slicer
		if octoprint.filemanager.valid_file_type(added_file, "stl") and slicer_name:
			# if it's an STL we now have to slice it before we can continue
			import os
			name, ext = os.path.splitext(added_file)
			gcode_path = name + ".gco"
			self._file_manager.slice(slicer_name,
			                         octoprint.filemanager.FileDestinations.LOCAL,
			                         added_file,
			                         octoprint.filemanager.FileDestinations.LOCAL,
			                         gcode_path)

	def on_created(self, event):
		self._upload(event.src_path)
