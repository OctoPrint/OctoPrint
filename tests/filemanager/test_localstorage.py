__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import os
import os.path
import unittest
from contextlib import contextmanager
from unittest import mock

from ddt import data, ddt, unpack

from octoprint.filemanager.storage import StorageEntry, StorageError, StorageFolder
from octoprint.filemanager.storage.local import LocalFileStorage


class FileWrapper:
    def __init__(self, filename):
        self.path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "_files", filename
        )

    def save(self, destination):
        import shutil

        shutil.copy(self.path, destination)


FILE_BP_CASE_STL = FileWrapper("bp_case.stl")
FILE_BP_CASE_GCODE = FileWrapper("bp_case.gcode")
FILE_CRAZYRADIO_STL = FileWrapper("crazyradio.stl")


@ddt
class LocalStorageTest(unittest.TestCase):
    def setUp(self):
        import tempfile

        self.basefolder = os.path.realpath(os.path.abspath(tempfile.mkdtemp()))
        self.storage = LocalFileStorage(self.basefolder)

        # mock file manager module
        self.filemanager_patcher = mock.patch("octoprint.filemanager")
        self.filemanager = self.filemanager_patcher.start()

        self.filemanager.valid_file_type.return_value = True

        def get_file_type(name):
            if name.lower().endswith(".stl"):
                return ["model", "stl"]
            elif (
                name.lower().endswith(".gco")
                or name.lower().endswith(".gcode")
                or name.lower.endswith(".g")
            ):
                return ["machinecode", "gcode"]
            else:
                return None

        self.filemanager.get_file_type.side_effect = get_file_type

    def tearDown(self):
        import shutil

        shutil.rmtree(self.basefolder)

        self.filemanager_patcher.stop()

    def test_add_file(self):
        self._add_and_verify_file("bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL)

    def test_add_file_overwrite(self):
        self._add_and_verify_file("bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL)

        from octoprint.filemanager.storage import StorageError

        self.assertRaises(
            StorageError,
            self._add_and_verify_file,
            "bp_case.stl",
            "bp_case.stl",
            FILE_BP_CASE_STL,
            overwrite=False,
        )

        self._add_and_verify_file(
            "bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL, overwrite=True
        )

    def test_add_file_with_display(self):
        stl_name = self._add_and_verify_file(
            "bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL, display="bp_cäse.stl"
        )
        stl_metadata = self.storage.get_metadata(stl_name)

        self.assertIsNotNone(stl_metadata)
        self.assertIn("display", stl_metadata)
        self.assertEqual("bp_cäse.stl", stl_metadata["display"])

    def test_remove_file(self):
        stl_name = self._add_and_verify_file(
            "bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL, display="BP Case.stl"
        )
        gcode_name = self._add_and_verify_file(
            "bp_case.gcode", "bp_case.gcode", FILE_BP_CASE_GCODE, display="BP Case.gcode"
        )

        stl_metadata = self.storage.get_metadata(stl_name)
        gcode_metadata = self.storage.get_metadata(gcode_name)

        self.assertIsNotNone(stl_metadata)
        self.assertIsNotNone(gcode_metadata)

        self.storage.remove_file(stl_name)
        self.assertFalse(os.path.exists(os.path.join(self.basefolder, stl_name)))

        stl_metadata = self.storage.get_metadata(stl_name)
        gcode_metadata = self.storage.get_metadata(gcode_name)

        self.assertIsNone(stl_metadata)
        self.assertIsNotNone(gcode_metadata)

    def test_copy_file(self):
        self._add_file("bp_case.stl", FILE_BP_CASE_STL, display="BP Case.stl")
        self._add_folder("test")

        self.assertTrue(os.path.isfile(os.path.join(self.basefolder, "bp_case.stl")))
        self.assertTrue(os.path.isdir(os.path.join(self.basefolder, "test")))

        self.storage.copy_file("bp_case.stl", "test/copied.stl")

        self.assertTrue(os.path.isfile(os.path.join(self.basefolder, "bp_case.stl")))
        self.assertTrue(
            os.path.isfile(os.path.join(self.basefolder, "test", "copied.stl"))
        )

        stl_metadata = self.storage.get_metadata("bp_case.stl")
        copied_metadata = self.storage.get_metadata("test/copied.stl")

        self.assertIsNotNone(stl_metadata)
        self.assertIsNotNone(copied_metadata)
        self.assertDictEqual(stl_metadata, copied_metadata)

    def test_move_file(self):
        self._add_file("bp_case.stl", FILE_BP_CASE_STL, display="BP Case.stl")
        self._add_folder("test")

        self.assertTrue(os.path.isfile(os.path.join(self.basefolder, "bp_case.stl")))
        self.assertTrue(os.path.isdir(os.path.join(self.basefolder, "test")))

        before_stl_metadata = self.storage.get_metadata("bp_case.stl")

        self.storage.move_file("bp_case.stl", "test/copied.stl")

        self.assertFalse(os.path.isfile(os.path.join(self.basefolder, "bp_case.stl")))
        self.assertTrue(
            os.path.isfile(os.path.join(self.basefolder, "test", "copied.stl"))
        )

        after_stl_metadata = self.storage.get_metadata("bp_case.stl")
        copied_metadata = self.storage.get_metadata("test/copied.stl")

        self.assertIsNotNone(before_stl_metadata)
        self.assertIsNone(after_stl_metadata)
        self.assertIsNotNone(copied_metadata)
        self.assertDictEqual(before_stl_metadata, copied_metadata)

    def test_copy_file_same_name(self):
        self._add_file("bp_case.stl", FILE_BP_CASE_STL)
        try:
            self.storage.copy_file("bp_case.stl", "bp_case.stl")
            self.fail("Expected an exception")
        except StorageError as e:
            self.assertEqual(e.code, StorageError.SOURCE_EQUALS_DESTINATION)

    @data("copy_file", "move_file")
    def test_copy_move_file_different_display(self, operation):
        self._add_file("bp_case.stl", FILE_BP_CASE_STL, display="bp_cäse.stl")

        before_metadata = self.storage.get_metadata("bp_case.stl")
        getattr(self.storage, operation)("bp_case.stl", "test.stl")
        after_metadata = self.storage.get_metadata("test.stl")

        self.assertIsNotNone(before_metadata)
        self.assertIsNotNone(after_metadata)
        self.assertNotIn("display", after_metadata)

    @data("copy_file", "move_file")
    def test_copy_move_file_same(self, operation):
        self._add_file("bp_case.stl", FILE_BP_CASE_STL)
        try:
            getattr(self.storage, operation)("bp_case.stl", "bp_case.stl")
            self.fail("Expected an exception")
        except StorageError as e:
            self.assertEqual(e.code, StorageError.SOURCE_EQUALS_DESTINATION)

    @data("copy_file", "move_file")
    def test_copy_move_file_missing_source(self, operation):
        try:
            getattr(self.storage, operation)("bp_case.stl", "test/copied.stl")
            self.fail("Expected an exception")
        except StorageError as e:
            self.assertEqual(e.code, StorageError.INVALID_SOURCE)

    @data("copy_file", "move_file")
    def test_copy_move_file_missing_destination_folder(self, operation):
        self._add_file("bp_case.stl", FILE_BP_CASE_STL)

        try:
            getattr(self.storage, operation)("bp_case.stl", "test/copied.stl")
            self.fail("Expected an exception")
        except StorageError as e:
            self.assertEqual(e.code, StorageError.INVALID_DESTINATION)

    @data("copy_file", "move_file")
    def test_copy_move_file_existing_destination_path(self, operation):
        self._add_file("bp_case.stl", FILE_BP_CASE_STL)
        self._add_folder("test")
        self._add_file("test/crazyradio.stl", FILE_CRAZYRADIO_STL)

        try:
            getattr(self.storage, operation)("bp_case.stl", "test/crazyradio.stl")
            self.fail("Expected an exception")
        except StorageError as e:
            self.assertEqual(e.code, StorageError.ALREADY_EXISTS)

    def test_add_folder(self):
        self._add_and_verify_folder("test", "test")

    def test_add_folder_with_display(self):
        self._add_and_verify_folder("test", "test", display="täst")
        metadata = self.storage.get_metadata("test")
        self.assertIsNotNone(metadata)
        self.assertIn("display", metadata)
        self.assertEqual("täst", metadata["display"])

    def test_add_subfolder(self):
        folder_name = self._add_and_verify_folder("folder", "folder")
        subfolder_name = self._add_and_verify_folder(
            (folder_name, "subfolder"), folder_name + "/subfolder"
        )
        stl_name = self._add_and_verify_file(
            (subfolder_name, "bp_case.stl"),
            subfolder_name + "/bp_case.stl",
            FILE_BP_CASE_STL,
        )

        self.assertTrue(os.path.exists(os.path.join(self.basefolder, folder_name)))
        self.assertTrue(os.path.exists(os.path.join(self.basefolder, subfolder_name)))
        self.assertTrue(os.path.exists(os.path.join(self.basefolder, stl_name)))

    def test_remove_folder(self):
        content_folder = self._add_and_verify_folder("content", "content")
        other_stl_name = self._add_and_verify_file(
            (content_folder, "crazyradio.stl"),
            content_folder + "/crazyradio.stl",
            FILE_CRAZYRADIO_STL,
        )

        empty_folder = self._add_and_verify_folder("empty", "empty")

        try:
            self.storage.remove_folder(content_folder, recursive=False)
        except Exception:
            self.assertTrue(os.path.exists(os.path.join(self.basefolder, content_folder)))
            self.assertTrue(os.path.isdir(os.path.join(self.basefolder, content_folder)))
            self.assertTrue(os.path.exists(os.path.join(self.basefolder, other_stl_name)))

        self.storage.remove_folder(content_folder, recursive=True)
        self.assertFalse(os.path.exists(os.path.join(self.basefolder, content_folder)))
        self.assertFalse(os.path.isdir(os.path.join(self.basefolder, content_folder)))

        self.storage.remove_folder(empty_folder, recursive=False)
        self.assertFalse(os.path.exists(os.path.join(self.basefolder, empty_folder)))
        self.assertFalse(os.path.isdir(os.path.join(self.basefolder, empty_folder)))

    def test_remove_folder_with_display(self):
        self._add_folder("folder", display="földer")

        before_metadata = self.storage.get_metadata("folder")
        self.storage.remove_folder("folder")
        after_metadata = self.storage.get_metadata("folder")

        self.assertIsNotNone(before_metadata)
        self.assertDictEqual(before_metadata, {"display": "földer"})
        self.assertIsNone(after_metadata)

    def test_copy_folder(self):
        self._add_folder("source")
        self._add_folder("destination")
        self._add_file(
            "source/crazyradio.stl", FILE_CRAZYRADIO_STL, display="Crazyradio.stl"
        )

        source_metadata = self.storage.get_metadata("source/crazyradio.stl")
        self.storage.copy_folder("source", "destination/copied")
        copied_metadata = self.storage.get_metadata("destination/copied/crazyradio.stl")

        self.assertTrue(os.path.isdir(os.path.join(self.basefolder, "source")))
        self.assertTrue(
            os.path.isfile(os.path.join(self.basefolder, "source", "crazyradio.stl"))
        )
        self.assertTrue(os.path.isdir(os.path.join(self.basefolder, "destination")))
        self.assertTrue(
            os.path.isdir(os.path.join(self.basefolder, "destination", "copied"))
        )
        self.assertTrue(
            os.path.isfile(
                os.path.join(self.basefolder, "destination", "copied", ".metadata.json")
            )
        )
        self.assertTrue(
            os.path.isfile(
                os.path.join(self.basefolder, "destination", "copied", "crazyradio.stl")
            )
        )

        self.assertIsNotNone(source_metadata)
        self.assertIsNotNone(copied_metadata)
        self.assertDictEqual(source_metadata, copied_metadata)

    def test_move_folder(self):
        self._add_folder("source")
        self._add_folder("destination")
        self._add_file(
            "source/crazyradio.stl", FILE_CRAZYRADIO_STL, display="Crazyradio.stl"
        )

        before_source_metadata = self.storage.get_metadata("source/crazyradio.stl")
        self.storage.move_folder("source", "destination/copied")
        after_source_metadata = self.storage.get_metadata("source/crazyradio.stl")
        copied_metadata = self.storage.get_metadata("destination/copied/crazyradio.stl")

        self.assertFalse(os.path.isdir(os.path.join(self.basefolder, "source")))
        self.assertFalse(
            os.path.isfile(os.path.join(self.basefolder, "source", "crazyradio.stl"))
        )
        self.assertTrue(os.path.isdir(os.path.join(self.basefolder, "destination")))
        self.assertTrue(
            os.path.isdir(os.path.join(self.basefolder, "destination", "copied"))
        )
        self.assertTrue(
            os.path.isfile(
                os.path.join(self.basefolder, "destination", "copied", ".metadata.json")
            )
        )
        self.assertTrue(
            os.path.isfile(
                os.path.join(self.basefolder, "destination", "copied", "crazyradio.stl")
            )
        )

        self.assertIsNotNone(before_source_metadata)
        self.assertIsNone(after_source_metadata)
        self.assertIsNotNone(copied_metadata)
        self.assertDictEqual(before_source_metadata, copied_metadata)

    def test_copy_folder_same_name(self):
        self._add_folder("folder")
        try:
            self.storage.copy_folder("folder", "folder")
            self.fail("Expected an exception")
        except StorageError as e:
            self.assertEqual(e.code, StorageError.SOURCE_EQUALS_DESTINATION)

    @data("copy_folder", "move_folder")
    def test_copy_move_folder_different_display(self, operation):
        self._add_folder("folder", display="földer")

        before_metadata = self.storage.get_metadata("folder")
        getattr(self.storage, operation)("folder", "test")
        after_metadata = self.storage.get_metadata("test")

        self.assertIsNotNone(before_metadata)
        self.assertDictEqual(before_metadata, {"display": "földer"})
        self.assertIsNone(after_metadata)

    @data("copy_folder", "move_folder")
    def test_copy_move_folder_same(self, operation):
        self._add_folder("folder")
        try:
            getattr(self.storage, operation)("folder", "folder")
            self.fail("Expected an exception")
        except StorageError as e:
            self.assertEqual(e.code, StorageError.SOURCE_EQUALS_DESTINATION)

    @data("copy_folder", "move_folder")
    def test_copy_move_folder_missing_source(self, operation):
        try:
            getattr(self.storage, operation)("source", "destination/copied")
            self.fail("Expected an exception")
        except StorageError as e:
            self.assertEqual(e.code, StorageError.INVALID_SOURCE)

    @data("copy_folder", "move_folder")
    def test_copy_move_folder_missing_destination_folder(self, operation):
        self._add_folder("source")
        self._add_file("source/crazyradio.stl", FILE_CRAZYRADIO_STL)

        try:
            getattr(self.storage, operation)("source", "destination/copied")
            self.fail("Expected an exception")
        except StorageError as e:
            self.assertEqual(e.code, StorageError.INVALID_DESTINATION)

    @data("copy_folder", "move_folder")
    def test_copy_move_folder_existing_destination_path(self, operation):
        self._add_folder("source")
        self._add_file("source/crazyradio.stl", FILE_CRAZYRADIO_STL)
        self._add_folder("destination")
        self._add_folder("destination/copied")

        try:
            getattr(self.storage, operation)("source", "destination/copied")
            self.fail("Expected an exception")
        except StorageError as e:
            self.assertEqual(e.code, StorageError.ALREADY_EXISTS)

    def test_list(self):
        self._add_and_verify_file("bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL)
        self._add_and_verify_file(
            "bp_case.gcode",
            "bp_case.gcode",
            FILE_BP_CASE_GCODE,
        )

        content_folder = self._add_and_verify_folder("content", "content")
        self._add_and_verify_file(
            (content_folder, "crazyradio.stl"),
            content_folder + "/crazyradio.stl",
            FILE_CRAZYRADIO_STL,
        )

        self._add_and_verify_folder("empty", "empty")

        file_list = self.storage.list_files()
        self.assertEqual(4, len(file_list))
        self.assertTrue("bp_case.stl" in file_list)
        self.assertTrue("bp_case.gcode" in file_list)
        self.assertTrue("content" in file_list)
        self.assertTrue("empty" in file_list)

        self.assertEqual("model", file_list["bp_case.stl"]["type"])

        self.assertEqual("machinecode", file_list["bp_case.gcode"]["type"])

        self.assertEqual("folder", file_list[content_folder]["type"])
        self.assertEqual(1, len(file_list[content_folder]["children"]))
        self.assertTrue("crazyradio.stl" in file_list["content"]["children"])
        self.assertEqual(
            "model", file_list["content"]["children"]["crazyradio.stl"]["type"]
        )

        self.assertEqual("folder", file_list["empty"]["type"])
        self.assertEqual(0, len(file_list["empty"]["children"]))

    def test_list_with_filter(self):
        self._add_and_verify_file(
            "bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL, display="BP Case.stl"
        )
        self._add_and_verify_file(
            "bp_case.gcode", "bp_case.gcode", FILE_BP_CASE_GCODE, display="BP Case.gcode"
        )

        content_folder = self._add_and_verify_folder("content", "content")
        self._add_and_verify_file(
            (content_folder, "crazyradio.stl"),
            content_folder + "/crazyradio.stl",
            FILE_CRAZYRADIO_STL,
        )
        self._add_and_verify_file(
            (content_folder, "bp_case.gcode"),
            content_folder + "/bp_case.gcode",
            FILE_BP_CASE_GCODE,
        )

        self._add_and_verify_folder("empty", "empty")

        def filter_machinecode(node: StorageEntry) -> bool:
            return node["type"] == "machinecode"

        file_list = self.storage.list_files(filter=filter_machinecode)
        self.assertTrue(3, len(file_list))
        self.assertTrue("bp_case.gcode" in file_list)
        self.assertTrue("content" in file_list)
        self.assertTrue("empty" in file_list)

        self.assertEqual("folder", file_list[content_folder]["type"])
        self.assertEqual(1, len(file_list[content_folder]["children"]))
        self.assertTrue("bp_case.gcode" in file_list[content_folder]["children"])

        self.assertEqual("folder", file_list["empty"]["type"])
        self.assertEqual(0, len(file_list["empty"]["children"]))

    def test_list_without_recursive(self):
        self._add_and_verify_file(
            "bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL, display="BP Case.stl"
        )
        self._add_and_verify_file(
            "bp_case.gcode", "bp_case.gcode", FILE_BP_CASE_GCODE, display="BP Case.gcode"
        )

        content_folder = self._add_and_verify_folder("content", "content")
        self._add_and_verify_file(
            (content_folder, "crazyradio.stl"),
            content_folder + "/crazyradio.stl",
            FILE_CRAZYRADIO_STL,
        )

        self._add_and_verify_folder("empty", "empty")

        file_list = self.storage.list_files(recursive=False)
        self.assertTrue(3, len(file_list))
        self.assertTrue("bp_case.gcode" in file_list)
        self.assertTrue("content" in file_list)
        self.assertTrue("empty" in file_list)

        self.assertEqual("folder", file_list[content_folder]["type"])
        self.assertEqual(0, len(file_list[content_folder]["children"]))
        self.assertNotEqual(0, file_list[content_folder]["size"])

        self.assertEqual("folder", file_list["empty"]["type"])
        self.assertEqual(0, len(file_list["empty"]["children"]))

    def test_get_entries(self):
        self._add_and_verify_file("bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL)
        self._add_and_verify_file(
            "bp_case.gcode",
            "bp_case.gcode",
            FILE_BP_CASE_GCODE,
        )

        self._add_and_verify_folder("content", "content")
        self._add_and_verify_file(
            ("content", "crazyradio.stl"),
            "content" + "/crazyradio.stl",
            FILE_CRAZYRADIO_STL,
        )

        self._add_and_verify_folder("empty", "empty")

        entries = self.storage.list_storage_entries()

        self.assertEqual(4, len(entries))
        self.assertTrue("bp_case.stl" in entries)
        self.assertTrue("bp_case.gcode" in entries)
        self.assertTrue("content" in entries)
        self.assertTrue("empty" in entries)

        self.assertEqual("model", entries["bp_case.stl"].entry_type)

        self.assertEqual("machinecode", entries["bp_case.gcode"].entry_type)

        self.assertTrue(isinstance(entries["content"], StorageFolder))
        self.assertEqual("folder", entries["content"].entry_type)
        self.assertEqual(1, len(entries["content"].children))
        self.assertTrue("crazyradio.stl" in entries["content"].children)
        self.assertEqual(
            "model", entries["content"].children["crazyradio.stl"].entry_type
        )

        self.assertTrue(isinstance(entries["empty"], StorageFolder))
        self.assertEqual("folder", entries["empty"].entry_type)
        self.assertEqual(0, len(entries["empty"].children))

    def test_get_entries_with_filter(self):
        self._add_and_verify_file(
            "bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL, display="BP Case.stl"
        )
        self._add_and_verify_file(
            "bp_case.gcode", "bp_case.gcode", FILE_BP_CASE_GCODE, display="BP Case.gcode"
        )

        self._add_and_verify_folder("content", "content")
        self._add_and_verify_file(
            ("content", "crazyradio.stl"),
            "content" + "/crazyradio.stl",
            FILE_CRAZYRADIO_STL,
        )
        self._add_and_verify_file(
            ("content", "bp_case.gcode"),
            "content" + "/bp_case.gcode",
            FILE_BP_CASE_GCODE,
        )

        self._add_and_verify_folder("empty", "empty")

        def filter_machinecode(node: StorageEntry) -> bool:
            return node.entry_type == "machinecode"

        entries = self.storage.list_storage_entries(filter=filter_machinecode)

        self.assertTrue(3, len(entries))
        self.assertTrue("bp_case.gcode" in entries)
        self.assertTrue("content" in entries)
        self.assertTrue("empty" in entries)

        self.assertTrue(isinstance(entries["content"], StorageFolder))
        self.assertEqual("folder", entries["content"].entry_type)
        self.assertEqual(1, len(entries["content"].children))
        self.assertTrue("bp_case.gcode" in entries["content"].children)

        self.assertTrue(isinstance(entries["empty"], StorageFolder))
        self.assertEqual("folder", entries["empty"].entry_type)
        self.assertEqual(0, len(entries["empty"].children))

    def test_get_entries_without_recursive(self):
        self._add_and_verify_file(
            "bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL, display="BP Case.stl"
        )
        self._add_and_verify_file(
            "bp_case.gcode", "bp_case.gcode", FILE_BP_CASE_GCODE, display="BP Case.gcode"
        )

        self._add_and_verify_folder("content", "content")
        self._add_and_verify_file(
            ("content", "crazyradio.stl"),
            "content" + "/crazyradio.stl",
            FILE_CRAZYRADIO_STL,
        )

        self._add_and_verify_folder("empty", "empty")

        entries = self.storage.list_storage_entries(recursive=False)

        self.assertTrue(3, len(entries))
        self.assertTrue("bp_case.gcode" in entries)
        self.assertTrue("content" in entries)
        self.assertTrue("empty" in entries)

        self.assertTrue(isinstance(entries["content"], StorageFolder))
        self.assertEqual("folder", entries["content"].entry_type)
        self.assertEqual(0, len(entries["content"].children))
        self.assertNotEqual(0, entries["content"].size)

        self.assertTrue(isinstance(entries["empty"], StorageFolder))
        self.assertEqual("folder", entries["empty"].entry_type)
        self.assertEqual(0, len(entries["empty"].children))
        self.assertEqual(0, entries["empty"].size)

    @data(
        ("", ("", "")),
        ("/", ("", "")),
        ("some_file.gco", ("", "some_file.gco")),
        ("/some_file.gco", ("", "some_file.gco")),
        ("some/folder/and/some file.gco", ("some/folder/and", "some file.gco")),
        ("/some/folder/and/some file.gco", ("some/folder/and", "some file.gco")),
    )
    @unpack
    def test_split_path(self, input, expected):
        actual = self.storage.split_path(input)
        self.assertEqual(expected, actual)

    @data(
        (("", ""), ""),
        (("", "some_file.gco"), "some_file.gco"),
        (("/", "some_file.gco"), "some_file.gco"),
        (("some/folder/and", "some file.gco"), "some/folder/and/some file.gco"),
        (("/some/folder/and", "some file.gco"), "some/folder/and/some file.gco"),
    )
    @unpack
    def test_join_path(self, input, expected):
        actual = self.storage.join_path(*input)
        self.assertEqual(expected, actual)

    @data(
        ("some_file.gco", "some_file.gco", False),
        ("some file.gco", "some file.gco", False),
        (
            "some_file with (parentheses) and ümläuts and digits 123.gco",
            "some_file with (parentheses) and ümläuts and digits 123.gco",
            False,
        ),
        ("there is no b in häußge.gco", "there is no b in häußge.gco", False),
        ("some file.gco", "some_file.gco", True),
        (
            "some_file with (parentheses) and ümläuts and digits 123.gco",
            "some_file_with_(parentheses)_and_umlauts_and_digits_123.gco",
            True,
        ),
        ("there is no b in häußge.gco", "there_is_no_b_in_haussge.gco", True),
    )
    @unpack
    def test_sanitize_name(self, input, expected, really_universal):
        with _set_really_universal(self.storage, really_universal):
            actual = self.storage.sanitize_name(input)
        self.assertEqual(expected, actual)
        self.storage._really_universal = False

    @data("some/folder/still/left.gco", "also\\no\\backslashes.gco")
    def test_sanitize_name_invalid(self, input):
        try:
            self.storage.sanitize_name(input)
            self.fail("expected a ValueError")
        except ValueError as e:
            self.assertEqual("name must not contain / or \\", e.args[0])

    @data(
        ("folder/with/subfolder", "/folder/with/subfolder"),
        ("folder/with/subfolder/../other/folder", "/folder/with/other/folder"),
        ("/folder/with/leading/slash", "/folder/with/leading/slash"),
        ("folder/with/leading/dot", "/folder/with/leading/dot"),
    )
    @unpack
    def test_sanitize_path(self, input, expected):
        actual = self.storage.sanitize_path(input)
        self.assertTrue(actual.startswith(self.basefolder))
        self.assertEqual(
            expected, actual[len(self.basefolder) :].replace(os.path.sep, "/")
        )

    @data("../../folder/out/of/the/basefolder", "some/folder/../../../and/then/back")
    def test_sanitize_path_invalid(self, input):
        try:
            self.storage.sanitize_path(input)
            self.fail("expected a ValueError")
        except ValueError as e:
            self.assertTrue(e.args[0].startswith("path not contained in base folder: "))

    @data(
        ("", "/", "", False),
        (
            "some/folder/with/trailing/slash/",
            "/some/folder/with/trailing/slash",
            "",
            False,
        ),
        (("some", "folder", ""), "/some/folder", "", False),
        ("some/folder/and/some file.gco", "/some/folder/and", "some file.gco", False),
        (
            ("some", "folder", "and", "some file.gco"),
            "/some/folder/and",
            "some file.gco",
            False,
        ),
        ("some file.gco", "/", "some file.gco", False),
        (("some file.gco",), "/", "some file.gco", False),
        ("some/folder/and/some file.gco", "/some/folder/and", "some_file.gco", True),
        (
            ("some", "folder", "and", "some file.gco"),
            "/some/folder/and",
            "some_file.gco",
            True,
        ),
        ("some file.gco", "/", "some_file.gco", True),
        (("some file.gco",), "/", "some_file.gco", True),
    )
    @unpack
    def test_sanitize(self, input, expected_path, expected_name, really_universal):
        with _set_really_universal(self.storage, really_universal):
            actual = self.storage.sanitize(input)
        self.assertTrue(isinstance(actual, tuple))
        self.assertEqual(2, len(actual))

        actual_path, actual_name = actual
        self.assertTrue(actual_path.startswith(self.basefolder))
        actual_path = actual_path[len(self.basefolder) :].replace(os.path.sep, "/")
        if not actual_path.startswith("/"):
            # if the actual path originally was just the base folder, we just stripped
            # away everything, so let's add a / again so the behaviour matches the
            # other preprocessing of our test data here
            actual_path = "/" + actual_path

        self.assertEqual(expected_path, actual_path)
        self.assertEqual(expected_name, actual_name)

    def _add_and_verify_file(
        self, path, expected_path, file_object, overwrite=False, display=None
    ):
        """Adds a file to the storage and verifies the sanitized path."""
        sanitized_path = self._add_file(
            path, file_object, overwrite=overwrite, display=display
        )
        self.assertEqual(expected_path, sanitized_path)
        return sanitized_path

    def test_migrate_metadata_to_json(self):
        metadata = {"test.gco": {"notes": []}}
        yaml_path = os.path.join(self.basefolder, ".metadata.yaml")
        json_path = os.path.join(self.basefolder, ".metadata.json")

        # prepare
        import yaml

        with open(yaml_path, "w") as f:
            yaml.safe_dump(metadata, f)

        # migrate
        self.storage._migrate_metadata(self.basefolder)

        # verify
        self.assertTrue(os.path.exists(json_path))
        self.assertFalse(os.path.exists(yaml_path))

        import json

        with open(json_path, encoding="utf-8") as f:
            json_metadata = json.load(f)
        self.assertDictEqual(metadata, json_metadata)

    def _add_file(
        self, path, file_object, overwrite=False, display=None, progress_callback=None
    ):
        """
        Adds a file to the storage.

        Ensures file is present and metadata file is present.

        Returns sanitized path.
        """
        sanitized_path = self.storage.add_file(
            path,
            file_object,
            allow_overwrite=overwrite,
            display=display,
            progress_callback=progress_callback,
        )

        split_path = sanitized_path.split("/")
        if len(split_path) == 1:
            file_path = os.path.join(self.basefolder, split_path[0])
            folder_path = self.basefolder
        else:
            file_path = os.path.join(self.basefolder, os.path.join(*split_path))
            folder_path = os.path.join(self.basefolder, os.path.join(*split_path[:-1]))

        if display:
            # if we have a display value, this should cause metadata.json to be
            self.assertTrue(os.path.isfile(file_path))
            self.assertTrue(os.path.isfile(os.path.join(folder_path, ".metadata.json")))

            metadata = self.storage.get_metadata(sanitized_path)
            self.assertIsNotNone(metadata)

        return sanitized_path

    def _add_and_verify_folder(self, path, expected_path, display=None):
        """Adds a folder to the storage and verifies sanitized path."""
        sanitized_path = self._add_folder(path, display=display)
        self.assertEqual(expected_path, sanitized_path)
        return sanitized_path

    def _add_folder(self, path, display=None):
        """
        Adds a folder to the storage.

        Verifies existence of folder.

        Returns sanitized path.
        """
        sanitized_path = self.storage.add_folder(path, display=display)
        self.assertTrue(
            os.path.isdir(
                os.path.join(self.basefolder, os.path.join(*sanitized_path.split("/")))
            )
        )
        return sanitized_path


@contextmanager
def _set_really_universal(storage, value):
    orig = storage._really_universal
    try:
        storage._really_universal = value
        yield
    finally:
        storage._really_universal = orig
