from unittest import mock

import pytest

from octoprint.filemanager.storage import StorageEntry, StorageFolder
from octoprint.printer import PrinterFile, PrinterFilesMixin

FILES = ["foo.gcode", "test/foo.gcode", "test/sub/foo.gcode", "test/sub/sub/foo.gcode"]


LIST_TESTS = (
    "path, filters, recursive, level, expected",
    [
        pytest.param(None, None, True, 0, FILES, id="recursive-unfiltered"),
        pytest.param(
            "test",
            None,
            True,
            0,
            ["test/foo.gcode", "test/sub/foo.gcode", "test/sub/sub/foo.gcode"],
            id="recursive-unfiltered-path",
        ),
        pytest.param(
            "test",
            None,
            False,
            0,
            ["test/foo.gcode"],
            id="nonrecursive-0-unfiltered-path",
        ),
        pytest.param(
            "test",
            None,
            False,
            1,
            ["test/foo.gcode", "test/sub/foo.gcode"],
            id="nonrecursive-1-unfiltered-path",
        ),
        pytest.param(
            None,
            (
                lambda x: x["path"].endswith("bar.gcode"),
                lambda x: x.path.endswith("bar.gcode"),
            ),
            True,
            0,
            [],
            id="recursive-filtered",
        ),
    ],
)


@pytest.mark.parametrize(*LIST_TESTS)
def test_get_files(path, filters, recursive, level, expected):
    connection = mock.MagicMock(PrinterFilesMixin)
    connection.get_printer_files.return_value = [
        PrinterFile(path=f, display=f, size=None, date=None) for f in FILES
    ]

    filter = None
    if filters:
        filter = filters[0]  # first item is for list_files use

    with mock.patch("octoprint.filemanager.get_file_type") as gft:
        from octoprint.filemanager.storage.printer import PrinterFileStorage

        gft.return_value = ["machinecode", "gcode"]

        printer_storage = PrinterFileStorage(connection)
        with pytest.deprecated_call():
            files = printer_storage.list_files(
                path=path, filter=filter, recursive=recursive, level=level
            )
    actual = _extract_paths_from_files(files)

    assert actual == expected


@pytest.mark.parametrize(*LIST_TESTS)
def test_list_storage_entries(path, filters, recursive, level, expected):
    connection = mock.MagicMock(PrinterFilesMixin)
    connection.get_printer_files.return_value = [
        PrinterFile(path=f, display=f, size=None, date=None) for f in FILES
    ]

    filter = None
    if filters:
        filter = filters[1]  # second item is for list_storage_entries use

    with mock.patch("octoprint.filemanager.get_file_type") as gft:
        from octoprint.filemanager.storage.printer import PrinterFileStorage

        gft.return_value = ["machinecode", "gcode"]

        printer_storage = PrinterFileStorage(connection)
        files = printer_storage.list_storage_entries(
            path=path, filter=filter, recursive=recursive, level=level
        )
    actual = _extract_paths_from_storage_entries(files)

    assert actual == expected


def test_set_additional_metadata():
    from octoprint.filemanager.storage import MetadataEntry
    from octoprint.filemanager.storage.printer import (
        PrinterFileStorage,
        StorageCapabilities,
    )

    capabilities = StorageCapabilities(metadata=True)
    meta = MetadataEntry()

    path = "test/foo.gcode"
    key = "unittest"
    data = {"foo": "bar"}

    connection = mock.MagicMock(PrinterFilesMixin)
    connection.current_storage_capabilities = capabilities
    connection.validate_printer_file_additional_metadata.return_value = True
    connection.get_printer_file_metadata.return_value = meta

    printer_storage = PrinterFileStorage(connection)
    printer_storage.set_additional_metadata(path, key, data)

    assert meta.additional.get("unittest") == data
    connection.set_printer_file_metadata.assert_called_with(path, meta)


def test_set_additional_metadata_unsupported():
    from octoprint.filemanager.storage import MetadataEntry
    from octoprint.filemanager.storage.printer import (
        PrinterFileStorage,
        StorageCapabilities,
        StorageError,
    )

    capabilities = StorageCapabilities()
    meta = MetadataEntry()

    path = "test/foo.gcode"
    key = "unittest"
    data = {"foo": "bar"}

    connection = mock.MagicMock(PrinterFilesMixin)
    connection.current_storage_capabilities = capabilities
    connection.validate_printer_file_additional_metadata.return_value = True
    connection.get_printer_file_metadata.return_value = meta

    printer_storage = PrinterFileStorage(connection)
    with pytest.raises(StorageError) as exc:
        printer_storage.set_additional_metadata(path, key, data)

    assert exc.value.code == StorageError.UNSUPPORTED
    assert meta.additional.get("unittest") is None
    connection.set_printer_file_metadata.assert_not_called()


def test_set_additional_metadata_invalid():
    from octoprint.filemanager.storage import MetadataEntry
    from octoprint.filemanager.storage.printer import (
        PrinterFileStorage,
        StorageCapabilities,
        StorageError,
    )

    capabilities = StorageCapabilities(metadata=True)
    meta = MetadataEntry()

    path = "test/foo.gcode"
    key = "unittest"
    data = {"foo": "bar"}

    connection = mock.MagicMock(PrinterFilesMixin)
    connection.current_storage_capabilities = capabilities
    connection.validate_printer_file_additional_metadata.return_value = False
    connection.get_printer_file_metadata.return_value = meta

    printer_storage = PrinterFileStorage(connection)
    with pytest.raises(StorageError) as exc:
        printer_storage.set_additional_metadata(path, key, data)

    assert exc.value.code == StorageError.INVALID_METADATA
    assert meta.additional.get("unittest") is None
    connection.set_printer_file_metadata.assert_not_called()


def test_validate_additional_metadata():
    from octoprint.filemanager.storage.printer import PrinterFileStorage

    connection = mock.MagicMock(PrinterFilesMixin)
    connection.validate_printer_file_additional_metadata.return_value = True

    printer_storage = PrinterFileStorage(connection)
    printer_storage.validate_additional_metadata({"foo": "bar"})


def _extract_paths_from_files(nodes: dict[str, dict]) -> list[str]:
    result = []

    for node in nodes.values():
        if node["type"] == "folder":
            result += _extract_paths_from_files(node["children"])
        else:
            result.append(node["path"])

    return result


def _extract_paths_from_storage_entries(nodes: dict[str, StorageEntry]) -> list[str]:
    result = []

    for node in nodes.values():
        if isinstance(node, StorageFolder):
            result += _extract_paths_from_storage_entries(node.children)
        else:
            result.append(node.path)

    return result
