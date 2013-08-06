

import unittest
from mock import patch

from octoprint.cura import CuraFactory
from octoprint.cura import CuraEngine

class CuraFactoryTestCase(unittest.TestCase):


	def test_cura_factory(self):

		fake_path = 'my/temp/path'
		result = CuraFactory.create_slicer(fake_path)

		self.assertEqual(fake_path, result.cura_path)


	@patch('threading.Thread')
	def test_cura_engine_process_file(self, thread):
		path = 'rosshendrickson/workspaces/opensource/CuraEngine/'
		
		cura_engine = CuraFactory.create_slicer(path)
		file_path = './cura/tests/test.stl'
		config_path = './cura/tests/config'
		gcode_filename= './cura/tests/output.gcode'

		args = [path, '-s', config_path, '-o', file_path]
		
		cura_engine.process_file(config_path, gcode_filename, file_path)
		self.assertTrue(thread.called)

