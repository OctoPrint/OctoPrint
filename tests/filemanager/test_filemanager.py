__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import io
import unittest
from unittest import mock

import octoprint.filemanager
import octoprint.filemanager.util
import octoprint.settings


class FilemanagerMethodTest(unittest.TestCase):
    def setUp(self):
        # mock plugin manager
        self.plugin_manager_patcher = mock.patch("octoprint.plugin.plugin_manager")
        self.plugin_manager_getter = self.plugin_manager_patcher.start()

        self.plugin_manager = mock.MagicMock()

        hook_extensions = {
            "some_plugin": lambda: dict({"machinecode": {"foo": ["foo", "f"]}}),
            "other_plugin": lambda: dict({"model": {"amf": ["amf"]}}),
            "mime_map": lambda: {
                "mime_map": {
                    "mime_map_yes": octoprint.filemanager.ContentTypeMapping(
                        ["mime_map_yes"], "application/mime_map_yes"
                    )
                }
            },
            "mime_detect": lambda: dict(
                {
                    "machinecode": {
                        "mime_detect_yes": octoprint.filemanager.ContentTypeDetector(
                            ["mime_detect_yes"], lambda x: "application/mime_detect_yes"
                        ),
                        "mime_detect_no": octoprint.filemanager.ContentTypeDetector(
                            ["mime_detect_no"], lambda x: None
                        ),
                    }
                }
            ),
        }
        self.plugin_manager.get_hooks.return_value = hook_extensions

        self.plugin_manager_getter.return_value = self.plugin_manager

    def tearDown(self):
        self.plugin_manager_patcher.stop()

    def test_full_extension_tree(self):
        full = octoprint.filemanager.full_extension_tree()
        self.assertTrue("machinecode" in full)
        self.assertTrue("gcode" in full["machinecode"])
        self.assertTrue(
            isinstance(
                full["machinecode"]["gcode"], octoprint.filemanager.ContentTypeMapping
            )
        )
        self.assertSetEqual(
            {"gcode", "gco", "g"}, set(full["machinecode"]["gcode"].extensions)
        )
        self.assertTrue("foo" in full["machinecode"])
        self.assertTrue(isinstance(full["machinecode"]["foo"], list))
        self.assertSetEqual({"f", "foo"}, set(full["machinecode"]["foo"]))

        self.assertTrue("model" in full)
        self.assertTrue("amf" in full["model"])
        self.assertTrue(isinstance(full["model"]["amf"], list))
        self.assertSetEqual({"amf"}, set(full["model"]["amf"]))

    def test_get_mimetype(self):
        self.assertEqual(octoprint.filemanager.get_mime_type("foo.gcode"), "text/plain")
        self.assertEqual(
            octoprint.filemanager.get_mime_type("foo.unknown"), "application/octet-stream"
        )
        self.assertEqual(
            octoprint.filemanager.get_mime_type("foo.mime_map_yes"),
            "application/mime_map_yes",
        )
        self.assertEqual(
            octoprint.filemanager.get_mime_type("foo.mime_map_no"),
            "application/octet-stream",
        )
        self.assertEqual(
            octoprint.filemanager.get_mime_type("foo.mime_detect_yes"),
            "application/mime_detect_yes",
        )
        self.assertEqual(
            octoprint.filemanager.get_mime_type("foo.mime_detect_no"),
            "application/octet-stream",
        )

    def test_valid_file_type(self):
        self.assertTrue(octoprint.filemanager.valid_file_type("foo.amf", type="model"))
        self.assertTrue(octoprint.filemanager.valid_file_type("foo.amf", type="amf"))
        self.assertFalse(
            octoprint.filemanager.valid_file_type("foo.stl", type="machinecode")
        )
        self.assertTrue(
            octoprint.filemanager.valid_file_type("foo.foo", type="machinecode")
        )
        self.assertTrue(octoprint.filemanager.valid_file_type("foo.foo", type="foo"))
        self.assertTrue(octoprint.filemanager.valid_file_type("foo.foo"))
        self.assertTrue(octoprint.filemanager.valid_file_type("foo.mime_map_yes"))
        self.assertTrue(octoprint.filemanager.valid_file_type("foo.mime_detect_yes"))
        self.assertFalse(octoprint.filemanager.valid_file_type("foo.unknown"))

    def test_get_file_type(self):
        self.assertEqual(
            ["machinecode", "gcode"], octoprint.filemanager.get_file_type("foo.gcode")
        )
        self.assertEqual(
            ["machinecode", "gcode"], octoprint.filemanager.get_file_type("foo.gco")
        )
        self.assertEqual(
            ["machinecode", "foo"], octoprint.filemanager.get_file_type("foo.f")
        )
        self.assertEqual(["model", "amf"], octoprint.filemanager.get_file_type("foo.amf"))
        self.assertIsNone(octoprint.filemanager.get_file_type("foo.unknown"))

    def test_hook_failure(self):
        def hook():
            raise RuntimeError("Boo!")

        self.plugin_manager.get_hooks.return_value = {"hook": hook}

        with mock.patch("octoprint.filemanager.logging") as patched_logging:
            logger = mock.MagicMock()
            patched_logging.getLogger.return_value = logger

            octoprint.filemanager.get_all_extensions()

            self.assertEqual(1, len(logger.mock_calls))


