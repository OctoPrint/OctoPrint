# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2019 The OctoPrint Project - Released under terms of the AGPLv3 License"

import octoprint.plugin
import logging

from octoprint.util.version import get_octoprint_version_string, is_released_octoprint_version

SENTRY_URL_SERVER = "https://827d1f11ccda4b31b924f29aaacab493@sentry.io/1373987"
SENTRY_URL_COREUI = "https://30bdc39d2248444c8bc01484f38c9444@sentry.io/1374096"

SETTINGS_DEFAULTS = dict(enabled=False,
                         enabled_unreleased=False,
                         unique_id=None,
                         url_server=SENTRY_URL_SERVER,
                         url_coreui=SENTRY_URL_COREUI)


class ErrorTrackingPlugin(octoprint.plugin.SettingsPlugin,
                          octoprint.plugin.AssetPlugin,
                          octoprint.plugin.TemplatePlugin):

	def get_template_configs(self):
		return [
			dict(type="generic", template="errortracking_javascripts.jinja2")
		]

	def get_template_vars(self):
		enabled = self._settings.get_boolean(["enabled"])
		enabled_unreleased = self._settings.get_boolean(["enabled_unreleased"])

		return dict(enabled=enabled and (enabled_unreleased or is_released_octoprint_version()),
		            unique_id=self._settings.get(["unique_id"]),
		            url_coreui=self._settings.get(["url_coreui"]))

	def get_assets(self):
		return dict(js=["js/sentry.min.js",])

	def get_settings_defaults(self):
		return SETTINGS_DEFAULTS


def __plugin_enable__():
	# this is a bit hackish, but we want to enable error tracking as early in the platform lifecycle as possible
	# and hence can't wait until our implementation is initialized and injected with settings

	from octoprint.settings import settings

	version = get_octoprint_version_string()

	s = settings()
	plugin_defaults = dict(plugins=dict(errortracking=SETTINGS_DEFAULTS))

	enabled = s.getBoolean(["plugins", "errortracking", "enabled"], defaults=plugin_defaults)
	enabled_unreleased = s.getBoolean(["plugins", "errortracking", "enabled_unreleased"], defaults=plugin_defaults)
	url_server = s.get(["plugins", "errortracking", "url_server"], defaults=plugin_defaults)
	unique_id = s.get(["plugins", "errortracking", "unique_id"], defaults=plugin_defaults)
	if unique_id is None:
		import uuid
		unique_id = str(uuid.uuid4())
		s.set(["plugins", "errortracking", "unique_id"], unique_id, defaults=plugin_defaults)
		s.save()

	if enabled and (enabled_unreleased or is_released_octoprint_version()):
		import sentry_sdk
		sentry_sdk.init(url_server,
		                release=version)

		with sentry_sdk.configure_scope() as scope:
			scope.user = dict(id=unique_id)

		logging.getLogger("octoprint.plugin.errortracking").info("Initialized error tracking")

__plugin_name__ = "Error Tracking"
__plugin_author__ = "Gina Häußge"
__plugin_implementation__ = ErrorTrackingPlugin()
