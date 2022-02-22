import unittest
from unittest import mock

import octoprint.plugin


class BlueprintPluginTest(unittest.TestCase):
    def setUp(self):
        self.basefolder = "/some/funny/basefolder"

        self.plugin = octoprint.plugin.BlueprintPlugin()
        self.plugin._basefolder = self.basefolder

        class MyAssetPlugin(
            octoprint.plugin.BlueprintPlugin, octoprint.plugin.AssetPlugin
        ):
            def get_asset_folder(self):
                return "/some/asset/folder"

        class MyTemplatePlugin(
            octoprint.plugin.BlueprintPlugin, octoprint.plugin.TemplatePlugin
        ):
            def get_template_folder(self):
                return "/some/template/folder"

        self.assetplugin = MyAssetPlugin()
        self.assetplugin._basefolder = self.basefolder

        self.templateplugin = MyTemplatePlugin()
        self.templateplugin._basefolder = self.basefolder

    def test_route(self):
        def test_method():
            pass

        octoprint.plugin.BlueprintPlugin.route("/test/method", methods=["GET"])(
            test_method
        )
        octoprint.plugin.BlueprintPlugin.route("/test/method/{foo}", methods=["PUT"])(
            test_method
        )

        self.assertTrue(hasattr(test_method, "_blueprint_rules"))
        self.assertTrue("test_method" in test_method._blueprint_rules)
        self.assertTrue(len(test_method._blueprint_rules["test_method"]) == 2)
        self.assertListEqual(
            test_method._blueprint_rules["test_method"],
            [
                ("/test/method", {"methods": ["GET"]}),
                ("/test/method/{foo}", {"methods": ["PUT"]}),
            ],
        )

    def test_errorhandler(self):
        def test_method():
            pass

        octoprint.plugin.BlueprintPlugin.errorhandler(404)(test_method)

        self.assertTrue(hasattr(test_method, "_blueprint_error_handler"))
        self.assertTrue("test_method" in test_method._blueprint_error_handler)
        self.assertTrue(len(test_method._blueprint_error_handler["test_method"]) == 1)
        self.assertListEqual(test_method._blueprint_error_handler["test_method"], [404])

    def test_get_blueprint_kwargs(self):
        import os

        expected = {
            "static_folder": os.path.join(self.basefolder, "static"),
            "template_folder": os.path.join(self.basefolder, "templates"),
        }

        result = self.plugin.get_blueprint_kwargs()

        self.assertEqual(result, expected)

    def test_get_blueprint_kwargs_assetplugin(self):
        import os

        expected = {
            "static_folder": self.assetplugin.get_asset_folder(),
            "template_folder": os.path.join(self.basefolder, "templates"),
        }

        result = self.assetplugin.get_blueprint_kwargs()

        self.assertEqual(result, expected)

    def test_get_blueprint_kwargs_templateplugin(self):
        import os

        expected = {
            "static_folder": os.path.join(self.basefolder, "static"),
            "template_folder": self.templateplugin.get_template_folder(),
        }

        result = self.templateplugin.get_blueprint_kwargs()

        self.assertEqual(result, expected)

    def test_get_blueprint(self):
        import os

        expected_kwargs = {
            "static_folder": os.path.join(self.basefolder, "static"),
            "template_folder": os.path.join(self.basefolder, "templates"),
        }

        class MyPlugin(octoprint.plugin.BlueprintPlugin):
            @octoprint.plugin.BlueprintPlugin.route("/some/path", methods=["GET"])
            def route_method(self):
                pass

            @octoprint.plugin.BlueprintPlugin.errorhandler(404)
            def errorhandler_method(self):
                pass

            @octoprint.plugin.BlueprintPlugin.route("/hidden/path", methods=["GET"])
            def _hidden_method(self):
                pass

        plugin = MyPlugin()
        plugin._basefolder = self.basefolder
        plugin._identifier = "myplugin"

        with mock.patch("flask.Blueprint") as MockBlueprint:
            blueprint = mock.MagicMock()
            MockBlueprint.return_value = blueprint

            errorhandler = mock.MagicMock()
            blueprint.errorhandler.return_value = errorhandler

            result = plugin.get_blueprint()

        self.assertEqual(result, blueprint)

        MockBlueprint.assert_called_once_with("myplugin", "myplugin", **expected_kwargs)
        blueprint.add_url_rule.assert_called_once_with(
            "/some/path", "route_method", view_func=plugin.route_method, methods=["GET"]
        )

        blueprint.errorhandler.assert_called_once_with(404)
        errorhandler.assert_called_once_with(plugin.errorhandler_method)

    def test_get_blueprint_cached(self):
        blueprint = mock.MagicMock()
        self.plugin._blueprint = blueprint

        result = self.plugin.get_blueprint()

        self.assertEqual(blueprint, result)
