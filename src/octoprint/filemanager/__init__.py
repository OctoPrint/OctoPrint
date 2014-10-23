# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import os

from octoprint.events import eventManager, Events

from .destinations import FileDestinations
from .analysis import QueueEntry, AnalysisQueue
from .storage import LocalFileStorage

extensions = dict(
	# extensions for 3d model files
	model=dict(
		stl=["stl"]
	),
	# extensions for printable machine code
	machinecode=dict(
		gcode=["gcode", "gco", "g"]
	)
)

def get_extensions(type, subtree=None):
	if not subtree:
		subtree = extensions

	for key, value in subtree.items():
		if key == type:
			return get_all_extensions(subtree=value)
		elif isinstance(value, dict):
			sub_extensions = get_extensions(type, subtree=value)
			if sub_extensions:
				return sub_extensions

	return None

def get_all_extensions(subtree=None):
	if not subtree:
		subtree = extensions

	result = []
	if isinstance(subtree, dict):
		for key, value in subtree.items():
			if isinstance(value, dict):
				result += get_all_extensions(value)
			elif isinstance(value, (list, tuple)):
				result += value
	elif isinstance(subtree, (list, tuple)):
		result = subtree
	return result

def get_path_for_extension(extension, subtree=None):
	if not subtree:
		subtree = extensions

	for key, value in subtree.items():
		if isinstance(value, (list, tuple)) and extension in value:
			return [key]
		elif isinstance(value, dict):
			path = get_path_for_extension(extension, subtree=value)
			if path:
				return [key] + path

	return None

all_extensions = get_all_extensions()

def valid_extension(extension, type=None):
	if not type:
		return extension in all_extensions
	else:
		extensions = get_extensions(type)
		if extensions:
			return extension in extensions

def valid_file_type(filename, type=None):
	_, extension = os.path.splitext(filename)
	extension = extension[1:].lower()
	return valid_extension(extension, type=type)

def get_file_type(filename):
	_, extension = os.path.splitext(filename)
	extension = extension[1:].lower()
	return get_path_for_extension(extension)


class NoSuchStorage(Exception):
	pass


