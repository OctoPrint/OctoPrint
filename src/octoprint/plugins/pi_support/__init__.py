# coding=utf-8
from __future__ import absolute_import, division, print_function

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

import flask
import os
import sarge

from flask_babel import gettext
from octoprint.util import RepeatedTimer

import octoprint.plugin

_PROC_DT_MODEL_PATH = "/proc/device-tree/model"
_OCTOPI_VERSION_PATH = "/etc/octopi_version"
_VCGENCMD = "/usr/bin/vcgencmd"

### uncomment for local debugging
#_PROC_DT_MODEL_PATH = "fake_model.txt"
#_OCTOPI_VERSION_PATH = "fake_octopi.txt"

# see https://www.raspberrypi.org/forums/viewtopic.php?f=63&t=147781&start=50#p972790
_FLAG_UNDERVOLTAGE = 1 << 0
_FLAG_FREQ_CAPPED = 1 << 1
_FLAG_THROTTLED = 1 << 2
_FLAG_PAST_UNDERVOLTAGE = 1 << 16
_FLAG_PAST_FREQ_CAPPED = 1 << 17
_FLAG_PAST_THROTTLED = 1 << 18


class ThrottleState(object):
	@classmethod
	def from_value(cls, value):
		if value == 0:
			return ThrottleState()

		kwargs = dict(undervoltage=_FLAG_UNDERVOLTAGE & value == _FLAG_UNDERVOLTAGE,
		              freq_capped=_FLAG_FREQ_CAPPED & value == _FLAG_FREQ_CAPPED,
		              throttled=_FLAG_THROTTLED & value == _FLAG_THROTTLED,
		              past_undervoltage=_FLAG_PAST_UNDERVOLTAGE & value == _FLAG_PAST_UNDERVOLTAGE,
		              past_freq_capped=_FLAG_PAST_FREQ_CAPPED & value == _FLAG_PAST_FREQ_CAPPED,
		              past_throttled=_FLAG_PAST_THROTTLED & value == _FLAG_PAST_THROTTLED)
		return ThrottleState(**kwargs)

	def __init__(self, **kwargs):
		self._undervoltage = False
		self._freq_capped = False
		self._throttled = False
		self._past_undervoltage = False
		self._past_freq_capped = False
		self._past_throttled = False

		for key, value in kwargs.items():
			local_key = "_{}".format(key)
			if hasattr(self, local_key) and isinstance(value, bool):
				setattr(self, local_key, value)

	@property
	def current_undervoltage(self):
		return self._undervoltage

	@property
	def past_undervoltage(self):
		return self._past_undervoltage

	@property
	def current_overheat(self):
		return self._freq_capped

	@property
	def past_overheat(self):
		return self._past_freq_capped

	@property
	def current_issue(self):
		return self._undervoltage or self._freq_capped or self._throttled

	@property
	def past_issue(self):
		return self._past_undervoltage or self._past_freq_capped or self._past_throttled

	def __eq__(self, other):
		if not isinstance(other, ThrottleState):
			return False

		return self._undervoltage == other._undervoltage \
		       and self._freq_capped == other._freq_capped \
		       and self._throttled == other._throttled \
		       and self._past_undervoltage == other._past_undervoltage \
		       and self._past_freq_capped == other._past_freq_capped \
		       and self._past_throttled == other._past_throttled

	def as_dict(self):
		return dict(current_undervoltage=self.current_undervoltage,
		            past_undervoltage=self.past_undervoltage,
		            current_overheat=self.current_overheat,
		            past_overheat=self.past_overheat,
		            current_issue=self.current_issue,
		            past_issue=self.past_issue)


_proc_dt_model = None
def get_proc_dt_model():
	global _proc_dt_model

	if _proc_dt_model is None:
		with open(_PROC_DT_MODEL_PATH, "r") as f:
			_proc_dt_model = f.readline().strip()

	return _proc_dt_model


def get_vcgencmd_throttled_state():
	output = sarge.get_stdout([_VCGENCMD, "get_throttled"])
	#output = "throttled=0x70005" # for local debugging
	if not "throttled=0x" in output:
		raise ValueError("cannot parse vcgencmd get_throttled output: {}".format(output))

	value = int(output[len("throttled="):], 0)
	return ThrottleState.from_value(value)


