# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import logging
import os
import pylru
import tempfile
import shutil

import octoprint.filemanager

from octoprint.util import is_hidden_path

class StorageInterface(object):
	"""
	Interface of storage adapters for OctoPrint.
	"""


	@property
	def analysis_backlog(self):
		"""
		Get an iterator over all items stored in the storage that need to be analysed by the :class:`~octoprint.filemanager.AnalysisQueue`.

		The yielded elements are expected as storage specific absolute paths to the respective files. Don't forget
		to recurse into folders if your storage adapter supports those.

		:return: an iterator yielding all un-analysed files in the storage
		"""
		# empty generator pattern, yield is intentionally unreachable
		return
		yield

	def file_exists(self, path):
		"""
		Returns whether the file indicated by ``path`` exists or not.
		:param string path: the path to check for existence
		:return: ``True`` if the file exists, ``False`` otherwise
		"""
		raise NotImplementedError()

	def list_files(self, path=None, filter=None, recursive=True):
		"""
		List all files in storage starting at ``path``. If ``recursive`` is set to True (the default), also dives into
		subfolders.

		An optional filter function can be supplied which will be called with a file name and file data and which has
		to return True if the file is to be included in the result or False if not.

		The data structure of the returned result will be a dictionary mapping from file names to entry data. File nodes
		will contain their metadata here, folder nodes will contain their contained files and folders. Example::

		   {
		     "some_folder": {
		       "type": "folder",
		       "children": {
		         "some_sub_folder": {
		           "type": "folder",
		           "children": { ... }
		         },
		         "some_file.gcode": {
		           "type": "machinecode",
		           "hash": "<sha1 hash>",
		           "links": [ ... ],
		           ...
		         },
		         ...
		       }
		     "test.gcode": {
		       "type": "machinecode",
		       "hash": "<sha1 hash>",
		       "links": [...],
		       ...
		     },
		     "test.stl": {
		       "type": "model",
		       "hash": "<sha1 hash>",
		       "links": [...],
		       ...
		     },
		     ...
		   }

		:param string path:     base path from which to recursively list all files, optional, if not supplied listing will start
		                        from root of base folder
		:param function filter: a filter that matches the files that are to be returned, may be left out in which case no
		                        filtering will take place
		:param bool recursive:  will also step into sub folders for building the complete list if set to True
		:return: a dictionary mapping entry names to entry data that represents the whole file list
		"""
		raise NotImplementedError()

	def add_folder(self, path, ignore_existing=True):
		"""
		Adds a folder as ``path``. The ``path`` will be sanitized.

		:param string path:          the path of the new folder
		:param bool ignore_existing: if set to True, no error will be raised if the folder to be added already exists
		:return: the sanitized name of the new folder to be used for future references to the folder
		"""
		raise NotImplementedError()

	def remove_folder(self, path, recursive=True):
		"""
		Removes the folder at ``path``.

		:param string path:    the path of the folder to remove
		:param bool recursive: if set to True, contained folders and files will also be removed, otherwise and error will
		                       be raised if the folder is not empty (apart from ``.metadata.yaml``) when it's to be removed
		"""
		raise NotImplementedError()

	def add_file(self, path, file_object, printer_profile=None, links=None, allow_overwrite=False):
		"""
		Adds the file ``file_object`` as ``path``

		:param string path:            the file's new path, will be sanitized
		:param object file_object:     a file object that provides a ``save`` method which will be called with the destination path
		                               where the object should then store its contents
		:param object printer_profile: the printer profile associated with this file (if any)
		:param list links:             any links to add with the file
		:param bool allow_overwrite:   if set to True no error will be raised if the file already exists and the existing file
		                               and its metadata will just be silently overwritten
		:return: the sanitized name of the file to be used for future references to it
		"""
		raise NotImplementedError()

	def remove_file(self, path):
		"""
		Removes the file at ``path``. Will also take care of deleting the corresponding entries
		in the metadata and deleting all links pointing to the file.

		:param string path: path of the file to remove
		"""
		raise NotImplementedError()

	def get_metadata(self, path):
		"""
		Retrieves the metadata for the file ``path``.

		:param path: virtual path to the file for which to retrieve the metadata
		:return: the metadata associated with the file
		"""
		raise NotImplementedError()

	def add_link(self, path, rel, data):
		"""
		Adds a link of relation ``rel`` to file ``path`` with the given ``data``.

		The following relation types are currently supported:

		  * ``model``: adds a link to a model from which the file was created/sliced, expected additional data is the ``name``
		    and optionally the ``hash`` of the file to link to. If the link can be resolved against another file on the
		    current ``path``, not only will it be added to the links of ``name`` but a reverse link of type ``machinecode``
		    refering to ``name`` and its hash will also be added to the linked ``model`` file
		  * ``machinecode``: adds a link to a file containing machine code created from the current file (model), expected
		    additional data is the ``name`` and optionally the ``hash`` of the file to link to. If the link can be resolved
		    against another file on the current ``path``, not only will it be added to the links of ``name`` but a reverse
		    link of type ``model`` refering to ``name`` and its hash will also be added to the linked ``model`` file.
		  * ``web``: adds a location on the web associated with this file (e.g. a website where to download a model),
		    expected additional data is a ``href`` attribute holding the website's URL and optionally a ``retrieved``
		    attribute describing when the content was retrieved

		Note that adding ``model`` links to files identifying as models or ``machinecode`` links to files identifying
		as machine code will be refused.

		:param path: path of the file for which to add a link
		:param rel: type of relation of the link to add (currently ``model``, ``machinecode`` and ``web`` are supported)
		:param data: additional data of the link to add
		"""
		raise NotImplementedError()

	def remove_link(self, path, rel, data):
		"""
		Removes the link consisting of ``rel`` and ``data`` from file ``name`` on ``path``.

		:param path: path of the file from which to remove the link
		:param rel: type of relation of the link to remove (currently ``model``, ``machinecode`` and ``web`` are supported)
		:param data: additional data of the link to remove, must match existing link
		"""
		raise NotImplementedError()

	def set_additional_metadata(self, path, key, data, overwrite=False, merge=False):
		"""
		Adds additional metadata to the metadata of ``path``. Metadata in ``data`` will be saved under ``key``.

		If ``overwrite`` is set and ``key`` already exists in ``name``'s metadata, the current value will be overwritten.

		If ``merge`` is set and ``key`` already exists and both ``data`` and the existing data under ``key`` are dictionaries,
		the two dictionaries will be merged recursively.

		:param path: the virtual path to the file for which to add additional metadata
		:param key: key of metadata to add
		:param data: metadata to add
		:param overwrite: if True and ``key`` already exists, it will be overwritten
		:param merge: if True and ``key`` already exists and both ``data`` and the existing data are dictionaries, they
		              will be merged
		"""
		raise NotImplementedError()

	def remove_additional_metadata(self, path, key):
		"""
		Removes additional metadata under ``key`` for ``name`` on ``path``

		:param path: the virtual path to the file for which to remove the metadata under ``key``
		:param key: the key to remove
		"""
		raise NotImplementedError()

	def sanitize(self, path):
		"""
		Sanitizes the given ``path``, stripping it of all invalid characters. The ``path`` may consist of both
		folder and file name, the underlying implementation must separate those if necessary and sanitize individually.

		:param string path: the path to sanitize
		:return: a 2-tuple containing the sanitized path and file name
		"""
		raise NotImplementedError()

	def sanitize_path(self, path):
		"""
		Sanitizes the given folder-only ``path``, stripping it of all invalid characters.
		:param string path: the path to sanitize
		:return: the sanitized path
		"""
		raise NotImplementedError()

	def sanitize_name(self, name):
		"""
		Sanitizes the given file ``name``, stripping it of all invalid characters.
		:param string name: the file name to sanitize
		:return: the sanitized name
		"""
		raise NotImplementedError()

	def split_path(self, path):
		"""
		Split ``path`` into base directory and file name.
		:param path: the path to split
		:return: a tuple (base directory, file name)
		"""
		raise NotImplementedError()

	def join_path(self, *path):
		"""
		Join path elements together
		:param path: path elements to join
		:return: joined representation of the path to be usable as fully qualified path for further operations
		"""
		raise NotImplementedError()

	def path_on_disk(self, path):
		"""
		Retrieves the path on disk for ``path``.

		Note: if the storage is not on disk and there exists no path on disk to refer to it, this method should
		raise an :class:`io.UnsupportedOperation`

		Opposite of :func:`path_in_storage`.

		:param string path: the virtual path for which to retrieve the path on disk
		:return: the path on disk to ``path``
		"""
		raise NotImplementedError()

	def path_in_storage(self, path):
		"""
		Retrieves the equivalent in the storage adapter for ``path``.

		Opposite of :func:`path_on_disk`.

		:param string path: the path for which to retrieve the storage path
		:return: the path in storage to ``path``
		"""
		raise NotImplementedError()



