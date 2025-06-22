import octoprint.plugin


class RewriteM107Plugin(octoprint.plugin.OctoPrintPlugin):
    def rewrite_m107(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        if gcode and gcode == "M107":
            cmd = "M106 S0"
        return (cmd,)

    def sent_m106(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        if gcode and gcode == "M106":
            self._logger.info(f"Just sent M106: {cmd}")


__plugin_name__ = "Rewrite M107"
__plugin_pythoncompat__ = ">=2.7,<4"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = RewriteM107Plugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.comm.protocol.gcode.queuing": __plugin_implementation__.rewrite_m107,
        "octoprint.comm.protocol.gcode.sent": __plugin_implementation__.sent_m106,
    }
