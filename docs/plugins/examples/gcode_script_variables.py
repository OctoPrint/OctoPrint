def gcode_script_variables(comm, script_type, script_name, *args, **kwargs):
    if not script_type == "gcode" or not script_name == "beforePrintStarted":
        return None

    prefix = None
    postfix = None
    variables = dict(myvariable="Hi! I'm a variable!")
    return prefix, postfix, variables


__plugin_name__ = "gcode script variables"
__plugin_pythoncompat__ = ">=2.7,<4"
__plugin_hooks__ = {"octoprint.comm.protocol.scripts": gcode_script_variables}
