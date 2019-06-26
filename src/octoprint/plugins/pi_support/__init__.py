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
import octoprint.events

_PROC_DT_MODEL_PATH = "/proc/device-tree/model"
_OCTOPI_VERSION_PATH = "/etc/octopi_version"
_VCGENCMD_THROTTLE = "/usr/bin/vcgencmd get_throttled"

### uncomment for local debugging
#import sys
#base = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "tests", "plugins", "pi_support", "fakes"))
#_PROC_DT_MODEL_PATH = os.path.join(base, "fake_model.txt")
#_OCTOPI_VERSION_PATH = os.path.join(base, "fake_octopi.txt")
#_VCGENCMD_THROTTLE = "{} {}".format(sys.executable, os.path.join(base, "fake_vcgencmd.py"))
#import itertools
#_VCGENCMD_OUTPUT = itertools.chain(iter(("0x0", "0x0", "0x50005", "0x50000", "0x70007")), itertools.repeat("0x70000"))


# see https://www.raspberrypi.org/forums/viewtopic.php?f=63&t=147781&start=50#p972790
_FLAG_UNDERVOLTAGE = 1 << 0
_FLAG_FREQ_CAPPED = 1 << 1
_FLAG_THROTTLED = 1 << 2
_FLAG_PAST_UNDERVOLTAGE = 1 << 16
_FLAG_PAST_FREQ_CAPPED = 1 << 17
_FLAG_PAST_THROTTLED = 1 << 18

