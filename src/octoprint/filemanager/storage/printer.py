import logging
import os
import tempfile
import time
from typing import IO, Optional

from octoprint.filemanager import get_file_type
from octoprint.filemanager.util import AbstractFileWrapper
from octoprint.printer import PrinterFile, PrinterFilesMixin

from . import MetadataEntry, StorageCapabilities, StorageError, StorageInterface


class PrinterFileStorage(StorageInterface):
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

        if filter is not None:
            files = [f for f in files if filter(f)]

        return files

    @property
    def capabilities(self) -> StorageCapabilities:
        return self._connection.current_storage_capabilities

    def get_size(self, path=None, recursive=False) -> Optional[int]:
        files = self._get_printer_files(path=path)

        sizes = [f.size for f in files if f.date is not None]
        if len(sizes):
            return sum(sizes)

        return None

    def get_lastmodified(self, path=None, recursive=False) -> Optional[int]:
        files = self._get_printer_files(path=path)

        dates = [f.date for f in files if f.date is not None]
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

    def list_files(
        self, path=None, filter=None, recursive=True, level=0, force_refresh=False
    ):
        files = self._get_printer_files(path=path, filter=filter, refresh=force_refresh)

        if not recursive:
            prefix = f"{path}/" if path else ""
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
            type_path = get_file_type(f.path)
            if not type_path:
                continue

            file_type = type_path[0]

            parts = f.path.split("/")
            name = parts[-1]

            entry = {
                "name": name,
                "path": f.path,
                "display": f.display,
                "type": file_type,
                "typePath": type_path,
            }
            if f.size is not None:
                entry["size"] = f.size
            if f.date is not None:
                entry["date"] = f.date

            node = result
            if len(parts) > 1:
                # we have folders
                fp = ""
                for p in parts[:-1]:
                    fp += f"/{p}" if fp else p
                    if p not in node:
                        node[p] = {
                            "name": p,
                            "path": fp,
                            "display": p,
                            "type": "folder",
                            "typePath": ["folder"],
                            "children": {},
                        }
                    node = node[p]["children"]

            node[name] = entry

        return result

    def add_folder(self, path, ignore_existing=True, display=None, user=None):
        if not self.capabilities.add_folder:
            raise StorageError(
                "Printer does not support folder creation", code=StorageError.UNSUPPORTED
            )

        files = self._get_printer_files()
        if any(x.path.startswith(path) or x.path.startswith("/" + path) for x in files):
            if not ignore_existing:
                raise StorageError(
                    f"{path} does already exist on the printer",
                    code=StorageError.ALREADY_EXISTS,
                )
            else:
                return

        self._connection.create_printer_folder(path)
        self._update_last_activity()

    def remove_folder(self, path, recursive=True):
        if not self.capabilities.remove_folder:
            raise StorageError(
                "Printer does not support folder deletion", code=StorageError.UNSUPPORTED
            )

        files = self._get_printer_files()

        for f in files:
            if f.path.startswith(path + "/") and not recursive:
                raise StorageError("{path} is not empty", code=StorageError.NOT_EMPTY)

        self._connection.delete_printer_folder(path, recursive=recursive)
        self._update_last_activity()

    def copy_folder(self, source, destination):
        if not self.capabilities.copy_folder:
            raise StorageError(
                "Printer does not support folder copies", code=StorageError.UNSUPPORTED
            )

        self._connection.copy_printer_folder(source, destination)  # TODO
        self._update_last_activity()

    def move_folder(self, source, destination):
        if not self.capabilities.move_folder:
            raise StorageError(
                "Printer does not support folder moves", code=StorageError.UNSUPPORTED
            )

        self._connection.move_printer_folder(source, destination)  # TODO
        self._update_last_activity()

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

        remote = self._connection.upload_printer_file(
            temp.name, path, upload_callback=callback
        )

        return remote

    def read_file(self, path: str) -> IO:
        if not self.capabilities.read_file:
            raise StorageError(
                "Printer does not support fetching file contents",
                code=StorageError.UNSUPPORTED,
            )

        return self._connection.download_printer_file(path)

    def remove_file(self, path):
        if not self.capabilities.remove_file:
            raise StorageError(
                "Printer does not support file deletion", code=StorageError.UNSUPPORTED
            )

        self._connection.delete_printer_file(path)
        self._update_last_activity()

    def copy_file(self, source, destination):
        if not self.capabilities.copy_file:
            raise StorageError(
                "Printer does not support file copies", code=StorageError.UNSUPPORTED
            )

        self._connection.copy_printer_file(source, destination)  # TODO
        self._update_last_activity()

    def move_file(self, source, destination):
        if not self.capabilities.move_file:
            raise StorageError(
                "Printer does not support file moves", code=StorageError.UNSUPPORTED
            )

        self._connection.move_printer_file(source, destination)  # TODO
        self._update_last_activity()

    def has_analysis(self, path):
        metadata = self.get_metadata(path)
        return metadata and metadata.analysis

    def get_metadata(self, path):
        if not self.capabilities.metadata:
            return None

        metadata = self._connection.get_printer_file_metadata(path)
        return metadata.model_dump()

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

    def _strip_leading_slash(self, path: str) -> str:
        if not path:
            return path

        while path[0] == "/":
            path = path[1:]

        return path

    def sanitize(self, path: str) -> tuple[str, str]:
        if path == "/":
            return "/", ""
        path = self._strip_leading_slash(path)
        path, name = self.split_path(path)
        return self.sanitize_path(path), self.sanitize_name(name)

    def sanitize_path(self, path: str) -> str:
        if path == "/":
            return path
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
