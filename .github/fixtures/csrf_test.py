from flask import jsonify

import octoprint.plugin


class CsrfTestPlugin(octoprint.plugin.BlueprintPlugin, octoprint.plugin.SimpleApiPlugin):
    # ~~ BlueprintPlugin mixin

    @octoprint.plugin.BlueprintPlugin.route("/active", methods=["POST"])
    def active_route(self):
        return jsonify({"message": "Hello World!"})

    @octoprint.plugin.BlueprintPlugin.route("/exempt", methods=["POST"])
    @octoprint.plugin.BlueprintPlugin.csrf_exempt()
    def exempt_route(self):
        return jsonify({"message": "Hello World!"})

    def is_blueprint_csrf_protected(self):
        return True

    # ~~ SimpleApiPlugin mixin

    def get_api_commands(self):
        return {"test": []}

    def on_api_command(self, command, data):
        return jsonify({"message": "Hello World!"})


__plugin_name__ = "CSRF Test"
__plugin_version__ = "0.1.0"
__plugin_description__ = "A SimpleApi/BlueprintPlugin for testing CSRF"
__plugin_pythoncompat__ = ">=3,<4"
__plugin_implementation__ = CsrfTestPlugin()
