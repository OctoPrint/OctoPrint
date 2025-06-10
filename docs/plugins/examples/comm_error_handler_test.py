import logging

_HANDLED_ERRORS = ("fan error", "bed missing")


def handle_error(comm, error_message, *args, **kwargs):
    lower_error = error_message.lower()
    if any(map(lambda x: x in lower_error, _HANDLED_ERRORS)):
        logging.getLogger("octoprint.plugin.error_handler_test").info(
            f'Error "{error_message}" is handled by this plugin'
        )
        return True


__plugin_name__ = "Comm Error Handler Test"
__plugin_pythoncompat__ = ">=2.7,<4"
__plugin_hooks__ = {"octoprint.comm.protocol.gcode.error": handle_error}
