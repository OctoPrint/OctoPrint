# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import unittest
import mock

import octoprint.filemanager

class FileManagerTest(unittest.TestCase):

	def setUp(self):
		import octoprint.slicing
		import octoprint.filemanager.storage

		self.addCleanup(self.cleanUp)

		# mock event manager
		self.event_manager_patcher = mock.patch("octoprint.filemanager.eventManager")
		event_manager = self.event_manager_patcher.start()
		event_manager.return_value.fire = mock.MagicMock()
		self.fire_event = event_manager.return_value.fire

		self.analysis_queue = mock.MagicMock(spec=octoprint.filemanager.AnalysisQueue)

		self.slicing_manager = mock.MagicMock(spec=octoprint.slicing.SlicingManager)

		self.local_storage = mock.MagicMock(spec=octoprint.filemanager.storage.LocalFileStorage)
		self.local_storage.analysis_backlog = iter([])

		self.storage_managers = dict()
		self.storage_managers[octoprint.filemanager.FileDestinations.LOCAL] = self.local_storage

		self.file_manager = octoprint.filemanager.FileManager(self.analysis_queue, self.slicing_manager, initial_storage_managers=self.storage_managers)

	def cleanUp(self):
		self.event_manager_patcher.stop()

	def test_add_file(self):
		wrapper = object()

		self.local_storage.add_file.return_value = ("", "test.file")
		self.local_storage.get_absolute_path.return_value = "prefix/test.file"

		file_path = self.file_manager.add_file(octoprint.filemanager.FileDestinations.LOCAL, "test.file", wrapper)

		self.assertEquals(("", "test.file"), file_path)
		self.local_storage.add_file.assert_called_once_with("test.file", wrapper, allow_overwrite=False, links=None)
		self.fire_event.assert_called_once_with(octoprint.filemanager.Events.UPDATED_FILES, dict(type="printables"))

	def test_remove_file(self):
		self.file_manager.remove_file(octoprint.filemanager.FileDestinations.LOCAL, "test.file")

		self.local_storage.remove_file.assert_called_once_with("test.file")
		self.fire_event.assert_called_once_with(octoprint.filemanager.Events.UPDATED_FILES, dict(type="printables"))

	def test_add_folder(self):
		self.local_storage.add_folder.return_value = ("", "test_folder")

		folder_path = self.file_manager.add_folder(octoprint.filemanager.FileDestinations.LOCAL, "test_folder")

		self.assertEquals(("", "test_folder"), folder_path)
		self.local_storage.add_folder.assert_called_once_with("test_folder", ignore_existing=True)
		self.fire_event.assert_called_once_with(octoprint.filemanager.Events.UPDATED_FILES, dict(type="printables"))

	def test_add_folder_not_ignoring_existing(self):
		self.local_storage.add_folder.side_effect = RuntimeError("already there")

		try:
			self.file_manager.add_folder(octoprint.filemanager.FileDestinations.LOCAL, "test_folder", ignore_existing=False)
			self.fail("Expected an exception to occur!")
		except RuntimeError as e:
			self.assertEquals("already there", e.message)
		self.local_storage.add_folder.assert_called_once_with("test_folder", ignore_existing=False)

	def test_remove_folder(self):
		self.file_manager.remove_folder(octoprint.filemanager.FileDestinations.LOCAL, "test_folder")

		self.local_storage.remove_folder.assert_called_once_with("test_folder", recursive=True)
		self.fire_event.assert_called_once_with(octoprint.filemanager.Events.UPDATED_FILES, dict(type="printables"))

	def test_remove_folder_nonrecursive(self):
		self.file_manager.remove_folder(octoprint.filemanager.FileDestinations.LOCAL, "test_folder", recursive=False)
		self.local_storage.remove_folder.assert_called_once_with("test_folder", recursive=False)

	def test_get_metadata(self):
		expected = dict(key="value")
		self.local_storage.get_metadata.return_value = expected

		metadata = self.file_manager.get_metadata(octoprint.filemanager.FileDestinations.LOCAL, "test.file")

		self.assertEquals(metadata, expected)
		self.local_storage.get_metadata.assert_called_once_with("test.file")

	@mock.patch("__builtin__.open", new_callable=mock.mock_open)
	@mock.patch("shutil.copyfileobj")
	@mock.patch("os.remove")
	@mock.patch("tempfile.NamedTemporaryFile")
	@mock.patch("time.time", side_effect=[1411979916.422, 1411979932.116])
	def test_slice(self, mocked_time, mocked_tempfile, mocked_os, mocked_shutil, mocked_open):
		callback = mock.MagicMock()
		callback_args = ("one", "two", "three")

		# mock temporary file
		temp_file = mock.MagicMock()
		temp_file.name = "tmp.file"
		mocked_tempfile.return_value = temp_file

		# mock metadata on local storage
		metadata = dict(hash="aabbccddeeff")
		self.local_storage.get_metadata.return_value = metadata

		# mock get_absolute_path method on local storage
		def get_absolute_path(path):
			if isinstance(path, tuple):
				import os
				joined_path = ""
				for part in path:
					joined_path = os.path.join(joined_path, part)
				path = joined_path
			return "prefix/" + path
		self.local_storage.get_absolute_path.side_effect = get_absolute_path

		# mock split_path method on local storage
		def split_path(path):
			return "", path
		self.local_storage.split_path.side_effect = split_path

		# mock add_file method on local storage
		def add_file(path, file_obj, links=None, allow_overwrite=False):
			file_obj.save("prefix/" + path)
			return "", path
		self.local_storage.add_file.side_effect = add_file

		# mock slice method on slicing manager
		def slice(slicer_name, source_path, dest_path, profile, done_cb, callback_args=None, overrides=None, on_progress=None, on_progress_args=None, on_progress_kwargs=None):
			self.assertEquals("some_slicer", slicer_name)
			self.assertEquals("prefix/source.file", source_path)
			self.assertEquals("tmp.file", dest_path)
			self.assertIsNone(profile)
			self.assertIsNone(overrides)
			self.assertIsNotNone(on_progress)
			self.assertIsNotNone(on_progress_args)
			self.assertTupleEqual(("some_slicer", octoprint.filemanager.FileDestinations.LOCAL, "source.file", octoprint.filemanager.FileDestinations.LOCAL, "dest.file"), on_progress_args)
			self.assertIsNone(on_progress_kwargs)

			if not callback_args:
				callback_args = ()
			done_cb(*callback_args)
		self.slicing_manager.slice.side_effect = slice

		##~~ execute tested method
		self.file_manager.slice("some_slicer", octoprint.filemanager.FileDestinations.LOCAL, "source.file", octoprint.filemanager.FileDestinations.LOCAL, "dest.file", callback=callback, callback_args=callback_args)

		# assert that events where fired
		expected_events = [mock.call(octoprint.filemanager.Events.SLICING_STARTED, {"stl": "source.file", "gcode": "dest.file", "progressAvailable": False}),
		                   mock.call(octoprint.filemanager.Events.SLICING_DONE, {"stl": "source.file", "gcode": "dest.file", "time": 15.694000005722046})]
		self.fire_event.call_args_list = expected_events

		# assert that model links were added
		expected_links = [("model", dict(name="source.file"))]
		self.local_storage.add_file.assert_called_once_with("dest.file", mock.ANY, allow_overwrite=True, links=expected_links)

		# assert that the generated gcode was manipulated as required
		expected_open_calls = [mock.call("prefix/dest.file", "w"), mock.call("tmp.file", "r")]
		self.assertEquals(mocked_open.call_args_list, expected_open_calls)
		mocked_open.return_value.write.assert_called_once_with(";Generated from source.file aabbccddeeff\r")

		# assert that the contents of tmp.file where copied to dest.file
		mocked_shutil.assert_called_once_with(mock.ANY, mock.ANY)

		# assert that the temporary file was deleted
		mocked_os.assert_called_once_with("tmp.file")

		# assert that our callback was called with the supplied arguments
		callback.assert_called_once_with(*callback_args)

	@mock.patch("os.remove")
	@mock.patch("tempfile.NamedTemporaryFile")
	@mock.patch("time.time", side_effect=[1411979916.422, 1411979932.116])
	def test_slice_error(self, mocked_time, mocked_tempfile, mocked_os):
		callback = mock.MagicMock()
		callback_args = ("one", "two", "three")

		# mock temporary file
		temp_file = mock.MagicMock()
		temp_file.name = "tmp.file"
		mocked_tempfile.return_value = temp_file

		# mock get_absolute_path method on local storage
		def get_absolute_path(path):
			if isinstance(path, tuple):
				import os
				joined_path = ""
				for part in path:
					joined_path = os.path.join(joined_path, part)
				path = joined_path
			return "prefix/" + path
		self.local_storage.get_absolute_path.side_effect = get_absolute_path

		# mock slice method on slicing manager
		def slice(slicer_name, source_path, dest_path, profile, done_cb, callback_args=None, overrides=None, on_progress=None, on_progress_args=None, on_progress_kwargs=None):
			self.assertEquals("some_slicer", slicer_name)
			self.assertEquals("prefix/source.file", source_path)
			self.assertEquals("tmp.file", dest_path)
			self.assertIsNone(profile)
			self.assertIsNone(overrides)
			self.assertIsNotNone(on_progress)
			self.assertIsNotNone(on_progress_args)
			self.assertTupleEqual(("some_slicer", octoprint.filemanager.FileDestinations.LOCAL, "source.file", octoprint.filemanager.FileDestinations.LOCAL, "dest.file"), on_progress_args)
			self.assertIsNone(on_progress_kwargs)

			if not callback_args:
				callback_args = ()
			done_cb(*callback_args, _error="Something went wrong")
		self.slicing_manager.slice.side_effect = slice

		##~~ execute tested method
		self.file_manager.slice("some_slicer", octoprint.filemanager.FileDestinations.LOCAL, "source.file", octoprint.filemanager.FileDestinations.LOCAL, "dest.file", callback=callback, callback_args=callback_args)

		# assert that events where fired
		expected_events = [mock.call(octoprint.filemanager.Events.SLICING_STARTED, {"stl": "source.file", "gcode": "dest.file"}),
		                   mock.call(octoprint.filemanager.Events.SLICING_FAILED, {"stl": "source.file", "gcode": "dest.file", "reason": "Something went wrong"})]
		self.fire_event.call_args_list = expected_events

		# assert that the temporary file was deleted
		mocked_os.assert_called_once_with("tmp.file")

		# assert that time.time was only called once
		mocked_time.assert_called_once()
