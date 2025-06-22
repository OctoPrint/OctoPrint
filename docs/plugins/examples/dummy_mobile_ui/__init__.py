import octoprint.plugin


class DummyMobileUiPlugin(octoprint.plugin.UiPlugin, octoprint.plugin.TemplatePlugin):
    def will_handle_ui(self, request):
        # returns True if the User Agent sent by the client matches one of
        # the User Agent strings known for any of the platforms android, ipad
        # or iphone
        return request.user_agent and request.user_agent.platform in (
            "android",
            "ipad",
            "iphone",
        )

    def on_ui_render(self, now, request, render_kwargs):
        # if will_handle_ui returned True, we will now render our custom index
        # template, using the render_kwargs as provided by OctoPrint
        from flask import make_response, render_template

        return make_response(
            render_template("dummy_mobile_ui_index.jinja2", **render_kwargs)
        )


__plugin_name__ = "Dummy Mobile UI"
__plugin_pythoncompat__ = ">=2.7,<4"
__plugin_implementation__ = DummyMobileUiPlugin()
