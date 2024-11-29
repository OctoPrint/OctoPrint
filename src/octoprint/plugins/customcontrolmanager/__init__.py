import octoprint.plugin


class CustomControlManagerPlugin(
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.AssetPlugin,
):
    def get_assets(self):
        return {
            "js": ["js/customcontrolmanager.js"],
            "css": ["css/customcontrolmanager.css"],
            "less": ["less/customcontrolmanager.less"],
        }


__plugin_name__ = "Custom Control Manager"
__plugin_author__ = "Gina Häußge, based on work by Marc Hannappel"
__plugin_description__ = "A UI to configure custom controls"
__plugin_license__ = "AGPLv3"
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_implementation__ = CustomControlManagerPlugin()
