__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import os
import os.path
import unittest
from contextlib import contextmanager
from unittest import mock

from ddt import data, ddt, unpack

from octoprint.filemanager.storage import LocalFileStorage, StorageError


class FileWrapper:
    def __init__(self, filename):
        self.path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "_files", filename
        )

        import hashlib

        blocksize = 65536
        hash = hashlib.sha1()
        with open(self.path, "rb") as f:
            buffer = f.read(blocksize)
            while len(buffer) > 0:
                hash.update(buffer)
                buffer = f.read(blocksize)
        self.hash = hash.hexdigest()

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

    def test_add_file_with_web(self):
        import time

        href = "http://www.example.com"
        retrieved = time.time()

        stl_name = self._add_and_verify_file(
            "bp_case.stl",
            "bp_case.stl",
            FILE_BP_CASE_STL,
            links=[("web", {"href": href, "retrieved": retrieved})],
        )
        stl_metadata = self.storage.get_metadata(stl_name)

        self.assertIsNotNone(stl_metadata)
        self.assertEqual(1, len(stl_metadata["links"]))
        link = stl_metadata["links"][0]
        self.assertTrue("web", link["rel"])
        self.assertTrue("href" in link)
        self.assertEqual(href, link["href"])
        self.assertTrue("retrieved" in link)
        self.assertEqual(retrieved, link["retrieved"])

    def test_add_file_with_association(self):
        stl_name = self._add_and_verify_file(
            "bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL
        )
        gcode_name = self._add_and_verify_file(
            "bp_case.gcode",
            "bp_case.gcode",
            FILE_BP_CASE_GCODE,
            links=[("model", {"name": stl_name})],
        )

        stl_metadata = self.storage.get_metadata(stl_name)
        gcode_metadata = self.storage.get_metadata(gcode_name)

        # forward link
        self.assertEqual(1, len(gcode_metadata["links"]))
        link = gcode_metadata["links"][0]
        self.assertEqual("model", link["rel"])
        self.assertTrue("name" in link)
        self.assertEqual(stl_name, link["name"])
        self.assertTrue("hash" in link)
        self.assertEqual(FILE_BP_CASE_STL.hash, link["hash"])

        # reverse link
        self.assertEqual(1, len(stl_metadata["links"]))
        link = stl_metadata["links"][0]
        self.assertEqual("machinecode", link["rel"])
        self.assertTrue("name" in link)
        self.assertEqual(gcode_name, link["name"])
        self.assertTrue("hash" in link)
        self.assertEqual(FILE_BP_CASE_GCODE.hash, link["hash"])

    def test_remove_file(self):
        stl_name = self._add_and_verify_file(
            "bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL
        )
        gcode_name = self._add_and_verify_file(
            "bp_case.gcode",
            "bp_case.gcode",
            FILE_BP_CASE_GCODE,
            links=[("model", {"name": stl_name})],
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

        self.assertEqual(0, len(gcode_metadata["links"]))

    def test_copy_file(self):
        self._add_file("bp_case.stl", FILE_BP_CASE_STL)
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
        self._add_file("bp_case.stl", FILE_BP_CASE_STL)
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
            self.assertEqual(e.code, StorageError.INVALID_DESTINATION)

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
            self.assertIsNotNone(self.storage.get_metadata(other_stl_name))

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
        self._add_file("source/crazyradio.stl", FILE_CRAZYRADIO_STL)

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
        self._add_file("source/crazyradio.stl", FILE_CRAZYRADIO_STL)

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
            self.assertEqual(e.code, StorageError.INVALID_DESTINATION)

    def test_list(self):
        bp_case_stl = self._add_and_verify_file(
            "bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL
        )
        self._add_and_verify_file(
            "bp_case.gcode",
            "bp_case.gcode",
            FILE_BP_CASE_GCODE,
            links=[("model", {"name": bp_case_stl})],
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
        self.assertEqual(FILE_BP_CASE_STL.hash, file_list["bp_case.stl"]["hash"])

        self.assertEqual("machinecode", file_list["bp_case.gcode"]["type"])
        self.assertEqual(FILE_BP_CASE_GCODE.hash, file_list["bp_case.gcode"]["hash"])

        self.assertEqual("folder", file_list[content_folder]["type"])
        self.assertEqual(1, len(file_list[content_folder]["children"]))
        self.assertTrue("crazyradio.stl" in file_list["content"]["children"])
        self.assertEqual(
            "model", file_list["content"]["children"]["crazyradio.stl"]["type"]
        )
        self.assertEqual(
            FILE_CRAZYRADIO_STL.hash,
            file_list["content"]["children"]["crazyradio.stl"]["hash"],
        )

        self.assertEqual("folder", file_list["empty"]["type"])
        self.assertEqual(0, len(file_list["empty"]["children"]))

    def test_list_with_filter(self):
        bp_case_stl = self._add_and_verify_file(
            "bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL
        )
        self._add_and_verify_file(
            "bp_case.gcode",
            "bp_case.gcode",
            FILE_BP_CASE_GCODE,
            links=[("model", {"name": bp_case_stl})],
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

        def filter_machinecode(node):
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
        bp_case_stl = self._add_and_verify_file(
            "bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL
        )
        self._add_and_verify_file(
            "bp_case.gcode",
            "bp_case.gcode",
            FILE_BP_CASE_GCODE,
            links=[("model", {"name": bp_case_stl})],
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

    def test_add_link_model(self):
        stl_name = self._add_and_verify_file(
            "bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL
        )
        gcode_name = self._add_and_verify_file(
            "bp_case.gcode", "bp_case.gcode", FILE_BP_CASE_GCODE
        )

        self.storage.add_link(gcode_name, "model", {"name": stl_name})

        stl_metadata = self.storage.get_metadata(stl_name)
        gcode_metadata = self.storage.get_metadata(gcode_name)

        # forward link
        self.assertEqual(1, len(gcode_metadata["links"]))
        link = gcode_metadata["links"][0]
        self.assertEqual("model", link["rel"])
        self.assertTrue("name" in link)
        self.assertEqual(stl_name, link["name"])
        self.assertTrue("hash" in link)
        self.assertEqual(FILE_BP_CASE_STL.hash, link["hash"])

        # reverse link
        self.assertEqual(1, len(stl_metadata["links"]))
        link = stl_metadata["links"][0]
        self.assertEqual("machinecode", link["rel"])
        self.assertTrue("name" in link)
        self.assertEqual(gcode_name, link["name"])
        self.assertTrue("hash" in link)
        self.assertEqual(FILE_BP_CASE_GCODE.hash, link["hash"])

    def test_add_link_machinecode(self):
        stl_name = self._add_and_verify_file(
            "bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL
        )
        gcode_name = self._add_and_verify_file(
            "bp_case.gcode", "bp_case.gcode", FILE_BP_CASE_GCODE
        )

        self.storage.add_link(stl_name, "machinecode", {"name": gcode_name})

        stl_metadata = self.storage.get_metadata(stl_name)
        gcode_metadata = self.storage.get_metadata(gcode_name)

        # forward link
        self.assertEqual(1, len(gcode_metadata["links"]))
        link = gcode_metadata["links"][0]
        self.assertEqual("model", link["rel"])
        self.assertTrue("name" in link)
        self.assertEqual(stl_name, link["name"])
        self.assertTrue("hash" in link)
        self.assertEqual(FILE_BP_CASE_STL.hash, link["hash"])

        # reverse link
        self.assertEqual(1, len(stl_metadata["links"]))
        link = stl_metadata["links"][0]
        self.assertEqual("machinecode", link["rel"])
        self.assertTrue("name" in link)
        self.assertEqual(gcode_name, link["name"])
        self.assertTrue("hash" in link)
        self.assertEqual(FILE_BP_CASE_GCODE.hash, link["hash"])

    def test_remove_link(self):
        stl_name = self._add_and_verify_file(
            "bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL
        )

        self.storage.add_link(stl_name, "web", {"href": "http://www.example.com"})
        self.storage.add_link(stl_name, "web", {"href": "http://www.example2.com"})

        stl_metadata = self.storage.get_metadata(stl_name)
        self.assertEqual(2, len(stl_metadata["links"]))

        self.storage.remove_link(stl_name, "web", {"href": "http://www.example.com"})

        stl_metadata = self.storage.get_metadata(stl_name)
        self.assertEqual(1, len(stl_metadata["links"]))

        self.storage.remove_link(stl_name, "web", {"href": "wrong_href"})

        stl_metadata = self.storage.get_metadata(stl_name)
        self.assertEqual(1, len(stl_metadata["links"]))

    def test_remove_link_bidirectional(self):
        stl_name = self._add_and_verify_file(
            "bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL
        )
        gcode_name = self._add_and_verify_file(
            "bp_case.gcode", "bp_case.gcode", FILE_BP_CASE_GCODE
        )

        self.storage.add_link(stl_name, "machinecode", {"name": gcode_name})
        self.storage.add_link(stl_name, "web", {"href": "http://www.example.com"})

        stl_metadata = self.storage.get_metadata(stl_name)
        gcode_metadata = self.storage.get_metadata(gcode_name)

        self.assertEqual(1, len(gcode_metadata["links"]))
        self.assertEqual(2, len(stl_metadata["links"]))

        self.storage.remove_link(
            gcode_name, "model", {"name": stl_name, "hash": FILE_BP_CASE_STL.hash}
        )

        stl_metadata = self.storage.get_metadata(stl_name)
        gcode_metadata = self.storage.get_metadata(gcode_name)

        self.assertEqual(0, len(gcode_metadata["links"]))
        self.assertEqual(1, len(stl_metadata["links"]))

    @data(
        ("some_file.gco", "some_file.gco", False),
        ("some file.gco", "some file.gco", False),
        (
            "some_file with (parentheses) and ümläuts and digits 123.gco",
            "some_file with (parentheses) and ümläuts and digits 123.gco",
            False,
        ),
        ("pengüino pequeño.stl", "pengüino pequeño.stl", False),
        ("some file.gco", "some_file.gco", True),
        (
            "some_file with (parentheses) and ümläuts and digits 123.gco",
            "some_file_with_(parentheses)_and_umlauts_and_digits_123.gco",
            True,
        ),
        ("pengüino pequeño.stl", "penguino_pequeno.stl", True),
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
        self, path, expected_path, file_object, links=None, overwrite=False, display=None
    ):
        """Adds a file to the storage and verifies the sanitized path."""
        sanitized_path = self._add_file(
            path, file_object, links=links, overwrite=overwrite, display=display
        )
        self.assertEqual(expected_path, sanitized_path)
        return sanitized_path

    def test_migrate_metadata_to_json(self):
        metadata = {"test.gco": {"hash": "aabbccddeeff", "links": [], "notes": []}}
        yaml_path = os.path.join(self.basefolder, ".metadata.yaml")
        json_path = os.path.join(self.basefolder, ".metadata.json")

        # prepare
        import yaml

        with open(yaml_path, "wt") as f:
            yaml.safe_dump(metadata, f)

        # migrate
        self.storage._migrate_metadata(self.basefolder)

        # verify
        self.assertTrue(os.path.exists(json_path))
        self.assertFalse(os.path.exists(yaml_path))  # TODO 1.3.10 change to assertFalse

        import json

        with open(json_path, encoding="utf-8") as f:
            json_metadata = json.load(f)
        self.assertDictEqual(metadata, json_metadata)

    def _add_file(self, path, file_object, links=None, overwrite=False, display=None):
        """
        Adds a file to the storage.

        Ensures file is present, metadata is present, hash and links (if applicable)
        are populated correctly.

        Returns sanitized path.
        """
        sanitized_path = self.storage.add_file(
            path, file_object, links=links, allow_overwrite=overwrite, display=display
        )

        split_path = sanitized_path.split("/")
        if len(split_path) == 1:
            file_path = os.path.join(self.basefolder, split_path[0])
            folder_path = self.basefolder
        else:
            file_path = os.path.join(self.basefolder, os.path.join(*split_path))
            folder_path = os.path.join(self.basefolder, os.path.join(*split_path[:-1]))

        self.assertTrue(os.path.isfile(file_path))
        self.assertTrue(os.path.isfile(os.path.join(folder_path, ".metadata.json")))

        metadata = self.storage.get_metadata(sanitized_path)
        self.assertIsNotNone(metadata)

        # assert hash
        self.assertTrue("hash" in metadata)
        self.assertEqual(file_object.hash, metadata["hash"])

        # assert presence of links if supplied
        if links:
            self.assertTrue("links" in metadata)

        return sanitized_path

    def _add_and_verify_folder(self, path, expected_path, display=None):
        """Adds a folder to the storage and verifies sanitized path."""
        sanitized_path = self._add_folder(path, display=display)
        self.assertEqual(expected_path, sanitized_path)
        return sanitized_path

    def _add_folder(self, path, display=None):
        """
        Adds a folder to the storage.

        Verifies existance of folder.

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
