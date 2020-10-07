# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import octoprint.plugin


class TestDeprecatedAssetPlugin(octoprint.plugin.AssetPlugin):
    pass


class TestSecondaryDeprecatedAssetPlugin(octoprint.plugin.AssetPlugin):
    pass


__plugin_name__ = "Deprecated Plugin"
__plugin_description__ = "Test deprecated plugin"
__plugin_implementations__ = [
    TestDeprecatedAssetPlugin(),
    TestSecondaryDeprecatedAssetPlugin(),
]
__plugin_pythoncompat__ = ">=2.7,<4"
