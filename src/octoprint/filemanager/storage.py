__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import copy
import logging
import os
import shutil
from contextlib import contextmanager
from os import scandir, walk

import pylru

import octoprint.filemanager
from octoprint.util import (
    atomic_write,
    is_hidden_path,
    time_this,
    to_bytes,
    to_unicode,
    yaml,
)
from octoprint.util.files import sanitize_filename


class StorageInterface:
    """
    Interface of storage adapters for OctoPrint.
    """

    # noinspection PyUnreachableCode
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

    # noinspection PyUnreachableCode
    def analysis_backlog_for_path(self, path=None):
        # empty generator pattern, yield is intentionally unreachable
        return
        yield

    def last_modified(self, path=None, recursive=False):
        """
        Get the last modification date of the specified ``path`` or ``path``'s subtree.

        Args:
            path (str or None): Path for which to determine the subtree's last modification date. If left out or
                set to None, defatuls to storage root.
            recursive (bool): Whether to determine only the date of the specified ``path`` (False, default) or
                the whole ``path``'s subtree (True).

        Returns: (float) The last modification date of the indicated subtree
        """
        raise NotImplementedError()

    def get_size(self, path=None, recursive=False) -> int:
        """
        Get the size of the specified ``path`` or ``path``'s subtree.

        Args:
            path (str or None): Path for which to determine the subtree's size. If left out or
                set to None, defaults to storage root.
            recursive (bool): Whether to determine only the size of the specified ``path`` (False, default) or
                the whole ``path``'s subtree (True).
        """
        raise NotImplementedError()

    def get_lastmodified(self, path: str = None, recursive: bool = False) -> int:
        """
        Get the modification date of the specified ``path`` or ``path``'s subtree.

        Args:
            path (str or None): Path for which to determine the modification date. If left our or
                set to None, defaults to storage root.
            recursive (bool): Whether to determine only the date of the specified ``path`` (False, default) or
                the whole ``path``'s subtree (True).
        """
        raise NotImplementedError()

    def file_in_path(self, path, filepath):
        """
        Returns whether the file indicated by ``file`` is inside ``path`` or not.
        :param string path: the path to check
        :param string filepath: path to the file
        :return: ``True`` if the file is inside the path, ``False`` otherwise
        """
        return NotImplementedError()

    def file_exists(self, path):
        """
        Returns whether the file indicated by ``path`` exists or not.
        :param string path: the path to check for existence
        :return: ``True`` if the file exists, ``False`` otherwise
        """
        raise NotImplementedError()

    def folder_exists(self, path):
        """
        Returns whether the folder indicated by ``path`` exists or not.
        :param string path: the path to check for existence
        :return: ``True`` if the folder exists, ``False`` otherwise
        """
        raise NotImplementedError()

    def list_files(
        self, path=None, filter=None, recursive=True, level=0, force_refresh=False
    ):
        """
        List all files in storage starting at ``path``. If ``recursive`` is set to True (the default), also dives into
        subfolders.

        An optional filter function can be supplied which will be called with a file name and file data and which has
        to return True if the file is to be included in the result or False if not.

        The data structure of the returned result will be a dictionary mapping from file names to entry data. File nodes
        will contain their metadata here, folder nodes will contain their contained files and folders. Example::

           {
             "some_folder": {
               "name": "some_folder",
               "path": "some_folder",
               "type": "folder",
               "children": {
                 "some_sub_folder": {
                   "name": "some_sub_folder",
                   "path": "some_folder/some_sub_folder",
                   "type": "folder",
                   "typePath": ["folder"],
                   "children": { ... }
                 },
                 "some_file.gcode": {
                   "name": "some_file.gcode",
                   "path": "some_folder/some_file.gcode",
                   "type": "machinecode",
                   "typePath": ["machinecode", "gcode"],
                   "hash": "<sha1 hash>",
                   "links": [ ... ],
                   ...
                 },
                 ...
               }
             "test.gcode": {
               "name": "test.gcode",
               "path": "test.gcode",
               "type": "machinecode",
               "typePath": ["machinecode", "gcode"],
               "hash": "<sha1 hash>",
               "links": [...],
               ...
             },
             "test.stl": {
               "name": "test.stl",
               "path": "test.stl",
               "type": "model",
               "typePath": ["model", "stl"],
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
        :param bool recursive:  will also step into sub folders for building the complete list if set to True, otherwise will only
                                do one step down into sub folders to be able to populate the ``children``.
        :return: a dictionary mapping entry names to entry data that represents the whole file list
        """
        raise NotImplementedError()

    def add_folder(self, path, ignore_existing=True, display=None):
        """
        Adds a folder as ``path``

        The ``path`` will be sanitized.

        :param string path:          the path of the new folder
        :param bool ignore_existing: if set to True, no error will be raised if the folder to be added already exists
        :param str display:          display name of the folder
        :return: the sanitized name of the new folder to be used for future references to the folder
        """
        raise NotImplementedError()

    def remove_folder(self, path, recursive=True):
        """
        Removes the folder at ``path``

        :param string path:    the path of the folder to remove
        :param bool recursive: if set to True, contained folders and files will also be removed, otherwise an error will
                               be raised if the folder is not empty (apart from any metadata files) when it's to be removed
        """
        raise NotImplementedError()

    def copy_folder(self, source, destination):
        """
        Copies the folder ``source`` to ``destination``

        :param string source: path to the source folder
        :param string destination: path to destination

        :return: the path in the storage to the copy of the folder
        """
        raise NotImplementedError()

    def move_folder(self, source, destination):
        """
        Moves the folder ``source`` to ``destination``

        :param string source: path to the source folder
        :param string destination: path to destination

        :return: the new path in the storage to the folder
        """
        raise NotImplementedError()

    def add_file(
        self,
        path,
        file_object,
        printer_profile=None,
        links=None,
        allow_overwrite=False,
        display=None,
    ):
        """
        Adds the file ``file_object`` as ``path``

        :param string path:            the file's new path, will be sanitized
        :param object file_object:     a file object that provides a ``save`` method which will be called with the destination path
                                       where the object should then store its contents
        :param object printer_profile: the printer profile associated with this file (if any)
        :param list links:             any links to add with the file
        :param bool allow_overwrite:   if set to True no error will be raised if the file already exists and the existing file
                                       and its metadata will just be silently overwritten
        :param str display:            display name of the file
        :return: the sanitized name of the file to be used for future references to it
        """
        raise NotImplementedError()

    def remove_file(self, path):
        """
        Removes the file at ``path``

        Will also take care of deleting the corresponding entries
        in the metadata and deleting all links pointing to the file.

        :param string path: path of the file to remove
        """
        raise NotImplementedError()

    def copy_file(self, source, destination):
        """
        Copies the file ``source`` to ``destination``

        :param string source: path to the source file
        :param string destination: path to destination

        :return: the path in the storage to the copy of the file
        """
        raise NotImplementedError()

    def move_file(self, source, destination):
        """
        Moves the file ``source`` to ``destination``

        :param string source: path to the source file
        :param string destination: path to destination

        :return: the new path in the storage to the file
        """
        raise NotImplementedError()

    def has_analysis(self, path):
        """
        Returns whether the file at path has been analysed yet

        :param path: virtual path to the file for which to retrieve the metadata
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
            referring to ``name`` and its hash will also be added to the linked ``model`` file
          * ``machinecode``: adds a link to a file containing machine code created from the current file (model), expected
            additional data is the ``name`` and optionally the ``hash`` of the file to link to. If the link can be resolved
            against another file on the current ``path``, not only will it be added to the links of ``name`` but a reverse
            link of type ``model`` referring to ``name`` and its hash will also be added to the linked ``model`` file.
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

    def get_additional_metadata(self, path, key):
        """
        Fetches additional metadata at ``key`` from the metadata of ``path``.

        :param path: the virtual path to the file for which to fetch additional metadata
        :param key: key of metadata to fetch
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

    def canonicalize(self, path):
        """
        Canonicalizes the given ``path``. The ``path`` may consist of both folder and file name, the underlying
        implementation must separate those if necessary.

        By default, this calls :func:`~octoprint.filemanager.StorageInterface.sanitize`, which also takes care
        of stripping any invalid characters.

        Args:
                path: the path to canonicalize

        Returns:
                a 2-tuple containing the canonicalized path and file name

        """
        return self.sanitize(path)

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


