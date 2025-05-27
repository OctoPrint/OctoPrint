import logging

_logger = logging.getLogger("octoprint.plugins.log_command_phases")


def handle_gcode_phase(
    comm_instance, phase, cmd, cmd_type, gcode, subcode=None, tags=None, *args, **kwargs
):
    output_parts = ["phase: {phase}", "cmd: {cmd}"]
    if cmd_type:
        output_parts.append("cmd_type: {cmd_type}")
    if gcode:
        output_parts.append("gcode: {gcode}")
    if subcode:
        output_parts.append("subcode: {subcode}")
    if tags:
        output_parts.append("tags: [ {tags} ]")

    _logger.info(
        " | ".join(output_parts).format(
            phase=phase,
            cmd=cmd,
            cmd_type=cmd_type,
            gcode=gcode,
            subcode=subcode if subcode else "",
            tags=", ".join(sorted(tags)) if tags else "",
        )
    )


__plugin_name__ = "Log command phases"
__plugin_description__ = "Logs the various phases a command sent through OctoPrint to the printer goes through to octoprint.log"
__plugin_pythoncompat__ = ">=2.7,<4"
__plugin_hooks__ = {
    "octoprint.comm.protocol.gcode.queuing": handle_gcode_phase,
    "octoprint.comm.protocol.gcode.queued": handle_gcode_phase,
    "octoprint.comm.protocol.gcode.sending": handle_gcode_phase,
    "octoprint.comm.protocol.gcode.sent": handle_gcode_phase,
}
