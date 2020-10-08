# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import octoprint.plugin


class TestSettingsPlugin(octoprint.plugin.SettingsPlugin):
    pass


__plugin_name__ = "Settings Plugin"
__plugin_description__ = "Test settings plugin"
__plugin_implementation__ = TestSettingsPlugin()
__plugin_pythoncompat__ = ">=2.7,<4"
