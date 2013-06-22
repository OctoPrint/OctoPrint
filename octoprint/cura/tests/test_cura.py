

import unittest

from cura import CuraFactory
from cura import CuraEngine

class CuraFactoryTestCase(unittest.TestCase):


    def test_cura_factory(self):

        fake_path = 'my/temp/path'
        result = CuraFactory.create_slicer(fake_path)

        self.assertEqual(fake_path, result.cura_path)

    def test_cura_engine_process_file(self):

        cura_engine = CuraFactory.create_slicer()

        file_path = './cura/tests/test_02.stl'
        config_path = './cura/tests/config'
        gcode_filename= './cura/tests/output.gcode'

        cura_engine.process_file(config_path, gcode_filename, file_path)


