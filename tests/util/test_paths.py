import pathlib
from unittest.mock import call, patch

import pytest

import octoprint.util.paths


@pytest.fixture
def testfolder():
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        folder = pathlib.Path(tmp) / "this/is/a/test"

        os.makedirs(folder)
        with open(folder / "file.txt", "w") as f:
            f.write("test")  # ./this/is/a/test/file.txt
        with open(folder.parent / "file.txt", "w") as f:
            f.write("test")  # ./this/is/a/file.txt

        yield tmp


@pytest.mark.parametrize(
    "path, expected",
    [
        pytest.param(
            "this/is/a/test/file.txt",
            [
                "/this/is/a/test/file.txt",
                "/this/is/a/test",
                "/this/is/a",
                "/this/is",
                "/this",
                "/",
            ],
        ),
        pytest.param(
            "this/is/a/file.txt",
            ["/this/is/a/file.txt", "/this/is/a", "/this/is", "/this", "/"],
        ),
    ],
)
@patch("os.utime")
def test_touch_all_until(patched_utime, testfolder, path, expected):
    p = pathlib.Path(testfolder) / path
    octoprint.util.paths.touch_all_until(p, testfolder)
    calls = [call(str(pathlib.Path(testfolder) / x[1:]), None) for x in expected]
    patched_utime.assert_has_calls(calls)


def test_touch_all_until_invalid(testfolder):
    p = pathlib.Path(testfolder) / "../this/is/a/file.txt"
    with pytest.raises(ValueError):
        octoprint.util.paths.touch_all_until(p, testfolder)
