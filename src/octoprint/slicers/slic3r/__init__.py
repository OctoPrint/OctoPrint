__author__ = "Ross Hendrickson savorywatt"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import logging
import os

from octoprint.settings import settings

class Slic3rFactory(object):

        @staticmethod
        def create_slicer(path=None):
                """Utilizes the factory pattern to setup a Slic3r object

                :param path: :class: `str`
                """
                if path:
                        return Slic3r(path)
                
                current_settings = settings(init=True)
                path = current_settings.get(["slic3r", "path"])

                return Slic3r(path)


class Slic3r(object):

        def  __init__(self, slicer_path):

                if not slicer_path:
                        raise Exception("Unable to create CuraEngine - no path specified")
                
                self.slicer_path = slicer_path
                self._logger = logging.getLogger(__name__)
                

        def process_file(
                        self, config, gcode, file_path, call_back=None, 
                        call_back_args=None):

                """Wraps around the main.cpp processFile method.

                :param config: :class: `string` :path to a slic3r config file:
                :param gcode: :class: `string :path to write out the gcode generated:
                :param file_path: :class: `string :path to the STL to be sliced:
                :note: This will spawn a thread to handle the subprocess call and allow
                us to be able to have a call back
                """
                import threading

                def start_thread(call_back, call_back_args, call_args, cwd):
                        import subprocess
                        self._logger.info("Running %r in %s" % (call_args, cwd))
                        try:
                                s = subprocess.Popen(call_args, stdout=subprocess.PIPE, cwd=cwd)
				while 1:
					line = s.stdout.readline()
					exitcode = s.poll()
					if (not line) and (exitcode is not None):
						break
					
					line = line[:-1]
					self._logger.info("%s", line)

                                call_back(*call_back_args)
                        except subprocess.CalledProcessError as (e):
                                self._logger.warn("Could not slice via Slic3r, got return code %r" % e.returncode)
                                call_back_args.append("Got returncode %r" % e.returncode)
                                call_back(*call_back_args)

                executable = self.slicer_path
                (workingDir, ignored) = os.path.split(executable)
                args = [executable, '--load', config, file_path, '-o',  gcode]

                thread = threading.Thread(target=start_thread, args=(call_back,
                        call_back_args, args, workingDir))

                thread.start()
