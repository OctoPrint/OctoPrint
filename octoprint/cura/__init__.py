__author__ = "Ross Hendrickson savorywatt"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import logging

from octoprint.settings import settings

class CuraFactory(object):

	@staticmethod
	def create_slicer(path=None):
		if path:
			return CuraEngine(path)
		current_settings = settings(init=True)
		path = current_settings.get(["curaEngine", "path"])

		return CuraEngine(path)


class CuraEngine(object):

	def  __init__(self, cura_path):

		if not cura_path:
			raise Exception("Unable to create CuraEngine - no path specified")
		
		self.cura_path = cura_path
		
		logging.info('CuraEngine Created')


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

		def start_thread(call_back, call_back_args, call_args):
			import subprocess
			logging.info("Starting SubProcess in Thread")
			logging.info("Subprocess args: %s" % str(call_args))
			process = subprocess.call(call_args)
			call_back(*call_back_args)
			logging.info("Slicing call back complete:%s" % str(call_back))

		args = [self.cura_path, '-s', config, '-o',  gcode, file_path]
		logging.info('CuraEngine args:%s' % str(args))

		thread = threading.Thread(target=start_thread, args=(call_back,
			call_back_args, args))

		thread.start()
		logging.info('CuraEngine Slicing File:%s' % file_path)
