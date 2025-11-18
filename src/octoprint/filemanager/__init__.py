__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import os
import time
from collections import namedtuple
from typing import IO, TYPE_CHECKING, Callable, Optional

import octoprint.plugin
import octoprint.util
from octoprint.events import Events, eventManager
from octoprint.util import deprecated, yaml
from octoprint.util import get_fully_qualified_classname as fqcn

from .analysis import AnalysisQueue, QueueEntry  # noqa: F401
from .destinations import FileDestinations  # noqa: F401
from .storage import (
    StorageCapabilities,
    StorageEntry,
    StorageError,
    StorageInterface,
    StorageMeta,
    StorageThumbnail,
)
from .storage.local import LocalFileStorage  # noqa: F401
from .util import AbstractFileWrapper, DiskFileWrapper, StreamWrapper  # noqa: F401

if TYPE_CHECKING:
    from octoprint.printer.job import PrintJob  # noqa: F401


ContentTypeMapping = namedtuple("ContentTypeMapping", "extensions, content_type")
ContentTypeDetector = namedtuple("ContentTypeDetector", "extensions, detector")

extensions = {}


def full_extension_tree():
    result = {
        "machinecode": {
            "gcode": ContentTypeMapping(["gcode", "gco", "g", "gc~"], "text/plain")
        }
    }

    def leaf_merger(a, b):
        supported_leaf_types = (ContentTypeMapping, ContentTypeDetector, list)
        if not isinstance(a, supported_leaf_types) or not isinstance(
            b, supported_leaf_types
        ):
            raise ValueError()

        if isinstance(a, ContentTypeDetector) and isinstance(b, ContentTypeMapping):
            raise ValueError()

        if isinstance(a, ContentTypeMapping) and isinstance(b, ContentTypeDetector):
            raise ValueError()

        a_list = a if isinstance(a, list) else a.extensions
        b_list = b if isinstance(b, list) else b.extensions
        merged = a_list + b_list

        content_type = None
        if isinstance(b, ContentTypeMapping):
            content_type = b.content_type
        elif isinstance(a, ContentTypeMapping):
            content_type = a.content_type

        detector = None
        if isinstance(b, ContentTypeDetector):
            detector = b.detector
        elif isinstance(a, ContentTypeDetector):
            detector = a.detector

        if content_type is not None:
            return ContentTypeMapping(merged, content_type)
        elif detector is not None:
            return ContentTypeDetector(merged, detector)
        else:
            return merged

    slicer_plugins = octoprint.plugin.plugin_manager().get_implementations(
        octoprint.plugin.SlicerPlugin
    )
    for plugin in slicer_plugins:
        try:
            plugin_result = plugin.get_slicer_extension_tree()
            if plugin_result is None or not isinstance(plugin_result, dict):
                continue
            octoprint.util.dict_merge(
                result, plugin_result, leaf_merger=leaf_merger, in_place=True
            )
        except Exception:
            logging.getLogger(__name__).exception(
                "Exception while retrieving additional extension "
                "tree entries from SlicerPlugin {name}".format(name=plugin._identifier),
                extra={"plugin": plugin._identifier},
            )

    extension_tree_hooks = octoprint.plugin.plugin_manager().get_hooks(
        "octoprint.filemanager.extension_tree"
    )
    for name, hook in extension_tree_hooks.items():
        try:
            hook_result = hook()
            if hook_result is None or not isinstance(hook_result, dict):
                continue
            result = octoprint.util.dict_merge(
                result, hook_result, leaf_merger=leaf_merger, in_place=True
            )
        except Exception:
            logging.getLogger(__name__).exception(
                "Exception while retrieving additional extension "
                "tree entries from hook {name}".format(name=name),
                extra={"plugin": name},
            )

    return result


def get_extensions(type, subtree=None):
    if subtree is None:
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
    if subtree is None:
        subtree = full_extension_tree()

    result = []
    if isinstance(subtree, dict):
        for value in subtree.values():
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
    if subtree is None:
        subtree = full_extension_tree()

    for key, value in subtree.items():
        if (
            isinstance(value, (ContentTypeMapping, ContentTypeDetector))
            and extension in value.extensions
        ):
            return [key]
        elif isinstance(value, (list, tuple)) and extension in value:
            return [key]
        elif isinstance(value, dict):
            path = get_path_for_extension(extension, subtree=value)
            if path:
                return [key] + path

    return None