class LocalFileStorage(StorageInterface):
	"""
	The ``LocalFileStorage`` is a storage implementation which holds all files, folders and metadata on disk.

	Metadata is managed inside ``.metadata.yaml`` files in the respective folders, indexed by the sanitized filenames
	stored within the folder. Metadata access is managed through an LRU cache to minimize access overhead.

	This storage type implements :func:`path_on_disk`.
	"""

	def __init__(self, basefolder, create=False):
		"""
		Initializes a ``LocalFileStorage`` instance under the given ``basefolder``, creating the necessary folder
		if necessary and ``create`` is set to ``True``.

		:param string basefolder: the path to the folder under which to create the storage
		:param bool create:       ``True`` if the folder should be created if it doesn't exist yet, ``False`` otherwise
		"""
		self._logger = logging.getLogger(__name__)

		self.basefolder = os.path.realpath(os.path.abspath(basefolder))
		if not os.path.exists(self.basefolder) and create:
			os.makedirs(self.basefolder)
		if not os.path.exists(self.basefolder) or not os.path.isdir(self.basefolder):
			raise RuntimeError("{basefolder} is not a valid directory".format(**locals()))

		import threading
		self._metadata_lock = threading.Lock()

		self._metadata_cache = pylru.lrucache(10)

		from slugify import Slugify
		self._slugify = Slugify()
		self._slugify.safe_chars = "-_.()[] "

		self._old_metadata = None
		self._initialize_metadata()

	def _initialize_metadata(self):
		self._logger.info("Initializing the file metadata for {}...".format(self.basefolder))

		old_metadata_path = os.path.join(self.basefolder, "metadata.yaml")
		backup_path = os.path.join(self.basefolder, "metadata.yaml.backup")

		if os.path.exists(old_metadata_path):
			# load the old metadata file
			try:
				with open(old_metadata_path) as f:
					import yaml
					self._old_metadata = yaml.safe_load(f)
			except:
				self._logger.exception("Error while loading old metadata file")

			# make sure the metadata is initialized as far as possible
			self._list_folder(self.basefolder)

			# rename the old metadata file
			self._old_metadata = None
			try:
				import shutil
				shutil.move(old_metadata_path, backup_path)
			except:
				self._logger.exception("Could not rename old metadata.yaml file")

		else:
			# make sure the metadata is initialized as far as possible
			self._list_folder(self.basefolder)

		self._logger.info("... file metadata for {} initialized successfully.".format(self.basefolder))

	@property
	def analysis_backlog(self):
		for entry in self._analysis_backlog_generator():
			yield entry

	def _analysis_backlog_generator(self, path=None):
		if path is None:
			path = self.basefolder

		metadata = self._get_metadata(path)
		if not metadata:
			metadata = dict()
		for entry in os.listdir(path):
			if is_hidden_path(entry) or not octoprint.filemanager.valid_file_type(entry):
				continue

			absolute_path = os.path.join(path, entry)
			if os.path.isfile(absolute_path):
				if not entry in metadata or not isinstance(metadata[entry], dict) or not "analysis" in metadata[entry]:
					printer_profile_rels = self.get_link(absolute_path, "printerprofile")
					if printer_profile_rels:
						printer_profile_id = printer_profile_rels[0]["id"]
					else:
						printer_profile_id = None

					yield entry, absolute_path, printer_profile_id
			elif os.path.isdir(absolute_path):
				for sub_entry in self._analysis_backlog_generator(absolute_path):
					yield self.join_path(entry, sub_entry[0]), sub_entry[1], sub_entry[2]

	def file_exists(self, path):
		path, name = self.sanitize(path)
		file_path = os.path.join(path, name)
		return os.path.exists(file_path) and os.path.isfile(file_path)

	def list_files(self, path=None, filter=None, recursive=True):
		if path:
			path = self.sanitize_path(path)
		else:
			path = self.basefolder
		return self._list_folder(path, entry_filter=filter, recursive=recursive)

	def add_folder(self, path, ignore_existing=True):
		path, name = self.sanitize(path)

		folder_path = os.path.join(path, name)
		if os.path.exists(folder_path):
			if not ignore_existing:
				raise RuntimeError("{name} does already exist in {path}".format(**locals()))
		else:
			os.mkdir(folder_path)

		return self.path_in_storage((path, name))

	def remove_folder(self, path, recursive=True):
		path, name = self.sanitize(path)

		folder_path = os.path.join(path, name)
		if not os.path.exists(folder_path):
			return

		contents = os.listdir(folder_path)
		if ".metadata.yaml" in contents:
			contents.remove(".metadata.yaml")
		if contents and not recursive:
			raise RuntimeError("{name} in {path} is not empty".format(**locals()))

		import shutil
		shutil.rmtree(folder_path)

	def add_file(self, path, file_object, printer_profile=None, links=None, allow_overwrite=False):
		path, name = self.sanitize(path)
		if not octoprint.filemanager.valid_file_type(name):
			raise RuntimeError("{name} is an unrecognized file type".format(**locals()))

		metadata = self._get_metadata(path)
		if not metadata:
			metadata = dict()

		file_path = os.path.join(path, name)
		if os.path.exists(file_path) and not os.path.isfile(file_path):
			raise RuntimeError("{name} does already exist in {path} and is not a file".format(**locals()))
		if os.path.exists(file_path) and not allow_overwrite:
			raise RuntimeError("{name} does already exist in {path} and overwriting is prohibited".format(**locals()))

		# make sure folders exist
		if not os.path.exists(path):
			os.makedirs(path)

		# save the file
		file_object.save(file_path)

		# save the file's hash to the metadata of the folder
		file_hash = self._create_hash(file_path)
		if not name in metadata or not "hash" in metadata[name] or metadata[name]["hash"] != file_hash:
			# make sure to create a new metadata entry if we've never seen that file with that content before
			file_metadata = dict(
				hash=file_hash
			)
			metadata[name] = file_metadata
			self._save_metadata(path, metadata)

		# process any links that were also provided for adding to the file
		if not links:
			links = []

		if printer_profile is not None:
			links.append(("printerprofile", dict(id=printer_profile["id"], name=printer_profile["name"])))

		self._add_links(name, path, links)

		# touch the file to set last access and modification time to now
		os.utime(file_path, None)

		return self.path_in_storage((path, name))

	def remove_file(self, path):
		path, name = self.sanitize(path)

		metadata = self._get_metadata(path)

		file_path = os.path.join(path, name)
		if not os.path.exists(file_path):
			return
		if not os.path.isfile(file_path):
			raise RuntimeError("{name} in {path} is not a file".format(**locals()))

		try:
			os.remove(file_path)
		except Exception as e:
			raise RuntimeError("Could not delete {name} in {path}".format(**locals()), e)

		if name in metadata:
			if "hash" in metadata[name]:
				hash = metadata[name]["hash"]
				for m in metadata.values():
					if not "links" in m:
						continue
					for link in m["links"]:
						if "rel" in link and "hash" in link and (link["rel"] == "model" or link["rel"] == "machinecode") and link["hash"] == hash:
							m["links"].remove(link)
			del metadata[name]
			self._save_metadata(path, metadata)

	def get_metadata(self, path):
		path, name = self.sanitize(path)

		metadata = self._get_metadata(path)
		if name in metadata:
			return metadata[name]
		else:
			return None

	def get_link(self, path, rel):
		path, name = self.sanitize(path)
		return self._get_links(name, path, rel)


	def add_link(self, path, rel, data):
		path, name = self.sanitize(path)
		self._add_links(name, path, [(rel, data)])

	def remove_link(self, path, rel, data):
		path, name = self.sanitize(path)
		self._remove_links(name, path, [(rel, data)])

	def add_history(self, path, data):
		path, name = self.sanitize(path)
		self._add_history(name, path, data)

	def update_history(self, path, index, data):
		path, name = self.sanitize(path)
		self._update_history(name, path, index, data)

	def remove_history(self, path, index):
		path, name = self.sanitize(path)
		self._update_history(name, path, index)

	def set_additional_metadata(self, path, key, data, overwrite=False, merge=False):
		path, name = self.sanitize(path)
		metadata = self._get_metadata(path)
		metadata_dirty = False

		if not name in metadata:
			return

		if not key in metadata[name] or overwrite:
			metadata[name][key] = data
			metadata_dirty = True
		elif key in metadata[name] and isinstance(metadata[name][key], dict) and isinstance(data, dict) and merge:
			current_data = metadata[name][key]

			import octoprint.util
			new_data = octoprint.util.dict_merge(current_data, data)
			metadata[name][key] = new_data
			metadata_dirty = True
		elif key in metadata[name] and overwrite:
			metadata[name][key] = data
			metadata_dirty = True

		if metadata_dirty:
			self._save_metadata(path, metadata)

	def remove_additional_metadata(self, path, key):
		path, name = self.sanitize(path)
		metadata = self._get_metadata(path)

		if not name in metadata:
			return

		if not key in metadata[name]:
			return

		del metadata[name][key]
		self._save_metadata(path, metadata)

	def split_path(self, path):
		split = path.split("/")
		if len(split) == 1:
			return "", split[0]
		else:
			return self.join_path(*split[:-1]), split[-1]

	def join_path(self, *path):
		return "/".join(path)

	def sanitize(self, path):
		"""
		Returns a ``(path, name)`` tuple derived from the provided ``path``.

		``path`` may be:
		  * a storage path
		  * an absolute file system path
		  * a tuple or list containing all individual path elements
		  * a string representation of the path
		  * with or without a file name

		Note that for a ``path`` without a trailing slash the last part will be considered a file name and
		hence be returned at second position. If you only need to convert a folder path, be sure to
		include a trailing slash for a string ``path`` or an empty last element for a list ``path``.
		"""
		name = None
		if isinstance(path, (str, unicode, basestring)):
			if path.startswith(self.basefolder):
				path = path[len(self.basefolder):]
			path = path.replace(os.path.sep, "/")
			path = path.split("/")
		if isinstance(path, (list, tuple)):
			if len(path) == 1:
				name = path[0]
				path = "/"
			else:
				name = path[-1]
				path = "/" + self.join_path(*path[:-1])
		if not path:
			path = "/"

		name = self.sanitize_name(name)
		path = self.sanitize_path(path)
		return path, name

	def sanitize_name(self, name):
		"""
		Raises a :class:`ValueError` for a ``name`` containing ``/`` or ``\``. Otherwise
		slugifies the given ``name`` by converting it to ASCII, leaving ``-``, ``_``, ``.``,
		``(``, and ``)`` as is.
		"""
		if name is None:
			return None

		if "/" in name or "\\" in name:
			raise ValueError("name must not contain / or \\")

		result = self._slugify(name).replace(" ", "_")
		if result and result != "." and result != ".." and result[0] == ".":
			# hidden files under *nix
			result = result[1:]
		return result

	def sanitize_path(self, path):
		"""
		Ensures that the on disk representation of ``path`` is located under the configured basefolder. Resolves all
		relative path elements (e.g. ``..``) and sanitizes folder names using :func:`sanitize_name`. Final path is the
		absolute path including leading ``basefolder`` path.
		"""
		if path[0] == "/":
			path = path[1:]
		elif path[0] == "." and path[1] == "/":
			path = path[2:]

		path_elements = path.split("/")
		joined_path = self.basefolder
		for path_element in path_elements:
			joined_path = os.path.join(joined_path, self.sanitize_name(path_element))
		path = os.path.realpath(joined_path)
		if not path.startswith(self.basefolder):
			raise ValueError("path not contained in base folder: {path}".format(**locals()))
		return path

	def _sanitize_entry(self, entry, path, entry_path):
		sanitized = self.sanitize_name(entry)
		if sanitized != entry:
			# entry is not sanitized yet, let's take care of that
			sanitized_path = os.path.join(path, sanitized)
			sanitized_name, sanitized_ext = os.path.splitext(sanitized)

			counter = 1
			while os.path.exists(sanitized_path):
				counter += 1
				sanitized = self.sanitize_name("{}_({}){}".format(sanitized_name, counter, sanitized_ext))
				sanitized_path = os.path.join(path, sanitized)

			try:
				shutil.move(entry_path, sanitized_path)

				self._logger.info("Sanitized \"{}\" to \"{}\"".format(entry_path, sanitized_path))
				return sanitized, sanitized_path
			except:
				self._logger.exception("Error while trying to rename \"{}\" to \"{}\", ignoring file".format(entry_path, sanitized_path))
				raise

		return entry, entry_path

	def path_in_storage(self, path):
		if isinstance(path, (tuple, list)):
			path = self.join_path(*path)
		if isinstance(path, (str, unicode, basestring)):
			if path.startswith(self.basefolder):
				path = path[len(self.basefolder):]
			path = path.replace(os.path.sep, "/")
		if path.startswith("/"):
			path = path[1:]

		return path

	def path_on_disk(self, path):
		path, name = self.sanitize(path)
		return os.path.join(path, name)

	##~~ internals

	def _add_history(self, name, path, data):
		metadata = self._get_metadata(path)

		if not name in metadata:
			metadata[name] = dict()

		if not "hash" in metadata[name]:
			metadata[name]["hash"] = self._create_hash(os.path.join(path, name))

		if not "history" in metadata[name]:
			metadata[name]["history"] = []

		metadata[name]["history"].append(data)
		self._calculate_stats_from_history(name, path, metadata=metadata, save=False)
		self._save_metadata(path, metadata)

	def _update_history(self, name, path, index, data):
		metadata = self._get_metadata(path)

		if not name in metadata or not "history" in metadata[name]:
			return

		try:
			metadata[name]["history"][index].update(data)
			self._calculate_stats_from_history(name, path, metadata=metadata, save=False)
			self._save_metadata(path, metadata)
		except IndexError:
			pass

	def _delete_history(self, name, path, index):
		metadata = self._get_metadata(path)

		if not name in metadata or not "history" in metadata[name]:
			return

		try:
			del metadata[name]["history"][index]
			self._calculate_stats_from_history(name, path, metadata=metadata, save=False)
			self._save_metadata(path, metadata)
		except IndexError:
			pass

	def _calculate_stats_from_history(self, name, path, metadata=None, save=True):
		if metadata is None:
			metadata = self._get_metadata(path)

		if not name in metadata or not "history" in metadata[name]:
			return

		# collect data from history
		former_print_times = dict()
		last_print = dict()


		for history_entry in metadata[name]["history"]:
			if not "printTime" in history_entry or not "success" in history_entry or not history_entry["success"] or not "printerProfile" in history_entry:
				continue

			printer_profile = history_entry["printerProfile"]
			print_time = history_entry["printTime"]

			if not printer_profile in former_print_times:
				former_print_times[printer_profile] = []
			former_print_times[printer_profile].append(print_time)

			if not printer_profile in last_print or last_print[printer_profile] is None or ("timestamp" in history_entry and history_entry["timestamp"] > last_print[printer_profile]["timestamp"]):
				last_print[printer_profile] = history_entry

		# calculate stats
		statistics = dict(averagePrintTime=dict(), lastPrintTime=dict())

		for printer_profile in former_print_times:
			if not former_print_times[printer_profile]:
				continue
			statistics["averagePrintTime"][printer_profile] = sum(former_print_times[printer_profile]) / float(len(former_print_times[printer_profile]))

		for printer_profile in last_print:
			if not last_print[printer_profile]:
				continue
			statistics["lastPrintTime"][printer_profile] = last_print[printer_profile]["printTime"]

		metadata[name]["statistics"] = statistics

		if save:
			self._save_metadata(path, metadata)

	def _get_links(self, name, path, searched_rel):
		metadata = self._get_metadata(path)
		result = []

		if not name in metadata:
			return result

		if not "links" in metadata[name]:
			return result

		for data in metadata[name]["links"]:
			if not "rel" in data or not data["rel"] == searched_rel:
				continue
			result.append(data)
		return result

	def _add_links(self, name, path, links):
		file_type = octoprint.filemanager.get_file_type(name)
		if file_type:
			file_type = file_type[0]

		metadata = self._get_metadata(path)
		metadata_dirty = False

		if not name in metadata:
			metadata[name] = dict()

		if not "hash" in metadata[name]:
			metadata[name]["hash"] = self._create_hash(os.path.join(path, name))

		if not "links" in metadata[name]:
			metadata[name]["links"] = []

		for rel, data in links:
			if (rel == "model" or rel == "machinecode") and "name" in data:
				if file_type == "model" and rel == "model":
					# adding a model link to a model doesn't make sense
					return
				elif file_type == "machinecode" and rel == "machinecode":
					# adding a machinecode link to a machinecode doesn't make sense
					return

				ref_path = os.path.join(path, data["name"])
				if not os.path.exists(ref_path):
					# file doesn't exist, we won't create the link
					continue

				# fetch hash of target file
				if data["name"] in metadata and "hash" in metadata[data["name"]]:
					hash = metadata[data["name"]]["hash"]
				else:
					hash = self._create_hash(ref_path)
					if not data["name"] in metadata:
						metadata[data["name"]] = dict(
							hash=hash,
							links=[]
						)
					else:
						metadata[data["name"]]["hash"] = hash

				if "hash" in data and not data["hash"] == hash:
					# file doesn't have the correct hash, we won't create the link
					continue

				if not "links" in metadata[data["name"]]:
					metadata[data["name"]]["links"] = []

				# add reverse link to link target file
				metadata[data["name"]]["links"].append(
					dict(rel="machinecode" if rel == "model" else "model", name=name, hash=metadata[name]["hash"])
				)
				metadata_dirty = True

				link_dict = dict(
					rel=rel,
					name=data["name"],
					hash=hash
				)

			elif rel == "web" and "href" in data:
				link_dict = dict(
					rel=rel,
					href=data["href"]
				)
				if "retrieved" in data:
					link_dict["retrieved"] = data["retrieved"]

			else:
				continue

			if link_dict:
				metadata[name]["links"].append(link_dict)
				metadata_dirty = True

		if metadata_dirty:
			self._save_metadata(path, metadata)

	def _remove_links(self, name, path, links):
		metadata = self._get_metadata(path)
		metadata_dirty = False

		if not name in metadata or not "hash" in metadata[name]:
			hash = self._create_hash(os.path.join(path, name))
		else:
			hash = metadata[name]["hash"]

		for rel, data in links:
			if (rel == "model" or rel == "machinecode") and "name" in data:
				if data["name"] in metadata and "links" in metadata[data["name"]]:
					ref_rel = "model" if rel == "machinecode" else "machinecode"
					for link in metadata[data["name"]]["links"]:
						if link["rel"] == ref_rel and "name" in link and link["name"] == name and "hash" in link and link["hash"] == hash:
							metadata[data["name"]]["links"].remove(link)
							metadata_dirty = True

			if "links" in metadata[name]:
				for link in metadata[name]["links"]:
					if not link["rel"] == rel:
						continue

					matches = True
					for k, v in data.items():
						if not k in link or not link[k] == v:
							matches = False
							break

					if not matches:
						continue

					metadata[name]["links"].remove(link)
					metadata_dirty = True

		if metadata_dirty:
			self._save_metadata(path, metadata)

	def _list_folder(self, path, entry_filter=None, recursive=True, **kwargs):
		if entry_filter is None:
			entry_filter = kwargs.get("filter", None)

		metadata = self._get_metadata(path)
		if not metadata:
			metadata = dict()
		metadata_dirty = False

		result = dict()
		for entry in os.listdir(path):
			if is_hidden_path(entry):
				# no hidden files and folders
				continue

			entry_path = os.path.join(path, entry)

			try:
				entry, entry_path = self._sanitize_entry(entry, path, entry_path)
			except:
				# error while trying to rename the file, we'll continue here and ignore it
				continue

			# file handling
			if os.path.isfile(entry_path):
				file_type = octoprint.filemanager.get_file_type(entry)
				if not file_type:
					# only supported extensions
					continue
				else:
					file_type = file_type[0]

				if entry in metadata and isinstance(metadata[entry], dict):
					entry_data = metadata[entry]
				else:
					entry_data = self._add_basic_metadata(path, entry, save=False, metadata=metadata)
					metadata_dirty = True

				# TODO extract model hash from source if possible to recreate link

				if not entry_filter or entry_filter(entry, entry_data):
					# only add files passing the optional filter
					extended_entry_data = dict()
					extended_entry_data.update(entry_data)
					extended_entry_data["name"] = entry
					extended_entry_data["type"] = file_type
					stat = os.stat(entry_path)
					if stat:
						extended_entry_data["size"] = stat.st_size
						extended_entry_data["date"] = int(stat.st_mtime)

					result[entry] = extended_entry_data

			# folder recursion
			elif os.path.isdir(entry_path) and recursive:
				sub_result = self._list_folder(entry_path, entry_filter=entry_filter)
				result[entry] = dict(
					name=entry,
					type="folder",
					children=sub_result
				)

		# TODO recreate links if we have metadata less entries

		# save metadata
		if metadata_dirty:
			self._save_metadata(path, metadata)

		return result

	def _add_basic_metadata(self, path, entry, additional_metadata=None, save=True, metadata=None):
		if additional_metadata is None:
			additional_metadata = dict()

		if metadata is None:
			metadata = self._get_metadata(path)

		entry_data = dict(
			hash=self._create_hash(os.path.join(path, entry)),
			links=[],
			notes=[]
		)

		if path == self.basefolder and self._old_metadata is not None and entry in self._old_metadata and "gcodeAnalysis" in self._old_metadata[entry]:
			# if there is still old metadata available and that contains an analysis for this file, use it!
			entry_data["analysis"] = self._old_metadata[entry]["gcodeAnalysis"]

		entry_data.update(additional_metadata)
		metadata[entry] = entry_data

		if save:
			self._save_metadata(path, metadata)

		return entry_data

	def _create_hash(self, path):
		import hashlib

		blocksize = 65536
		hash = hashlib.sha1()
		with open(path, "rb") as f:
			buffer = f.read(blocksize)
			while len(buffer) > 0:
				hash.update(buffer)
				buffer = f.read(blocksize)

		return hash.hexdigest()

	def _get_metadata(self, path):
		if path in self._metadata_cache:
			return self._metadata_cache[path]

		metadata_path = os.path.join(path, ".metadata.yaml")
		if os.path.exists(metadata_path):
			with self._metadata_lock:
				with open(metadata_path) as f:
					try:
						import yaml
						metadata = yaml.safe_load(f)
					except:
						self._logger.exception("Error while reading .metadata.yaml from {path}".format(**locals()))
					else:
						self._metadata_cache[path] = metadata
						return metadata
		return dict()

	def _save_metadata(self, path, metadata):
		metadata_path = os.path.join(path, ".metadata.yaml")

		with self._metadata_lock:
			try:
				import yaml
				import shutil

				file_obj = tempfile.NamedTemporaryFile(delete=False)
				try:
					yaml.safe_dump(metadata, stream=file_obj, default_flow_style=False, indent="  ", allow_unicode=True)
					file_obj.close()
					shutil.move(file_obj.name, metadata_path)
				finally:
					try:
						if os.path.exists(file_obj.name):
							os.remove(file_obj.name)
					except Exception as e:
						self._logger.warn("Could not delete file {}: {}".format(file_obj.name, str(e)))
			except:
				self._logger.exception("Error while writing .metadata.yaml to {path}".format(**locals()))
			else:
				self._metadata_cache[path] = metadata
