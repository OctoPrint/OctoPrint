# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import os

import octoprint.plugin
import octoprint.util

from octoprint.events import eventManager, Events

from .destinations import FileDestinations
from .analysis import QueueEntry, AnalysisQueue
from .storage import LocalFileStorage
from .util import AbstractFileWrapper, StreamWrapper, DiskFileWrapper

from collections import namedtuple

ContentTypeMapping = namedtuple("ContentTypeMapping", "extensions, content_type")
ContentTypeDetector = namedtuple("ContentTypeDetector", "extensions, detector")

extensions = dict(
)

def full_extension_tree():
	result = dict(
		# extensions for 3d model files
		model=dict(
			stl=ContentTypeMapping(["stl"], "application/sla")
		),
		# extensions for printable machine code
		machinecode=dict(
			gcode=ContentTypeMapping(["gcode", "gco", "g"], "text/plain")
		)
	)

	extension_tree_hooks = octoprint.plugin.plugin_manager().get_hooks("octoprint.filemanager.extension_tree")
	for name, hook in extension_tree_hooks.items():
		try:
			hook_result = hook()
			if hook_result is None or not isinstance(hook_result, dict):
				continue
			result = octoprint.util.dict_merge(result, hook_result)
		except:
			logging.getLogger(__name__).exception("Exception while retrieving additional extension tree entries from hook {name}".format(name=name))

	return result

def get_extensions(type, subtree=None):
	if not subtree:
		subtree = full_extension_tree()

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
		subtree = full_extension_tree()

	result = []
	if isinstance(subtree, dict):
		for key, value in subtree.items():
			if isinstance(value, dict):
				result += get_all_extensions(value)
			elif isinstance(value, (ContentTypeMapping, ContentTypeDetector)):
				result += value.extensions
			elif isinstance(value, (list, tuple)):
				result += value
	elif isinstance(subtree, (ContentTypeMapping, ContentTypeDetector)):
		result = subtree.extensions
	elif isinstance(subtree, (list, tuple)):
		result = subtree
	return result

def get_path_for_extension(extension, subtree=None):
	if not subtree:
		subtree = full_extension_tree()

	for key, value in subtree.items():
		if isinstance(value, (ContentTypeMapping, ContentTypeDetector)) and extension in value.extensions:
			return [key]
		elif isinstance(value, (list, tuple)) and extension in value:
			return [key]
		elif isinstance(value, dict):
			path = get_path_for_extension(extension, subtree=value)
			if path:
				return [key] + path

	return None

def get_content_type_mapping_for_extension(extension, subtree=None):
	if not subtree:
		subtree = full_extension_tree()

	for key, value in subtree.items():
		content_extension_matches = isinstance(value, (ContentTypeMapping, ContentTypeDetector)) and extension in value. extensions
		list_extension_matches = isinstance(value, (list, tuple)) and extension in value

		if content_extension_matches or list_extension_matches:
			return value
		elif isinstance(value, dict):
			result = get_content_type_mapping_for_extension(extension, subtree=value)
			if result is not None:
				return result

	return None

def valid_extension(extension, type=None):
	if not type:
		return extension in get_all_extensions()
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

def get_mime_type(filename):
	_, extension = os.path.splitext(filename)
	extension = extension[1:].lower()
	mapping = get_content_type_mapping_for_extension(extension)
	if mapping:
		if isinstance(mapping, ContentTypeMapping) and mapping.content_type is not None:
			return mapping.content_type
		elif isinstance(mapping, ContentTypeDetector) and callable(mapping.detector):
			result = mapping.detector(filename)
			if result is not None:
				return result
	return "application/octet-stream"


class NoSuchStorage(Exception):
	pass


