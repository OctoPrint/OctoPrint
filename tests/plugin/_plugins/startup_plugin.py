# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import octoprint.plugin


class TestStartupPlugin(octoprint.plugin.StartupPlugin):
    def get_sorting_key(self, context=None):
        if context == "sorting_test":
            return 10
        else:
            return None


__plugin_name__ = "Startup Plugin"
__plugin_description__ = "Test startup plugin"
__plugin_implementation__ = TestStartupPlugin()
__plugin_pythoncompat__ = ">=2.7,<4"
