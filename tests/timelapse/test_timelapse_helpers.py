# coding=utf-8
from __future__ import absolute_import

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2016 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest
import mock

import os
import time

from collections import namedtuple
_stat = namedtuple("StatResult", "st_size, st_ctime, st_mtime")

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

	@mock.patch("os.stat")
	@mock.patch("os.listdir")
	def test_get_finished_timelapses(self, mock_listdir, mock_stat):

		## prepare

		files = dict()
		files["one.mpg"] = _stat(st_size=1024, st_ctime=self.now, st_mtime=self.now)
		files["nope.jpg"] = _stat(st_size=100, st_ctime=self.now, st_mtime=self.now)
		files["two.mpg"] = _stat(st_size=2048, st_ctime=self.now, st_mtime=self.now)

		mocked_path = "/path/to/timelapse"
		self.settings.getBaseFolder.return_value = mocked_path

		mock_listdir.return_value = sorted(files.keys())

		def stat(p):
			name = p[len(mocked_path) + 1:]
			return files[name]
		mock_stat.side_effect = stat

		## test
		result = octoprint.timelapse.get_finished_timelapses()

		## verify
		self.assertEqual(len(result), 2)
		self.assertEqual(result[0]["name"], "one.mpg")
		self.assertEqual(result[0]["bytes"], 1024)
		self.assertEqual(result[1]["name"], "two.mpg")
		self.assertEqual(result[1]["bytes"], 2048)

	@mock.patch("os.stat")
	@mock.patch("os.listdir")
	def test_unrendered_timelapses(self, mock_listdir, mock_stat):
		## prepare
		files = dict()
		files["one-0.jpg"] = _stat(st_size=1, st_ctime=self.now - 1, st_mtime=self.now - 1)
		files["one-1.jpg"] = _stat(st_size=2, st_ctime=self.now, st_mtime=self.now)
		files["one-2.jpg"] = _stat(st_size=3, st_ctime=self.now, st_mtime=self.now)
		files["nope.mpg"] = _stat(st_size=2048, st_ctime=self.now, st_mtime=self.now)
		files["two-0.jpg"] = _stat(st_size=4, st_ctime=self.now, st_mtime=self.now)
		files["two-1.jpg"] = _stat(st_size=5, st_ctime=self.now, st_mtime=self.now)

		mocked_path = "/path/to/timelapse/tmp"
		self.settings.getBaseFolder.return_value = mocked_path

		mock_listdir.return_value = sorted(files.keys())

		def stat(p):
			name = p[len(mocked_path) + 1:]
			return files[name]
		mock_stat.side_effect = stat

		## test
		result = octoprint.timelapse.get_unrendered_timelapses()

		## verify
		self.assertEqual(len(result), 2)

		self.assertEqual(result[0]["name"], "one")
		self.assertEqual(result[0]["count"], 3)
		self.assertEqual(result[0]["bytes"], 6)

		self.assertEqual(result[1]["name"], "two")
		self.assertEqual(result[1]["count"], 2)
		self.assertEqual(result[1]["bytes"], 9)