def is_octopi():
	return os.path.exists(_OCTOPI_VERSION_PATH)


_octopi_version = None
def get_octopi_version():
	global _octopi_version

	if _octopi_version is None:
		with open(_OCTOPI_VERSION_PATH, "r") as f:
			_octopi_version = f.readline().strip()

	return _octopi_version


class PiSupportPlugin(octoprint.plugin.EnvironmentDetectionPlugin,
                      octoprint.plugin.SimpleApiPlugin,
                      octoprint.plugin.AssetPlugin,
                      octoprint.plugin.TemplatePlugin,
                      octoprint.plugin.StartupPlugin):

	# noinspection PyMissingConstructor
	def __init__(self):
		self._throttle_state = ThrottleState()
		self._throttle_check = None

	#~~ EnvironmentDetectionPlugin

	def get_additional_environment(self):
		result = dict(model=get_proc_dt_model())

		if is_octopi():
			result.update(dict(octopi_version=get_octopi_version()))

		return result

	#~~ SimpleApiPlugin

	def on_api_get(self, request):
		try:
			state = get_vcgencmd_throttled_state()
		except:
			self._logger.exception("Got an error while trying to fetch the current throttle state via {}".format(_VCGENCMD))
			state = ThrottleState()

		result = dict(throttle_state=state.as_dict())
		result.update(self.get_additional_environment())
		return flask.jsonify(**result)

	#~~ AssetPlugin

	def get_assets(self):
		return dict(
			js=["js/pi_support.js"],
			css=["css/pi_support.css"]
		)

	#~~ TemplatePlugin

	def get_template_configs(self):
		configs = []

		if is_octopi():
			configs.append(dict(type="about", name="About OctoPi", template="pi_support_about_octopi.jinja2"))

		return configs

	def get_template_vars(self):
		return self.get_additional_environment()

	#~~ StartupPlugin

	def on_after_startup(self):
		self._throttle_check = RepeatedTimer(self._check_throttled_state_interval,
		                                     self._check_throttled_state,
		                                     run_first=True)
		self._throttle_check.start()

	#~~ Helpers

	def _check_throttled_state_interval(self):
		if self._throttle_state.current_undervoltage or self._throttle_state.current_overheat:
			# check state every 30s if something's currently amiss
			return 30
		else:
			# check state every 5min if nothing's currently amiss
			return 300

	def _check_throttled_state(self):
		try:
			state = get_vcgencmd_throttled_state()
		except:
			self._logger.exception("Got an error while trying to fetch the current throttle state via {}".format(_VCGENCMD))
			return

		if self._throttle_state == state:
			# no change
			return

		self._throttle_state = state

		if state.current_issue or state.past_issue:
			message = "This Raspberry Pi is reporting problems that might lead to bad performance or errors caused by overheating or insufficient power."
			if self._throttle_state.current_undervoltage or self._throttle_state.past_undervoltage:
				message += "\n!!! UNDERVOLTAGE REPORTED !!! Make sure that the power supply and power cable are capable of supplying enough voltage and current to your Pi."
			if self._throttle_state.current_overheat or self._throttle_state.past_overheat:
				message += "\n!!! FREQUENCY CAPPING DUE TO OVERHEATING REPORTED !!! Improve cooling on the Pi's CPU and GPU."
			self._logger.warn(message)

			self._plugin_manager.send_plugin_message(self._identifier, dict(type="throttle_state",
			                                                                state=self._throttle_state.as_dict()))


__plugin_name__ = "Pi Support Plugin"
__plugin_author__ = "Gina Häußge"
__plugin_description__ = "Provides additional information about your Pi in the UI."
__plugin_disabling_discouraged__ = gettext("Without this plugin OctoPrint will no longer be able to "
                                           "provide additional information about your Pi,"
                                           "which will make it more tricky to help you if you need support.")
__plugin_license__ = "AGPLv3"

def __plugin_check__():
	from octoprint.util.platform import get_os
	if get_os() != "linux" or not os.path.exists(_PROC_DT_MODEL_PATH):
		return False

	proc_dt_model = get_proc_dt_model()
	if proc_dt_model is None:
		return False

	return "raspberry pi" in proc_dt_model.lower()

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = PiSupportPlugin()
