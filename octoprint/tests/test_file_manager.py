import unittest
from mock import Mock
from mock import patch

import logging

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

	@patch('octoprint.cura.CuraEngine.process_file')
	def test_add_stl_file(self, process):

		fake = Mock()
		fake.filename = "test_stl.stl"
		self.filenames.append(fake.filename)
		fake.__getitem__ = "SOMETHING"

		result = self.manager.addFile(fake)

		logging.info("RESULT:%s" % str(result))

		self.assertTrue(fake.filename == result)

		self.assertTrue(process.called)

	def test_add_gcode_file(self):
		fake = Mock()
		fake.filename = "test_stl.gcode"
		self.filenames.append(fake.filename)
		fake.__getitem__ = "SOMETHING"

		result = self.manager.addFile(fake)

		logging.info("RESULT:%s" % str(result))

		self.assertTrue(fake.filename == result)


class FileUtilTestCase(unittest.TestCase):

	def test_isGcode(self):

		from octoprint.util import isGcodeFileName

		filename = "/asdj/wefasdf/junk.stl"

		result = isGcodeFileName(filename)

		self.assertFalse(result)

		filename = "/asdj/wefasdf/junk.gcode"

		result = isGcodeFileName(filename)

		self.assertTrue(result)

	def test_isSTLFileName(self):

		from octoprint.util import isSTLFileName
		filename = "/asdj/wefasdf/junk.stl"

		result = isSTLFileName(filename)

		self.assertTrue(result)

		filename = "/asdj/wefasdf/junk.gcode"

		result = isSTLFileName(filename)

		self.assertFalse(result)

	def test_genGcodeFileName(self):

		from octoprint.util import genGcodeFileName

		filename = "test.stl"

		expected = "test.gcode"

		result = genGcodeFileName(filename)

		self.assertEqual(result, expected)