def get_content_type_mapping_for_extension(extension, subtree=None):
    if subtree is None:
        subtree = full_extension_tree()

    for value in subtree.values():
        content_extension_matches = (
            isinstance(value, (ContentTypeMapping, ContentTypeDetector))
            and extension in value.extensions
        )
        list_extension_matches = isinstance(value, (list, tuple)) and extension in value

        if content_extension_matches or list_extension_matches:
            return value
        elif isinstance(value, dict):
            result = get_content_type_mapping_for_extension(extension, subtree=value)
            if result is not None:
                return result

    return None


def valid_extension(extension, type=None, tree=None):
    if not type:
        return extension in get_all_extensions(subtree=tree)
    else:
        extensions = get_extensions(type, subtree=tree)
        if extensions:
            return extension in extensions


def valid_file_type(filename, type=None, tree=None):
    parts = filename.split(".")

    for x in range(len(parts) - 1):
        extension = ".".join(parts[-(x + 1) :]).lower()
        if valid_extension(extension, type=type, tree=tree):
            return True

    return False


def get_file_type(filename):
    parts = filename.split(".")

    for x in range(len(parts) - 1):
        extension = ".".join(parts[-(x + 1) :]).lower()
        path = get_path_for_extension(extension)
        if path:
            return path

    return None


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


