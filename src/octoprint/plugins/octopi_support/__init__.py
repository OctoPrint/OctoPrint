# coding=utf-8
from __future__ import absolute_import, division, print_function

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

import flask
import os

from flask.ext.babel import gettext

import octoprint.plugin

_OCTOPI_VERSION_PATH = "/etc/octopi_version"
_CPUINFO_PATH = "/proc/cpuinfo"

# based on https://elinux.org/RPi_HardwareHistory#Which_Pi_have_I_got.3F
_RPI_REVISION_MAP = {
	"Beta": "1B (Beta)",
	"0002": "1B",
	"0003": "1B",
	"0004": "1B",
	"0005": "1B",
	"0006": "1B",
	"0007": "1A",
	"0008": "1A",
	"0009": "1A",
	"000d": "1B",
	"000e": "1B",
	"000f": "1B",
	"0010": "B+",
	"0011": "CM1",
	"0012": "A+",
	"0013": "B+",
	"0014": "CM1",
	"0015": "A+",
	"a01040": "2B",
	"a01041": "2B",
	"a21041": "2B",
	"a22042": "2B",
	"900021": "A+",
	"900032": "B+",
	"900092": "Zero",
	"900093": "Zero",
	"920093": "Zero",
	"9000c1": "Zero W",
	"a02082": "3B",
	"a020a0": "CM3",
	"a22082": "3B",
	"a32082": "3B",
}


def get_octopi_version():
	with open(_OCTOPI_VERSION_PATH, "r") as f:
		version_line = f.readline()
		return version_line.strip()


def get_pi_cpuinfo():
	fields = dict(revision="Revision",
	              hardware="Hardware",
	              serial="Serial")

	result = dict()
	with open(_CPUINFO_PATH) as f:
		for line in f:
			if not line:
				continue

			for key, prefix in fields.items():
				if line.startswith(prefix):
					result[key] = line[line.index(":") + 1:].strip()

	return result


def get_pi_model(hardware, revision):
	if hardware not in ("BCM2835",):
		return "unknown"

	if revision.startswith("1000"):
		# strip flag for over-volted (https://elinux.org/RPi_HardwareHistory#Which_Pi_have_I_got.3F)
		revision = revision[4:]

	return _RPI_REVISION_MAP.get(revision.lower(), "unknown")


class OctoPiSupportPlugin(octoprint.plugin.EnvironmentDetectionPlugin,
                          octoprint.plugin.SimpleApiPlugin,
                          octoprint.plugin.AssetPlugin,
                          octoprint.plugin.TemplatePlugin):

	# noinspection PyMissingConstructor
	def __init__(self):
		self._version = None
		self._cpuinfo = None
		self._model = None

	#~~ EnvironmentDetectionPlugin

	def get_additional_environment(self):
		return dict(version=self._get_version(),
		            revision=self._get_cpuinfo().get("revision", "unknown"),
		            model=self._get_model())

	#~~ SimpleApiPlugin

	def on_api_get(self, request):
		return flask.jsonify(version=self._get_version())

	#~~ AssetPlugin

	def get_assets(self):
		return dict(
			js=["js/octopi_support.js"],
			css=["css/octopi_support.css"]
		)

	#~~ TemplatePlugin

	def get_template_configs(self):
		return [
			dict(type="about", name="About OctoPi", template="octopi_support_about.jinja2")
		]

	def get_template_vars(self):
		return dict(version=self._get_version())

	#~~ Helpers

	def _get_version(self):
		if self._version is None:
			try:
				self._version = get_octopi_version()
			except:
				self._logger.exception("Error while reading OctoPi version from file {}".format(_OCTOPI_VERSION_PATH))
				self._version = "unknown"
		return self._version

	def _get_model(self):
		if self._model is None:
			try:
				cpuinfo = self._get_cpuinfo()
				self._model = get_pi_model(cpuinfo.get("hardware", "unknown"),
				                           cpuinfo.get("revision", "unknown"))
			except:
				self._logger.exception("Error while detecting RPi model")
				self._model = "unknown"
		return self._model

	def _get_cpuinfo(self):
		if self._cpuinfo is None:
			try:
				self._cpuinfo = get_pi_cpuinfo()
			except:
				self._logger.exception("Error while fetching cpu info")
				self._cpuinfo = dict()
		return self._cpuinfo

__plugin_name__ = "OctoPi Support Plugin"
__plugin_author__ = "Gina Häußge"
__plugin_description__ = "Provides additional information about your OctoPi instance in the UI."
__plugin_disabling_discouraged__ = gettext("Without this plugin OctoPrint will no longer be able to "
                                           "provide additional information about your OctoPi instance,"
                                           "which will make it more tricky to help you if you need support.")
__plugin_license__ = "AGPLv3"

def __plugin_check__():
	from octoprint.util.platform import get_os
	return get_os() == "linux" and os.path.exists(_OCTOPI_VERSION_PATH)

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = OctoPiSupportPlugin()
