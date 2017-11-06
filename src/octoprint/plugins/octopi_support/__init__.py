# coding=utf-8
from __future__ import absolute_import, division, print_function

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

import flask
import os

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


def get_pi_revision():
	with open(_CPUINFO_PATH) as f:
		for line in f:
			if line and line.startswith("Revision:"):
				return line[line.index(":") + 1:].strip()
	return "unknown"


def get_pi_model(revision):
	if revision.startswith("1000"):
		# strip flag for over-volted (https://elinux.org/RPi_HardwareHistory#Which_Pi_have_I_got.3F)
		revision = revision[4:]
	return _RPI_REVISION_MAP.get(revision.lower(), "unknown")


class OctoPiSupportPlugin(octoprint.plugin.EnvironmentDetectionPlugin,
                          octoprint.plugin.SimpleApiPlugin,
                          octoprint.plugin.AssetPlugin,
                          octoprint.plugin.TemplatePlugin):

	def __init__(self):
		self._version = None
		self._revision = None
		self._model = None

	#~~ EnvironmentDetectionPlugin

	def get_additional_environment(self):
		return dict(version=self._get_version(),
		            revision=self._get_revision(),
		            model=self._get_model())

	#~~ SimpleApiPlugin

	def on_api_get(self, request):
		return flask.jsonify(version=self._get_version(),
		                     revision=self._get_revision(),
		                     model=self._get_model())

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
		version = self._get_version()
		revision = self._get_revision()
		model = self._get_model()

		return dict(version=version,
		            rpi=(revision is not None and revision != "unknown" and model is not None and model != "unknown"),
		            rpi_revision=revision,
		            rpi_model=model)

	#~~ Helpers

	def _get_version(self):
		if self._version is None:
			try:
				self._version = get_octopi_version()
			except:
				self._logger.exception("Error while reading OctoPi version from file {}".format(_OCTOPI_VERSION_PATH))
		return self._version

	def _get_model(self):
		if self._model is None:
			try:
				self._model = get_pi_model(self._get_revision())
			except:
				self._logger.exception("Error while detecting RPi model")
		return self._model

	def _get_revision(self):
		if self._revision is None:
			try:
				self._revision = get_pi_revision()
			except:
				self._logger.exception("Error while detecting RPi revision")
		return self._revision

def __plugin_check__():
	from octoprint.util.platform import get_os
	return get_os() == "linux" and os.path.exists(_OCTOPI_VERSION_PATH)

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = OctoPiSupportPlugin()