class FileManager:
    def __init__(
        self,
        analysis_queue,
        slicing_manager,
        printer_profile_manager,
        initial_storage_managers=None,
    ):
        self._logger = logging.getLogger(__name__)
        self._analysis_queue = analysis_queue
        self._analysis_queue.register_finish_callback(self._on_analysis_finished)

        self._storage_managers: dict[str, StorageInterface] = {}
        if initial_storage_managers:
            self._storage_managers.update(initial_storage_managers)

        self._slicing_manager = slicing_manager
        self._printer_profile_manager = printer_profile_manager

        import threading

        self._slicing_jobs = {}
        self._slicing_jobs_mutex = threading.Lock()

        self._slicing_progress_callbacks = []
        self._last_slicing_progress = None

        self._progress_plugins = []
        self._preprocessor_hooks = {}

        import octoprint.settings

        self._recovery_file = os.path.join(
            octoprint.settings.settings().getBaseFolder("data"),
            "print_recovery_data.yaml",
        )
        self._analyzeGcode = octoprint.settings.settings().get(["gcodeAnalysis", "runAt"])

    def initialize(self, process_backlog=False):
        self.reload_plugins()
        if process_backlog:
            self.process_backlog()

    def process_backlog(self):
        # only check for a backlog if gcodeAnalysis is 'idle' or 'always'
        if self._analyzeGcode == "never":
            return

        def worker():
            self._logger.info(
                "Adding backlog items from all storage types to analysis queue..."
            )
            for storage_type, storage_manager in self._storage_managers.items():
                self._determine_analysis_backlog(storage_type, storage_manager)

        import threading

        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()

    def reload_plugins(self):
        self._progress_plugins = octoprint.plugin.plugin_manager().get_implementations(
            octoprint.plugin.ProgressPlugin
        )
        self._preprocessor_hooks = octoprint.plugin.plugin_manager().get_hooks(
            "octoprint.filemanager.preprocessor"
        )

    def register_slicingprogress_callback(self, callback):
        self._slicing_progress_callbacks.append(callback)

    def unregister_slicingprogress_callback(self, callback):
        try:
            self._slicing_progress_callbacks.remove(callback)
        except ValueError:
            # callback was not registered
            pass

    def _determine_analysis_backlog(
        self, storage_type, storage_manager, root=None, high_priority=False
    ):
        counter = 0

        backlog_generator = storage_manager.analysis_backlog
        if root is not None:
            backlog_generator = storage_manager.analysis_backlog_for_path(path=root)

        for entry, path, _ in backlog_generator:
            file_type = get_file_type(path)[-1]
            file_name = storage_manager.split_path(path)

            # we'll use the default printer profile for the backlog since we don't know better
            queue_entry = QueueEntry(
                file_name,
                entry,
                file_type,
                storage_type,
                path,
                self._printer_profile_manager.get_default(),
                None,
            )
            if self._analysis_queue.enqueue(queue_entry, high_priority=high_priority):
                counter += 1

        if root:
            self._logger.info(
                f'Added {counter} items from storage type "{storage_type}" and root "{root}" to analysis queue'
            )
        else:
            self._logger.info(
                f'Added {counter} items from storage type "{storage_type}" to analysis queue'
            )

    def add_storage(self, storage_type, storage_manager):
        self._storage_managers[storage_type] = storage_manager
        self._determine_analysis_backlog(storage_type, storage_manager)
        self._logger.info(f"Added storage manager for {storage_type}")

    def remove_storage(self, storage_type):
        try:
            del self._storage_managers[storage_type]
            self._logger.info(f"Removed storage manager for {storage_type}")
        except KeyError:
            pass

    @property
    def registered_storages(self):
        return list(self._storage_managers.keys())

    @property
    def registered_storage_meta(self) -> dict[str:StorageMeta]:
        return {
            key: StorageMeta(
                key=key, name=storage.name, capabilities=storage.capabilities
            )
            for key, storage in self._storage_managers.items()
        }

    @property
    def slicing_enabled(self):
        return self._slicing_manager.slicing_enabled

    @property
    def registered_slicers(self):
        return self._slicing_manager.registered_slicers

    @property
    def default_slicer(self):
        return self._slicing_manager.default_slicer

    def analyse(self, destination, path, printer_profile_id=None):
        if not self.file_exists(destination, path):
            return

        if printer_profile_id is None:
            printer_profile = self._printer_profile_manager.get_current_or_default()
        else:
            printer_profile = self._printer_profile_manager.get(printer_profile_id)
            if printer_profile is None:
                printer_profile = self._printer_profile_manager.get_current_or_default()

        queue_entry = self._analysis_queue_entry(destination, path)
        self._analysis_queue.dequeue(queue_entry)

        queue_entry = self._analysis_queue_entry(
            destination, path, printer_profile=printer_profile
        )
        if queue_entry:
            return self._analysis_queue.enqueue(queue_entry, high_priority=True)

        return False

    def slice(
        self,
        slicer_name,
        source_location,
        source_path,
        dest_location,
        dest_path,
        position=None,
        profile=None,
        printer_profile_id=None,
        overrides=None,
        display=None,
        callback=None,
        callback_args=None,
    ):
        absolute_source_path = self.path_on_disk(source_location, source_path)

        def stlProcessed(
            source_location,
            source_path,
            tmp_path,
            dest_location,
            dest_path,
            start_time,
            printer_profile_id,
            callback,
            callback_args,
            _error=None,
            _cancelled=False,
            _analysis=None,
        ):
            try:
                if _error:
                    eventManager().fire(
                        Events.SLICING_FAILED,
                        {
                            "slicer": slicer_name,
                            "stl": source_path,
                            "stl_location": source_location,
                            "gcode": dest_path,
                            "gcode_location": dest_location,
                            "reason": _error,
                        },
                    )
                elif _cancelled:
                    eventManager().fire(
                        Events.SLICING_CANCELLED,
                        {
                            "slicer": slicer_name,
                            "stl": source_path,
                            "stl_location": source_location,
                            "gcode": dest_path,
                            "gcode_location": dest_location,
                        },
                    )
                else:
                    source_meta = self.get_metadata(source_location, source_path)
                    hash = source_meta.get("hash", "n/a")

                    import io

                    links = [("model", {"name": source_path})]
                    _, stl_name = self.split_path(source_location, source_path)
                    file_obj = StreamWrapper(
                        os.path.basename(dest_path),
                        io.BytesIO(
                            f";Generated from {stl_name} (hash: {hash})\n".encode(
                                "ascii", "replace"
                            )
                        ),
                        io.FileIO(tmp_path, "rb"),
                    )

                    printer_profile = self._printer_profile_manager.get(
                        printer_profile_id
                    )
                    self.add_file(
                        dest_location,
                        dest_path,
                        file_obj,
                        display=display,
                        links=links,
                        allow_overwrite=True,
                        printer_profile=printer_profile,
                        analysis=_analysis,
                    )

                    end_time = time.monotonic()
                    eventManager().fire(
                        Events.SLICING_DONE,
                        {
                            "slicer": slicer_name,
                            "stl": source_path,
                            "stl_location": source_location,
                            "gcode": dest_path,
                            "gcode_location": dest_location,
                            "time": end_time - start_time,
                        },
                    )

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

        start_time = time.monotonic()
        eventManager().fire(
            Events.SLICING_STARTED,
            {
                "slicer": slicer_name,
                "stl": source_path,
                "stl_location": source_location,
                "gcode": dest_path,
                "gcode_location": dest_location,
                "progressAvailable": (
                    slicer.get_slicer_properties().get("progress_report", False)
                    if slicer
                    else False
                ),
            },
        )

        import tempfile

        f = tempfile.NamedTemporaryFile(suffix=".gco", delete=False)
        temp_path = f.name
        f.close()

        with self._slicing_jobs_mutex:
            source_job_key = (source_location, source_path)
            dest_job_key = (dest_location, dest_path)
            if dest_job_key in self._slicing_jobs:
                (
                    job_slicer_name,
                    job_absolute_source_path,
                    job_temp_path,
                ) = self._slicing_jobs[dest_job_key]

                self._slicing_manager.cancel_slicing(
                    job_slicer_name, job_absolute_source_path, job_temp_path
                )
                del self._slicing_jobs[dest_job_key]

            self._slicing_jobs[dest_job_key] = self._slicing_jobs[source_job_key] = (
                slicer_name,
                absolute_source_path,
                temp_path,
            )

        args = (
            source_location,
            source_path,
            temp_path,
            dest_location,
            dest_path,
            start_time,
            printer_profile_id,
            callback,
            callback_args,
        )
        self._slicing_manager.slice(
            slicer_name,
            absolute_source_path,
            temp_path,
            profile,
            stlProcessed,
            position=position,
            callback_args=args,
            overrides=overrides,
            printer_profile_id=printer_profile_id,
            on_progress=self.on_slicing_progress,
            on_progress_args=(
                slicer_name,
                source_location,
                source_path,
                dest_location,
                dest_path,
            ),
        )

    def on_slicing_progress(
        self,
        slicer,
        source_location,
        source_path,
        dest_location,
        dest_path,
        _progress=None,
    ):
        if not _progress:
            return

        progress_int = int(_progress * 100)
        if self._last_slicing_progress != progress_int:
            self._last_slicing_progress = progress_int
            for callback in self._slicing_progress_callbacks:
                try:
                    callback.sendSlicingProgress(
                        slicer,
                        source_location,
                        source_path,
                        dest_location,
                        dest_path,
                        progress_int,
                    )
                except Exception:
                    self._logger.exception(
                        "Exception while pushing slicing progress",
                        extra={"callback": fqcn(callback)},
                    )

            if progress_int:

                def call_plugins(
                    slicer,
                    source_location,
                    source_path,
                    dest_location,
                    dest_path,
                    progress,
                ):
                    for plugin in self._progress_plugins:
                        try:
                            plugin.on_slicing_progress(
                                slicer,
                                source_location,
                                source_path,
                                dest_location,
                                dest_path,
                                progress,
                            )
                        except Exception:
                            self._logger.exception(
                                "Exception while sending slicing progress to plugin %s"
                                % plugin._identifier,
                                extra={"plugin": plugin._identifier},
                            )

                import threading

                thread = threading.Thread(
                    target=call_plugins,
                    args=(
                        slicer,
                        source_location,
                        source_path,
                        dest_location,
                        dest_path,
                        progress_int,
                    ),
                )
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

    @deprecated(
        "list_files has been deprecated in favor of list_storage_entries", since="1.12.0"
    )
    def list_files(
        self,
        locations=None,
        path=None,
        filter=None,
        recursive=None,
        level=0,
        force_refresh=False,
    ):
        if not locations:
            locations = list(self._storage_managers.keys())
        if isinstance(locations, str):
            locations = [locations]

        result = {}
        for loc in locations:
            try:
                result[loc] = self._storage(loc).list_files(
                    path=path,
                    filter=filter,
                    recursive=recursive,
                    level=level,
                    force_refresh=force_refresh,
                )
            except NoSuchStorage:
                # unknown loc, we ignore this, it probably just got unregistered
                result[loc] = {}
            except Exception:
                self._logger.exception(f"Error while listing files for {loc}")
        return result

    @deprecated(
        "get_file has been deprecated in favor of get_storage_entry", since="1.12.0"
    )
    def get_file(self, location: str, path: str) -> dict:
        return self._storage(location).get_file(path)

    def list_storage_entries(
        self,
        locations: list[str] = None,
        path: str = None,
        filter: callable = None,
        recursive: bool = True,
        level: int = 0,
        force_refresh: bool = False,
    ) -> dict[str, dict[str, StorageEntry]]:
        if not locations:
            locations = list(self._storage_managers.keys())
        if isinstance(locations, str):
            locations = [locations]

        result = {}
        for loc in locations:
            try:
                result[loc] = self._storage(loc).list_storage_entries(
                    path=path,
                    filter=filter,
                    recursive=recursive,
                    level=level,
                    force_refresh=force_refresh,
                )
            except NoSuchStorage:
                # unknown loc, we ignore this, it probably just got unregistered
                pass
            except Exception:
                self._logger.exception(f"Error while fetching storage entries for {loc}")
        return result

    def get_storage_entry(self, storage: str, path: str) -> StorageEntry:
        path = self.path_in_storage(storage, path)

        return self._storage(storage).get_storage_entry(path)

    def add_file(
        self,
        location: str,
        path: str,
        file_object: AbstractFileWrapper,
        allow_overwrite: bool = False,
        printer_profile=None,
        analysis=None,
        display: str = None,
        user: str = None,
        progress_callback: callable = None,
        *args,
        **kwargs,
    ):
        if not self._storage(location).capabilities.write_file:
            raise StorageError(
                f"Storage {location} does not support adding files",
                code=StorageError.UNSUPPORTED,
            )

        if printer_profile is None:
            printer_profile = self._printer_profile_manager.get_current_or_default()

        path_in_storage = self._storage(location).path_in_storage(path)

        for name, hook in self._preprocessor_hooks.items():
            try:
                hook_file_object = hook(
                    path_in_storage,
                    file_object,
                    printer_profile=printer_profile,
                    allow_overwrite=allow_overwrite,
                )
            except Exception:
                self._logger.exception(
                    "Error when calling preprocessor hook for plugin {}, ignoring".format(
                        name
                    ),
                    extra={"plugin": name},
                )
                continue

            if hook_file_object is not None:
                file_object = hook_file_object

        queue_entry = self._analysis_queue_entry(location, path_in_storage)
        if queue_entry is not None:
            self._analysis_queue.dequeue(queue_entry)

        path_in_storage = self._storage(location).add_file(
            path_in_storage,
            file_object,
            allow_overwrite=allow_overwrite,
            display=display,
            user=user,
            progress_callback=progress_callback,
        )

        queue_entry = self._analysis_queue_entry(
            location,
            path_in_storage,
            printer_profile=printer_profile,
            analysis=analysis,
        )
        if queue_entry:
            self._analysis_queue.enqueue(queue_entry, high_priority=True)

        _, name = self._storage(location).split_path(path_in_storage)
        eventManager().fire(
            Events.FILE_ADDED,
            {
                "storage": location,
                "path": path_in_storage,
                "name": name,
                "type": get_file_type(name),
                "operation": "add",
            },
        )
        eventManager().fire(Events.UPDATED_FILES, {"type": "printables"})
        return path_in_storage

    def read_file(self, storage: str, path: str) -> IO:
        if not self._storage(storage).capabilities.read_file:
            raise StorageError(
                f"Reading files from {storage} is not supported",
                code=StorageError.UNSUPPORTED,
            )

        if not self.file_exists(storage, path):
            raise StorageError(
                f"File {path} cannot be found on {storage}",
                code=StorageError.DOES_NOT_EXIST,
            )

        return self._storage(storage).read_file(path)

    def remove_file(self, location, path):
        path_in_storage = self._storage(location).path_in_storage(path)
        queue_entry = self._analysis_queue_entry(location, path_in_storage)
        self._analysis_queue.dequeue(queue_entry)
        self._storage(location).remove_file(path_in_storage)

        _, name = self._storage(location).split_path(path_in_storage)
        eventManager().fire(
            Events.FILE_REMOVED,
            {
                "storage": location,
                "path": path,
                "name": name,
                "type": get_file_type(name),
                "operation": "remove",
            },
        )
        eventManager().fire(Events.UPDATED_FILES, {"type": "printables"})

    def copy_file(self, storage, source, destination):
        if not self._storage(storage).capabilities.copy_file:
            raise StorageError(
                f"File copy on {storage} is not supported", code=StorageError.UNSUPPORTED
            )

        path_in_storage = self._storage(storage).copy_file(source, destination)
        if not self.has_analysis(storage, path_in_storage):
            queue_entry = self._analysis_queue_entry(storage, path_in_storage)
            if queue_entry:
                self._analysis_queue.enqueue(queue_entry)

        _, name = self._storage(storage).split_path(path_in_storage)
        eventManager().fire(
            Events.FILE_ADDED,
            {
                "storage": storage,
                "path": path_in_storage,
                "name": name,
                "type": get_file_type(name),
                "operation": "copy",
            },
        )
        eventManager().fire(Events.UPDATED_FILES, {"type": "printables"})

    def move_file(self, storage, source, destination):
        source_in_storage = self._storage(storage).path_in_storage(source)
        destination_in_storage = self._storage(storage).path_in_storage(destination)

        queue_entry = self._analysis_queue_entry(storage, source_in_storage)
        self._analysis_queue.dequeue(queue_entry)
        path = self._storage(storage).move_file(source_in_storage, destination_in_storage)
        if not self.has_analysis(storage, path):
            queue_entry = self._analysis_queue_entry(storage, path)
            if queue_entry:
                self._analysis_queue.enqueue(queue_entry)

        _, source_name = self._storage(storage).split_path(source_in_storage)
        _, destination_name = self._storage(storage).split_path(destination_in_storage)

        eventManager().fire(
            Events.FILE_REMOVED,
            {
                "storage": storage,
                "path": source_in_storage,
                "name": source_name,
                "type": get_file_type(source_name),
                "operation": "move",
            },
        )
        eventManager().fire(
            Events.FILE_ADDED,
            {
                "storage": storage,
                "path": destination_in_storage,
                "name": destination_name,
                "type": get_file_type(destination_name),
                "operation": "move",
            },
        )
        eventManager().fire(
            Events.FILE_MOVED,
            {
                "source_storage": storage,
                "source_path": source_in_storage,
                "source_name": source_name,
                "source_type": get_file_type(source_name),
                "destination_storage": storage,
                "destination_path": destination_in_storage,
                "destination_name": destination_name,
                "destination_type": get_file_type(destination_name),
                # backwards compatibility
                "storage": storage,
            },
        )

        eventManager().fire(Events.UPDATED_FILES, {"type": "printables"})

    def add_folder(self, storage, path, ignore_existing=True, display=None, user=None):
        path_in_storage = self._storage(storage).add_folder(
            path, ignore_existing=ignore_existing, display=display, user=user
        )

        _, name = self._storage(storage).split_path(path_in_storage)
        eventManager().fire(
            Events.FOLDER_ADDED,
            {"storage": storage, "path": path_in_storage, "name": name},
        )
        eventManager().fire(Events.UPDATED_FILES, {"type": "printables"})
        return path_in_storage

    def remove_folder(self, storage, path, recursive=True):
        path_in_storage = self._storage(storage).path_in_storage(path)

        self._analysis_queue.dequeue_folder(storage, path_in_storage)
        self._analysis_queue.pause()
        self._storage(storage).remove_folder(path_in_storage, recursive=recursive)
        self._analysis_queue.resume()

        _, name = self._storage(storage).split_path(path_in_storage)
        eventManager().fire(
            Events.FOLDER_REMOVED,
            {"storage": storage, "path": path_in_storage, "name": name},
        )
        eventManager().fire(Events.UPDATED_FILES, {"type": "printables"})

    def copy_folder(self, storage, source, destination):
        path_in_storage = self._storage(storage).copy_folder(source, destination)
        self._determine_analysis_backlog(
            storage, self._storage(storage), root=path_in_storage
        )

        _, name = self._storage(storage).split_path(path_in_storage)
        eventManager().fire(
            Events.FOLDER_ADDED,
            {"storage": storage, "path": path_in_storage, "name": name},
        )
        eventManager().fire(Events.UPDATED_FILES, {"type": "printables"})

    def move_folder(self, storage, source, destination):
        source_in_storage = self._storage(storage).path_in_storage(source)
        destination_in_storage = self._storage(storage).path_in_storage(destination)

        self._analysis_queue.dequeue_folder(storage, source_in_storage)
        self._analysis_queue.pause()
        destination_in_storage = self._storage(storage).move_folder(
            source_in_storage, destination_in_storage
        )
        self._determine_analysis_backlog(
            storage, self._storage(storage), root=destination_in_storage
        )
        self._analysis_queue.resume()

        _, source_name = self._storage(storage).split_path(source_in_storage)
        _, destination_name = self._storage(storage).split_path(destination_in_storage)

        eventManager().fire(
            Events.FOLDER_REMOVED,
            {"storage": storage, "path": source_in_storage, "name": source_name},
        )
        eventManager().fire(
            Events.FOLDER_ADDED,
            {
                "storage": storage,
                "path": destination_in_storage,
                "name": destination_name,
            },
        )
        eventManager().fire(
            Events.FOLDER_MOVED,
            {
                "storage": storage,
                "source_path": source_in_storage,
                "source_name": source_name,
                "destination_path": destination_in_storage,
                "destination_name": destination_name,
            },
        )

        eventManager().fire(Events.UPDATED_FILES, {"type": "printables"})

    def copy_file_across_storage(
        self,
        source_storage: str,
        source_path: str,
        destination_storage: str,
        destination_path: str,
        progress_callback: Callable = None,
    ) -> None:
        self._action_across_storage(
            "copy_file",
            source_storage,
            source_path,
            destination_storage,
            destination_path,
            progress_callback=progress_callback,
        )

    def move_file_across_storage(
        self,
        source_storage: str,
        source_path: str,
        destination_storage: str,
        destination_path: str,
        progress_callback: Callable = None,
    ) -> None:
        self._action_across_storage(
            "move_file",
            source_storage,
            source_path,
            destination_storage,
            destination_path,
            progress_callback=progress_callback,
        )

    def _action_across_storage(
        self,
        action: str,
        source_storage: str,
        source_path: str,
        destination_storage: str,
        destination_path: str,
        progress_callback: Callable = None,
    ) -> None:
        storage_src = self._storage(source_storage)
        storage_dst = self._storage(destination_storage)

        if (
            not storage_src.capabilities.read_file
            or not storage_dst.capabilities.write_file
            or (action == "move_file" and not storage_src.capabilities.remove_file)
        ):
            raise StorageError(
                f"File copy from storage {source_storage} to {destination_storage} is not supported",
                code=StorageError.UNSUPPORTED,
            )

        source_in_storage = storage_src.path_in_storage(source_path)
        destination_in_storage = storage_dst.path_in_storage(destination_path)
        _, source_name = storage_src.split_path(source_in_storage)

        # get metadata for source
        metadata = {}
        if storage_src.capabilities.metadata:
            metadata = storage_src.get_metadata(source_path)

        # get file object for source
        source_file = storage_src.read_file(source_path)
        source_wrapper = StreamWrapper(source_name, source_file)

        # write it to the destination storage
        def callback(*args, **kwargs):
            if kwargs.get("done", False) or kwargs.get("failed", False):
                _, destination_name = storage_dst.split_path(destination_in_storage)

                if action == "copy_file":
                    # trigger FILE_ADDED
                    eventManager.fire(
                        Events.FILE_ADDED,
                        {
                            "storage": destination_storage,
                            "path": destination_in_storage,
                            "name": destination_name,
                            "type": get_file_type(destination_name),
                            "operation": "copy",
                        },
                    )

                elif action == "move_file":
                    # delete source file
                    storage_src.remove_file(source_in_storage)

                    # trigger FILE_REMOVED, FILE_ADDED, FILE_MOVED
                    eventManager.fire(
                        Events.FILE_REMOVED,
                        {
                            "storage": source_storage,
                            "path": source_in_storage,
                            "name": source_name,
                            "type": get_file_type(source_name),
                            "operation": "move",
                        },
                    )

                    eventManager.fire(
                        Events.FILE_ADDED,
                        {
                            "storage": destination_storage,
                            "path": destination_in_storage,
                            "name": destination_name,
                            "type": get_file_type(destination_name),
                            "operation": "move",
                        },
                    )

                    eventManager.fire(
                        Events.FILE_MOVED,
                        {
                            "source_storage": source_storage,
                            "source_path": source_in_storage,
                            "source_name": source_name,
                            "source_type": get_file_type(source_name),
                            "destination_storage": destination_storage,
                            "destination_path": destination_in_storage,
                            "destination_name": destination_name,
                            "destination_type": get_file_type(destination_name),
                            # backwards compatibility
                            "storage": source_storage,
                        },
                    )

                eventManager.fire(Events.UPDATED_FILES, {"type": "printables"})

            if callable(progress_callback):
                progress_callback(*args, **kwargs)

        storage_dst.add_file(
            destination_in_storage,
            source_wrapper,
            display=metadata.get("display"),
            user=metadata.get("user"),
            progress_callback=callback,
        )

    def get_size(self, location, path):
        try:
            return self._storage(location).get_size(path)
        except Exception:
            return -1

    def get_lastmodified(self, location: str, path: str) -> int:
        try:
            return self._storage(location).get_lastmodified(path)
        except Exception:
            return -1

    def has_analysis(self, location, path):
        return self._storage(location).has_analysis(path)

    def get_metadata(self, location, path):
        return self._storage(location).get_metadata(path)

    @deprecated(
        "add_link has been deprecated and will be removed in a future version",
        since="1.12.0",
    )
    def add_link(self, location, path, rel, data):
        self._storage(location).add_link(path, rel, data)

    @deprecated(
        "add_link has been deprecated and will be removed in a future version",
        since="1.12.0",
    )
    def remove_link(self, location, path, rel, data):
        self._storage(location).remove_link(path, rel, data)

    def create_job(
        self, location, path, owner: str = None, params: dict = None
    ) -> "PrintJob":
        return self._storage(location).create_job(path, owner=owner, params=params)

    def log_print(self, location, path, timestamp, print_time, success, printer_profile):
        try:
            if self._storage(location).capabilities.history:
                data = {
                    "timestamp": timestamp,
                    "success": success,
                    "printerProfile": printer_profile,
                }
                if success:
                    data["printTime"] = print_time

                self._storage(location).add_history(path, data)

                eventManager().fire(
                    Events.METADATA_STATISTICS_UPDATED,
                    {"storage": location, "path": path},
                )
        except NoSuchStorage:
            # if there's no storage configured where to log the print, we'll just not log it
            pass

    def save_recovery_data(self, location, path, pos):
        import time

        from octoprint.util import atomic_write

        data = {
            "origin": location,
            "path": self.path_in_storage(location, path),
            "pos": pos,
            "date": time.time(),
        }
        try:
            with atomic_write(self._recovery_file, mode="wt", max_permissions=0o666) as f:
                yaml.save_to_file(data, file=f, pretty=True)
        except Exception:
            self._logger.exception(
                f"Could not write recovery data to file {self._recovery_file}"
            )

    def delete_recovery_data(self):
        if not os.path.isfile(self._recovery_file):
            return

        try:
            os.remove(self._recovery_file)
        except Exception:
            self._logger.exception(
                f"Error deleting recovery data file {self._recovery_file}"
            )

    def get_recovery_data(self):
        if not os.path.isfile(self._recovery_file):
            return None

        try:
            data = yaml.load_from_file(path=self._recovery_file)

            if not isinstance(data, dict) or not all(
                x in data for x in ("origin", "path", "pos", "date")
            ):
                raise ValueError("Invalid recovery data structure")
            return data
        except Exception:
            self._logger.exception(
                f"Could not read recovery data from file {self._recovery_file}"
            )
            self.delete_recovery_data()

    def has_thumbnail(self, location, path) -> bool:
        return self._storage(location).has_thumbnail(path)

    def get_thumbnail(self, location, path, sizehint=None) -> Optional[StorageThumbnail]:
        return self._storage(location).get_thumbnail(path, sizehint=sizehint)

    def read_thumbnail(
        self, location, path, sizehint=None
    ) -> tuple[StorageThumbnail, IO]:
        return self._storage(location).read_thumbnail(path, sizehint=sizehint)

    def get_additional_metadata(self, location, path, key):
        return self._storage(location).get_additional_metadata(path, key)

    def set_additional_metadata(
        self, location, path, key, data, overwrite=False, merge=False
    ):
        self._storage(location).set_additional_metadata(
            path, key, data, overwrite=overwrite, merge=merge
        )

    def remove_additional_metadata(self, location, path, key):
        self._storage(location).remove_additional_metadata(path, key)

    def path_on_disk(self, location, path):
        return self._storage(location).path_on_disk(path)

    def canonicalize(self, location, path):
        return self._storage(location).canonicalize(path)

    def sanitize(self, location, path):
        return self._storage(location).sanitize(path)

    def sanitize_name(self, location, name):
        return self._storage(location).sanitize_name(name)

    def sanitize_path(self, location, path):
        return self._storage(location).sanitize_path(path)

    def split_path(self, location, path):
        return self._storage(location).split_path(path)

    def join_path(self, location, *path):
        return self._storage(location).join_path(*path)

    def path_in_storage(self, location, path):
        return self._storage(location).path_in_storage(path)

    def last_modified(self, location, path=None, recursive=False):
        return self._storage(location).get_lastmodified(path=path, recursive=recursive)

    def hash(self, location, path=None, recursive=False):
        return self._storage(location).get_hash(path=path, recursive=recursive)

    def current_capabilities(self, location) -> StorageCapabilities:
        return self._storage(location).current_capabilities

    def capabilities(self, location) -> StorageCapabilities:
        return self._storage(location).capabilities

    def _storage(self, location: str) -> StorageInterface:
        if location == FileDestinations.SDCARD:
            location = FileDestinations.PRINTER

        try:
            return self._storage_managers[location]
        except KeyError:
            raise NoSuchStorage(
                f"No storage configured for destination {location}"
            ) from None

    def _add_analysis_result(self, location, path, result):
        if location not in self._storage_managers:
            return
        if not result:
            return

        storage_manager = self._storage_managers[location]
        storage_manager.set_additional_metadata(path, "analysis", result, overwrite=True)

    def _on_analysis_finished(self, entry, result):
        self._add_analysis_result(entry.location, entry.path, result)

    def _analysis_queue_entry(self, location, path, printer_profile=None, analysis=None):
        storage = self._storage(location)
        if not storage.capabilities.path_on_disk:
            return None

        if printer_profile is None:
            printer_profile = self._printer_profile_manager.get_current_or_default()

        path_in_storage = storage.path_in_storage(path)
        absolute_path = storage.path_on_disk(path)
        _, file_name = storage.split_path(path)
        file_type = get_file_type(absolute_path)

        if file_type:
            return QueueEntry(
                file_name,
                path_in_storage,
                file_type[-1],
                location,
                absolute_path,
                printer_profile,
                analysis,
            )
        else:
            return None