class FileManagerTest(unittest.TestCase):
    def setUp(self):
        import octoprint.filemanager.storage
        import octoprint.printer.profile
        import octoprint.slicing

        self.addCleanup(self.cleanUp)

        # mock event manager
        self.event_manager_patcher = mock.patch("octoprint.filemanager.eventManager")
        event_manager = self.event_manager_patcher.start()
        event_manager.return_value.fire = mock.MagicMock()
        self.fire_event = event_manager.return_value.fire

        # mock plugin manager
        self.plugin_manager_patcher = mock.patch("octoprint.plugin.plugin_manager")
        self.plugin_manager = self.plugin_manager_patcher.start()

        # mock settings
        self.settings_patcher = mock.patch("octoprint.settings.settings")
        self.settings_getter = self.settings_patcher.start()

        self.settings = mock.create_autospec(octoprint.settings.Settings)
        self.settings.getBaseFolder.return_value = "/path/to/a/base_folder"

        self.settings_getter.return_value = self.settings

        self.analysis_queue = mock.MagicMock(spec=octoprint.filemanager.AnalysisQueue)

        self.slicing_manager = mock.MagicMock(spec=octoprint.slicing.SlicingManager)

        self.printer_profile_manager = mock.MagicMock(
            spec=octoprint.printer.profile.PrinterProfileManager
        )

        self.local_storage = mock.MagicMock(
            spec=octoprint.filemanager.storage.LocalFileStorage
        )
        self.local_storage.analysis_backlog = iter([])

        self.storage_managers = {}
        self.storage_managers[
            octoprint.filemanager.FileDestinations.LOCAL
        ] = self.local_storage

        self.file_manager = octoprint.filemanager.FileManager(
            self.analysis_queue,
            self.slicing_manager,
            self.printer_profile_manager,
            initial_storage_managers=self.storage_managers,
        )

    def cleanUp(self):
        self.event_manager_patcher.stop()
        self.plugin_manager_patcher.stop()
        self.settings_patcher.stop()

    def test_add_file(self):
        wrapper = object()

        self.local_storage.add_file.return_value = ("", "test.gcode")
        self.local_storage.path_on_disk.return_value = "prefix/test.gcode"
        self.local_storage.split_path.return_value = ("", "test.gcode")

        test_profile = {"id": "_default", "name": "My Default Profile"}
        self.printer_profile_manager.get_current_or_default.return_value = test_profile

        file_path = self.file_manager.add_file(
            octoprint.filemanager.FileDestinations.LOCAL, "test.gcode", wrapper
        )

        self.assertEqual(("", "test.gcode"), file_path)
        self.local_storage.add_file.assert_called_once_with(
            "test.gcode",
            wrapper,
            printer_profile=test_profile,
            allow_overwrite=False,
            links=None,
            display=None,
        )

        expected_events = [
            mock.call(
                octoprint.filemanager.Events.FILE_ADDED,
                {
                    "storage": octoprint.filemanager.FileDestinations.LOCAL,
                    "name": "test.gcode",
                    "path": "test.gcode",
                    "type": ["machinecode", "gcode"],
                },
            ),
            mock.call(octoprint.filemanager.Events.UPDATED_FILES, {"type": "printables"}),
        ]
        self.fire_event.call_args_list = expected_events

    def test_add_file_display(self):
        wrapper = object()

        self.local_storage.add_file.return_value = ("", "test.gcode")
        self.local_storage.path_on_disk.return_value = "prefix/test.gcode"
        self.local_storage.split_path.return_value = ("", "test.gcode")

        test_profile = {"id": "_default", "name": "My Default Profile"}
        self.printer_profile_manager.get_current_or_default.return_value = test_profile

        file_path = self.file_manager.add_file(
            octoprint.filemanager.FileDestinations.LOCAL,
            "test.gcode",
            wrapper,
            display="täst.gcode",
        )

        self.assertEqual(("", "test.gcode"), file_path)
        self.local_storage.add_file.assert_called_once_with(
            "test.gcode",
            wrapper,
            printer_profile=test_profile,
            allow_overwrite=False,
            links=None,
            display="täst.gcode",
        )

    def test_remove_file(self):
        self.local_storage.path_on_disk.return_value = "prefix/test.gcode"
        self.local_storage.split_path.return_value = ("", "test.gcode")

        self.file_manager.remove_file(
            octoprint.filemanager.FileDestinations.LOCAL, "test.gcode"
        )

        self.local_storage.remove_file.assert_called_once_with("test.gcode")
        self.analysis_queue.dequeue.assert_called_once()
        expected_events = [
            mock.call(
                octoprint.filemanager.Events.FILE_REMOVED,
                {
                    "storage": octoprint.filemanager.FileDestinations.LOCAL,
                    "name": "test.gcode",
                    "path": "test.gcode",
                    "type": ["machinecode", "gcode"],
                },
            ),
            mock.call(octoprint.filemanager.Events.UPDATED_FILES, {"type": "printables"}),
        ]
        self.fire_event.call_args_list = expected_events

    def test_add_folder(self):
        self.local_storage.add_folder.return_value = ("", "test_folder")
        self.local_storage.split_path.return_value = ("", "test_folder")

        folder_path = self.file_manager.add_folder(
            octoprint.filemanager.FileDestinations.LOCAL, "test_folder"
        )

        self.assertEqual(("", "test_folder"), folder_path)
        self.local_storage.add_folder.assert_called_once_with(
            "test_folder", ignore_existing=True, display=None
        )

        expected_events = [
            mock.call(
                octoprint.filemanager.Events.FOLDER_ADDED,
                {
                    "storage": octoprint.filemanager.FileDestinations.LOCAL,
                    "name": "test_folder",
                    "path": "test_folder",
                },
            ),
            mock.call(octoprint.filemanager.Events.UPDATED_FILES, {"type": "printables"}),
        ]
        self.fire_event.call_args_list = expected_events

    def test_add_folder_not_ignoring_existing(self):
        self.local_storage.add_folder.side_effect = RuntimeError("already there")

        with self.assertRaises(RuntimeError, msg="already there"):
            self.file_manager.add_folder(
                octoprint.filemanager.FileDestinations.LOCAL,
                "test_folder",
                ignore_existing=False,
            )
            self.fail("Expected an exception to occur!")
        self.local_storage.add_folder.assert_called_once_with(
            "test_folder", ignore_existing=False, display=None
        )

    def test_add_folder_display(self):
        self.local_storage.add_folder.side_effect = RuntimeError("already there")

        with self.assertRaises(RuntimeError, msg="already there"):
            self.file_manager.add_folder(
                octoprint.filemanager.FileDestinations.LOCAL,
                "test_folder",
                display="täst_folder",
            )
            self.fail("Expected an exception to occur!")
        self.local_storage.add_folder.assert_called_once_with(
            "test_folder", ignore_existing=True, display="täst_folder"
        )

    def test_remove_folder(self):
        self.local_storage.split_path.return_value = ("", "test_folder")

        self.file_manager.remove_folder(
            octoprint.filemanager.FileDestinations.LOCAL, "test_folder"
        )

        self.local_storage.remove_folder.assert_called_once_with(
            "test_folder", recursive=True
        )
        self.analysis_queue.dequeue_folder.assert_called_once_with(
            octoprint.filemanager.FileDestinations.LOCAL, "test_folder"
        )
        expected_events = [
            mock.call(
                octoprint.filemanager.Events.FOLDER_REMOVED,
                {
                    "storage": octoprint.filemanager.FileDestinations.LOCAL,
                    "name": "test_folder",
                    "path": "test_folder",
                },
            ),
            mock.call(octoprint.filemanager.Events.UPDATED_FILES, {"type": "printables"}),
        ]
        self.fire_event.call_args_list = expected_events

    def test_remove_folder_nonrecursive(self):
        self.local_storage.split_path.return_value = ("", "test_folder")

        self.file_manager.remove_folder(
            octoprint.filemanager.FileDestinations.LOCAL, "test_folder", recursive=False
        )

        self.local_storage.remove_folder.assert_called_once_with(
            "test_folder", recursive=False
        )
        self.analysis_queue.dequeue_folder.assert_called_once_with(
            octoprint.filemanager.FileDestinations.LOCAL, "test_folder"
        )

    @mock.patch("octoprint.util.atomic_write", create=True)
    @mock.patch("octoprint.util.yaml.save_to_file", create=True)
    @mock.patch("time.time")
    def test_save_recovery_data(
        self, mock_time, mock_yaml_save_to_file, mock_atomic_write
    ):
        import os

        now = 123456789
        path = "some_file.gco"
        pos = 1234
        recovery_file = os.path.join("/path/to/a/base_folder", "print_recovery_data.yaml")

        mock_atomic_write_handle = mock_atomic_write.return_value.__enter__.return_value
        mock_time.return_value = now
        self.local_storage.path_in_storage.return_value = path

        with mock.patch("builtins.open", mock.mock_open(), create=True):
            self.file_manager.save_recovery_data(
                octoprint.filemanager.FileDestinations.LOCAL, path, pos
            )
            mock_atomic_write.assert_called_with(
                recovery_file, max_permissions=0o666, mode="wt"
            )

        expected = {
            "origin": octoprint.filemanager.FileDestinations.LOCAL,
            "path": path,
            "pos": pos,
            "date": now,
        }

        mock_yaml_save_to_file.assert_called_with(
            expected,
            file=mock_atomic_write_handle,
            pretty=True,
        )

    @mock.patch("octoprint.util.atomic_write", create=True)
    @mock.patch("octoprint.util.yaml.save_to_file", create=True)
    @mock.patch("time.time")
    def test_save_recovery_data_with_error(
        self, mock_time, mock_yaml_safe_dump, mock_atomic_write
    ):
        path = "some_file.gco"
        pos = 1234

        self.local_storage.path_in_storage.return_value = path

        mock_yaml_safe_dump.side_effect = RuntimeError

        with mock.patch("builtins.open", mock.mock_open(), create=True):
            self.file_manager.save_recovery_data(
                octoprint.filemanager.FileDestinations.LOCAL, path, pos
            )

    @mock.patch("os.path.isfile")
    @mock.patch("os.remove")
    def test_delete_recovery_data(self, mock_remove, mock_isfile):
        import os

        recovery_file = os.path.join("/path/to/a/base_folder", "print_recovery_data.yaml")

        mock_isfile.return_value = True

        self.file_manager.delete_recovery_data()

        mock_remove.assert_called_with(recovery_file)

    @mock.patch("os.path.isfile")
    @mock.patch("os.remove")
    def test_delete_recovery_data_no_file(self, mock_remove, mock_isfile):
        mock_isfile.return_value = False

        self.file_manager.delete_recovery_data()

        self.assertFalse(mock_remove.called)

    @mock.patch("os.path.isfile")
    @mock.patch("os.remove")
    def test_delete_recovery_data_error(self, mock_remove, mock_isfile):
        mock_isfile.return_value = True
        mock_remove.side_effect = RuntimeError

        self.file_manager.delete_recovery_data()

    @mock.patch("os.path.isfile", return_value=True)
    def test_get_recovery_data(self, mock_isfile):
        import os

        recovery_file = os.path.join("/path/to/a/base_folder", "print_recovery_data.yaml")

        data = {
            "path": "some_path.gco",
            "origin": "local",
            "pos": 1234,
            "date": 123456789,
        }

        # moved safe_load to here so we could mock up the return value properly
        with mock.patch("octoprint.util.yaml.load_from_file", return_value=data) as n:
            result = self.file_manager.get_recovery_data()

            self.assertDictEqual(data, result)
            n.assert_called_with(path=recovery_file)
            mock_isfile.assert_called_with(recovery_file)

    @mock.patch("os.path.isfile")
    def test_get_recovery_data_no_file(self, mock_isfile):
        mock_isfile.return_value = False

        result = self.file_manager.get_recovery_data()

        self.assertIsNone(result)

    @mock.patch("os.path.isfile")
    @mock.patch("octoprint.util.yaml.load_from_file")
    @mock.patch("os.remove")
    def test_get_recovery_data_broken_file(
        self, mock_remove, mock_yaml_load, mock_isfile
    ):
        import os

        recovery_file = os.path.join("/path/to/a/base_folder", "print_recovery_data.yaml")

        mock_isfile.return_value = True
        mock_yaml_load.side_effect = RuntimeError

        result = self.file_manager.get_recovery_data()

        self.assertIsNone(result)
        mock_remove.assert_called_with(recovery_file)

    def test_get_metadata(self):
        expected = {"key": "value"}
        self.local_storage.get_metadata.return_value = expected

        metadata = self.file_manager.get_metadata(
            octoprint.filemanager.FileDestinations.LOCAL, "test.file"
        )

        self.assertEqual(metadata, expected)
        self.local_storage.get_metadata.assert_called_once_with("test.file")

    @mock.patch("octoprint.filemanager.util.atomic_write")
    @mock.patch("io.FileIO")
    @mock.patch("shutil.copyfileobj")
    @mock.patch("os.remove")
    @mock.patch("tempfile.NamedTemporaryFile")
    @mock.patch("os.chmod")
    def test_slice(
        self,
        mocked_chmod,
        mocked_tempfile,
        mocked_os,
        mocked_shutil,
        mocked_fileio,
        mocked_atomic_write,
    ):
        callback = mock.MagicMock()
        callback_args = ("one", "two", "three")

        # mock temporary file
        temp_file = mock.MagicMock()
        temp_file.name = "tmp.file"
        mocked_tempfile.return_value = temp_file

        # mock metadata on local storage
        metadata = {"hash": "aabbccddeeff"}
        self.local_storage.get_metadata.return_value = metadata

        # mock printer profile
        expected_printer_profile = {"id": "_default", "name": "My Default Profile"}
        self.printer_profile_manager.get_current_or_default.return_value = (
            expected_printer_profile
        )
        self.printer_profile_manager.get.return_value = None

        # mock get_absolute_path method on local storage
        def path_on_disk(path):
            if isinstance(path, tuple):
                import os

                joined_path = ""
                for part in path:
                    joined_path = os.path.join(joined_path, part)
                path = joined_path
            return "prefix/" + path

        self.local_storage.path_on_disk.side_effect = path_on_disk

        # mock split_path method on local storage - no folder support
        def split_path(path):
            return "", path

        self.local_storage.split_path.side_effect = split_path

        # mock add_file method on local storage
        def add_file(
            path,
            file_obj,
            printer_profile=None,
            links=None,
            allow_overwrite=False,
            display=None,
        ):
            file_obj.save("prefix/" + path)
            return path

        self.local_storage.add_file.side_effect = add_file

        # mock slice method on slicing manager
        def slice(
            slicer_name,
            source_path,
            dest_path,
            profile,
            done_cb,
            printer_profile_id=None,
            position=None,
            callback_args=None,
            overrides=None,
            on_progress=None,
            on_progress_args=None,
            on_progress_kwargs=None,
        ):
            self.assertEqual("some_slicer", slicer_name)
            self.assertEqual("prefix/source.file", source_path)
            self.assertEqual("tmp.file", dest_path)
            self.assertIsNone(profile)
            self.assertIsNone(overrides)
            self.assertIsNone(printer_profile_id)
            self.assertIsNone(position)
            self.assertIsNotNone(on_progress)
            self.assertIsNotNone(on_progress_args)
            self.assertTupleEqual(
                (
                    "some_slicer",
                    octoprint.filemanager.FileDestinations.LOCAL,
                    "source.file",
                    octoprint.filemanager.FileDestinations.LOCAL,
                    "dest.file",
                ),
                on_progress_args,
            )
            self.assertIsNone(on_progress_kwargs)

            if not callback_args:
                callback_args = ()
            done_cb(*callback_args)

        self.slicing_manager.slice.side_effect = slice

        ##~~ execute tested method
        self.file_manager.slice(
            "some_slicer",
            octoprint.filemanager.FileDestinations.LOCAL,
            "source.file",
            octoprint.filemanager.FileDestinations.LOCAL,
            "dest.file",
            callback=callback,
            callback_args=callback_args,
        )

        # assert that events where fired
        expected_events = [
            mock.call(
                octoprint.filemanager.Events.SLICING_STARTED,
                {"stl": "source.file", "gcode": "dest.file", "progressAvailable": False},
            ),
            mock.call(
                octoprint.filemanager.Events.SLICING_DONE,
                {"stl": "source.file", "gcode": "dest.file", "time": 15.694000005722046},
            ),
            mock.call(
                octoprint.filemanager.Events.FILE_ADDED,
                {
                    "storage": octoprint.filemanager.FileDestinations.LOCAL,
                    "name": "dest.file",
                    "path": "dest.file",
                    "type": None,
                },
            ),
        ]
        self.fire_event.call_args_list = expected_events

        # assert that model links were added
        expected_links = [("model", {"name": "source.file"})]
        self.local_storage.add_file.assert_called_once_with(
            "dest.file",
            mock.ANY,
            printer_profile=expected_printer_profile,
            allow_overwrite=True,
            links=expected_links,
            display=None,
        )

        # assert that the generated gcode was manipulated as required
        expected_atomic_write_calls = [mock.call("prefix/dest.file", mode="wb")]
        self.assertEqual(mocked_atomic_write.call_args_list, expected_atomic_write_calls)
        # mocked_open.return_value.write.assert_called_once_with(";Generated from source.file aabbccddeeff\r")

        # assert that shutil was asked to copy the concatenated multistream
        self.assertEqual(2, len(mocked_shutil.call_args_list))
        self.assertTrue(isinstance(mocked_shutil.call_args_list[0][0][0], io.BytesIO))

        # assert that the temporary file was deleted
        mocked_os.assert_called_once_with("tmp.file")

        # assert that our callback was called with the supplied arguments
        callback.assert_called_once_with(*callback_args)

    @mock.patch("os.remove")
    @mock.patch("tempfile.NamedTemporaryFile")
    def test_slice_error(self, mocked_tempfile, mocked_os):
        callback = mock.MagicMock()
        callback_args = ("one", "two", "three")

        # mock temporary file
        temp_file = mock.MagicMock()
        temp_file.name = "tmp.file"
        mocked_tempfile.return_value = temp_file

        # mock path_on_disk method on local storage
        def path_on_disk(path):
            if isinstance(path, tuple):
                import os

                joined_path = ""
                for part in path:
                    joined_path = os.path.join(joined_path, part)
                path = joined_path
            return "prefix/" + path

        self.local_storage.path_on_disk.side_effect = path_on_disk

        # mock slice method on slicing manager
        def slice(
            slicer_name,
            source_path,
            dest_path,
            profile,
            done_cb,
            printer_profile_id=None,
            position=None,
            callback_args=None,
            overrides=None,
            on_progress=None,
            on_progress_args=None,
            on_progress_kwargs=None,
        ):
            self.assertEqual("some_slicer", slicer_name)
            self.assertEqual("prefix/source.file", source_path)
            self.assertEqual("tmp.file", dest_path)
            self.assertIsNone(profile)
            self.assertIsNone(overrides)
            self.assertIsNone(printer_profile_id)
            self.assertIsNone(position)
            self.assertIsNotNone(on_progress)
            self.assertIsNotNone(on_progress_args)
            self.assertTupleEqual(
                (
                    "some_slicer",
                    octoprint.filemanager.FileDestinations.LOCAL,
                    "source.file",
                    octoprint.filemanager.FileDestinations.LOCAL,
                    "dest.file",
                ),
                on_progress_args,
            )
            self.assertIsNone(on_progress_kwargs)

            if not callback_args:
                callback_args = ()
            done_cb(*callback_args, _error="Something went wrong")

        self.slicing_manager.slice.side_effect = slice

        ##~~ execute tested method
        self.file_manager.slice(
            "some_slicer",
            octoprint.filemanager.FileDestinations.LOCAL,
            "source.file",
            octoprint.filemanager.FileDestinations.LOCAL,
            "dest.file",
            callback=callback,
            callback_args=callback_args,
        )

        # assert that events where fired
        expected_events = [
            mock.call(
                octoprint.filemanager.Events.SLICING_STARTED,
                {"stl": "source.file", "gcode": "dest.file"},
            ),
            mock.call(
                octoprint.filemanager.Events.SLICING_FAILED,
                {
                    "stl": "source.file",
                    "gcode": "dest.file",
                    "reason": "Something went wrong",
                },
            ),
        ]
        self.fire_event.call_args_list = expected_events

        # assert that the temporary file was deleted
        mocked_os.assert_called_once_with("tmp.file")
