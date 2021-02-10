import octoprint.plugin


class TestSettingsPlugin(octoprint.plugin.SettingsPlugin):
    pass


__plugin_name__ = "Settings Plugin"
__plugin_description__ = "Test settings plugin"
__plugin_implementation__ = TestSettingsPlugin()
__plugin_pythoncompat__ = ">=2.7,<4"
