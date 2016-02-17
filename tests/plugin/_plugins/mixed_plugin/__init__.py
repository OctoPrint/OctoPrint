# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import octoprint.plugin


class TestMixedPlugin(octoprint.plugin.StartupPlugin, octoprint.plugin.SettingsPlugin):
	def get_sorting_key(self, context=None):
		if context == "sorting_test":
			return 100
		else:
			return None


__plugin_name__ = "Mixed Plugin"
__plugin_description__ = "Test mixed plugin"
__plugin_implementation__ = TestMixedPlugin()
