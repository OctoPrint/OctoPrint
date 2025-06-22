def custom_atcommand_handler(
    comm, phase, command, parameters, tags=None, *args, **kwargs
):
    if command != "wait":
        return

    if tags is None:
        tags = set()

    if "script:afterPrintPaused" in tags:
        # This makes sure we don't run into an infinite loop if the user included @wait in the afterPrintPaused
        # GCODE script for whatever reason
        return

    comm.setPause(True, tags=tags)


__plugin_name__ = "Custom @ command"
__plugin_pythoncompat__ = ">=2.7,<4"
__plugin_hooks__ = {"octoprint.comm.protocol.atcommand.queuing": custom_atcommand_handler}
