import octoprint.plugin


class TornadoRoutePlugin(octoprint.plugin.SettingsPlugin):
    def route_hook(self, server_routes, *args, **kwargs):
        from octoprint.server.util.tornado import (
            LargeResponseHandler,
            UrlProxyHandler,
            path_validation_factory,
        )
        from octoprint.util import is_hidden_path

        return [
            (
                r"/download/(.*)",
                LargeResponseHandler,
                dict(
                    path=self._settings.global_get_basefolder("uploads"),
                    as_attachment=True,
                    path_validation=path_validation_factory(
                        lambda path: not is_hidden_path(path), status_code=404
                    ),
                ),
            ),
            (
                r"forward",
                UrlProxyHandler,
                dict(
                    url=self._settings.global_get(["webcam", "snapshot"]),
                    as_attachment=True,
                ),
            ),
        ]


__plugin_name__ = "Add Tornado Route"
__plugin_description__ = "Adds two tornado routes to demonstrate hook usage"
__plugin_pythoncompat__ = ">=2.7,<4"


def __plugin_load__():
    global __plugin_implementation__
    global __plugin_hooks__

    __plugin_implementation__ = TornadoRoutePlugin()
    __plugin_hooks__ = {
        "octoprint.server.http.routes": __plugin_implementation__.route_hook
    }