class ThrottleState(object):
	@classmethod
	def from_value(cls, value=0):
		if value == 0:
			return ThrottleState()

		kwargs = dict(undervoltage=_FLAG_UNDERVOLTAGE & value == _FLAG_UNDERVOLTAGE,
		              freq_capped=_FLAG_FREQ_CAPPED & value == _FLAG_FREQ_CAPPED,
		              throttled=_FLAG_THROTTLED & value == _FLAG_THROTTLED,
		              past_undervoltage=_FLAG_PAST_UNDERVOLTAGE & value == _FLAG_PAST_UNDERVOLTAGE,
		              past_freq_capped=_FLAG_PAST_FREQ_CAPPED & value == _FLAG_PAST_FREQ_CAPPED,
		              past_throttled=_FLAG_PAST_THROTTLED & value == _FLAG_PAST_THROTTLED,
		              raw_value=value)
		return ThrottleState(**kwargs)

	def __init__(self, **kwargs):
		self._raw_value = kwargs.get('raw_value', -1)
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
	def undervoltage(self):
		return self.current_undervoltage or self.past_undervoltage

	@property
	def current_undervoltage(self):
		return self._undervoltage

	@property
	def past_undervoltage(self):
		return self._past_undervoltage

	@property
	def overheat(self):
		return self.current_overheat or self.past_overheat

	@property
	def current_overheat(self):
		return self._freq_capped

	@property
	def past_overheat(self):
		return self._past_freq_capped

	@property
	def issue(self):
		return self.current_issue or self.past_issue

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
		return dict(raw_value=self._raw_value,
		            current_undervoltage=self.current_undervoltage,
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
			_proc_dt_model = f.readline().strip(" \t\r\n\0")

	return _proc_dt_model


def get_vcgencmd_throttled_state(command):
	output = sarge.get_stdout(command)
	#output = "throttled={}".format(next(_VCGENCMD_OUTPUT)) # for local debugging
	if not "throttled=0x" in output:
		raise ValueError("cannot parse \"{}\" output: {}".format(command, output))

	value = output[len("throttled="):].strip(" \t\r\n\0")
	value = int(value, 0)
	return ThrottleState.from_value(value)


def is_octopi():
	return os.path.exists(_OCTOPI_VERSION_PATH)


_octopi_version = None
def get_octopi_version():
	global _octopi_version

	if _octopi_version is None:
		with open(_OCTOPI_VERSION_PATH, "r") as f:
			_octopi_version = f.readline().strip(" \t\r\n\0")

	return _octopi_version


class PiSupportPlugin(octoprint.plugin.EnvironmentDetectionPlugin,
                      octoprint.plugin.SimpleApiPlugin,
                      octoprint.plugin.AssetPlugin,
                      octoprint.plugin.TemplatePlugin,
                      octoprint.plugin.StartupPlugin,
                      octoprint.plugin.SettingsPlugin):

	# noinspection PyMissingConstructor
	def __init__(self):
		self._throttle_state = ThrottleState()
		self._throttle_check = None
		self._throttle_undervoltage = False
		self._throttle_overheat = False
		self._throttle_functional = True

	#~~ EnvironmentDetectionPlugin

	def get_additional_environment(self):
		result = dict(model=get_proc_dt_model())

		if is_octopi():
			result.update(dict(octopi_version=get_octopi_version()))

		return result

	#~~ SimpleApiPlugin

	def on_api_get(self, request):
		result = dict(throttle_state=self._throttle_state.as_dict())
		result.update(self.get_additional_environment())
		return flask.jsonify(**result)

	#~~ AssetPlugin

	def get_assets(self):
		return dict(
			js=["js/pi_support.js"],
			clientjs=["clientjs/pi_support.js"],
			css=["css/pi_support.css"]
		)

	#~~ TemplatePlugin

	def get_template_configs(self):
		configs = [dict(type="settings", name=gettext("Pi Support"), template="pi_support_settings.jinja2", custom_bindings=False)]

		if is_octopi():
			configs.append(dict(type="about", name="About OctoPi", template="pi_support_about_octopi.jinja2"))

		return configs

	def get_template_vars(self):
		return self.get_additional_environment()

	#~~ StartupPlugin

	def on_startup(self, *args, **kwargs):
		if self._settings.get_boolean(["vcgencmd_throttle_check_enabled"]):
			self._check_throttled_state()
			self._throttle_check = RepeatedTimer(self._check_throttled_state_interval,
			                                     self._check_throttled_state,
			                                     condition=self._check_throttled_state_condition)
			self._throttle_check.start()

	#~~ SettingsPlugin

	def get_settings_defaults(self):
		return dict(vcgencmd_throttle_check_enabled=True,
		            vcgencmd_throttle_check_command=_VCGENCMD_THROTTLE)

	def get_settings_restricted_paths(self):
		return dict(admin=[["vcgencmd_throttle_check_enabled"], ["vcgencmd_throttle_check_command"]])

	#~~ Helpers

	def _check_throttled_state_interval(self):
		if self._throttle_state.current_issue:
			# check state every 30s if something's currently amiss
			return 30
		else:
			# check state every 5min if nothing's currently amiss
			return 300

	def _check_throttled_state_condition(self):
		return self._throttle_functional

	def get_throttle_state(self, run_now=False):
		"""Exposed as public helper."""
		if run_now:
			self._check_throttled_state()

		if not self._throttle_functional:
			return False

		return self._throttle_state.as_dict()

	def _check_throttled_state(self):
		command = self._settings.get(["vcgencmd_throttle_check_command"])

		self._logger.debug("Retrieving throttle state via \"{}\"".format(command))
		try:
			state = get_vcgencmd_throttled_state(command)
		except:
			self._logger.exception("Got an error while trying to fetch the current throttle state via \"{}\"".format(command))
			self._throttle_functional = False
			return

		if self._throttle_state == state:
			# no change
			return

		self._throttle_state = state

		if (not self._throttle_undervoltage and self._throttle_state.undervoltage) \
				or (not self._throttle_overheat and self._throttle_state.overheat):
			message = "This Raspberry Pi is reporting problems that might lead to bad performance or errors caused " \
			          "by overheating or insufficient power."

			if self._throttle_state.undervoltage:
				self._throttle_undervoltage = True
				message += "\n!!! UNDERVOLTAGE REPORTED !!! Make sure that the power supply and power cable are " \
				           "capable of supplying enough voltage and current to your Pi."

			if self._throttle_state.overheat:
				self._throttle_overheat = True
				message += "\n!!! FREQUENCY CAPPING DUE TO OVERHEATING REPORTED !!! Improve cooling on the Pi's " \
				           "CPU and GPU."

			self._logger.warn(message)

		self._plugin_manager.send_plugin_message(self._identifier, dict(type="throttle_state",
		                                                                state=self._throttle_state.as_dict()))

		# noinspection PyUnresolvedReferences
		self._event_bus.fire(octoprint.events.Events.PLUGIN_PI_SUPPORT_THROTTLE_STATE, self._throttle_state.as_dict())


def register_custom_events(*args, **kwargs):
	return ["throttle_state",]


__plugin_name__ = "Pi Support Plugin"
__plugin_author__ = "Gina Häußge"
__plugin_description__ = "Provides additional information about your Pi in the UI."
__plugin_disabling_discouraged__ = gettext("Without this plugin OctoPrint will no longer be able to "
                                           "provide additional information about your Pi, "
                                           "which will make it more tricky to help you if you need support.")
__plugin_license__ = "AGPLv3"

def __plugin_check__():
	try:
		proc_dt_model = get_proc_dt_model()
		if proc_dt_model is None:
			return False
	except:
		return False

	return "raspberry pi" in proc_dt_model.lower()

def __plugin_load__():
	plugin = PiSupportPlugin()
	global __plugin_implementation__
	__plugin_implementation__ = plugin

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.events.register_custom_events": register_custom_events
	}

	global __plugin_helpers__
	__plugin_helpers__ = dict(get_throttled=plugin.get_throttle_state)
