import unittest
from mock import Mock
from mock import patch

import logging

from octoprint.filemanager.destinations import FileDestinations


class FileManipulationTestCase(unittest.TestCase):

	def setUp(self):

		from octoprint.settings import settings
		from octoprint.gcodefiles import GcodeManager
		self.settings = settings(True)
		self.manager = GcodeManager()

		self.filenames = []

	def tearDown(self):

		for filename in self.filenames:
			self.manager.removeFile(filename)

		logging.info("REMOVED %s filenames" % str(len(self.filenames)))

	@patch('octoprint.settings.Settings.getBoolean')
	@patch('octoprint.slicers.cura.Cura.process_file')
	def test_add_stl_file_curaDisabled(self, process, getterMock):

		getterMock.return_value = False

		fake = Mock()
		fake.filename = "test_stl.stl"
		self.filenames.append(fake.filename)
		fake.__getitem__ = "SOMETHING"

		result, done = self.manager.addFile(fake, FileDestinations.LOCAL)

		logging.info("RESULT:%s" % str(result))

		self.assertFalse(process.called)
		self.assertIsNone(result)
		self.assertTrue(done)

	@patch('octoprint.settings.Settings.getBoolean')
	@patch('octoprint.slicers.cura.Cura.process_file')
	def test_add_stl_file_curaEnabled(self, process, getterMock):

		getterMock.return_value = True

		fake = Mock()
		fake.filename = "test_stl.stl"
		self.filenames.append(fake.filename)
		fake.__getitem__ = "SOMETHING"

		result, done = self.manager.addFile(fake, FileDestinations.LOCAL)

		logging.info("RESULT:%s" % str(result))

		getterMock.assert_called_once_with(["cura", "enabled"])
		self.assertTrue(process.called)
		self.assertTrue(fake.filename == result)
		self.assertFalse(done)

	def test_add_gcode_file(self):
		fake = Mock()
		fake.filename = "test_stl.gcode"
		self.filenames.append(fake.filename)
		fake.__getitem__ = "SOMETHING"

		result, done = self.manager.addFile(fake, FileDestinations.LOCAL)

		logging.info("RESULT:%s" % str(result))

		self.assertTrue(fake.filename == result)
		self.assertTrue(done)


class FileUtilTestCase(unittest.TestCase):

	def test_isGcode(self):

		from octoprint.gcodefiles import isGcodeFileName

		filename = "/asdj/wefasdf/junk.stl"

		result = isGcodeFileName(filename)

		self.assertFalse(result)

		filename = "/asdj/wefasdf/junk.gcode"

		result = isGcodeFileName(filename)

		self.assertTrue(result)

	def test_isSTLFileName(self):

		from octoprint.gcodefiles import isSTLFileName
		filename = "/asdj/wefasdf/junk.stl"

		result = isSTLFileName(filename)

		self.assertTrue(result)

		filename = "/asdj/wefasdf/junk.gcode"

		result = isSTLFileName(filename)

		self.assertFalse(result)

	def test_genGcodeFileName(self):

		from octoprint.gcodefiles import genGcodeFileName

		filename = "test.stl"

		expected = "test.gcode"

		result = genGcodeFileName(filename)

		self.assertEqual(result, expected)
