__author__ = "Gina Häußge <gina@octoprint.org>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


from typing import IO, TYPE_CHECKING, Any, Optional

from octoprint.filemanager.util import AbstractFileWrapper
from octoprint.schema import BaseModel
from octoprint.util import deprecated

if TYPE_CHECKING:
    from octoprint.printer.job import PrintJob  # noqa: F401


class StorageCapabilities(BaseModel):
    write_file: bool = False
    read_file: bool = False
    remove_file: bool = False
    copy_file: bool = False
    move_file: bool = False

    add_folder: bool = False
    remove_folder: bool = False
    copy_folder: bool = False
    move_folder: bool = False

    metadata: bool = False
    history: bool = False
    thumbnails: bool = False

    path_on_disk: bool = False


class HistoryEntry(BaseModel):
    timestamp: float
    success: bool
    printerProfile: str
    printTime: Optional[float] = None


class AnalysisVolume(BaseModel):
    minX: float
    minY: float
    minZ: float
    maxX: float
    maxY: float
    maxZ: float


class AnalysisDimensions(BaseModel):
    width: float
    height: float
    depth: float


class AnalysisFilamentUse(BaseModel):
    length: Optional[float] = None
    volume: Optional[float] = None
    weight: Optional[float] = None


class AnalysisResult(BaseModel):
    printingArea: Optional[AnalysisVolume] = None
    dimensions: Optional[AnalysisDimensions] = None
    travelArea: Optional[AnalysisVolume] = None
    travelDimensions: Optional[AnalysisDimensions] = None
    estimatedPrintTime: Optional[float] = None
    filament: dict[str, AnalysisFilamentUse] = {}
    additional: Optional[dict[str, Any]] = {}


class Statistics(BaseModel):
    averagePrintTime: dict[str, float] = {}
    lastPrintTime: dict[str, float] = {}


class MetadataEntry(BaseModel):
    analysis: Optional[AnalysisResult] = None
    history: list[HistoryEntry] = []
    statistics: Optional[Statistics] = None
    additional: dict[str, Any] = {}


class StorageEntry(BaseModel):
    name: str
    display: str
    origin: str
    path: str
    user: Optional[str] = None

    date: Optional[int] = None
    size: Optional[int] = None

    entry_type: str
    type_path: list[str]


class StorageFile(StorageEntry):
    metadata: Optional[MetadataEntry] = None
    thumbnails: list[str] = []


class StorageFolder(StorageEntry):
    children: dict[str, StorageEntry] = {}

    entry_type: str = "folder"
    type_path: list[str] = ["folder"]


class StorageThumbnail(BaseModel):
    name: str
    printable: str
    sizehint: str
    mime: str = "application/octet-stream"
    size: int = -1
    last_modified: int = -1


class StorageMeta(BaseModel):
    key: str
    name: str
    capabilities: StorageCapabilities


