__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

import os
import sys
import unittest
from unittest import mock

import ddt

import octoprint.util


class BomAwareOpenTest(unittest.TestCase):
    """
    Tests for :func:`octoprint.util.bom_aware_open`.
    """

    def setUp(self):
        self.filename_utf8_with_bom = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), "_files", "utf8_with_bom.txt"
        )
        self.filename_utf8_without_bom = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), "_files", "utf8_without_bom.txt"
        )

    def test_bom_aware_open_with_bom(self):
        """Tests that the contents of a UTF8 file with BOM are loaded correctly (without the BOM)."""

        # test
        with octoprint.util.bom_aware_open(
            self.filename_utf8_with_bom, encoding="utf-8"
        ) as f:
            contents = f.readlines()

        # assert
        self.assertEqual(len(contents), 3)
        self.assertTrue(contents[0].startswith("#"))

    def test_bom_aware_open_without_bom(self):
        """Tests that the contents of a UTF8 file without BOM are loaded correctly."""

        # test
        with octoprint.util.bom_aware_open(
            self.filename_utf8_without_bom, encoding="utf-8"
        ) as f:
            contents = f.readlines()

        # assert
        self.assertEqual(len(contents), 3)
        self.assertTrue(contents[0].startswith("#"))

    def test_bom_aware_open_ascii(self):
        """Tests that the contents of a UTF8 file loaded as ASCII are replaced correctly if "replace" is specified on errors."""

        # test
        with octoprint.util.bom_aware_open(
            self.filename_utf8_with_bom, errors="replace"
        ) as f:
            contents = f.readlines()

        # assert
        self.assertEqual(len(contents), 3)
        self.assertTrue(contents[0].startswith("\ufffd" * 3 + "#"))
        self.assertTrue(contents[2].endswith("\ufffd\ufffd" * 6))

    def test_bom_aware_open_encoding_error(self):
        """Tests that an encoding error is thrown if not suppressed when opening a UTF8 file as ASCII."""
        try:
            with octoprint.util.bom_aware_open(self.filename_utf8_without_bom) as f:
                f.readlines()
            self.fail("Expected an exception")
        except UnicodeDecodeError:
            pass

    def test_bom_aware_open_parameters_text_mode(self):
        """Tests that the parameters are propagated properly in text mode."""

        with mock.patch("builtins.open", wraps=open) as mock_open:
            with octoprint.util.bom_aware_open(
                self.filename_utf8_without_bom,
                mode="rt",
                encoding="utf-8",
                errors="ignore",
            ) as f:
                f.readlines()

        calls = [
            mock.call(self.filename_utf8_without_bom, mode="rb"),
            mock.call(
                self.filename_utf8_without_bom,
                encoding="utf-8",
                mode="rt",
                errors="ignore",
            ),
        ]
        mock_open.assert_has_calls(calls)

    def test_bom_aware_open_parameters_binary_mode(self):
        """Tests that binary mode raises an AssertionError."""
        self.assertRaises(
            AssertionError,
            octoprint.util.bom_aware_open,
            self.filename_utf8_without_bom,
            mode="rb",
            encoding="utf-8",
            errors="ignore",
        )


class GetBomTest(unittest.TestCase):
    """
    Tests for :func:`octoprint.util.get_bom`.
    """

    def setUp(self):
        self.filename_utf8_with_bom = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), "_files", "utf8_with_bom.txt"
        )
        self.filename_utf8_without_bom = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), "_files", "utf8_without_bom.txt"
        )

    def test_get_bom_no_bom(self):
        """Tests that no BOM is returned if no BOM is present."""

        # test
        bom = octoprint.util.get_bom(self.filename_utf8_without_bom, "utf-8-sig")

        # assert
        self.assertIsNone(bom)

    def test_get_bom_utf8_bom(self):
        """Tests that a UTF8 BOM is returned if present."""

        # test
        bom = octoprint.util.get_bom(self.filename_utf8_with_bom, "utf-8-sig")

        # assert
        self.assertEqual(bom, b"\xef\xbb\xbf")

    def test_get_bom_wrong_encoding(self):
        """Tests that an UTF8 BOM is only returned if proper encoding was set."""

        # test
        bom = octoprint.util.get_bom(self.filename_utf8_with_bom, "utf-16-le")

        # assert
        self.assertIsNone(bom)


