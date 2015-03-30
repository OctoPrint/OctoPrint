from __future__ import absolute_import

import octoprint.plugin


class TestStartupPlugin(octoprint.plugin.StartupPlugin):
	pass


__plugin_name__ = "Startup Plugin"
__plugin_description__ = "Test startup plugin"
__plugin_implementation__ = TestStartupPlugin()