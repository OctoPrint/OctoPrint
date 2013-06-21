

import unittest

from cura import CuraWrapper
from cura import CuraEngine

class CuraWrapperTestCase(unittest.TestCase):


    def test_cura_wrapper(self):

        fake_path = 'my/temp/path'
        result = CuraWrapper.create_slicer(fake_path)

        self.assertEqual(fake_path, result.cura_path)

    def test_cura_engine_process_file(self):

        cura_engine = CuraWrapper.create_slicer()

        file_path = '/cura/tests/test.stl'
        config_path = '/cura/tests/config'
        gcode_filename= 'output.gcode'

        cura_engine.process_file(config_path, gcode_filename, file_path)