class TestAtomicWrite(unittest.TestCase):
    """
    Tests for :func:`octoprint.util.atomic_write`.
    """

    def setUp(self):
        pass

    @mock.patch("shutil.move")
    @mock.patch("tempfile.NamedTemporaryFile")
    @mock.patch("os.chmod")
    @mock.patch("os.path.exists")
    def test_atomic_write(self, mock_exists, mock_chmod, mock_ntf, mock_move):
        """Tests the regular basic "good" case."""

        # setup
        path = "tempfile.tmp"
        umask = 0o026

        mock_file = mock.MagicMock()
        mock_file.name = path

        mock_ntf.return_value = mock_file
        mock_exists.return_value = False

        # test
        with mock.patch("octoprint.util.UMASK", umask):
            with octoprint.util.atomic_write("somefile.yaml") as f:
                f.write("test")

        # assert
        mock_ntf.assert_called_once_with(
            mode="w+b", prefix="tmp", suffix="", dir="", delete=False
        )
        mock_file.write.assert_called_once_with("test")
        mock_file.close.assert_called_once_with()
        mock_chmod.assert_called_once_with(path, 0o644 & ~umask)
        mock_move.assert_called_once_with(path, "somefile.yaml")

    @mock.patch("shutil.move")
    @mock.patch("tempfile.NamedTemporaryFile")
    @mock.patch("os.chmod")  # not used but needs to be mocked
    @mock.patch("os.path.exists")
    def test_atomic_write_path_aware(self, mock_exists, mock_chmod, mock_ntf, mock_move):
        """Tests whether the tempoary file is to created in the same directory as the target file."""

        # setup
        tmpdirpath = "/testpath/with/subdirectories"
        path = os.path.join(tmpdirpath, "tempfile.tmp")
        targetpath = os.path.join(tmpdirpath, "somefile.yaml")

        mock_file = mock.MagicMock()
        mock_file.name = path

        mock_ntf.return_value = mock_file
        mock_exists.return_value = False

        # test
        with octoprint.util.atomic_write(targetpath) as f:
            f.write("test")

        # assert
        mock_ntf.assert_called_once_with(
            mode="w+b",
            prefix="tmp",
            suffix="",
            dir=tmpdirpath,
            delete=False,
        )
        mock_move.assert_called_once_with(path, targetpath)

    @mock.patch("shutil.move")
    @mock.patch("tempfile.NamedTemporaryFile")
    @mock.patch("os.chmod")  # not used but needs to be mocked
    @mock.patch("os.path.exists")
    def test_atomic_write_rel_path_aware(
        self, mock_exists, mock_chmod, mock_ntf, mock_move
    ):
        """Tests whether the tempoary file is to created in the same directory as the target file. This time submitting a relative path."""

        # setup
        tmpdirpath = "../test"
        path = os.path.join(tmpdirpath, "tempfile.tmp")
        targetpath = os.path.join(tmpdirpath, "somefile.yaml")

        mock_file = mock.MagicMock()
        mock_file.name = path

        mock_ntf.return_value = mock_file
        mock_exists.return_value = False

        # test
        with octoprint.util.atomic_write(targetpath) as f:
            f.write("test")

        # assert
        mock_ntf.assert_called_once_with(
            mode="w+b",
            prefix="tmp",
            suffix="",
            dir=tmpdirpath,
            delete=False,
        )
        mock_move.assert_called_once_with(path, targetpath)

    @mock.patch("shutil.move")
    @mock.patch("tempfile.NamedTemporaryFile")
    @mock.patch("os.chmod")
    @mock.patch("os.path.exists")
    def test_atomic_write_error_on_write(
        self, mock_exists, mock_chmod, mock_ntf, mock_move
    ):
        """Tests the error case where something in the wrapped code fails."""

        # setup
        path = "tempfile.tmp"

        mock_file = mock.MagicMock()
        mock_file.name = path
        mock_file.write.side_effect = RuntimeError()

        mock_ntf.return_value = mock_file
        mock_exists.return_value = False

        # test
        try:
            with octoprint.util.atomic_write("somefile.yaml") as f:
                f.write("test")
            self.fail("Expected an exception")
        except RuntimeError:
            pass

        # assert
        mock_ntf.assert_called_once_with(
            mode="w+b", prefix="tmp", suffix="", dir="", delete=False
        )
        mock_file.close.assert_called_once_with()
        self.assertFalse(mock_move.called)
        self.assertFalse(mock_chmod.called)

    @mock.patch("shutil.move")
    @mock.patch("tempfile.NamedTemporaryFile")
    @mock.patch("os.chmod")
    @mock.patch("os.path.exists")
    def test_atomic_write_error_on_move(
        self, mock_exists, mock_chmod, mock_ntf, mock_move
    ):
        """Tests the error case where the final move fails."""
        # setup
        path = "tempfile.tmp"

        mock_file = mock.MagicMock()
        mock_file.name = path

        mock_ntf.return_value = mock_file
        mock_move.side_effect = RuntimeError()
        mock_exists.return_value = False

        # test
        try:
            with octoprint.util.atomic_write("somefile.yaml") as f:
                f.write("test")
            self.fail("Expected an exception")
        except RuntimeError:
            pass

        # assert
        mock_ntf.assert_called_once_with(
            mode="w+b", prefix="tmp", suffix="", dir="", delete=False
        )
        mock_file.close.assert_called_once_with()
        self.assertTrue(mock_move.called)
        self.assertTrue(mock_chmod.called)

    @mock.patch("shutil.move")
    @mock.patch("tempfile.NamedTemporaryFile")
    @mock.patch("os.chmod")
    @mock.patch("os.path.exists")
    def test_atomic_write_parameters(self, mock_exists, mock_chmod, mock_ntf, mock_move):
        """Tests that the open parameters are propagated properly."""

        # setup
        path = "tempfile.tmp"
        umask = 0o026

        mock_file = mock.MagicMock()
        mock_file.name = path

        mock_ntf.return_value = mock_file
        mock_exists.return_value = False

        # test
        with mock.patch("octoprint.util.UMASK", umask):
            with octoprint.util.atomic_write(
                "somefile.yaml", mode="w", prefix="foo", suffix="bar"
            ) as f:
                f.write("test")

        # assert
        mock_ntf.assert_called_once_with(
            mode="w", prefix="foo", suffix="bar", dir="", delete=False, encoding="utf-8"
        )
        mock_file.close.assert_called_once_with()
        mock_chmod.assert_called_once_with(path, 0o664 & ~umask)
        mock_move.assert_called_once_with(path, "somefile.yaml")

    @mock.patch("shutil.move")
    @mock.patch("tempfile.NamedTemporaryFile")
    @mock.patch("os.chmod")
    @mock.patch("os.path.exists")
    def test_atomic_write_custom_permissions(
        self, mock_exists, mock_chmod, mock_ntf, mock_move
    ):
        """Tests that custom permissions may be set."""

        # setup
        path = "tempfile.tmp"

        mock_file = mock.MagicMock()
        mock_file.name = path

        mock_ntf.return_value = mock_file
        mock_exists.return_value = False

        # test
        with octoprint.util.atomic_write(
            "somefile.yaml", mode="wt", permissions=0o755
        ) as f:
            f.write("test")

        # assert
        mock_ntf.assert_called_once_with(
            mode="wt", prefix="tmp", suffix="", dir="", delete=False, encoding="utf-8"
        )
        mock_file.close.assert_called_once_with()
        mock_chmod.assert_called_once_with(path, 0o755)
        mock_move.assert_called_once_with(path, "somefile.yaml")

    @mock.patch("shutil.move")
    @mock.patch("tempfile.NamedTemporaryFile")
    @mock.patch("os.chmod")
    @mock.patch("os.path.exists")
    @mock.patch("os.stat")
    def test_atomic_permissions_combined(
        self,
        mock_stat,
        mock_exists,
        mock_chmod,
        mock_ntf,
        mock_move,
    ):
        """Tests that the permissions of an existing file are combined with the requested permissions."""

        # setup
        path = "tempfile.tmp"

        mock_file = mock.MagicMock()
        mock_file.name = path

        mock_ntf.return_value = mock_file
        mock_exists.return_value = True

        mock_stat_result = mock.MagicMock()
        mock_stat_result.st_mode = 0o666
        mock_stat.return_value = mock_stat_result

        # test
        with octoprint.util.atomic_write(
            "somefile.yaml", mode="wt", permissions=0o755
        ) as f:
            f.write("test")

        # assert
        mock_ntf.assert_called_once_with(
            mode="wt", prefix="tmp", suffix="", dir="", delete=False, encoding="utf-8"
        )
        mock_file.close.assert_called_once_with()
        mock_chmod.assert_called_once_with(path, 0o777)  # 0o755 | 0o666
        mock_move.assert_called_once_with(path, "somefile.yaml")

    @mock.patch("shutil.move")
    @mock.patch("tempfile.NamedTemporaryFile")
    @mock.patch("os.chmod")
    @mock.patch("os.path.exists")
    @mock.patch("os.stat")
    def test_atomic_permissions_limited(
        self,
        mock_stat,
        mock_exists,
        mock_chmod,
        mock_ntf,
        mock_move,
    ):
        """Tests that max_permissions limit the combined file permissions."""

        # setup
        path = "tempfile.tmp"

        mock_file = mock.MagicMock()
        mock_file.name = path

        mock_ntf.return_value = mock_file
        mock_exists.return_value = True

        mock_stat_result = mock.MagicMock()
        mock_stat_result.st_mode = 0o755
        mock_stat.return_value = mock_stat_result

        # test
        with octoprint.util.atomic_write(
            "somefile.yaml", mode="wt", permissions=0o600, max_permissions=0o666
        ) as f:
            f.write("test")

        # assert
        mock_ntf.assert_called_once_with(
            mode="wt", prefix="tmp", suffix="", dir="", delete=False, encoding="utf-8"
        )
        mock_file.close.assert_called_once_with()
        mock_chmod.assert_called_once_with(
            path, 0o644
        )  # (0o600 | 0o755) & 0o666 = 0o755 & 0o666 = 0o644
        mock_move.assert_called_once_with(path, "somefile.yaml")


