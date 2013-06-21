__author__ = "Ross Hendrickson savorywatt"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import logging
import subprocess

class CuraWrapper(object):

    CURA_PATH = '/home/rosshendrickson/workspaces/opensource/CuraEngine/CuraEngine'

    @staticmethod
    def create_slicer(path=None):

        if path:
            return CuraEngine(path)
        else:
            return CuraEngine(CuraWrapper.CURA_PATH)



class CuraEngine(object):

    def  __init__(self, cura_path):


        self.cura_path = cura_path

        logging.info('CuraEngine Created')


    def process_file(self, config, gcode, file_path):
        """Wraps around the main.cpp processFile method.

        :param config: :class: `string` :path to a cura config file:
        :param gcode: :class: `string :path to write out the gcode generated:
        :param file_path: :class: `string :path to the STL to be sliced:

        :note This just uses subprocess at the moment.
        """

        args = [self.cura_path, '-s', config, '-o',  gcode, file_path]
        logging.info('CuraEngine args:%s' % str(args))

        process = subprocess.call(args)
        logging.info('CuraEngine Exit:%s' % str(process))
