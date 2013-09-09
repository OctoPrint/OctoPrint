

import unittest
from mock import patch

from octoprint.slicers.cura import CuraFactory
from octoprint.slicers.cura import Cura

class CuraFactoryTestCase(unittest.TestCase):


	def test_cura_factory(self):

		fake_path = 'my/temp/path'
		result = CuraFactory.create_slicer(fake_path)

		self.assertEqual(fake_path, result.cura_path)


	@patch('threading.Thread')
	def test_cura_engine_process_file(self, thread):
		path = 'rosshendrickson/workspaces/opensource/CuraEngine/'
		
		cura = CuraFactory.create_slicer(path)
		file_path = './cura/tests/test.stl'
		config_path = './cura/tests/config'
		gcode_filename = './cura/tests/output.gcode'

		cura.process_file(config_path, gcode_filename, file_path)
		self.assertTrue(thread.called)