class StorageError(Exception):
    UNKNOWN = "unknown"
    INVALID_DIRECTORY = "invalid_directory"
    INVALID_FILE = "invalid_file"
    INVALID_SOURCE = "invalid_source"
    INVALID_DESTINATION = "invalid_destination"
    DOES_NOT_EXIST = "does_not_exist"
    ALREADY_EXISTS = "already_exists"
    SOURCE_EQUALS_DESTINATION = "source_equals_destination"
    NOT_EMPTY = "not_empty"

    def __init__(self, message, code=None, cause=None):
        Exception.__init__(self, message)
        self.cause = cause

        if code is None:
            code = StorageError.UNKNOWN
        self.code = code


class LocalFileStorage(StorageInterface):
    """
    The ``LocalFileStorage`` is a storage implementation which holds all files, folders and metadata on disk.

    Metadata is managed inside ``.metadata.json`` files in the respective folders, indexed by the sanitized filenames
    stored within the folder. Metadata access is managed through an LRU cache to minimize access overhead.

    This storage type implements :func:`path_on_disk`.
    """

    def __init__(self, basefolder, create=False, really_universal=False):
        """
        Initializes a ``LocalFileStorage`` instance under the given ``basefolder``, creating the necessary folder
        if necessary and ``create`` is set to ``True``.

        :param string basefolder:     the path to the folder under which to create the storage
        :param bool create:           ``True`` if the folder should be created if it doesn't exist yet, ``False`` otherwise
        :param bool really_universal: ``True`` if the file names should be forced to really universal, ``False`` otherwise
        """
        self._logger = logging.getLogger(__name__)

        self.basefolder = os.path.realpath(os.path.abspath(to_unicode(basefolder)))
        if not os.path.exists(self.basefolder) and create:
            os.makedirs(self.basefolder)
        if not os.path.exists(self.basefolder) or not os.path.isdir(self.basefolder):
            raise StorageError(
                f"{basefolder} is not a valid directory",
                code=StorageError.INVALID_DIRECTORY,
            )

        self._really_universal = really_universal

        import threading

        self._metadata_lock_mutex = threading.RLock()
        self._metadata_locks = {}
        self._persisted_metadata_lock_mutex = threading.RLock()
        self._persisted_metadata_locks = {}

        self._metadata_cache = pylru.lrucache(100)
        self._filelist_cache = {}
        self._filelist_cache_mutex = threading.RLock()

        self._old_metadata = None
        self._initialize_metadata()

    def _initialize_metadata(self):
        self._logger.info(f"Initializing the file metadata for {self.basefolder}...")

        old_metadata_path = os.path.join(self.basefolder, "metadata.yaml")
        backup_path = os.path.join(self.basefolder, "metadata.yaml.backup")

        if os.path.exists(old_metadata_path):
            # load the old metadata file
            try:
                self._old_metadata = yaml.load_from_file(path=old_metadata_path)
            except Exception:
                self._logger.exception("Error while loading old metadata file")

            # make sure the metadata is initialized as far as possible
            self._list_folder(self.basefolder)

            # rename the old metadata file
            self._old_metadata = None
            try:
                import shutil

                shutil.move(old_metadata_path, backup_path)
            except Exception:
                self._logger.exception("Could not rename old metadata.yaml file")

        else:
            # make sure the metadata is initialized as far as possible, but don't cache (#5049)
            self._list_folder(self.basefolder, fill_cache=False)

        self._logger.info(
            f"... file metadata for {self.basefolder} initialized successfully."
        )

    @property
    def analysis_backlog(self):
        return self.analysis_backlog_for_path()

    def analysis_backlog_for_path(self, path=None):
        if path:
            path = self.sanitize_path(path)

        yield from self._analysis_backlog_generator(path)

    def _analysis_backlog_generator(self, path=None):
        if path is None:
            path = self.basefolder

        metadata = self._get_metadata(path)
        if not metadata:
            metadata = {}
        for entry in scandir(path):
            if is_hidden_path(entry.name):
                continue

            if entry.is_file() and octoprint.filemanager.valid_file_type(entry.name):
                if (
                    entry.name not in metadata
                    or not isinstance(metadata[entry.name], dict)
                    or "analysis" not in metadata[entry.name]
                ):
                    printer_profile_rels = self.get_link(entry.path, "printerprofile")
                    if printer_profile_rels:
                        printer_profile_id = printer_profile_rels[0]["id"]
                    else:
                        printer_profile_id = None

                    yield entry.name, entry.path, printer_profile_id
            elif os.path.isdir(entry.path):
                for sub_entry in self._analysis_backlog_generator(entry.path):
                    yield (
                        self.join_path(entry.name, sub_entry[0]),
                        sub_entry[1],
                        sub_entry[2],
                    )

    def last_modified(self, path=None, recursive=False):
        if path is None:
            path = self.basefolder
        else:
            path = os.path.join(self.basefolder, path)

        def last_modified_for_path(p):
            metadata = os.path.join(p, ".metadata.json")
            if os.path.exists(metadata):
                return max(os.stat(p).st_mtime, os.stat(metadata).st_mtime)
            else:
                return os.stat(p).st_mtime

        if recursive:
            return max(last_modified_for_path(root) for root, _, _ in walk(path))
        else:
            return last_modified_for_path(path)

    def get_size(self, path=None, recursive=False):
        if path is None:
            path = self.basefolder

        path, name = self.sanitize(path)
        path = os.path.join(path, name)

        # shortcut for individual files
        if os.path.isfile(path):
            return os.stat(path).st_size

        size = 0
        for entry in os.scandir(path):
            if entry.is_file():
                size += entry.stat().st_size
            elif recursive and entry.is_dir():
                size += self.get_size(entry.path, recursive=recursive)

        return size

    def get_lastmodified(self, path: str = None, recursive: bool = False) -> int:
        if path is None:
            path = self.basefolder

        path, name = self.sanitize(path)
        path = os.path.join(path, name)

        # shortcut for individual files
        if os.path.isfile(path):
            return int(os.stat(path).st_mtime)

        last_modified = 0
        for entry in os.scandir(path):
            if entry.is_file():
                last_modified = max(last_modified, entry.stat().st_mtime)
            elif recursive and entry.is_dir():
                last_modified = max(
                    last_modified,
                    self.get_lastmodified(entry.path, recursive=recursive),
                )

        return int(last_modified)

    def file_in_path(self, path, filepath):
        filepath = self.sanitize_path(filepath)
        path = self.sanitize_path(path)

        return filepath == path or filepath.startswith(path + os.sep)

    def file_exists(self, path):
        path, name = self.sanitize(path)
        file_path = os.path.join(path, name)
        return os.path.exists(file_path) and os.path.isfile(file_path)

    def folder_exists(self, path):
        path, name = self.sanitize(path)
        folder_path = os.path.join(path, name)
        return os.path.exists(folder_path) and os.path.isdir(folder_path)

    def list_files(
        self, path=None, filter=None, recursive=True, level=0, force_refresh=False
    ):
        if path:
            path = self.sanitize_path(to_unicode(path))
            base = self.path_in_storage(path)
            if base:
                base += "/"
        else:
            path = self.basefolder
            base = ""

        def strip_children(nodes):
            result = {}
            for key, node in nodes.items():
                if node["type"] == "folder":
                    node = copy.copy(node)
                    node["children"] = {}
                result[key] = node
            return result

        def strip_grandchildren(nodes):
            result = {}
            for key, node in nodes.items():
                if node["type"] == "folder":
                    node = copy.copy(node)
                    node["children"] = strip_children(node["children"])
                result[key] = node
            return result

        def apply_filter(nodes, filter_func):
            result = {}
            for key, node in nodes.items():
                if filter_func(node) or node["type"] == "folder":
                    if node["type"] == "folder":
                        node = copy.copy(node)
                        node["children"] = apply_filter(
                            node.get("children", {}), filter_func
                        )
                    result[key] = node
            return result

        result = self._list_folder(path, base=base, force_refresh=force_refresh)
        if not recursive:
            if level > 0:
                result = strip_grandchildren(result)
            else:
                result = strip_children(result)
        if callable(filter):
            result = apply_filter(result, filter)
        return result

    def add_folder(self, path, ignore_existing=True, display=None):
        display_path, display_name = self.canonicalize(path)
        path = self.sanitize_path(display_path)
        name = self.sanitize_name(display_name)

        if display is not None:
            display_name = display

        folder_path = os.path.join(path, name)
        if os.path.exists(folder_path):
            if not ignore_existing:
                raise StorageError(
                    f"{name} does already exist in {path}",
                    code=StorageError.ALREADY_EXISTS,
                )
        else:
            os.mkdir(folder_path)

        if display_name != name:
            metadata = self._get_metadata_entry(path, name, default={})
            metadata["display"] = display_name
            self._update_metadata_entry(path, name, metadata)

        return self.path_in_storage((path, name))

    def remove_folder(self, path, recursive=True):
        path, name = self.sanitize(path)

        folder_path = os.path.join(path, name)
        if not os.path.exists(folder_path):
            return

        empty = True
        for entry in scandir(folder_path):
            if entry.name == ".metadata.json" or entry.name == ".metadata.yaml":
                continue
            empty = False
            break

        if not empty and not recursive:
            raise StorageError(
                f"{name} in {path} is not empty",
                code=StorageError.NOT_EMPTY,
            )

        import shutil

        shutil.rmtree(folder_path)

        self._remove_metadata_entry(path, name)

    def _get_source_destination_data(self, source, destination, must_not_equal=False):
        """Prepares data dicts about source and destination for copy/move."""
        source_path, source_name = self.sanitize(source)

        destination_canon_path, destination_canon_name = self.canonicalize(destination)
        destination_path = self.sanitize_path(destination_canon_path)
        destination_name = self.sanitize_name(destination_canon_name)

        source_fullpath = os.path.join(source_path, source_name)
        destination_fullpath = os.path.join(destination_path, destination_name)

        if not os.path.exists(source_fullpath):
            raise StorageError(
                f"{source_name} in {source_path} does not exist",
                code=StorageError.INVALID_SOURCE,
            )

        if not os.path.isdir(destination_path):
            raise StorageError(
                "Destination path {} does not exist or is not a folder".format(
                    destination_path
                ),
                code=StorageError.INVALID_DESTINATION,
            )
        if (
            os.path.exists(destination_fullpath)
            and source_fullpath != destination_fullpath
        ):
            raise StorageError(
                f"{destination_name} does already exist in {destination_path}",
                code=StorageError.ALREADY_EXISTS,
            )

        source_meta = self._get_metadata_entry(source_path, source_name)
        if source_meta:
            source_display = source_meta.get("display", source_name)
        else:
            source_display = source_name

        if (
            must_not_equal or source_display == destination_canon_name
        ) and source_fullpath == destination_fullpath:
            raise StorageError(
                "Source {} and destination {} are the same folder".format(
                    source_path, destination_path
                ),
                code=StorageError.SOURCE_EQUALS_DESTINATION,
            )

        source_data = {
            "path": source_path,
            "name": source_name,
            "display": source_display,
            "fullpath": source_fullpath,
        }
        destination_data = {
            "path": destination_path,
            "name": destination_name,
            "display": destination_canon_name,
            "fullpath": destination_fullpath,
        }
        return source_data, destination_data

    def _set_display_metadata(self, destination_data, source_data=None):
        if (
            source_data
            and destination_data["name"] == source_data["name"]
            and source_data["name"] != source_data["display"]
        ):
            display = source_data["display"]
        elif destination_data["name"] != destination_data["display"]:
            display = destination_data["display"]
        else:
            display = None

        destination_meta = self._get_metadata_entry(
            destination_data["path"], destination_data["name"], default={}
        )
        if display:
            destination_meta["display"] = display
            self._update_metadata_entry(
                destination_data["path"], destination_data["name"], destination_meta
            )
        elif "display" in destination_meta:
            del destination_meta["display"]
            self._update_metadata_entry(
                destination_data["path"], destination_data["name"], destination_meta
            )

    def copy_folder(self, source, destination):
        source_data, destination_data = self._get_source_destination_data(
            source, destination, must_not_equal=True
        )

        try:
            shutil.copytree(source_data["fullpath"], destination_data["fullpath"])
        except Exception as e:
            raise StorageError(
                "Could not copy %s in %s to %s in %s"
                % (
                    source_data["name"],
                    source_data["path"],
                    destination_data["name"],
                    destination_data["path"],
                ),
                cause=e,
            )

        self._set_display_metadata(destination_data, source_data=source_data)

        return self.path_in_storage(destination_data["fullpath"])

    def move_folder(self, source, destination):
        source_data, destination_data = self._get_source_destination_data(
            source, destination
        )

        # only a display rename? Update that and bail early
        if source_data["fullpath"] == destination_data["fullpath"]:
            self._set_display_metadata(destination_data)
            return self.path_in_storage(destination_data["fullpath"])

        try:
            shutil.move(source_data["fullpath"], destination_data["fullpath"])
        except Exception as e:
            raise StorageError(
                "Could not move %s in %s to %s in %s"
                % (
                    source_data["name"],
                    source_data["path"],
                    destination_data["name"],
                    destination_data["path"],
                ),
                cause=e,
            )

        self._set_display_metadata(destination_data, source_data=source_data)
        self._remove_metadata_entry(source_data["path"], source_data["name"])
        self._delete_metadata(source_data["fullpath"])

        return self.path_in_storage(destination_data["fullpath"])

    def add_file(
        self,
        path,
        file_object,
        printer_profile=None,
        links=None,
        allow_overwrite=False,
        display=None,
    ):
        display_path, display_name = self.canonicalize(path)
        path = self.sanitize_path(display_path)
        name = self.sanitize_name(display_name)

        if display:
            display_name = display

        if not octoprint.filemanager.valid_file_type(name):
            raise StorageError(
                f"{name} is an unrecognized file type",
                code=StorageError.INVALID_FILE,
            )

        file_path = os.path.join(path, name)
        if os.path.exists(file_path) and not os.path.isfile(file_path):
            raise StorageError(
                f"{name} does already exist in {path} and is not a file",
                code=StorageError.ALREADY_EXISTS,
            )
        if os.path.exists(file_path) and not allow_overwrite:
            raise StorageError(
                f"{name} does already exist in {path} and overwriting is prohibited",
                code=StorageError.ALREADY_EXISTS,
            )

        # make sure folders exist
        if not os.path.exists(path):
            # TODO persist display names of path segments!
            os.makedirs(path)

        # save the file
        file_object.save(file_path)

        # save the file's hash to the metadata of the folder
        file_hash = self._create_hash(file_path)
        metadata = self._get_metadata_entry(path, name, default={})
        metadata_dirty = False
        if "hash" not in metadata or metadata["hash"] != file_hash:
            # hash changed -> throw away old metadata
            metadata = {"hash": file_hash}
            metadata_dirty = True

        if "display" not in metadata and display_name != name:
            # display name is not the same as file name -> store in metadata
            metadata["display"] = display_name
            metadata_dirty = True

        if metadata_dirty:
            self._update_metadata_entry(path, name, metadata)

        # process any links that were also provided for adding to the file
        if not links:
            links = []

        if printer_profile is not None:
            links.append(
                (
                    "printerprofile",
                    {"id": printer_profile["id"], "name": printer_profile["name"]},
                )
            )

        self._add_links(name, path, links)

        # touch the file to set last access and modification time to now
        os.utime(file_path, None)

        return self.path_in_storage((path, name))

    def remove_file(self, path):
        path, name = self.sanitize(path)

        file_path = os.path.join(path, name)
        if not os.path.exists(file_path):
            return
        if not os.path.isfile(file_path):
            raise StorageError(
                f"{name} in {path} is not a file",
                code=StorageError.INVALID_FILE,
            )

        try:
            os.remove(file_path)
        except Exception as e:
            raise StorageError(f"Could not delete {name} in {path}", cause=e)

        self._remove_metadata_entry(path, name)

    def copy_file(self, source, destination):
        source_data, destination_data = self._get_source_destination_data(
            source, destination, must_not_equal=True
        )

        if not octoprint.filemanager.valid_file_type(destination_data["name"]):
            raise StorageError(
                f"{destination_data['name']} is an unrecognized file type",
                code=StorageError.INVALID_FILE,
            )

        try:
            shutil.copy2(source_data["fullpath"], destination_data["fullpath"])
        except Exception as e:
            raise StorageError(
                "Could not copy %s in %s to %s in %s"
                % (
                    source_data["name"],
                    source_data["path"],
                    destination_data["name"],
                    destination_data["path"],
                ),
                cause=e,
            )

        self._copy_metadata_entry(
            source_data["path"],
            source_data["name"],
            destination_data["path"],
            destination_data["name"],
        )
        self._set_display_metadata(destination_data, source_data=source_data)

        return self.path_in_storage(destination_data["fullpath"])

    def move_file(self, source, destination, allow_overwrite=False):
        source_data, destination_data = self._get_source_destination_data(
            source, destination
        )

        if not octoprint.filemanager.valid_file_type(destination_data["name"]):
            raise StorageError(
                f"{destination_data['name']} is an unrecognized file type",
                code=StorageError.INVALID_FILE,
            )

        # only a display rename? Update that and bail early
        if source_data["fullpath"] == destination_data["fullpath"]:
            self._set_display_metadata(destination_data)
            return self.path_in_storage(destination_data["fullpath"])

        try:
            shutil.move(source_data["fullpath"], destination_data["fullpath"])
        except Exception as e:
            raise StorageError(
                "Could not move %s in %s to %s in %s"
                % (
                    source_data["name"],
                    source_data["path"],
                    destination_data["name"],
                    destination_data["path"],
                ),
                cause=e,
            )

        self._copy_metadata_entry(
            source_data["path"],
            source_data["name"],
            destination_data["path"],
            destination_data["name"],
            delete_source=True,
        )
        self._set_display_metadata(destination_data, source_data=source_data)

        return self.path_in_storage(destination_data["fullpath"])

    def has_analysis(self, path):
        metadata = self.get_metadata(path)
        return "analysis" in metadata

    def get_metadata(self, path):
        path, name = self.sanitize(path)
        return self._get_metadata_entry(path, name)

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
        self._delete_history(name, path, index)

    def get_additional_metadata(self, path, key):
        path, name = self.sanitize(path)
        metadata = self._get_metadata(path)

        if name not in metadata:
            return

        return metadata[name].get(key)

    def set_additional_metadata(self, path, key, data, overwrite=False, merge=False):
        path, name = self.sanitize(path)
        metadata = self._get_metadata(path)
        metadata_dirty = False

        if name not in metadata:
            return

        metadata = self._copied_metadata(metadata, name)

        if key not in metadata[name] or overwrite:
            metadata[name][key] = data
            metadata_dirty = True
        elif (
            key in metadata[name]
            and isinstance(metadata[name][key], dict)
            and isinstance(data, dict)
            and merge
        ):
            import octoprint.util

            metadata[name][key] = octoprint.util.dict_merge(
                metadata[name][key], data, in_place=True
            )
            metadata_dirty = True

        if metadata_dirty:
            self._save_metadata(path, metadata)

    def remove_additional_metadata(self, path, key):
        path, name = self.sanitize(path)
        metadata = self._get_metadata(path)

        if name not in metadata:
            return

        if key not in metadata[name]:
            return

        metadata = self._copied_metadata(metadata, name)
        del metadata[name][key]
        self._save_metadata(path, metadata)

    def split_path(self, path):
        path = to_unicode(path)
        split = path.split("/")

        if len(split) == 1:
            return "", split[0]

        return self.path_in_storage(self.join_path(*split[:-1])), split[-1]

    def join_path(self, *path):
        return self.path_in_storage("/".join(map(to_unicode, path)))

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

        path, name = self.canonicalize(path)
        name = self.sanitize_name(name)
        path = self.sanitize_path(path)
        return path, name

    def canonicalize(self, path):
        name = None
        if isinstance(path, str):
            path = to_unicode(path)
            if path.startswith(self.basefolder):
                path = path[len(self.basefolder) :]
            path = path.replace(os.path.sep, "/")
            path = path.split("/")
        if isinstance(path, (list, tuple)):
            if len(path) == 1:
                name = to_unicode(path[0])
                path = ""
            else:
                name = to_unicode(path[-1])
                path = self.join_path(*map(to_unicode, path[:-1]))
        if not path:
            path = ""

        return path, name

    def sanitize_name(self, name):
        """
        Raises a :class:`ValueError` for a ``name`` containing ``/`` or ``\\``. Otherwise
        sanitizes the given ``name`` using ``octoprint.files.sanitize_filename``. Also
        strips any leading ``.``.
        """
        return sanitize_filename(name, really_universal=self._really_universal)

    def sanitize_path(self, path):
        """
        Ensures that the on disk representation of ``path`` is located under the configured basefolder. Resolves all
        relative path elements (e.g. ``..``) and sanitizes folder names using :func:`sanitize_name`. Final path is the
        absolute path including leading ``basefolder`` path.
        """
        path = to_unicode(path)

        if len(path):
            if path[0] == "/":
                path = path[1:]
            elif path[0] == "." and path[1] == "/":
                path = path[2:]

        path_elements = path.split("/")
        joined_path = self.basefolder
        for path_element in path_elements:
            if path_element == ".." or path_element == ".":
                joined_path = os.path.join(joined_path, path_element)
            else:
                joined_path = os.path.join(joined_path, self.sanitize_name(path_element))
        path = os.path.realpath(joined_path)
        if not path.startswith(self.basefolder):
            raise ValueError(f"path not contained in base folder: {path}")
        return path

    def _sanitize_entry(self, entry, path, entry_path):
        entry = to_unicode(entry)
        sanitized = self.sanitize_name(entry)
        if sanitized != entry:
            # entry is not sanitized yet, let's take care of that
            sanitized_path = os.path.join(path, sanitized)
            sanitized_name, sanitized_ext = os.path.splitext(sanitized)

            counter = 1
            while os.path.exists(sanitized_path):
                counter += 1
                sanitized = self.sanitize_name(
                    f"{sanitized_name}_({counter}){sanitized_ext}"
                )
                sanitized_path = os.path.join(path, sanitized)

            try:
                shutil.move(entry_path, sanitized_path)

                self._logger.info(f'Sanitized "{entry_path}" to "{sanitized_path}"')
                return sanitized, sanitized_path
            except Exception:
                self._logger.exception(
                    'Error while trying to rename "{}" to "{}", ignoring file'.format(
                        entry_path, sanitized_path
                    )
                )
                raise

        return entry, entry_path

    def path_in_storage(self, path):
        if isinstance(path, (tuple, list)):
            path = self.join_path(*path)
        if isinstance(path, str):
            path = to_unicode(path)
            if path.startswith(self.basefolder):
                path = path[len(self.basefolder) :]
            path = path.replace(os.path.sep, "/")
        while path.startswith("/"):
            path = path[1:]

        return path

    def path_on_disk(self, path):
        path, name = self.sanitize(path)
        return os.path.join(path, name)

    ##~~ internals

    def _add_history(self, name, path, data):
        metadata = self._copied_metadata(self._get_metadata(path), name)

        if "hash" not in metadata[name]:
            metadata[name]["hash"] = self._create_hash(os.path.join(path, name))

        if "history" not in metadata[name]:
            metadata[name]["history"] = []

        metadata[name]["history"].append(data)
        self._calculate_stats_from_history(name, path, metadata=metadata, save=False)
        self._save_metadata(path, metadata)

    def _update_history(self, name, path, index, data):
        metadata = self._get_metadata(path)

        if name not in metadata or "history" not in metadata[name]:
            return

        metadata = self._copied_metadata(metadata, name)

        try:
            metadata[name]["history"][index].update(data)
            self._calculate_stats_from_history(name, path, metadata=metadata, save=False)
            self._save_metadata(path, metadata)
        except IndexError:
            pass

    def _delete_history(self, name, path, index):
        metadata = self._get_metadata(path)

        if name not in metadata or "history" not in metadata[name]:
            return

        metadata = self._copied_metadata(metadata, name)

        try:
            del metadata[name]["history"][index]
            self._calculate_stats_from_history(name, path, metadata=metadata, save=False)
            self._save_metadata(path, metadata)
        except IndexError:
            pass

    def _calculate_stats_from_history(self, name, path, metadata=None, save=True):
        if metadata is None:
            metadata = self._copied_metadata(self._get_metadata(path), name)

        if "history" not in metadata[name]:
            return

        # collect data from history
        former_print_times = {}
        last_print = {}

        for history_entry in metadata[name]["history"]:
            if (
                "printTime" not in history_entry
                or "success" not in history_entry
                or not history_entry["success"]
                or "printerProfile" not in history_entry
            ):
                continue

            printer_profile = history_entry["printerProfile"]
            if not printer_profile:
                continue

            print_time = history_entry["printTime"]
            try:
                print_time = float(print_time)
            except Exception:
                self._logger.warning(
                    "Invalid print time value found in print history for {} in {}/.metadata.json: {!r}".format(
                        name, path, print_time
                    )
                )
                continue

            if printer_profile not in former_print_times:
                former_print_times[printer_profile] = []
            former_print_times[printer_profile].append(print_time)

            if (
                printer_profile not in last_print
                or last_print[printer_profile] is None
                or (
                    "timestamp" in history_entry
                    and history_entry["timestamp"]
                    > last_print[printer_profile]["timestamp"]
                )
            ):
                last_print[printer_profile] = history_entry

        # calculate stats
        statistics = {"averagePrintTime": {}, "lastPrintTime": {}}

        for printer_profile in former_print_times:
            if not former_print_times[printer_profile]:
                continue
            statistics["averagePrintTime"][printer_profile] = sum(
                former_print_times[printer_profile]
            ) / len(former_print_times[printer_profile])

        for printer_profile in last_print:
            if not last_print[printer_profile]:
                continue
            statistics["lastPrintTime"][printer_profile] = last_print[printer_profile][
                "printTime"
            ]

        metadata[name]["statistics"] = statistics

        if save:
            self._save_metadata(path, metadata)

    def _get_links(self, name, path, searched_rel):
        metadata = self._get_metadata(path)
        result = []

        if name not in metadata:
            return result

        if "links" not in metadata[name]:
            return result

        for data in metadata[name]["links"]:
            if "rel" not in data or not data["rel"] == searched_rel:
                continue
            result.append(data)
        return result

    def _add_links(self, name, path, links):
        file_type = octoprint.filemanager.get_file_type(name)
        if file_type:
            file_type = file_type[0]

        metadata = self._copied_metadata(self._get_metadata(path), name)
        metadata_dirty = False

        if "hash" not in metadata[name]:
            metadata[name]["hash"] = self._create_hash(os.path.join(path, name))

        if "links" not in metadata[name]:
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
                    if data["name"] not in metadata:
                        metadata[data["name"]] = {"hash": hash, "links": []}
                    else:
                        metadata[data["name"]]["hash"] = hash

                if "hash" in data and not data["hash"] == hash:
                    # file doesn't have the correct hash, we won't create the link
                    continue

                if "links" not in metadata[data["name"]]:
                    metadata[data["name"]]["links"] = []

                # add reverse link to link target file
                metadata[data["name"]]["links"].append(
                    {
                        "rel": "machinecode" if rel == "model" else "model",
                        "name": name,
                        "hash": metadata[name]["hash"],
                    }
                )
                metadata_dirty = True

                link_dict = {"rel": rel, "name": data["name"], "hash": hash}

            elif rel == "web" and "href" in data:
                link_dict = {"rel": rel, "href": data["href"]}
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
        metadata = self._copied_metadata(self._get_metadata(path), name)
        metadata_dirty = False

        hash = metadata[name].get("hash", self._create_hash(os.path.join(path, name)))

        for rel, data in links:
            if (rel == "model" or rel == "machinecode") and "name" in data:
                if data["name"] in metadata and "links" in metadata[data["name"]]:
                    ref_rel = "model" if rel == "machinecode" else "machinecode"
                    for link in metadata[data["name"]]["links"]:
                        if (
                            link["rel"] == ref_rel
                            and "name" in link
                            and link["name"] == name
                            and "hash" in link
                            and link["hash"] == hash
                        ):
                            metadata[data["name"]] = copy.deepcopy(metadata[data["name"]])
                            metadata[data["name"]]["links"].remove(link)
                            metadata_dirty = True

            if "links" in metadata[name]:
                for link in metadata[name]["links"]:
                    if not link["rel"] == rel:
                        continue

                    matches = True
                    for k, v in data.items():
                        if k not in link or not link[k] == v:
                            matches = False
                            break

                    if not matches:
                        continue

                    metadata[name]["links"].remove(link)
                    metadata_dirty = True

        if metadata_dirty:
            self._save_metadata(path, metadata)

    @time_this(
        logtarget=__name__ + ".timings",
        message="{func}({func_args},{func_kwargs}) took {timing:.2f}ms",
        incl_func_args=True,
        log_enter=True,
    )
    def _list_folder(self, path, base="", force_refresh=False, fill_cache=True, **kwargs):
        def get_size(nodes):
            total_size = 0
            for node in nodes.values():
                if "size" in node:
                    total_size += node["size"]
            return total_size

        def enrich_folders(nodes):
            nodes = copy.copy(nodes)
            for key, value in nodes.items():
                if value["type"] == "folder":
                    value = copy.copy(value)
                    value["children"] = self._list_folder(
                        os.path.join(path, key),
                        base=value["path"] + "/",
                        force_refresh=force_refresh,
                    )
                    value["size"] = get_size(value["children"])
                    nodes[key] = value
            return nodes

        metadata_dirty = False
        try:
            with self._filelist_cache_mutex:
                cache = self._filelist_cache.get(path)
                lm = self.last_modified(path, recursive=True)
                if not force_refresh and cache and cache[0] >= lm:
                    return enrich_folders(cache[1])

                metadata = self._get_metadata(path)
                if not metadata:
                    metadata = {}

                result = {}

                for entry in scandir(path):
                    if is_hidden_path(entry.name):
                        # no hidden files and folders
                        continue

                    try:
                        entry_name = entry_display = entry.name
                        entry_path = entry.path
                        entry_is_file = entry.is_file()
                        entry_is_dir = entry.is_dir()
                        entry_stat = entry.stat()
                    except Exception:
                        # error while trying to fetch file metadata, that might be thanks to file already having
                        # been moved or deleted - ignore it and continue
                        continue

                    try:
                        new_entry_name, new_entry_path = self._sanitize_entry(
                            entry_name, path, entry_path
                        )
                        if entry_name != new_entry_name or entry_path != new_entry_path:
                            entry_display = to_unicode(entry_name)
                            entry_name = new_entry_name
                            entry_path = new_entry_path
                            entry_stat = os.stat(entry_path)
                    except Exception:
                        # error while trying to rename the file, we'll continue here and ignore it
                        continue

                    path_in_location = entry_name if not base else base + entry_name

                    try:
                        # file handling
                        if entry_is_file:
                            type_path = octoprint.filemanager.get_file_type(entry_name)
                            if not type_path:
                                # only supported extensions
                                continue
                            else:
                                file_type = type_path[0]

                            if entry_name in metadata and isinstance(
                                metadata[entry_name], dict
                            ):
                                entry_metadata = metadata[entry_name]
                                if (
                                    "display" not in entry_metadata
                                    and entry_display != entry_name
                                ):
                                    if not metadata_dirty:
                                        metadata = self._copied_metadata(
                                            metadata, entry_name
                                        )
                                    metadata[entry_name]["display"] = entry_display
                                    entry_metadata["display"] = entry_display
                                    metadata_dirty = True
                            else:
                                if not metadata_dirty:
                                    metadata = self._copied_metadata(metadata, entry_name)
                                entry_metadata = self._add_basic_metadata(
                                    path,
                                    entry_name,
                                    display_name=entry_display,
                                    save=False,
                                    metadata=metadata,
                                )
                                metadata_dirty = True

                            extended_entry_data = {}
                            extended_entry_data.update(entry_metadata)
                            extended_entry_data["name"] = entry_name
                            extended_entry_data["display"] = entry_metadata.get(
                                "display", entry_name
                            )
                            extended_entry_data["path"] = path_in_location
                            extended_entry_data["type"] = file_type
                            extended_entry_data["typePath"] = type_path
                            stat = entry_stat
                            if stat:
                                extended_entry_data["size"] = stat.st_size
                                extended_entry_data["date"] = int(stat.st_mtime)

                            result[entry_name] = extended_entry_data

                        # folder recursion
                        elif entry_is_dir:
                            if entry_name in metadata and isinstance(
                                metadata[entry_name], dict
                            ):
                                entry_metadata = metadata[entry_name]
                                if (
                                    "display" not in entry_metadata
                                    and entry_display != entry_name
                                ):
                                    if not metadata_dirty:
                                        metadata = self._copied_metadata(
                                            metadata, entry_name
                                        )
                                    metadata[entry_name]["display"] = entry_display
                                    entry_metadata["display"] = entry_display
                                    metadata_dirty = True
                            elif entry_name != entry_display:
                                if not metadata_dirty:
                                    metadata = self._copied_metadata(metadata, entry_name)
                                entry_metadata = self._add_basic_metadata(
                                    path,
                                    entry_name,
                                    display_name=entry_display,
                                    save=False,
                                    metadata=metadata,
                                )
                                metadata_dirty = True
                            else:
                                entry_metadata = {}

                            entry_data = {
                                "name": entry_name,
                                "display": entry_metadata.get("display", entry_name),
                                "path": path_in_location,
                                "type": "folder",
                                "typePath": ["folder"],
                            }
                            if entry_stat:
                                entry_data["date"] = int(entry_stat.st_mtime)

                            result[entry_name] = entry_data
                    except Exception:
                        # So something went wrong somewhere while processing this file entry - log that and continue
                        self._logger.exception(
                            f"Error while processing entry {entry_path}"
                        )
                        continue

                if fill_cache:
                    self._filelist_cache[path] = (
                        lm,
                        result,
                    )
                return enrich_folders(result)
        finally:
            # save metadata
            if metadata_dirty:
                self._save_metadata(path, metadata)

    def _add_basic_metadata(
        self,
        path,
        entry,
        display_name=None,
        additional_metadata=None,
        save=True,
        metadata=None,
    ):
        if additional_metadata is None:
            additional_metadata = {}

        if metadata is None:
            metadata = self._get_metadata(path)

        entry_path = os.path.join(path, entry)

        if os.path.isfile(entry_path):
            entry_data = {
                "hash": self._create_hash(os.path.join(path, entry)),
                "links": [],
                "notes": [],
            }
            if (
                path == self.basefolder
                and self._old_metadata is not None
                and entry in self._old_metadata
                and "gcodeAnalysis" in self._old_metadata[entry]
            ):
                # if there is still old metadata available and that contains an analysis for this file, use it!
                entry_data["analysis"] = self._old_metadata[entry]["gcodeAnalysis"]

        elif os.path.isdir(entry_path):
            entry_data = {}

        else:
            return

        if display_name is not None and not display_name == entry:
            entry_data["display"] = display_name

        entry_data.update(additional_metadata)

        metadata = copy.copy(metadata)
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

    def _get_metadata_entry(self, path, name, default=None):
        with self._get_metadata_lock(path):
            metadata = self._get_metadata(path)
            return metadata.get(name, default)

    def _remove_metadata_entry(self, path, name):
        with self._get_metadata_lock(path):
            metadata = self._get_metadata(path)
            if name not in metadata:
                return

            metadata = copy.copy(metadata)

            if "hash" in metadata[name]:
                hash = metadata[name]["hash"]
                for m in metadata.values():
                    if "links" not in m:
                        continue
                    links_hash = (
                        lambda link: "hash" in link
                        and link["hash"] == hash
                        and "rel" in link
                        and (link["rel"] == "model" or link["rel"] == "machinecode")
                    )
                    m["links"] = [link for link in m["links"] if not links_hash(link)]

            del metadata[name]
            self._save_metadata(path, metadata)

    def _update_metadata_entry(self, path, name, data):
        with self._get_metadata_lock(path):
            metadata = copy.copy(self._get_metadata(path))
            metadata[name] = data
            self._save_metadata(path, metadata)

    def _copy_metadata_entry(
        self,
        source_path,
        source_name,
        destination_path,
        destination_name,
        delete_source=False,
        updates=None,
    ):
        with self._get_metadata_lock(source_path):
            source_data = self._get_metadata_entry(source_path, source_name, default={})
            if not source_data:
                return

            if delete_source:
                self._remove_metadata_entry(source_path, source_name)

        if updates is not None:
            source_data.update(updates)

        with self._get_metadata_lock(destination_path):
            self._update_metadata_entry(destination_path, destination_name, source_data)

    def _get_metadata(self, path, force=False):
        import json

        if not force:
            metadata = self._metadata_cache.get(path)
            if metadata:
                return metadata

        self._migrate_metadata(path)

        metadata_path = os.path.join(path, ".metadata.json")

        metadata = None
        with self._get_persisted_metadata_lock(path):
            if os.path.exists(metadata_path):
                with open(metadata_path, encoding="utf-8") as f:
                    try:
                        metadata = json.load(f)
                    except Exception:
                        self._logger.exception(
                            f"Error while reading .metadata.json from {path}"
                        )

        def valid_json(value):
            try:
                json.dumps(value, allow_nan=False)
                return True
            except Exception:
                return False

        if isinstance(metadata, dict):
            old_size = len(metadata)
            metadata = {k: v for k, v in metadata.items() if valid_json(v)}
            metadata = {
                k: v for k, v in metadata.items() if os.path.exists(os.path.join(path, k))
            }
            new_size = len(metadata)
            if new_size != old_size:
                self._logger.info(
                    "Deleted {} stale or invalid entries from metadata for path {}".format(
                        old_size - new_size, path
                    )
                )
                self._save_metadata(path, metadata)
            else:
                with self._get_metadata_lock(path):
                    self._metadata_cache[path] = metadata
            return metadata
        else:
            return {}

    def _save_metadata(self, path, metadata):
        import json

        with self._get_metadata_lock(path):
            self._metadata_cache[path] = metadata

        with self._get_persisted_metadata_lock(path):
            metadata_path = os.path.join(path, ".metadata.json")
            try:
                with atomic_write(metadata_path, mode="wb") as f:
                    f.write(
                        to_bytes(json.dumps(metadata, indent=2, separators=(",", ": ")))
                    )
            except Exception:
                self._logger.exception(f"Error while writing .metadata.json to {path}")

    def _delete_metadata(self, path):
        with self._get_metadata_lock(path):
            if path in self._metadata_cache:
                del self._metadata_cache[path]

        with self._get_persisted_metadata_lock(path):
            metadata_files = (".metadata.json", ".metadata.yaml")
            for metadata_file in metadata_files:
                metadata_path = os.path.join(path, metadata_file)
                if os.path.exists(metadata_path):
                    try:
                        os.remove(metadata_path)
                    except Exception:
                        self._logger.exception(
                            f"Error while deleting {metadata_file} from {path}"
                        )

    @staticmethod
    def _copied_metadata(metadata, name):
        metadata = copy.copy(metadata)
        metadata[name] = copy.deepcopy(metadata.get(name, {}))
        return metadata

    def _migrate_metadata(self, path):
        # we switched to json in 1.3.9 - if we still have yaml here, migrate it now
        import json

        with self._get_persisted_metadata_lock(path):
            metadata_path_yaml = os.path.join(path, ".metadata.yaml")
            metadata_path_json = os.path.join(path, ".metadata.json")

            if not os.path.exists(metadata_path_yaml):
                # nothing to migrate
                return

            if os.path.exists(metadata_path_json):
                # already migrated
                try:
                    os.remove(metadata_path_yaml)
                except Exception:
                    self._logger.exception(
                        f"Error while removing .metadata.yaml from {path}"
                    )
                return

            try:
                metadata = yaml.load_from_file(path=metadata_path_yaml)
            except Exception:
                self._logger.exception(f"Error while reading .metadata.yaml from {path}")
                return

            if not isinstance(metadata, dict):
                # looks invalid, ignore it
                return

            with atomic_write(metadata_path_json, mode="wb") as f:
                f.write(to_bytes(json.dumps(metadata, indent=2, separators=(",", ": "))))

            try:
                os.remove(metadata_path_yaml)
            except Exception:
                self._logger.exception(f"Error while removing .metadata.yaml from {path}")

    @contextmanager
    def _get_metadata_lock(self, path):
        with self._metadata_lock_mutex:
            if path not in self._metadata_locks:
                import threading

                self._metadata_locks[path] = (0, threading.RLock())

            counter, lock = self._metadata_locks[path]
            counter += 1
            self._metadata_locks[path] = (counter, lock)

        yield lock

        with self._metadata_lock_mutex:
            counter = self._metadata_locks[path][0]
            counter -= 1
            if counter <= 0:
                del self._metadata_locks[path]
            else:
                self._metadata_locks[path] = (counter, lock)

    @contextmanager
    def _get_persisted_metadata_lock(self, path):
        with self._persisted_metadata_lock_mutex:
            if path not in self._persisted_metadata_locks:
                import threading

                self._persisted_metadata_locks[path] = (0, threading.RLock())

            counter, lock = self._persisted_metadata_locks[path]
            counter += 1
            self._persisted_metadata_locks[path] = (counter, lock)

        yield lock

        with self._persisted_metadata_lock_mutex:
            counter = self._persisted_metadata_locks[path][0]
            counter -= 1
            if counter <= 0:
                del self._persisted_metadata_locks[path]
            else:
                self._persisted_metadata_locks[path] = (counter, lock)
