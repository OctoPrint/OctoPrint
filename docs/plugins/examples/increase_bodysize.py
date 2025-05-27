import flask

import octoprint.plugin


class BodySizePlugin(octoprint.plugin.BlueprintPlugin, octoprint.plugin.SettingsPlugin):
    def __init__(self):
        self._sizes = (100, 200, 500, 1024)

    @octoprint.plugin.BlueprintPlugin.route("/upload/<int:size>", methods=["POST"])
    def api_endpoint(self, size):
        if size not in self._sizes:
            return flask.make_response(404)

        input_name = "file"
        keys = ("name", "size", "content_type", "path")

        result = dict(
            found_file=False,
        )
        for key in keys:
            param = input_name + "." + key
            if param in flask.request.values:
                result["found_file"] = True
                result[key] = flask.request.values[param]

        return flask.jsonify(result)

    def bodysize_hook(self, current_max_body_sizes, *args, **kwargs):
        return [("POST", r"/upload/%i" % size, size * 1024) for size in self._sizes]


__plugin_name__ = "Increase upload size"
__plugin_description__ = "Increases the body size on some custom API endpoints"
__plugin_pythoncompat__ = ">=2.7,<4"


def __plugin_load__():
    global __plugin_implementation__
    global __plugin_hooks__

    __plugin_implementation__ = BodySizePlugin()
    __plugin_hooks__ = {
        "octoprint.server.http.bodysize": __plugin_implementation__.bodysize_hook
    }
