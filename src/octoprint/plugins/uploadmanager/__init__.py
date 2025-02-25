import octoprint.plugin


class UploadmanagerPlugin(
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.AssetPlugin,
):
    def get_assets(self):
        return {
            "js": [
                "js/ko.click.single.js",
                "js/ko.click.double.js",
                "js/ko.marquee.js",
                "js/uploadmanager.js",
            ],
            "css": ["css/uploadmanager.css"],
            "less": ["less/uploadmanager.less"],
        }


__plugin_name__ = "Upload Manager"
__plugin_author__ = "Gina Häußge, based on work by Marc Hannappel"
__plugin_description__ = "A file manager to manage the printables you upload to OctoPrint"
__plugin_license__ = "AGPLv3"
__plugin_pythoncompat__ = ">=3.9,<4"
__plugin_implementation__ = UploadmanagerPlugin()