class FileManager(object):
	def __init__(self, analysis_queue, slicing_manager, printer_profile_manager, initial_storage_managers=None):
		self._logger = logging.getLogger(__name__)
		self._analysis_queue = analysis_queue
		self._analysis_queue.register_finish_callback(self._on_analysis_finished)

		self._storage_managers = dict()
		if initial_storage_managers:
			self._storage_managers.update(initial_storage_managers)

		self._slicing_manager = slicing_manager
		self._printer_profile_manager = printer_profile_manager

		import threading
		self._slicing_jobs = dict()
		self._slicing_jobs_mutex = threading.Lock()

		self._slicing_progress_callbacks = []
		self._last_slicing_progress = None

		self._progress_plugins = []
		self._preprocessor_hooks = dict()

		import octoprint.settings
		self._recovery_file = os.path.join(octoprint.settings.settings().getBaseFolder("data"), "print_recovery_data.yaml")

	def initialize(self):
		self.reload_plugins()

		def worker():
			self._logger.info("Adding backlog items from all storage types to analysis queue...".format(**locals()))
			for storage_type, storage_manager in self._storage_managers.items():
				self._determine_analysis_backlog(storage_type, storage_manager)

		import threading
		thread = threading.Thread(target=worker)
		thread.daemon = True
		thread.start()

	def reload_plugins(self):
		self._progress_plugins = octoprint.plugin.plugin_manager().get_implementations(octoprint.plugin.ProgressPlugin)
		self._preprocessor_hooks = octoprint.plugin.plugin_manager().get_hooks("octoprint.filemanager.preprocessor")

	def register_slicingprogress_callback(self, callback):
		self._slicing_progress_callbacks.append(callback)

	def unregister_slicingprogress_callback(self, callback):
		try:
			self._slicing_progress_callbacks.remove(callback)
		except ValueError:
			# callback was not registered
			pass

	def _determine_analysis_backlog(self, storage_type, storage_manager):
		counter = 0
		for entry, path, printer_profile in storage_manager.analysis_backlog:
			file_type = get_file_type(path)[-1]

			# we'll use the default printer profile for the backlog since we don't know better
			queue_entry = QueueEntry(entry, file_type, storage_type, path, self._printer_profile_manager.get_default())
			self._analysis_queue.enqueue(queue_entry, high_priority=False)
			counter += 1
		self._logger.info("Added {counter} items from storage type \"{storage_type}\" to analysis queue".format(**locals()))

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

	def slice(self, slicer_name, source_location, source_path, dest_location, dest_path,
	          position=None, profile=None, printer_profile_id=None, overrides=None, callback=None, callback_args=None):
		absolute_source_path = self.path_on_disk(source_location, source_path)

		def stlProcessed(source_location, source_path, tmp_path, dest_location, dest_path, start_time, printer_profile_id, callback, callback_args, _error=None, _cancelled=False, _analysis=None):
			try:
				if _error:
					eventManager().fire(Events.SLICING_FAILED, {"stl": source_path, "gcode": dest_path, "reason": _error})
				elif _cancelled:
					eventManager().fire(Events.SLICING_CANCELLED, {"stl": source_path, "gcode": dest_path})
				else:
					source_meta = self.get_metadata(source_location, source_path)
					hash = source_meta["hash"]

					import io
					links = [("model", dict(name=source_path))]
					_, stl_name = self.split_path(source_location, source_path)
					file_obj = StreamWrapper(os.path.basename(dest_path),
					                         io.BytesIO(u";Generated from {stl_name} {hash}\n".format(**locals()).encode("ascii", "replace")),
					                         io.FileIO(tmp_path, "rb"))

					printer_profile = self._printer_profile_manager.get(printer_profile_id)
					self.add_file(dest_location, dest_path, file_obj, links=links, allow_overwrite=True, printer_profile=printer_profile, analysis=_analysis)

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

		slicer = self._slicing_manager.get_slicer(slicer_name)

		import time
		start_time = time.time()
		eventManager().fire(Events.SLICING_STARTED, {"stl": source_path, "gcode": dest_path, "progressAvailable": slicer.get_slicer_properties()["progress_report"] if slicer else False})

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

		args = (source_location, source_path, temp_path, dest_location, dest_path, start_time, printer_profile_id, callback, callback_args)
		self._slicing_manager.slice(slicer_name,
		                            absolute_source_path,
		                            temp_path,
		                            profile,
		                            stlProcessed,
		                            position=position,
		                            callback_args=args,
		                            overrides=overrides,
		                            printer_profile_id=printer_profile_id,
		                            on_progress=self.on_slicing_progress,
		                            on_progress_args=(slicer_name, source_location, source_path, dest_location, dest_path))

	def on_slicing_progress(self, slicer, source_location, source_path, dest_location, dest_path, _progress=None):
		if not _progress:
			return

		progress_int = int(_progress * 100)
		if self._last_slicing_progress != progress_int:
			self._last_slicing_progress = progress_int
			for callback in self._slicing_progress_callbacks:
				try: callback.sendSlicingProgress(slicer, source_location, source_path, dest_location, dest_path, progress_int)
				except: self._logger.exception("Exception while pushing slicing progress")

			if progress_int:
				def call_plugins(slicer, source_location, source_path, dest_location, dest_path, progress):
					for plugin in self._progress_plugins:
						try:
							plugin.on_slicing_progress(slicer, source_location, source_path, dest_location, dest_path, progress)
						except:
							self._logger.exception("Exception while sending slicing progress to plugin %s" % plugin._identifier)

				import threading
				thread = threading.Thread(target=call_plugins, args=(slicer, source_location, source_path, dest_location, dest_path, progress_int))
				thread.daemon = False
				thread.start()


	def get_busy_files(self):
		return self._slicing_jobs.keys()

	def file_in_path(self, destination, path, file):
		return self._storage(destination).file_in_path(path, file)

	def file_exists(self, destination, path):
		return self._storage(destination).file_exists(path)

	def folder_exists(self, destination, path):
		return self._storage(destination).folder_exists(path)

	def list_files(self, destinations=None, path=None, filter=None, recursive=None):
		if not destinations:
			destinations = self._storage_managers.keys()
		if isinstance(destinations, (str, unicode, basestring)):
			destinations = [destinations]

		result = dict()
		for dst in destinations:
			result[dst] = self._storage_managers[dst].list_files(path=path, filter=filter, recursive=recursive)
		return result

	def add_file(self, destination, path, file_object, links=None, allow_overwrite=False, printer_profile=None, analysis=None):
		if printer_profile is None:
			printer_profile = self._printer_profile_manager.get_current_or_default()

		for hook in self._preprocessor_hooks.values():
			try:
				hook_file_object = hook(path, file_object, links=links, printer_profile=printer_profile, allow_overwrite=allow_overwrite)
			except:
				self._logger.exception("Error when calling preprocessor hook {}, ignoring".format(hook))
				continue

			if hook_file_object is not None:
				file_object = hook_file_object
		file_path = self._storage(destination).add_file(path, file_object, links=links, printer_profile=printer_profile, allow_overwrite=allow_overwrite)
		absolute_path = self._storage(destination).path_on_disk(file_path)

		if analysis is None:
			file_type = get_file_type(absolute_path)
			if file_type:
				queue_entry = QueueEntry(file_path, file_type[-1], destination, absolute_path, printer_profile)
				self._analysis_queue.enqueue(queue_entry, high_priority=True)
		else:
			self._add_analysis_result(destination, path, analysis)

		eventManager().fire(Events.UPDATED_FILES, dict(type="printables"))
		return file_path

	def remove_file(self, destination, path):
		self._storage(destination).remove_file(path)
		eventManager().fire(Events.UPDATED_FILES, dict(type="printables"))

	def copy_file(self, destination, source, dst):
		self._storage(destination).copy_file(source, dst)
		eventManager().fire(Events.UPDATED_FILES, dict(type="printables"))

	def move_file(self, destination, source, dst):
		self._storage(destination).move_file(source, dst)
		eventManager().fire(Events.UPDATED_FILES, dict(type="printables"))

	def add_folder(self, destination, path, ignore_existing=True):
		folder_path = self._storage(destination).add_folder(path, ignore_existing=ignore_existing)
		eventManager().fire(Events.UPDATED_FILES, dict(type="printables"))
		return folder_path

	def remove_folder(self, destination, path, recursive=True):
		self._storage(destination).remove_folder(path, recursive=recursive)
		eventManager().fire(Events.UPDATED_FILES, dict(type="printables"))

	def copy_folder(self, destination, source, dst):
		self._storage(destination).copy_folder(source, dst)
		eventManager().fire(Events.UPDATED_FILES, dict(type="printables"))

	def move_folder(self, destination, source, dst):
		self._storage(destination).move_folder(source, dst)
		eventManager().fire(Events.UPDATED_FILES, dict(type="printables"))

	def get_metadata(self, destination, path):
		return self._storage(destination).get_metadata(path)

	def add_link(self, destination, path, rel, data):
		self._storage(destination).add_link(path, rel, data)

	def remove_link(self, destination, path, rel, data):
		self._storage(destination).remove_link(path, rel, data)

	def log_print(self, destination, path, timestamp, print_time, success, printer_profile):
		try:
			if success:
				self._storage(destination).add_history(path, dict(timestamp=timestamp, printTime=print_time, success=success, printerProfile=printer_profile))
			else:
				self._storage(destination).add_history(path, dict(timestamp=timestamp, success=success, printerProfile=printer_profile))
			eventManager().fire(Events.METADATA_STATISTICS_UPDATED, dict(storage=destination, path=path))
		except NoSuchStorage:
			# if there's no storage configured where to log the print, we'll just not log it
			pass

	def save_recovery_data(self, origin, path, pos):
		import time
		import yaml
		from octoprint.util import atomic_write

		data = dict(origin=origin,
		            path=self.path_in_storage(origin, path),
		            pos=pos,
		            date=time.time())
		try:
			with atomic_write(self._recovery_file) as f:
				yaml.safe_dump(data, stream=f, default_flow_style=False, indent="  ", allow_unicode=True)
		except:
			self._logger.exception("Could not write recovery data to file {}".format(self._recovery_file))

	def delete_recovery_data(self):
		if not os.path.isfile(self._recovery_file):
			return

		try:
			os.remove(self._recovery_file)
		except:
			self._logger.exception("Error deleting recovery data file {}".format(self._recovery_file))

	def get_recovery_data(self):
		if not os.path.isfile(self._recovery_file):
			return None

		import yaml
		try:
			with open(self._recovery_file) as f:
				data = yaml.safe_load(f)
			return data
		except:
			self._logger.exception("Could not read recovery data from file {}".format(self._recovery_file))
			self.delete_recovery_data()

	def set_additional_metadata(self, destination, path, key, data, overwrite=False, merge=False):
		self._storage(destination).set_additional_metadata(path, key, data, overwrite=overwrite, merge=merge)

	def remove_additional_metadata(self, destination, path, key):
		self._storage(destination).remove_additional_metadata(path, key)

	def path_on_disk(self, destination, path):
		return self._storage(destination).path_on_disk(path)

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

	def path_in_storage(self, destination, path):
		return self._storage(destination).path_in_storage(path)

	def _storage(self, destination):
		if not destination in self._storage_managers:
			raise NoSuchStorage("No storage configured for destination {destination}".format(**locals()))
		return self._storage_managers[destination]

	def _add_analysis_result(self, destination, path, result):
		if not destination in self._storage_managers:
			return

		storage_manager = self._storage_managers[destination]
		storage_manager.set_additional_metadata(path, "analysis", result)

	def _on_analysis_finished(self, entry, result):
		self._add_analysis_result(entry.location, entry.path, result)

