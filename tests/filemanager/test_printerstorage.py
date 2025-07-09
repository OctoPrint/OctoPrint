from unittest import mock

import pytest

from octoprint.printer import PrinterFile, PrinterFilesMixin

FILES = ["foo.gcode", "test/foo.gcode", "test/sub/foo.gcode", "test/sub/sub/foo.gcode"]


@pytest.mark.parametrize(
    "path, filter, recursive, level, expected",
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
            lambda x: x.path.endswith("bar.gcode"),
            True,
            0,
            [],
            id="recursive-filtered",
        ),
    ],
)
def test_get_files(path, filter, recursive, level, expected):
    connection = mock.MagicMock(PrinterFilesMixin)
    connection.get_printer_files.return_value = [
        PrinterFile(path=f, display=f, size=None, date=None) for f in FILES
    ]

    with mock.patch("octoprint.filemanager.storage.printer.get_file_type") as gft:
        from octoprint.filemanager.storage.printer import PrinterFileStorage

        gft.return_value = ["machinecode", "gcode"]

        printer_storage = PrinterFileStorage(connection)
        files = printer_storage.list_files(
            path=path, filter=filter, recursive=recursive, level=level
        )
    actual = _extract_paths(files)

    assert actual == expected


def _extract_paths(nodes: dict) -> list[str]:
    result = []

    for node in nodes.values():
        if node["type"] == "folder":
            result += _extract_paths(node["children"])
        else:
            result.append(node["path"])

    return result
