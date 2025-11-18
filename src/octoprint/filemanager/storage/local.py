__author__ = "Gina Häußge <gina@octoprint.org>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import copy
import logging
import os
import shutil
import time
import typing
from contextlib import contextmanager
from os import scandir, walk

import gcode_thumbnail_tool as gtt
import pylru

import octoprint.filemanager
from octoprint.filemanager.util import AbstractFileWrapper
from octoprint.util import (
    atomic_write,
    is_hidden_path,
    time_this,
    to_bytes,
    to_unicode,
    yaml,
)
from octoprint.util.files import sanitize_filename

from . import (
    AnalysisDimensions,
    AnalysisFilamentUse,
    AnalysisResult,
    AnalysisVolume,
    HistoryEntry,
    MetadataEntry,
    Statistics,
    StorageCapabilities,
    StorageEntry,
    StorageError,
    StorageFile,
    StorageFolder,
    StorageInterface,
    StorageThumbnail,
)

if typing.TYPE_CHECKING:
    from octoprint.printer.job import PrintJob  # noqa: F401


class LocalFileStorage(StorageInterface):
    """
    The ``LocalFileStorage`` is a storage implementation which holds all files, folders and metadata on disk.

    Metadata is managed inside ``.metadata.json`` files in the respective folders, indexed by the sanitized filenames
    stored within the folder. Metadata access is managed through an LRU cache to minimize access overhead.

    This storage type implements :func:`path_on_disk`.
    """

    storage = "local"
    name = "Local"

    capabilities = StorageCapabilities(
        write_file=True,
        read_file=True,
        remove_file=True,
        copy_file=True,
        move_file=True,
        add_folder=True,
        remove_folder=True,
        copy_folder=True,
        move_folder=True,
        metadata=True,
        history=True,
        thumbnails=True,
        path_on_disk=True,
    )

    THUMBNAIL_DIR = ".thumbs"

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

        self._last_activity = 0

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

    def _update_last_activity(self):
        self._last_activity = time.monotonic()
        self._logger.debug(f"Last Activity: {self._last_activity}")

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
                    yield entry.name, entry.path, None
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
            values = [0] + [last_modified_for_path(root) for root, _, _ in walk(path)]
            return max(values)
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
        if not os.path.exists(path):
            return 0

        last_modified = os.stat(path).st_mtime

        # shortcut for individual files
        if os.path.isfile(path):
            return int(last_modified)

        for entry in os.scandir(path):
            try:
                if entry.is_file():
                    last_modified = max(last_modified, entry.stat().st_mtime)
                elif recursive and entry.is_dir():
                    last_modified = max(
                        last_modified,
                        self.get_lastmodified(entry.path, recursive=recursive),
                    )
            except FileNotFoundError:
                # avoid a potential race condition, file might be removed between scandir & stat call
                pass

        return int(last_modified)

    def get_hash(self, path: str = None, recursive: bool = False) -> str:
        import hashlib

        hash = hashlib.sha1()

        def hash_update(value: str):
            hash.update(value.encode("utf-8"))

        hash_update(str(self.get_lastmodified(path, recursive=recursive)))
        hash_update(str(self._last_activity))
        return hash.hexdigest()

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

    def get_storage_entry(self, path: str) -> StorageEntry:
        path_on_disk = self.sanitize_path(path)
        if not os.path.exists(path_on_disk):
            return None

        parent_on_disk = os.path.dirname(path_on_disk)
        metadata = self._get_metadata(parent_on_disk)
        if not metadata:
            metadata = {}

        entry, dirty = self._prep_storage_entry(path, metadata)
        if dirty:
            self._save_metadata(parent_on_disk, metadata)
        return entry

    def list_storage_entries(
        self,
        path: str = None,
        filter: callable = None,
        recursive: bool = True,
        level: int = 0,
        force_refresh: bool = False,
    ) -> dict[str, StorageEntry]:
        if path:
            path = self.sanitize_path(path)
            base = self.path_in_storage(path)
            if base:
                base += "/"
        else:
            path = self.basefolder
            base = ""

        def strip_children(nodes: dict[str, StorageEntry]) -> dict[str, StorageEntry]:
            result = {}
            for key, node in nodes.items():
                if isinstance(node, StorageFolder):
                    node = copy.copy(node)
                    node.children = {}
                result[key] = node
            return result

        def strip_grandchildren(
            nodes: dict[str, StorageEntry],
        ) -> dict[str, StorageEntry]:
            result = {}
            for key, node in nodes.items():
                if isinstance(node, StorageFolder):
                    node = copy.copy(node)
                    node.children = strip_children(node.children)
                result[key] = node
            return result

        def apply_filter(
            nodes: dict[str, StorageEntry], filter_func: callable
        ) -> dict[str, StorageEntry]:
            result = {}
            for key, node in nodes.items():
                if filter_func(node) or isinstance(node, StorageFolder):
                    if isinstance(node, StorageFolder):
                        node = copy.copy(node)
                        node.children = apply_filter(node.children, filter_func)
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

    def add_folder(self, path, ignore_existing=True, display=None, user=None):
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
            self._update_last_activity()

        metadata = self._get_metadata_entry(path, name, default={})
        metadata_dirty = False

        if display_name != name:
            metadata["display"] = display_name
            metadata_dirty = True

        if user:
            metadata["user"] = user
            metadata_dirty = True

        if metadata_dirty:
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
        self._update_last_activity()

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
            self._update_last_activity()
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
            ) from e

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
            self._update_last_activity()
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
            ) from e

        self._set_display_metadata(destination_data, source_data=source_data)
        self._remove_metadata_entry(source_data["path"], source_data["name"])
        self._delete_metadata(source_data["fullpath"])

        return self.path_in_storage(destination_data["fullpath"])

    def add_file(
        self,
        path: str,
        file_obj: AbstractFileWrapper,
        allow_overwrite=False,
        display=None,
        user=None,
        progress_callback=None,
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
        file_obj.save(file_path)

        # populate metadata
        metadata = self._get_metadata_entry(path, name, default={})
        metadata_dirty = False

        if display_name != name and "display" not in metadata:
            # display name is not the same as file name -> store in metadata
            metadata["display"] = display_name
            metadata_dirty = True

        if user and "user" not in metadata:
            metadata["user"] = user
            metadata_dirty = True

        if metadata_dirty:
            self._update_metadata_entry(path, name, metadata)

        self._extract_thumbnails(file_path)

        # touch the file to set last access and modification time to now
        os.utime(file_path, None)
        self._update_last_activity()

        if progress_callback:
            progress_callback(done=True)
        return self.path_in_storage((path, name))

    def read_file(self, path) -> typing.IO:
        path, name = self.sanitize(path)
        file_path = os.path.join(path, name)

        if not os.path.exists(file_path):
            raise StorageError(
                f"{name} in {path} does not exist", code=StorageError.DOES_NOT_EXIST
            )

        if not os.path.isfile(file_path):
            raise StorageError(
                f"{name} in {path} is not a file",
                code=StorageError.INVALID_FILE,
            )

        return open(file_path, mode="rb")

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
            self._update_last_activity()
        except Exception as e:
            raise StorageError(f"Could not delete {name} in {path}", cause=e) from e

        self._remove_metadata_entry(path, name)
        self._remove_thumbnails(path, name)

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
            self._update_last_activity()
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
            ) from e

        self._copy_metadata_entry(
            source_data["path"],
            source_data["name"],
            destination_data["path"],
            destination_data["name"],
        )
        self._set_display_metadata(destination_data, source_data=source_data)

        self._copy_thumbnails(
            source_data["path"],
            source_data["name"],
            destination_data["path"],
            destination_data["name"],
        )

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
            self._update_last_activity()
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
            ) from e

        self._copy_metadata_entry(
            source_data["path"],
            source_data["name"],
            destination_data["path"],
            destination_data["name"],
            delete_source=True,
        )
        self._set_display_metadata(destination_data, source_data=source_data)

        self._copy_thumbnails(
            source_data["path"],
            source_data["name"],
            destination_data["path"],
            destination_data["name"],
            delete_source=True,
        )

        return self.path_in_storage(destination_data["fullpath"])

    def has_analysis(self, path):
        metadata = self.get_metadata(path)
        return metadata and "analysis" in metadata

    def get_metadata(self, path):
        path, name = self.sanitize(path)
        return self._get_metadata_entry(path, name)

    def add_history(self, path, data):
        path, name = self.sanitize(path)
        self._add_history(name, path, data)

    def update_history(self, path, index, data):
        path, name = self.sanitize(path)
        self._update_history(name, path, index, data)

    def remove_history(self, path, index):
        path, name = self.sanitize(path)
        self._delete_history(name, path, index)

    def has_thumbnail(self, path) -> bool:
        path, name = self.sanitize(path)
        thumbnails = self._get_thumbnails(path, name)
        return thumbnails and len(thumbnails) > 0

    def get_thumbnail(self, path, sizehint=None) -> StorageThumbnail:
        sh, thumb = self._thumbnail_from_sizehint(path, sizehint=sizehint)
        if not thumb:
            return None

        return self._to_thumbnail_info(thumb, sh, path)

    def read_thumbnail(self, path, sizehint=None) -> tuple[StorageThumbnail, typing.IO]:
        sh, thumb = self._thumbnail_from_sizehint(path, sizehint=sizehint)
        if not thumb:
            return None

        info = self._to_thumbnail_info(thumb, sh, path)

        return info, open(thumb, mode="rb")

    def _to_thumbnail_info(
        self, thumb: str, sizehint: str, printable: str
    ) -> StorageThumbnail:
        from filetype import guess_mime

        name = thumb
        if "/" in thumb:
            name = thumb.rsplit("/", maxsplit=1)[1]

        stat = os.stat(thumb)
        mime = guess_mime(thumb)

        return StorageThumbnail(
            name=name,
            printable=printable,
            sizehint=sizehint,
            mime=mime,
            size=stat.st_size,
            last_modified=int(stat.st_mtime),
        )

    def _thumbnail_from_sizehint(
        self, path: str, sizehint: str = None
    ) -> tuple[str, str]:
        path, name = self.sanitize(path)
        thumbnails = self._get_thumbnails(path, name)
        if not thumbnails:
            raise StorageError(
                f"{name} in {path} does not have any thumbnails",
                code=StorageError.DOES_NOT_EXIST,
            )

        if sizehint is not None:
            thumb = thumbnails.get(sizehint)
            if thumb:
                return sizehint, thumb
        return next(iter(thumbnails.items()))

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

    @time_this(
        logtarget=__name__ + ".timings",
        message="{func}({func_args},{func_kwargs}) took {timing:.2f}ms",
        incl_func_args=True,
        log_enter=True,
    )
    def _list_folder(
        self, path, base="", force_refresh=False, fill_cache=True, **kwargs
    ) -> dict[str, StorageEntry]:
        with self._filelist_cache_mutex:
            cache = self._filelist_cache.get(path)
            lm = self.last_modified(path, recursive=True)
            if not force_refresh and cache and cache[0] >= lm:
                return self._enrich_folders(cache[1])

            metadata = self._get_metadata(path)
            if not metadata:
                metadata = {}
            metadata_dirty = False

            try:
                result = {}

                for entry in scandir(path):
                    if is_hidden_path(entry.name):
                        # no hidden files and folders
                        continue

                    entry, dirty = self._prep_storage_entry(base + entry.name, metadata)
                    if not entry:
                        # error while trying to fetch file metadata, that might be thanks to file already having
                        # been moved or deleted - ignore it and continue
                        continue
                    result[entry.name] = entry
                    metadata_dirty = metadata_dirty or dirty

                if fill_cache:
                    self._filelist_cache[path] = (
                        lm,
                        result,
                    )
                return result
            finally:
                # save metadata
                if metadata_dirty:
                    self._save_metadata(path, metadata)

    def _prep_storage_entry(
        self,
        path: str,
        metadata: dict,
        force_refresh: bool = False,
    ) -> tuple[StorageEntry, bool]:
        try:
            path_on_disk = self.path_on_disk(path)

            name = display = os.path.basename(path_on_disk)
            stat = os.stat(path_on_disk)

            try:
                new_name, new_path_on_disk = self._sanitize_entry(
                    name, path, path_on_disk
                )
                if name != new_name or path_on_disk != new_path_on_disk:
                    display = to_unicode(name)
                    name = new_name
                    path_on_disk = new_path_on_disk
                    stat = os.stat(path_on_disk)
            except Exception:
                # error while trying to rename or stat the file, we'll return here
                return None, False

            folder = os.path.isdir(path_on_disk)
            parent_on_disk = os.path.dirname(path_on_disk)

            metadata_dirty = False

            try:
                # folder recursion
                if folder:
                    if name in metadata and isinstance(metadata[name], dict):
                        entry_metadata = metadata[name]
                        if "display" not in entry_metadata and display != name:
                            metadata[name]["display"] = display
                            metadata_dirty = True

                    elif name != display:
                        entry_metadata = self._add_basic_metadata(
                            parent_on_disk,
                            name,
                            display_name=display,
                            save=False,
                            metadata=metadata,
                        )
                        metadata_dirty = True

                    else:
                        entry_metadata = {}

                    storage_entry = StorageFolder(
                        name=name,
                        display=entry_metadata.get("display", name),
                        origin=self.storage,
                        path=path,
                    )
                    if stat:
                        storage_entry.date = int(stat.st_mtime)

                    storage_entry = self._enrich_folder(
                        storage_entry, force_refresh=force_refresh
                    )

                    return storage_entry, metadata_dirty

                # file handling
                else:
                    type_path = octoprint.filemanager.get_file_type(name)
                    if not type_path:
                        # only supported extensions
                        return None, metadata_dirty
                    else:
                        file_type = type_path[0]

                    if name in metadata and isinstance(metadata[name], dict):
                        entry_metadata = metadata[name]
                        if "display" not in entry_metadata and display != name:
                            metadata[name]["display"] = display
                            metadata_dirty = True
                    else:
                        entry_metadata = self._add_basic_metadata(
                            parent_on_disk,
                            name,
                            display_name=display,
                            save=False,
                            metadata=metadata,
                        )
                        metadata_dirty = True

                    storage_entry = StorageFile(
                        name=name,
                        display=entry_metadata.get("display", name),
                        origin=self.storage,
                        path=path,
                        entry_type=file_type,
                        type_path=type_path,
                    )

                    if entry_metadata:
                        storage_entry.metadata = MetadataEntry()

                        if "user" in entry_metadata:
                            storage_entry.user = entry_metadata["user"]

                        if "analysis" in entry_metadata:
                            meta_analysis = entry_metadata["analysis"]

                            analysis = AnalysisResult()

                            if "estimatedPrintTime" in meta_analysis:
                                analysis.estimatedPrintTime = meta_analysis[
                                    "estimatedPrintTime"
                                ]

                            if "printingArea" in meta_analysis:
                                x = meta_analysis["printingArea"]
                                analysis.printingArea = AnalysisVolume(
                                    minX=x["minX"],
                                    minY=x["minY"],
                                    minZ=x["minZ"],
                                    maxX=x["maxX"],
                                    maxY=x["maxY"],
                                    maxZ=x["maxZ"],
                                )

                            if "travelArea" in meta_analysis:
                                x = meta_analysis["travelArea"]
                                analysis.travelArea = AnalysisVolume(
                                    minX=x["minX"],
                                    minY=x["minY"],
                                    minZ=x["minZ"],
                                    maxX=x["maxX"],
                                    maxY=x["maxY"],
                                    maxZ=x["maxZ"],
                                )

                            if "dimensions" in meta_analysis:
                                x = meta_analysis["dimensions"]
                                analysis.dimensions = AnalysisDimensions(
                                    width=x["width"], height=x["height"], depth=x["depth"]
                                )

                            if "travelDimensions" in meta_analysis:
                                x = meta_analysis["travelDimensions"]
                                analysis.travelDimensions = AnalysisDimensions(
                                    width=x["width"], height=x["height"], depth=x["depth"]
                                )

                            if "filament" in meta_analysis:
                                x = meta_analysis["filament"]
                                result = {}
                                for tool, data in x.items():
                                    result[tool] = AnalysisFilamentUse(
                                        length=data["length"], volume=data["volume"]
                                    )
                                analysis.filament = result

                            additional_analysis_keys = [
                                x
                                for x in meta_analysis
                                if x
                                not in (
                                    "estimatedPrintTime",
                                    "printingArea",
                                    "travelArea",
                                    "dimensions",
                                    "travelDimensions",
                                    "filament",
                                )
                            ]
                            if additional_analysis_keys:
                                # there are more things stored in this analysis
                                analysis.additional = {
                                    k: v
                                    for k, v in meta_analysis.items()
                                    if k in additional_analysis_keys
                                }

                            storage_entry.metadata.analysis = analysis

                        if "history" in entry_metadata:
                            history = []
                            for h in entry_metadata["history"]:
                                if any(
                                    x not in h
                                    for x in ("timestamp", "success", "printerProfile")
                                ):
                                    continue
                                history.append(
                                    HistoryEntry(
                                        timestamp=h["timestamp"],
                                        success=h["success"],
                                        printerProfile=h["printerProfile"],
                                        printTime=h.get("printTime"),
                                    )
                                )
                            storage_entry.metadata.history = history

                        if "statistics" in entry_metadata:
                            stats = entry_metadata["statistics"]
                            storage_entry.metadata.statistics = Statistics(
                                averagePrintTime=stats.get("averagePrintTime", {}),
                                lastPrintTime=stats.get("lastPrintTime", {}),
                            )

                        additional_metadata_keys = [
                            x
                            for x in entry_metadata
                            if x
                            not in (
                                "user",
                                "display",
                                "analysis",
                                "history",
                                "statistics",
                            )
                        ]
                        if additional_metadata_keys:
                            # there are still keys left, those are additional keys
                            storage_entry.metadata.additional = {
                                k: v
                                for k, v in entry_metadata.items()
                                if k in additional_metadata_keys
                            }

                    if stat:
                        storage_entry.size = stat.st_size
                        storage_entry.date = int(stat.st_mtime)

                    thumbnails = self._get_thumbnails(os.path.dirname(path_on_disk), name)
                    if thumbnails:
                        storage_entry.thumbnails = list(thumbnails.keys())

                    return storage_entry, metadata_dirty

            except Exception:
                # So something went wrong somewhere while processing this file entry - log that and continue
                self._logger.exception(f"Error while processing entry {path}")

                return None, metadata_dirty

        except FileNotFoundError:
            # it might have gotten deleted while we were processing this - handle this gracefully
            return None, False

    @staticmethod
    def _get_total_size(nodes: dict[str, dict]) -> int:
        total_size = 0
        for node in nodes.values():
            if "size" in node:
                total_size += node["size"]
        return total_size

    def _enrich_folder(self, folder: StorageFolder, force_refresh: bool = False) -> dict:
        assert isinstance(folder, StorageFolder)

        path = folder.path
        path_on_disk = self.path_on_disk(path)

        # make a copy...
        folder = StorageFolder(
            name=folder.name,
            display=folder.display,
            origin=self.storage,
            path=folder.path,
            date=folder.date,
            size=folder.size,
        )

        # ... then enrich that
        folder.children = self._list_folder(
            path_on_disk, base=path + "/", force_refresh=force_refresh
        )
        folder.size = self.get_size(path_on_disk)

        return folder

    def _enrich_folders(
        self, nodes: dict[str, StorageEntry], force_refresh: bool = False
    ) -> dict[str, dict]:
        enriched = {}
        for key, value in nodes.items():
            if isinstance(value, StorageFolder):
                enriched[key] = self._enrich_folder(value, force_refresh=force_refresh)
            else:
                enriched[key] = value
        return enriched

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

    def _get_thumbnails(self, path: str, name: str) -> dict[str, str]:
        thumbnail_path = os.path.join(path, self.THUMBNAIL_DIR)

        if not os.path.exists(thumbnail_path):
            return {}

        result = {}
        for item in os.listdir(thumbnail_path):
            if item.startswith(f"{name}.") and item.endswith(".png"):
                # format is <name>.<sizehint>.png
                sizehint = item[len(name) + 1 : -len(".png")]
                result[sizehint] = os.path.join(thumbnail_path, item)

        def to_area(hint: str) -> int:
            x, y = map(int, hint.split("x"))
            return x * y

        sorted_result = {}
        for sizehint in sorted(result.keys(), key=to_area, reverse=True):
            sorted_result[sizehint] = result[sizehint]
        return sorted_result

    def _extract_thumbnails(self, path: str) -> None:
        folder, name = self.sanitize(path)

        thumbnails = gtt.extract_thumbnail_bytes_from_gcode_file(
            os.path.join(folder, name)
        )
        if not thumbnails:
            return

        thumbnail_path = os.path.join(folder, self.THUMBNAIL_DIR)
        if not os.path.exists(thumbnail_path):
            os.makedirs(thumbnail_path)
        for sizehint, data in thumbnails.images.items():
            output_name = f"{name}.{sizehint}.png"
            output_path = os.path.join(thumbnail_path, output_name)
            with open(output_path, mode="wb") as f:
                f.write(data)
            self._logger.debug(f"Extracted thumbnail {output_name} from {path}")

    def _remove_thumbnails(self, path: str, name: str) -> None:
        path = self.sanitize_path(path)
        thumbnail_path = os.path.join(path, self.THUMBNAIL_DIR)

        if not os.path.exists(thumbnail_path):
            # nothing to do
            return

        for item in os.listdir(thumbnail_path):
            if item.startswith(f"{name}.") and item.endswith(".png"):
                try:
                    os.remove(os.path.join(thumbnail_path, item))
                except Exception:
                    self._logger.exception(
                        f"Error deleting thumbnail {item} of {path}/{name}"
                    )

    def _copy_thumbnails(
        self,
        src_path: str,
        src_name: str,
        dst_path: str,
        dst_name: str,
        delete_source: bool = False,
    ) -> None:
        src_path = self.sanitize_path(src_path)
        dst_path = self.sanitize_path(dst_path)

        src_thumbnail_path = os.path.join(src_path, self.THUMBNAIL_DIR)
        if not os.path.exists(src_thumbnail_path):
            # nothing to do
            return

        dst_thumbnail_path = os.path.join(dst_path, self.THUMBNAIL_DIR)

        for item in os.listdir(src_thumbnail_path):
            if item.startswith(f"{src_name}.") and item.endswith(".png"):
                # found one!
                _, sizehint = item[: -len(".png")].rsplit(".", maxsplit=1)

                if not os.path.exists(dst_thumbnail_path):
                    os.makedirs(dst_thumbnail_path)

                src = os.path.join(src_thumbnail_path, item)
                dst = os.path.join(dst_thumbnail_path, f"{dst_name}.{sizehint}.png")

                try:
                    if delete_source:
                        shutil.move(src, dst)
                    else:
                        shutil.copy2(src, dst)
                except Exception:
                    self._logger.exception("Error copying/moving {src} to {dst}")

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
                self._update_last_activity()
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
                        self._update_last_activity()
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
