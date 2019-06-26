# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import os
import shutil
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
		watchdog.events.PatternMatchingEventHandler.__init__(self, patterns=list(map(lambda x: "*.%s" % x, octoprint.filemanager.get_all_extensions())))

		self._logger = logging.getLogger(__name__)

		self._file_manager = file_manager
		self._printer = printer

	def initial_scan(self, folder):
		def run_scan():
			try:
				from os import scandir
			except ImportError:
				from scandir import scandir

			self._logger.info("Running initial scan on watched folder...")
			for entry in scandir(folder):
				path = entry.path

				if not self._valid_path(path):
					continue

				self._logger.info("Found {}, trying to add it".format(path))
				self._upload(path)
			self._logger.info("... initial scan done.")

		thread = threading.Thread(target=run_scan)
		thread.daemon = True
		thread.start()

	def on_created(self, event):
		path = event.src_path
		if not self._valid_path(path):
			return

		thread = threading.Thread(target=self._repeatedly_check, args=(path,))
		thread.daemon = True
		thread.start()

	def _upload(self, path):
		# noinspection PyBroadException
		try:
			file_wrapper = octoprint.filemanager.util.DiskFileWrapper(os.path.basename(path), path)

			# determine future filename of file to be uploaded, abort if it can't be uploaded
			try:
				futurePath, futureFilename = self._file_manager.sanitize(octoprint.filemanager.FileDestinations.LOCAL, file_wrapper.filename)
			except Exception:
				self._logger.exception("Could not wrap %s", path)
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
				except Exception:
					pass

			if reselect:
				self._printer.select_file(self._file_manager.path_on_disk(octoprint.filemanager.FileDestinations.LOCAL,
				                                                          added_file),
				                          False)
		except Exception:
			self._logger.exception("There was an error while processing the file {} in the watched folder".format(path))
		finally:
			if os.path.exists(path):
				# file is still there - that should only happen if something went wrong, so mark it as failed
				# noinspection PyBroadException
				try:
					shutil.move(path, "{}.failed".format(path))
				except:
					# something went really wrong here.... but we can't do anything about it, so just log it
					self._logger.exception("There was an error while trying to mark {} as failed in the watched folder".format(path))

	def _repeatedly_check(self, path, interval=1, stable=5):
		try:
			last_size = os.stat(path).st_size
		except Exception:
			return

		countdown = stable

		while True:
			try:
				new_size = os.stat(path).st_size
			except Exception:
				return

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

	def _valid_path(self, path):
		_, ext = os.path.splitext(path)
		return octoprint.filemanager.valid_file_type(path) and not octoprint.util.is_hidden_path(path) and ext != "failed"
