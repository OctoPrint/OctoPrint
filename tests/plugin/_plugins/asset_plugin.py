import octoprint.plugin


class TestAssetPlugin(octoprint.plugin.AssetPlugin):
    pass


__plugin_name__ = "Asset Plugin"
__plugin_description__ = "Test asset plugin"
__plugin_implementation__ = TestAssetPlugin()
__plugin_pythoncompat__ = ">=2.7,<4"
