# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import octoprint.plugin


class TestAssetPlugin(octoprint.plugin.AssetPlugin):
    pass


__plugin_name__ = "Asset Plugin"
__plugin_description__ = "Test asset plugin"
__plugin_implementation__ = TestAssetPlugin()
__plugin_pythoncompat__ = ">=2.7,<4"
