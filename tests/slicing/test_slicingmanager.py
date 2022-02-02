__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest
from unittest import mock

import octoprint.slicing


class TestSlicingManager(unittest.TestCase):
    def setUp(self):
        self.addCleanup(self.cleanUp)

        import tempfile

        self.profile_path = tempfile.mkdtemp()

        self.slicer_plugin = mock.MagicMock()
        self.slicer_plugin.get_slicer_properties.return_value = {
            "type": "mock",
            "name": "Mock",
            "same_device": True,
        }
        self.slicer_plugin.is_slicer_configured.return_value = True

        # mock plugin manager
        self.plugin_manager_patcher = mock.patch("octoprint.plugin.plugin_manager")
        self.plugin_manager = self.plugin_manager_patcher.start()
        self._mock_slicer_plugins(self.slicer_plugin)

        # mock profile manager
        import octoprint.printer.profile

        self.printer_profile_manager = mock.MagicMock(
            spec=octoprint.printer.profile.PrinterProfileManager
        )

        # mock settings
        self.settings_patcher = mock.patch("octoprint.slicing.settings")
        settings = self.settings_patcher.start()
        self.settings = settings.return_value

        self.slicing_manager = octoprint.slicing.SlicingManager(
            self.profile_path, self.printer_profile_manager
        )
        self.slicing_manager.initialize()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.profile_path)

    def cleanUp(self):
        self.settings_patcher.stop()
        self.plugin_manager_patcher.stop()

    def _mock_slicer_plugins(self, *plugins):
        def get_implementations(*types):
            import octoprint.plugin

            if octoprint.plugin.SlicerPlugin in types:
                return plugins
            return {}

        self.plugin_manager.return_value.get_implementations.side_effect = (
            get_implementations
        )

    def test_registered_slicers(self):
        self.assertEqual(["mock"], self.slicing_manager.registered_slicers)

    def test_slicing_enabled(self):
        self.assertTrue(self.slicing_manager.slicing_enabled)

    def test_default_slicer(self):
        def get(path):
            if path == ["slicing", "defaultSlicer"]:
                return "mock"
            else:
                return None

        self.settings.get.side_effect = get

        self.assertEqual("mock", self.slicing_manager.default_slicer)

    def test_default_slicer_unknown(self):
        def get(path):
            if path == ["slicing", "defaultSlicer"]:
                return "unknown"
            else:
                return None

        self.settings.get.side_effect = get

        self.assertIsNone(self.slicing_manager.default_slicer)

    @mock.patch("threading.Thread")
    @mock.patch("tempfile.NamedTemporaryFile")
    @mock.patch("os.remove")
    def test_slice(self, mocked_os_remove, mocked_tempfile, mocked_thread):
        # mock temporary file
        temp_file = mock.MagicMock()
        temp_file.name = "tmp.file"
        mocked_tempfile.return_value = temp_file

        # mock retrieval of default profile
        def get(path):
            return {}

        self.settings.get.side_effect = get

        default_profile = octoprint.slicing.SlicingProfile(
            "mock", "default", {"layer_height": 0.2, "fill_density": 40}
        )
        self.slicer_plugin.get_slicer_default_profile.return_value = default_profile

        # mock threading
        class MockThread:
            def __init__(self):
                self.target = None
                self.args = None
                self.mock = None

            def constructor(self, target=None, args=None):
                self.target = target
                self.args = args
                self.mock = mock.MagicMock()
                self.mock.start.side_effect = self.start
                return self.mock

            def start(self):
                self.target(*self.args)

        mock_thread = MockThread()
        mocked_thread.side_effect = mock_thread.constructor

        # mock slicing
        self.slicer_plugin.do_slice.return_value = True, None

        # mock printer profile manager
        printer_profile = {"_id": "mock_printer", "_name": "Mock Printer Profile"}

        def get_printer_profile(printer_profile_id):
            self.assertEqual("mock_printer", printer_profile_id)
            return printer_profile

        self.printer_profile_manager.get.side_effect = get_printer_profile

        ##~~ call tested method
        slicer_name = "mock"
        source_path = "prefix/source.file"
        dest_path = "prefix/dest.file"
        profile_name = "dummy_profile"
        printer_profile_id = "mock_printer"
        position = {"x": 10, "y": 20}
        callback = mock.MagicMock()
        callback_args = ("one", "two", "three")
        callback_kwargs = {"foo": "bar"}
        overrides = {"layer_height": 0.5}

        self.slicing_manager.slice(
            slicer_name,
            source_path,
            dest_path,
            profile_name,
            callback,
            printer_profile_id=printer_profile_id,
            position=position,
            callback_args=callback_args,
            callback_kwargs=callback_kwargs,
            overrides=overrides,
        )

        # assert that temporary profile was created properly
        self.slicer_plugin.save_slicer_profile.assert_called_once_with(
            "tmp.file", default_profile, overrides=overrides
        )
        # assert that slicing thread was created properly
        mocked_thread.assert_called_once_with(
            target=mock.ANY,
            args=(
                self.slicer_plugin,
                source_path,
                dest_path,
                profile_name,
                overrides,
                printer_profile,
                position,
                callback,
                callback_args,
                callback_kwargs,
            ),
        )
        self.assertTrue(mock_thread.mock.daemon)
        self.assertEqual(mock_thread.mock.start.call_count, 1)

        # assert that slicer was called correctly
        self.slicer_plugin.do_slice.assert_called_once_with(
            source_path,
            printer_profile,
            machinecode_path=dest_path,
            profile_path="tmp.file",
            position=position,
            on_progress=None,
            on_progress_args=None,
            on_progress_kwargs=None,
        )

        # assert that temporary profile was deleted again
        mocked_os_remove.assert_called_once_with("tmp.file")

        # assert that callback was called property
        callback.assert_called_once_with(*callback_args, **callback_kwargs)