class StorageInterface:
    """
    Interface of storage adapters for OctoPrint.
    """

    storage = "dummy"
    name = "Dummy"
    capabilities = StorageCapabilities()

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

    def get_hash(self, path: str = None, recursive: bool = False) -> str:
        """
        Get a hash corresponding to the current state of the specified ``path`` or ``path``'s subtree.

        Args:
            path (str or None): Path for which to determine the hash. If left out or set to None, defaults to
                the storage root.
            recursive (bool): Whether to determine only the date of the specified ``path`` (False, default) or
                the whole ``path``'s subtree (True).
        """
        raise NotImplementedError()

    @deprecated(
        "last_modified has been deprecated in favor of get_lastmodified", since="1.12.0"
    )
    def last_modified(self, *args, **kwargs):
        return self.get_lastmodified(*args, **kwargs)

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

    def get_storage_entry(self, path: str) -> StorageEntry:
        if "/" in path:
            folder, name = path.rsplit("/", 1)
        else:
            folder = None
            name = path

        entries = self.list_storage_entries(path=folder, recursive=False, level=1)
        return entries.get(name)

    def list_storage_entries(
        self,
        path: str = None,
        filter: callable = None,
        recursive: bool = True,
        level: int = 0,
        force_refresh: bool = False,
    ) -> dict[str, StorageEntry]:
        """ """
        raise NotImplementedError()

    @deprecated(
        "get_file has been deprecated in favor of get_storage_entry", since="1.12.0"
    )
    def get_file(self, path: str) -> dict:
        entry = self.get_storage_entry(path)
        if entry is None:
            return None

        return self._convert_storage_entry_to_dict(entry)

    @deprecated(
        "list_files has been deprecated in favor of list_storage_entries", since="1.12.0"
    )
    def list_files(
        self,
        path: str = None,
        filter: callable = None,
        recursive: bool = True,
        level: int = 0,
        force_refresh: bool = False,
    ) -> dict[str, dict]:
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
        if filter is not None:
            wrapped_filter = filter
            filter = lambda node: wrapped_filter(
                self._convert_storage_entry_to_dict(node)
            )

        tree = self.list_storage_entries(
            path=path,
            filter=filter,
            recursive=recursive,
            force_refresh=force_refresh,
            level=level,
        )
        return {k: self._convert_storage_entry_to_dict(v) for k, v in tree.items()}

    def add_folder(self, path, ignore_existing=True, display=None, user=None) -> str:
        """
        Adds a folder as ``path``

        The ``path`` will be sanitized.

        :param string path:          the path of the new folder
        :param bool ignore_existing: if set to True, no error will be raised if the folder to be added already exists
        :param str display:          display name of the folder
        :param str user:             user who created the folder, if known
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

    def copy_folder(self, source, destination) -> str:
        """
        Copies the folder ``source`` to ``destination``

        :param string source: path to the source folder
        :param string destination: path to destination

        :return: the path in the storage to the copy of the folder
        """
        raise NotImplementedError()

    def move_folder(self, source, destination) -> str:
        """
        Moves the folder ``source`` to ``destination``

        :param string source: path to the source folder
        :param string destination: path to destination

        :return: the new path in the storage to the folder
        """
        raise NotImplementedError()

    def add_file(
        self,
        path: str,
        data: AbstractFileWrapper,
        allow_overwrite: bool = False,
        display: str = None,
        user: str = None,
        progress_callback: callable = None,
        *args,
        **kwargs,
    ) -> str:
        """
        Adds the file ``file_object`` as ``path``

        Arguments:
          path(str): the file's new path, will be sanitized
          data(AbstractFileWrapper): a file object to save as the file's contents
          allow_overwrite(bool): if the file already exists and this is set, an error will be raised
          display(str): display name of the file
          user(str): user who added the file, if known
          progress_callback(callable): callback to send progress information to

        Returns:
          (str) the new filename
        """
        raise NotImplementedError()

    def read_file(self, path: str) -> IO:
        """
        Returns an IO object to read the contents of the file.
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

    def copy_file(self, source, destination) -> str:
        """
        Copies the file ``source`` to ``destination``

        :param string source: path to the source file
        :param string destination: path to destination

        :return: the path in the storage to the copy of the file
        """
        raise NotImplementedError()

    def move_file(self, source, destination) -> str:
        """
        Moves the file ``source`` to ``destination``

        :param string source: path to the source file
        :param string destination: path to destination

        :return: the new path in the storage to the file
        """
        raise NotImplementedError()

    def has_analysis(self, path) -> bool:
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

    @deprecated(
        "add_link has been deprecated and will be removed in a future version",
        since="1.12.0",
    )
    def add_link(self, path, rel, data):
        pass

    @deprecated(
        "add_link has been deprecated and will be removed in a future version",
        since="1.12.0",
    )
    def remove_link(self, path, rel, data):
        pass

    def add_history(self, path, data):
        raise NotImplementedError()

    def update_history(self, path, index, data):
        raise NotImplementedError()

    def remove_history(self, path, index):
        raise NotImplementedError()

    def has_thumbnail(self, path: str) -> bool:
        raise NotImplementedError()

    def get_thumbnail(
        self, path: str, sizehint: str = None
    ) -> Optional[StorageThumbnail]:
        raise NotImplementedError()

    def read_thumbnail(self, path: str, sizehint: str = None) -> Optional[IO]:
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

    def create_job(self, path, owner: str = None, params: dict = None) -> "PrintJob":
        from octoprint.printer.job import DurationEstimate, FilamentEstimate, PrintJob

        entry = self.get_storage_entry(path)
        if not isinstance(entry, StorageFile):
            raise ValueError(f"{self.storage}:{path} is not a file, can't create job")

        path_on_disk = None
        if self.capabilities.path_on_disk:
            path_on_disk = self.path_on_disk(path)

        duration_estimate = None
        filament_estimate = {}

        if entry.metadata and entry.metadata.analysis:
            if entry.metadata.analysis.estimatedPrintTime:
                duration_estimate = DurationEstimate(
                    estimate=entry.metadata.analysis.estimatedPrintTime, source="analysis"
                )
            if entry.metadata.analysis.filament:
                filament_estimate = {
                    k: FilamentEstimate(length=v.length, volume=v.volume, weight=v.weight)
                    for k, v in entry.metadata.analysis.filament.items()
                }

        return PrintJob(
            storage=self.storage,
            path=entry.path,
            display=entry.display,
            size=entry.size,
            date=entry.date,
            owner=owner,
            duration_estimate=duration_estimate,
            filament_estimate=filament_estimate,
            path_on_disk=path_on_disk,
            params=params,
        )

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

    def _convert_storage_entry_to_dict(self, entry: StorageEntry) -> dict:
        """Converts StorageEntry tree to legacy dict structure"""
        if isinstance(entry, StorageFolder):
            result = entry.model_dump(by_alias=True)
            result["children"] = {
                k: self._convert_storage_entry_to_dict(v)
                for k, v in entry.children.items()
            }

            result["type"] = result["entry_type"]
            del result["entry_type"]

            result["typePath"] = result["type_path"]
            del result["type_path"]

            return result

        elif isinstance(entry, StorageFile):
            result = entry.model_dump(by_alias=True)
            if "metadata" in result and result["metadata"]:
                result.update(**result["metadata"])
                del result["metadata"]

            result["type"] = result["entry_type"]
            del result["entry_type"]

            result["typePath"] = result["type_path"]
            del result["type_path"]

            return result

        else:
            return {}


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
    UNSUPPORTED = "unsupported"

    def __init__(self, message, code=None, cause=None):
        Exception.__init__(self, message)
        self.cause = cause

        if code is None:
            code = StorageError.UNKNOWN
        self.code = code
