# coding=utf-8
from __future__ import absolute_import

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2016 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest
import mock

import os
import time

import octoprint.settings
import octoprint.timelapse

class TimelapseTest(unittest.TestCase):

	def setUp(self):
		# mock settings
		self.settings_patcher = mock.patch("octoprint.timelapse.settings")
		self.settings_getter = self.settings_patcher.start()

		self.settings = mock.create_autospec(octoprint.settings.Settings)
		self.settings_getter.return_value = self.settings

		self.now = time.time()

	def cleanUp(self):
		self.settings_patcher.stop()

	@mock.patch("os.remove")
	@mock.patch("os.listdir")
	def test_delete_unrendered_timelapse(self, mock_listdir, mock_remove):
		## prepare

		mocked_path = "/path/to/timelapse/tmp"
		mocked_files = ["a-0.jpg",
		                "a-1.jpg",
		                "a-2.jpg",
		                "b-0.jpg",
		                "b-1.jpg",
		                "tmp_00000.jpg",
		                "tmp_00001.jpg"]

		self.settings.getBaseFolder.return_value = mocked_path
		mock_listdir.return_value = mocked_files

		## test
		octoprint.timelapse.delete_unrendered_timelapse("b")

		## verify
		expected_deletions = map(lambda x: os.path.join(mocked_path, x), ["b-0.jpg",
		                                                                  "b-1.jpg"])
		expected_deletion_calls = map(mock.call, expected_deletions)
		self.assertListEqual(mock_remove.mock_calls, expected_deletion_calls)

	@mock.patch("time.time")
	@mock.patch("os.remove")
	@mock.patch("os.path.getmtime")
	@mock.patch("os.listdir")
	def test_delete_old_unrendered_timelapses(self, mock_listdir, mock_mtime, mock_remove, mock_time):
		## prepare

		mocked_path = "/path/to/timelapse/tmp"
		mocked_files = ["old-0.jpg",
		                "old-1.jpg",
		                "old-2.jpg",
		                "prefix-0.jpg",
		                "prefix-1.jpg",
		                "tmp_00000.jpg",
		                "tmp_00001.jpg"]
		now = self.now
		days = 1

		def mtime(p):
			if p.startswith(os.path.join(mocked_path, "old-0")):
				# old-0 is definitely older than cutoff
				return 0
			else:
				# all other files were just created
				return now

		self.settings.getBaseFolder.return_value = mocked_path
		self.settings.getInt.return_value = days

		mock_time.return_value = now

		mock_listdir.return_value = mocked_files

		mock_mtime.side_effect = mtime

		## test
		octoprint.timelapse.delete_old_unrendered_timelapses()

		## verify
		expected_deletions = map(lambda x: os.path.join(mocked_path, x), ["tmp_00000.jpg",
		                                                                  "tmp_00001.jpg",
		                                                                  "old-0.jpg",
		                                                                  "old-1.jpg",
		                                                                  "old-2.jpg"])
		expected_deletion_calls = map(mock.call, expected_deletions)
		self.assertListEqual(mock_remove.mock_calls, expected_deletion_calls)
