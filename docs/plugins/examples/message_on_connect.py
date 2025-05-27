def message_on_connect(comm, script_type, script_name, *args, **kwargs):
    if not script_type == "gcode" or not script_name == "afterPrinterConnected":
        return None

    prefix = None
    postfix = "M117 OctoPrint connected"
    return prefix, postfix


__plugin_name__ = "Message on connect"
__plugin_pythoncompat__ = ">=2.7,<4"
__plugin_hooks__ = {"octoprint.comm.protocol.scripts": message_on_connect}
