import octoprint.plugin


class CustomActionCommandPlugin(octoprint.plugin.OctoPrintPlugin):
    def custom_action_handler(self, comm, line, action, *args, **kwargs):
        if not action == "custom":
            return

        self._logger.info('Received "custom" action from printer')


__plugin_name__ = "Custom action command"
__plugin_pythoncompat__ = ">=2.7,<4"


def __plugin_load__():
    plugin = CustomActionCommandPlugin()

    global __plugin_implementation__
    __plugin_implementation__ = plugin

    global __plugin_hooks__
    __plugin_hooks__ = {"octoprint.comm.protocol.action": plugin.custom_action_handler}
