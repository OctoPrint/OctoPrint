# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import os
import time
import threading
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
		try:
			file_wrapper = octoprint.filemanager.util.DiskFileWrapper(os.path.basename(path), path)

			# determine future filename of file to be uploaded, abort if it can't be uploaded
			try:
				futurePath, futureFilename = self._file_manager.sanitize(octoprint.filemanager.FileDestinations.LOCAL, file_wrapper.filename)
			except:
				futurePath = None
				futureFilename = None

			if futureFilename is None or (len(self._file_manager.registered_slicers) == 0 and not octoprint.filemanager.valid_file_type(futureFilename)):
				return

			# prohibit overwriting currently selected file while it's being printed
			futureFullPath = self._file_manager.join_path(octoprint.filemanager.FileDestinations.LOCAL, futurePath, futureFilename)
			futureFullPathInStorage = self._file_manager.path_in_storage(octoprint.filemanager.FileDestinations.LOCAL, futureFullPath)

			if not self._printer.can_modify_file(futureFullPathInStorage, False):
				return

			reselect = self._printer.is_current_file(futureFullPathInStorage, False)

			added_file = self._file_manager.add_file(octoprint.filemanager.FileDestinations.LOCAL,
			                                         file_wrapper.filename,
			                                         file_wrapper,
			                                         allow_overwrite=True)
			if os.path.exists(path):
				try:
					os.remove(path)
				except:
					pass

			if reselect:
				self._printer.select_file(self._file_manager.path_on_disk(octoprint.filemanager.FileDestinations.LOCAL,
				                                                          added_file),
				                          False)
		except:
			self._logger.exception("There was an error while processing the file {} in the watched folder".format(path))

	def on_created(self, event):
		thread = threading.Thread(target=self._repeatedly_check, args=(event.src_path,))
		thread.daemon = True
		thread.start()

	def _repeatedly_check(self, path, interval=1, stable=5):
		last_size = os.stat(path).st_size
		countdown = stable

		while True:
			new_size = os.stat(path).st_size
			if new_size == last_size:
				self._logger.debug("File at {} is no longer growing, counting down: {}".format(path, countdown))
				countdown -= 1
				if countdown <= 0:
					break
			else:
				self._logger.debug("File at {} is still growing (last: {}, new: {}), waiting...".format(path, last_size, new_size))
				countdown = stable

			last_size = new_size
			time.sleep(interval)

		self._logger.debug("File at {} is stable, moving it".format(path))
		self._upload(path)
