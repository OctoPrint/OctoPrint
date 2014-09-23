import sarge

__author__ = "Ross Hendrickson savorywatt"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import logging
import os

from octoprint.settings import settings

class CuraFactory(object):

	@staticmethod
	def create_slicer(path=None):
		"""Utilizes the factory pattern to setup a CuraEngine object

		:param path: :class: `str`
		"""
		if path:
			return Cura(path)
		
		current_settings = settings(init=True)
		path = current_settings.get(["cura", "path"])

		return Cura(path)


class Cura(object):

	def  __init__(self, cura_path):

		if not cura_path:
			raise Exception("Unable to create CuraEngine - no path specified")
		
		self.cura_path = cura_path
		self._logger = logging.getLogger(__name__)
		

	def process_file(
			self, config, gcode, file_path, call_back=None, 
			call_back_args=None):

		"""Wraps around the main.cpp processFile method.

		:param config: :class: `string` :path to a cura config file:
		:param gcode: :class: `string :path to write out the gcode generated:
		:param file_path: :class: `string :path to the STL to be sliced:
		:note: This will spawn a thread to handle the subprocess call and allow
		us to be able to have a call back
		"""
		import threading

		def start_thread(call_back, call_back_args, call_args, cwd):
			self._logger.info("Running %r in %s" % (call_args, cwd))
			command = " ".join(call_args)
			try:
				p = sarge.run(command, cwd=cwd)
				if p.returncode == 0:
					call_back(*call_back_args)
				else:
					self._logger.warn("Could not slice via Cura, got return code %r" % p.returncode)
					call_back_args.append("Got returncode %r" % p.returncode)
					call_back(*call_back_args)
			except:
				self._logger.exception("Could not slice via Cura, got an unknown error")
				call_back_args.append("Unknown error, please consult the log file")
				call_back(*call_back_args)

		executable = self.cura_path
		(workingDir, ignored) = os.path.split(executable)
		args = [executable, '-i', config, '-s', file_path, '-o',  gcode]

		thread = threading.Thread(target=start_thread, args=(call_back,
			call_back_args, args, workingDir))

		thread.start()
