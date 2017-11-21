from __future__ import absolute_import

import copy
import logging
import os
import platform
import sys
import threading
import yaml

import psutil

from octoprint.plugin import EnvironmentDetectionPlugin
from octoprint.util import get_formatted_size
from octoprint.util.platform import get_os

class EnvironmentDetector(object):

	def __init__(self, plugin_manager):
		self._plugin_manager = plugin_manager

		self._cache = None
		self._cache_lock = threading.RLock()

		self._environment_plugins = self._plugin_manager.get_implementations(EnvironmentDetectionPlugin)

		self._logger = logging.getLogger(__name__)

	@property
	def environment(self):
		with self._cache_lock:
			if self._cache is None:
				self.run_detection()
			return copy.deepcopy(self._cache)

	def run_detection(self, notify_plugins=True):
		environment = dict()
		environment["os"] = self._detect_os()
		environment["python"] = self._detect_python()
		environment["hardware"] = self._detect_hardware()

		plugin_result = self._detect_from_plugins()
		if plugin_result:
			environment["plugins"] = plugin_result

		with self._cache_lock:
			self._cache = environment

		if notify_plugins:
			self.notify_plugins()

		return environment

	def _detect_os(self):
		return dict(id=get_os(),
		            platform=sys.platform)

	def _detect_python(self):
		result = dict()

		# determine python version
		result["version"] = platform.python_version()

		# determine if we are running from a virtual environment
		if hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and os.path.realpath(sys.prefix) != os.path.realpath(sys.base_prefix)):
			result["virtualenv"] = sys.prefix

		# try to find pip version
		try:
			import pip
			result["pip"] = pip.__version__
		except:
			result["pip"] = "unknown"

		return result

	def _detect_hardware(self):
		return dict(cores=psutil.cpu_count(),
		            freq=psutil.cpu_freq().max,
		            ram=get_formatted_size(psutil.virtual_memory().total))

	def _detect_from_plugins(self):
		result = dict()

		for implementation in self._environment_plugins:
			try:
				additional = implementation.get_additional_environment()
				if additional is not None and isinstance(additional, dict) and len(additional):
					result[implementation._identifier] = additional
			except:
				self._logger.exception("Error while fetching additional "
				                       "environment data from plugin {}".format(implementation._identifier))

		return result

	def log_detected_environment(self, only_to_handler=None):
		def _log(message, level=logging.INFO):
			if only_to_handler is not None:
				import octoprint.logging
				octoprint.logging.log_to_handler(self._logger, only_to_handler, level, message, [])
			else:
				self._logger.log(level, message)

		_log(self._format())

	def _format(self):
		with self._cache_lock:
			if self._cache is None:
				self.run_detection()
			environment = copy.deepcopy(self._cache)

		dumped_environment = yaml.safe_dump(environment,
		                                    default_flow_style=False,
		                                    indent="    ",
		                                    allow_unicode=True).strip()
		environment_lines = "\n".join(map(lambda l: "|  {}".format(l), dumped_environment.split("\n")))
		return u"Detected environment is Python {} under {} ({}). Details:\n{}".format(environment["python"]["version"],
		                                                                               environment["os"]["id"].title(),
		                                                                               environment["os"]["platform"],
		                                                                               environment_lines)

	def notify_plugins(self):
		with self._cache_lock:
			if self._cache is None:
				self.run_detection(notify_plugins=False)
			environment = copy.deepcopy(self._cache)

		for implementation in self._environment_plugins:
			try:
				implementation.on_environment_detected(environment)
			except:
				self._logger.exception("Error while sending environment "
				                       "detection result to plugin {}".format(implementation._identifier))