class FileManager(object):
	def __init__(self, analysis_queue, slicing_manager, initial_storage_managers=None):
		self._logger = logging.getLogger(__name__)
		self._analysis_queue = analysis_queue
		self._analysis_queue.register_finish_callback(self._on_analysis_finished)

		self._storage_managers = dict()
		if initial_storage_managers:
			self._storage_managers.update(initial_storage_managers)

		self._slicing_manager = slicing_manager

		import threading
		self._slicing_jobs = dict()
		self._slicing_jobs_mutex = threading.Lock()

		self._slicing_progress_callbacks = []
		self._last_slicing_progress = None

		for storage_type, storage_manager in self._storage_managers.items():
			self._determine_analysis_backlog(storage_type, storage_manager)

	def register_slicingprogress_callback(self, callback):
		self._slicing_progress_callbacks.append(callback)

	def unregister_slicingprogress_callback(self, callback):
		self._slicing_progress_callbacks.remove(callback)

	def _determine_analysis_backlog(self, storage_type, storage_manager):
		self._logger.info("Adding backlog items from {storage_type} to analysis queue".format(**locals()))
		for entry, path in storage_manager.analysis_backlog:
			file_type = get_file_type(path)[-1]

			queue_entry = QueueEntry(entry, file_type, storage_type, path)
			self._analysis_queue.enqueue(queue_entry, high_priority=False)

	def add_storage(self, storage_type, storage_manager):
		self._storage_managers[storage_type] = storage_manager
		self._determine_analysis_backlog(storage_type, storage_manager)

	def remove_storage(self, type):
		if not type in self._storage_managers:
			return
		del self._storage_managers[type]

	@property
	def slicing_enabled(self):
		return self._slicing_manager.slicing_enabled

	@property
	def registered_slicers(self):
		return self._slicing_manager.registered_slicers

	@property
	def default_slicer(self):
		return self._slicing_manager.default_slicer

	def slice(self, slicer_name, source_location, source_path, dest_location, dest_path, profile=None, overrides=None, callback=None, callback_args=None):
		absolute_source_path = self.get_absolute_path(source_location, source_path)

		def stlProcessed(source_location, source_path, tmp_path, dest_location, dest_path, start_time, callback, callback_args, _error=None, _cancelled=False):
			try:
				if _error:
					eventManager().fire(Events.SLICING_FAILED, {"stl": source_path, "gcode": dest_path, "reason": _error})
				elif _cancelled:
					eventManager().fire(Events.SLICING_CANCELLED, {"stl": source_path, "gcode": dest_path})
				else:
					source_meta = self.get_metadata(source_location, source_path)
					hash = source_meta["hash"]

					class Wrapper(object):
						def __init__(self, stl_name, temp_path, hash):
							self.stl_name = stl_name
							self.temp_path = temp_path
							self.hash = hash

						def save(self, absolute_dest_path):
							with open(absolute_dest_path, "w") as d:
								d.write(";Generated from {stl_name} {hash}\r".format(**vars(self)))
								with open(tmp_path, "r") as s:
									import shutil
									shutil.copyfileobj(s, d)

					links = [("model", dict(name=source_path))]
					_, stl_name = self.split_path(source_location, source_path)
					file_obj = Wrapper(stl_name, temp_path, hash)
					self.add_file(dest_location, dest_path, file_obj, links=links, allow_overwrite=True)

					end_time = time.time()
					eventManager().fire(Events.SLICING_DONE, {"stl": source_path, "gcode": dest_path, "time": end_time - start_time})

					if callback is not None:
						if callback_args is None:
							callback_args = ()
						callback(*callback_args)
			finally:
				os.remove(tmp_path)

				source_job_key = (source_location, source_path)
				dest_job_key = (dest_location, dest_path)

				with self._slicing_jobs_mutex:
					if source_job_key in self._slicing_jobs:
						del self._slicing_jobs[source_job_key]
					if dest_job_key in self._slicing_jobs:
						del self._slicing_jobs[dest_job_key]

		import time
		start_time = time.time()
		eventManager().fire(Events.SLICING_STARTED, {"stl": source_path, "gcode": dest_path})

		import tempfile
		f = tempfile.NamedTemporaryFile(suffix=".gco", delete=False)
		temp_path = f.name
		f.close()

		with self._slicing_jobs_mutex:
			source_job_key = (source_location, source_path)
			dest_job_key = (dest_location, dest_path)
			if dest_job_key in self._slicing_jobs:
				job_slicer_name, job_absolute_source_path, job_temp_path = self._slicing_jobs[dest_job_key]

				self._slicing_manager.cancel_slicing(job_slicer_name, job_absolute_source_path, job_temp_path)
				del self._slicing_jobs[dest_job_key]

			self._slicing_jobs[dest_job_key] = self._slicing_jobs[source_job_key] = (slicer_name, absolute_source_path, temp_path)

		args = (source_location, source_path, temp_path, dest_location, dest_path, start_time, callback, callback_args)
		return self._slicing_manager.slice(
			slicer_name,
			absolute_source_path,
			temp_path,
			profile,
			stlProcessed,
			callback_args=args,
			overrides=overrides,
			on_progress=self.on_slicing_progress,
			on_progress_args=(slicer_name, source_location, source_path, dest_location, dest_path))

	def on_slicing_progress(self, slicer, source_location, source_path, dest_location, dest_path, _progress=None):
		if not _progress:
			return

		progress_int = int(_progress * 100)
		if self._last_slicing_progress == progress_int:
			return
		else:
			self._last_slicing_progress = progress_int

		for callback in self._slicing_progress_callbacks:
			try: callback.sendSlicingProgress(slicer, source_location, source_path, dest_location, dest_path, progress_int)
			except: self._logger.exception("Exception while pushing slicing progress")

	def get_busy_files(self):
		return self._slicing_jobs.keys()

	def file_exists(self, destination, path):
		return self._storage(destination).file_exists(path)

	def list_files(self, destinations=None, path=None, filter=None, recursive=None):
		if not destinations:
			destinations = self._storage_managers.keys()
		if isinstance(destinations, (str, unicode, basestring)):
			destinations = [destinations]

		result = dict()
		for dst in destinations:
			result[dst] = self._storage_managers[dst].list_files(path=path, filter=filter, recursive=recursive)
		return result

	def add_file(self, destination, path, file_object, links=None, allow_overwrite=False):
		file_path = self._storage(destination).add_file(path, file_object, links=links, allow_overwrite=allow_overwrite)
		absolute_path = self._storage(destination).get_absolute_path(file_path)
		file_type = get_file_type(file_path)[-1]

		queue_entry = QueueEntry(file_path, file_type, destination, absolute_path)
		self._analysis_queue.enqueue(queue_entry, high_priority=True)

		eventManager().fire(Events.UPDATED_FILES, dict(type="printables"))
		return file_path

	def remove_file(self, destination, path):
		self._storage(destination).remove_file(path)
		eventManager().fire(Events.UPDATED_FILES, dict(type="printables"))

	def add_folder(self, destination, path, ignore_existing=True):
		folder_path = self._storage(destination).add_folder(path, ignore_existing=ignore_existing)
		eventManager().fire(Events.UPDATED_FILES, dict(type="printables"))
		return folder_path

	def remove_folder(self, destination, path, recursive=True):
		self._storage(destination).remove_folder(path, recursive=recursive)
		eventManager().fire(Events.UPDATED_FILES, dict(type="printables"))

	def get_metadata(self, destination, path):
		return self._storage(destination).get_metadata(path)

	def add_link(self, destination, path, rel, data):
		self._storage(destination).add_link(path, rel, data)

	def remove_link(self, destination, path, rel, data):
		self._storage(destination).remove_link(path, rel, data)

	def log_print(self, destination, path, timestamp, print_time, success):
		try:
			self._storage(destination).add_history(path, dict(timestamp=timestamp, printTime=print_time, success=success))
		except NoSuchStorage:
			# if there's no storage configured where to log the print, we'll just not log it
			pass

	def set_additional_metadata(self, destination, path, key, data, overwrite=False, merge=False):
		self._storage(destination).set_additional_metadata(path, key, data, overwrite=overwrite, merge=merge)

	def remove_additional_metadata(self, destination, path, key):
		self._storage(destination).remove_additional_metadata(path, key)

	def get_absolute_path(self, destination, path):
		return self._storage(destination).get_absolute_path(path)

	def sanitize(self, destination, path):
		return self._storage(destination).sanitize(path)

	def sanitize_name(self, destination, name):
		return self._storage(destination).sanitize_name(name)

	def sanitize_path(self, destination, path):
		return self._storage(destination).sanitize_path(path)

	def split_path(self, destination, path):
		return self._storage(destination).split_path(path)

	def join_path(self, destination, *path):
		return self._storage(destination).join_path(*path)

	def rel_path(self, destination, path):
		return self._storage(destination).rel_path(path)

	def _storage(self, destination):
		if not destination in self._storage_managers:
			raise NoSuchStorage("No storage configured for destination {destination}".format(**locals()))
		return self._storage_managers[destination]

	def _on_analysis_finished(self, entry, result):
		if not entry.location in self._storage_managers:
			return

		storage_manager = self._storage_managers[entry.location]
		storage_manager.set_additional_metadata(entry.path, "analysis", result)