class TempDirTest(unittest.TestCase):
    @mock.patch("shutil.rmtree")
    @mock.patch("tempfile.mkdtemp")
    def test_tempdir(self, mock_mkdtemp, mock_rmtree):
        """Tests regular "good" case."""

        # setup
        path = "/path/to/tmpdir"
        mock_mkdtemp.return_value = path

        # test
        with octoprint.util.tempdir() as td:
            self.assertEqual(td, path)

        # assert
        mock_mkdtemp.assert_called_once_with()
        mock_rmtree.assert_called_once_with(path, ignore_errors=False, onerror=None)

    @mock.patch("shutil.rmtree")
    @mock.patch("tempfile.mkdtemp")
    def test_tempdir_parameters_mkdtemp(self, mock_mkdtemp, mock_rmtree):
        """Tests that parameters for mkdtemp are properly propagated."""

        # setup
        path = "/path/to/tmpdir"
        mock_mkdtemp.return_value = path

        # test
        with octoprint.util.tempdir(prefix="prefix", suffix="suffix", dir="dir") as td:
            self.assertEqual(td, path)

        # assert
        mock_mkdtemp.assert_called_once_with(prefix="prefix", suffix="suffix", dir="dir")
        mock_rmtree.assert_called_once_with(path, ignore_errors=False, onerror=None)

    @mock.patch("shutil.rmtree")
    @mock.patch("tempfile.mkdtemp")
    def test_tempdir_parameters_rmtree(self, mock_mkdtemp, mock_rmtree):
        """Tests that parameters for rmtree are properly propagated."""

        # setup
        path = "/path/to/tmpdir"
        mock_mkdtemp.return_value = path

        onerror = mock.MagicMock()

        # test
        with octoprint.util.tempdir(ignore_errors=True, onerror=onerror) as td:
            self.assertEqual(td, path)

        # assert
        mock_mkdtemp.assert_called_once_with()
        mock_rmtree.assert_called_once_with(path, ignore_errors=True, onerror=onerror)


