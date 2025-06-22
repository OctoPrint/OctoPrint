def sanitize_temperatures(comm, parsed_temps):
    return {
        k: v
        for k, v in parsed_temps.items()
        if isinstance(v, tuple) and len(v) == 2 and is_sane(v[0])
    }


def is_sane(actual):
    return 1.0 <= actual <= 300.0


__plugin_name__ = "Sanitize Temperatures"
__plugin_pythoncompat__ = ">=2.7,<4"
__plugin_hooks__ = {
    "octoprint.comm.protocol.temperatures.received": sanitize_temperatures
}
