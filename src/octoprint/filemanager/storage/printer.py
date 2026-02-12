import logging
import os
import tempfile
import time
from typing import IO, Optional

from octoprint.filemanager import get_file_type
from octoprint.filemanager.util import AbstractFileWrapper
from octoprint.printer import PrinterFile, PrinterFilesError, PrinterFilesMixin

from . import (
    MetadataEntry,
    StorageCapabilities,
    StorageEntry,
    StorageError,
    StorageFile,
    StorageFolder,
    StorageInterface,
    StorageThumbnail,
    StorageUsage,
)


class PrinterFileStorage(StorageInterface):
    """
    StorageInterface for accessing files stored on the connected printer, through
    the existing printer connection.

    .. md-mermaid::

       sequenceDiagram
         participant Connector
         participant PrinterFileStorage
         participant Printer
         participant FileManager

         activate Connector
         activate FileManager
         activate Printer

         Note over Connector,FileManager: Printer files become available
         Connector->>Printer: on_printer_files_available(True)
         break connection != PrinterFilesMixin
            Printer->Printer: log exception
         end
         Printer->>+PrinterFileStorage: new PrinterFileStorage(connection)
         PrinterFileStorage-->>Printer: storage
         Printer->>FileManager: register_storage("printer", storage)

         Note over Connector,FileManager: Printer files are requested
         FileManager->>PrinterFileStorage: get_printer_files(...)
         PrinterFileStorage->>Connector: list_storage_entries(...)
         Connector--)Printer: on_printer_files_refreshed(files)
         Connector-->>PrinterFileStorage: files
         PrinterFileStorage-->>FileManager: files

         Note over Connector,FileManager: Printer files become unavailable
         Connector->>Printer: on_printer_files_available(False)
         Printer->>FileManager: unregister_storage("printer")
         deactivate PrinterFileStorage

    """

    storage = "printer"
    name = "Printer"

    def __init__(self, connection: PrinterFilesMixin):
        if not isinstance(connection, PrinterFilesMixin):
            raise ValueError(
                "Connection must implement octoprint.printer.PrinterFilesMixin"
            )

        self._logger = logging.getLogger(__name__)
        self._connection = connection

        self._last_activity = 0

    def _update_last_activity(self):
        self._last_activity = time.monotonic()

    def _get_printer_files(
        self, path=None, filter=None, refresh=False
    ) -> list[PrinterFile]:
        files = self._connection.get_printer_files(refresh=refresh)

        if path:
            match = [f for f in files if f.path == path]
            if match:
                # path is a single file
                files = match
            else:
                # path might be a directory
                files = [f for f in files if f.path.startswith(path + "/")]

        return files

    @property
    def capabilities(self) -> StorageCapabilities:
        return self._connection.current_storage_capabilities

    def get_size(self, path=None, recursive=False) -> Optional[int]:
        files = self._get_printer_files(path=path)

        sizes = [f.size for f in files if f.size is not None]
        if len(sizes):
            return sum(sizes)

        return None

    def get_lastmodified(self, path=None, recursive=False) -> Optional[int]:
        files = self._get_printer_files(path=path)

        dates = [f.date.timestamp() for f in files if f.date is not None]
        if len(dates):
            return max(dates)

        return None

    def get_hash(self, path: str = None, recursive: bool = False) -> str:
        import hashlib

        files = sorted(
            f.path for f in self._get_printer_files(path=path) if f.path is not None
        )

        hash = hashlib.sha1()

        def hash_update(value: str):
            hash.update(value.encode("utf-8"))

        hash_update(",".join(files))
        hash_update(str(self.get_lastmodified(path, recursive=recursive)))
        return hash.hexdigest()

    def file_in_path(self, path, filepath):
        return filepath.startswith(path + "/")

    def file_exists(self, path):
        files = self._get_printer_files()
        paths = [f.path for f in files]
        return path in paths

    def folder_exists(self, path):
        files = self._get_printer_files()
        paths = [f.path for f in files]
        return any(p.startswith(path + "/") for p in paths)

    def list_storage_entries(
        self,
        path: str = None,
        filter: callable = None,
        recursive: bool = True,
        level: int = 0,
        force_refresh: bool = False,
    ) -> dict[str, StorageEntry]:
        files = self._get_printer_files(path=path, filter=filter, refresh=force_refresh)

        files = sorted(files, key=lambda x: x.path)

        prefix = f"{path}/" if path else ""
        if not recursive:
            if level > 0:
                files = [
                    f
                    for f in files
                    if f.path.startswith(prefix)
                    and len(f.path[len(prefix) :].split("/")) <= 2
                ]
            else:
                files = [
                    f
                    for f in files
                    if f.path.startswith(prefix) and "/" not in f.path[len(prefix) :]
                ]

        result = {}
        for f in files:
            if f.path == prefix:
                continue

            type_path = get_file_type(f.path)
            if not type_path:
                if f.path.endswith("/"):
                    type_path = ["folder"]
                else:
                    continue

            file_type = type_path[0]

            parts = f.path[len(prefix) :].split("/")
            if parts[-1] == "":
                parts = parts[:-1]
            name = parts[-1]

            if file_type == "folder":
                entry = StorageFolder(
                    name=name, origin=self.storage, path=f.path[:-1], display=f.display
                )
            else:
                entry = StorageFile(
                    name=name,
                    origin=self.storage,
                    path=f.path,
                    display=f.display,
                    entry_type=file_type,
                    type_path=type_path,
                    metadata=f.metadata,
                    thumbnails=f.thumbnails,
                )

            if f.size is not None and file_type != "folder":
                entry.size = f.size
            if f.date is not None:
                entry.date = f.date

            node = result
            if len(parts) > 1:
                # we have folders
                fp = ""
                for p in parts[:-1]:
                    fp += f"/{p}" if fp else p
                    if p not in node:
                        node[p] = StorageFolder(
                            name=p,
                            origin=self.storage,
                            path=fp,
                            display=p,
                        )
                    node = node[p].children

            node[name] = entry

        if filter is not None:
            result = {k: v for k, v in result.items() if filter(v)}

        def _add_calculated_size(node: StorageFolder) -> int:
            size = 0
            for child in node.children.values():
                size += (
                    _add_calculated_size(child)
                    if isinstance(child, StorageFolder)
                    else child.size
                    if child.size
                    else 0
                )
            node.size = size
            return size

        for node in result.values():
            if isinstance(node, StorageFolder):
                _add_calculated_size(node)

        return result

    def add_folder(self, path, ignore_existing=True, display=None, user=None) -> str:
        if not self.capabilities.add_folder:
            raise StorageError(
                "Printer does not support folder creation", code=StorageError.UNSUPPORTED
            )

        files = self._get_printer_files()
        path_prefix = path + "/"
        slashed_path_prefix = "/" + path_prefix
        if any(
            x.path.startswith(path_prefix) or x.path.startswith(slashed_path_prefix)
            for x in files
        ):
            if not ignore_existing:
                raise StorageError(
                    f"{path} does already exist on the printer",
                    code=StorageError.ALREADY_EXISTS,
                )
            else:
                return path

        try:
            result = self._connection.create_printer_folder(path)
            self._update_last_activity()
            return result
        except PrinterFilesError as exc:
            raise StorageError("Folder creation failed") from exc

    def remove_folder(self, path, recursive=True):
        if not self.capabilities.remove_folder:
            raise StorageError(
                "Printer does not support folder deletion", code=StorageError.UNSUPPORTED
            )

        files = self._get_printer_files()

        for f in files:
            if f.path.startswith(path + "/") and not recursive:
                raise StorageError(f"{path} is not empty", code=StorageError.NOT_EMPTY)

        try:
            self._connection.delete_printer_folder(path, recursive=recursive)
            self._update_last_activity()
        except PrinterFilesError as exc:
            raise StorageError("Folder deletion failed") from exc

    def copy_folder(self, source, destination, allow_overwrite: bool = False) -> str:
        if not self.capabilities.copy_folder:
            raise StorageError(
                "Printer does not support folder copies", code=StorageError.UNSUPPORTED
            )

        if not allow_overwrite and (
            self.file_exists(destination) or self.folder_exists(destination)
        ):
            raise StorageError(
                f"{destination} does already exist",
                code=StorageError.ALREADY_EXISTS,
            )

        try:
            result = self._connection.copy_printer_folder(source, destination)  # TODO
            self._update_last_activity()
            return result
        except PrinterFilesError as exc:
            raise StorageError("Folder copy failed") from exc

    def move_folder(self, source, destination, allow_overwrite: bool = False):
        if not self.capabilities.move_folder:
            raise StorageError(
                "Printer does not support folder moves", code=StorageError.UNSUPPORTED
            )

        if not allow_overwrite and (
            self.file_exists(destination) or self.folder_exists(destination)
        ):
            raise StorageError(
                f"{destination} does already exist",
                code=StorageError.ALREADY_EXISTS,
            )

        try:
            result = self._connection.move_printer_folder(source, destination)
            self._update_last_activity()
            return result
        except PrinterFilesError as exc:
            raise StorageError("Folder move failed") from exc

    def add_file(
        self,
        path: str,
        file_object: AbstractFileWrapper,
        allow_overwrite: bool = False,
        progress_callback: callable = None,
        *args,
        **kwargs,
    ):
        if not self.capabilities.write_file:
            raise StorageError(
                "Printer does not support adding files", code=StorageError.UNSUPPORTED
            )

        files = self._get_printer_files()
        if not allow_overwrite and any(x.path == path for x in files):
            raise StorageError(
                "File does already exist", code=StorageError.ALREADY_EXISTS
            )

        temp = tempfile.NamedTemporaryFile(mode="wb", delete=False)
        file_object.save(temp.name)
        temp.close()

        def callback(*args, **kwargs):
            if kwargs.get("failed", False) or kwargs.get("done", False):
                os.remove(temp.name)
                self._update_last_activity()
            if progress_callback:
                progress_callback(*args, **kwargs)

        try:
            remote = self._connection.upload_printer_file(
                temp.name, path, progress_callback=callback
            )
            self._update_last_activity()
            return remote
        except PrinterFilesError as exc:
            raise StorageError("File creation failed") from exc

    def read_file(self, path: str) -> IO:
        if not self.capabilities.read_file:
            raise StorageError(
                "Printer does not support fetching file contents",
                code=StorageError.UNSUPPORTED,
            )

        try:
            return self._connection.download_printer_file(path)
        except PrinterFilesError as exc:
            raise StorageError("File read failed") from exc

    def remove_file(self, path):
        if not self.capabilities.remove_file:
            raise StorageError(
                "Printer does not support file deletion", code=StorageError.UNSUPPORTED
            )

        try:
            self._connection.delete_printer_file(path)
            self._update_last_activity()
        except PrinterFilesError as exc:
            raise StorageError("File deletion failed") from exc

    def copy_file(self, source, destination, allow_overwrite: bool = False):
        if not self.capabilities.copy_file:
            raise StorageError(
                "Printer does not support file copies", code=StorageError.UNSUPPORTED
            )

        if not allow_overwrite and (
            self.file_exists(destination) or self.folder_exists(destination)
        ):
            raise StorageError(
                f"{destination} does already exist",
                code=StorageError.ALREADY_EXISTS,
            )

        try:
            result = self._connection.copy_printer_file(source, destination)  # TODO
            self._update_last_activity()
            return result
        except PrinterFilesError as exc:
            raise StorageError("File copy failed") from exc

    def move_file(self, source, destination, allow_overwrite: bool = False):
        if not self.capabilities.move_file:
            raise StorageError(
                "Printer does not support file moves", code=StorageError.UNSUPPORTED
            )

        if not allow_overwrite and (
            self.file_exists(destination) or self.folder_exists(destination)
        ):
            raise StorageError(
                f"{destination} does already exist",
                code=StorageError.ALREADY_EXISTS,
            )

        try:
            result = self._connection.move_printer_file(source, destination)  # TODO
            self._update_last_activity()
            return result
        except PrinterFilesError as exc:
            raise StorageError("File move failed") from exc

    def has_analysis(self, path):
        metadata = self.get_metadata(path)
        return metadata and metadata.analysis

    def get_metadata(self, path, default=None):
        if not self.capabilities.metadata:
            return None

        metadata = self._connection.get_printer_file_metadata(path)
        if metadata:
            return metadata.model_dump()
        else:
            return default

    def has_thumbnail(self, path) -> bool:
        return self._connection.has_thumbnail(path)

    def get_thumbnail(self, path, sizehint=None) -> Optional[StorageThumbnail]:
        return self._connection.get_thumbnail(path, sizehint=sizehint)

    def read_thumbnail(
        self, path, sizehint=None
    ) -> Optional[tuple[StorageThumbnail, IO]]:
        return self._connection.download_thumbnail(path, sizehint=sizehint)

    def add_link(self, path, rel, data):
        pass  # not supported

    def remove_link(self, path, rel, data):
        pass  # not supported

    def get_additional_metadata(self, path, key):
        if not self.capabilities.metadata:
            return None

        metadata = self._connection.get_printer_file_metadata(path)
        return metadata.model_extra.get(key)

    def set_additional_metadata(self, path, key, data, overwrite=False, merge=False):
        if not self.capabilities.metadata:
            raise StorageError(
                "Printer does not support storing additional metadata",
                code=StorageError.UNSUPPORTED,
            )

        metadata = self._connection.get_printer_file_metadata(path)
        if metadata is None:
            metadata = MetadataEntry()

        if key in metadata.model_extra:
            if not overwrite:
                return

            if merge:
                import octoprint.util

                data = octoprint.util.dict_merge(metadata.model_extra[key], data)

        metadata.model_extra[key] = data
        self._connection.set_printer_file_metadata(path, metadata)
        self._update_last_activity()

    def remove_additional_metadata(self, path, key):
        if not self.capabilities.metadata:
            raise StorageError(
                "Printer does not support storing additional metadata",
                code=StorageError.UNSUPPORTED,
            )

        metadata = self._connection.get_printer_file_metadata(path)
        if metadata is None:
            metadata = MetadataEntry()

        try:
            del metadata.model_extra[key]
            self._update_last_activity()
        except KeyError:
            pass

    def create_job(self, path, owner: str = None, params: dict = None):
        job = self._connection.create_job(path, owner=owner, params=params)
        if job is None:
            job = super().create_job(path, owner=owner, params=params)
        return job

    def _strip_leading_slash(self, path: str) -> str:
        while path and path[0] == "/":
            path = path[1:]

        return path

    def sanitize(self, path: str) -> tuple[str, str]:
        if path == "" or path == "/":
            return "/", ""
        path = self._strip_leading_slash(path)
        path, name = self.split_path(path)
        return self.sanitize_path(path), self.sanitize_name(name)

    def sanitize_path(self, path: str) -> str:
        if path == "" or path == "/":
            return "/"
        return self._strip_leading_slash(path)

    def sanitize_name(self, name: str) -> str:
        return self._connection.sanitize_file_name(name.replace("/", ""))

    def split_path(self, path: str) -> tuple[str, str]:
        path = self._strip_leading_slash(path)
        if "/" not in path:
            return "", path

        return path.rsplit("/", 1)

    def join_path(self, *path: str) -> str:
        return self._strip_leading_slash("/".join(path))

    def path_on_disk(self, path) -> str:
        raise StorageError(
            "Printer does not support path_on_disk", code=StorageError.UNSUPPORTED
        )

    def path_in_storage(self, path) -> str:
        pp, pf = self.canonicalize(path)
        if not pp:
            return pf
        else:
            return self.join_path(pp, pf)

    def get_usage(self) -> Optional[StorageUsage]:
        if not self._connection:
            return None
        usage = self._connection.get_usage_information()
        if not usage:
            return None
        return StorageUsage(used=usage.used, total=usage.total)