@ddt.ddt
class IsHiddenPathTest(unittest.TestCase):
    def setUp(self):
        import tempfile

        self.basepath = tempfile.mkdtemp()

        self.path_always_visible = os.path.join(self.basepath, "always_visible.txt")
        self.path_hidden_on_windows = os.path.join(self.basepath, "hidden_on_windows.txt")
        self.path_always_hidden = os.path.join(self.basepath, ".always_hidden.txt")

        import sys

        for attr in (
            "path_always_visible",
            "path_hidden_on_windows",
            "path_always_hidden",
        ):
            path = getattr(self, attr)
            with open(path, "wt+", encoding="utf-8") as f:
                f.write(attr)

        if sys.platform == "win32":
            # we use ctypes and the windows API to set the hidden attribute on the file
            # only hidden on windows
            import ctypes

            ctypes.windll.kernel32.SetFileAttributesW(str(self.path_hidden_on_windows), 2)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.basepath)

    @ddt.data(
        (None, False),
        ("path_always_visible", False),
        ("path_always_hidden", True),
        ("path_hidden_on_windows", sys.platform == "win32"),
    )
    @ddt.unpack
    def test_is_hidden_path(self, path_id, expected):
        path = getattr(self, path_id) if path_id is not None else None
        self.assertEqual(octoprint.util.is_hidden_path(path), expected)
