import os
import re

import yaml

from octoprint.util import atomic_write


def all_migrations():
    candidates = globals()
    return [
        candidates[x]
        for x in candidates
        if x.startswith("migrate_") and callable(candidates[x])
    ]


def migrate_gcode_scripts(settings, config):
    """
    Migrates an old development version of gcode scripts to the new template based format.

    Added in 1.2.0
    """

    dirty = False
    if "scripts" in config:
        if "gcode" in config["scripts"]:
            if "templates" in config["scripts"]["gcode"]:
                del config["scripts"]["gcode"]["templates"]

            replacements = {
                "disable_steppers": "M84",
                "disable_hotends": "{% snippet 'disable_hotends' %}",
                "disable_bed": "M140 S0",
                "disable_fan": "M106 S0",
            }

            for name, script in config["scripts"]["gcode"].items():
                settings.saveScript("gcode", name, script.format(**replacements))
        del config["scripts"]
        dirty = True
    return dirty


def migrate_printer_parameters(settings, config):
    """
    Migrates the old "printer > parameters" data structure to the new printer profile mechanism.

    Added in 1.2.0
    """
    default_profile = (
        config["printerProfiles"]["defaultProfile"]
        if "printerProfiles" in config and "defaultProfile" in config["printerProfiles"]
        else {}
    )
    dirty = False

    if "printerParameters" in config:
        printer_parameters = config["printerParameters"]

        if "movementSpeed" in printer_parameters or "invertAxes" in printer_parameters:
            dirty = True
            default_profile["axes"] = {"x": {}, "y": {}, "z": {}, "e": {}}
            if "movementSpeed" in printer_parameters:
                for axis in ("x", "y", "z", "e"):
                    if axis in printer_parameters["movementSpeed"]:
                        default_profile["axes"][axis]["speed"] = printer_parameters[
                            "movementSpeed"
                        ][axis]
                del config["printerParameters"]["movementSpeed"]
            if "invertedAxes" in printer_parameters:
                for axis in ("x", "y", "z", "e"):
                    if axis in printer_parameters["invertedAxes"]:
                        default_profile["axes"][axis]["inverted"] = True
                del config["printerParameters"]["invertedAxes"]

        if (
            "numExtruders" in printer_parameters
            or "extruderOffsets" in printer_parameters
        ):
            dirty = True
            if "extruder" not in default_profile:
                default_profile["extruder"] = {}

            if "numExtruders" in printer_parameters:
                default_profile["extruder"]["count"] = printer_parameters["numExtruders"]
                del config["printerParameters"]["numExtruders"]
            if "extruderOffsets" in printer_parameters:
                extruder_offsets = []
                for offset in printer_parameters["extruderOffsets"]:
                    if "x" in offset and "y" in offset:
                        extruder_offsets.append((offset["x"], offset["y"]))
                default_profile["extruder"]["offsets"] = extruder_offsets
                del config["printerParameters"]["extruderOffsets"]

        if "bedDimensions" in printer_parameters:
            dirty = True
            bed_dimensions = printer_parameters["bedDimensions"]
            if "volume" not in default_profile:
                default_profile["volume"] = {}

            if (
                "circular" in bed_dimensions
                and "r" in bed_dimensions
                and bed_dimensions["circular"]
            ):
                default_profile["volume"]["formFactor"] = "circular"
                default_profile["volume"]["width"] = 2 * bed_dimensions["r"]
                default_profile["volume"]["depth"] = default_profile["volume"]["width"]
            elif "x" in bed_dimensions or "y" in bed_dimensions:
                default_profile["volume"]["formFactor"] = "rectangular"
                if "x" in bed_dimensions:
                    default_profile["volume"]["width"] = bed_dimensions["x"]
                if "y" in bed_dimensions:
                    default_profile["volume"]["depth"] = bed_dimensions["y"]
            del config["printerParameters"]["bedDimensions"]

    if dirty:
        if "printerProfiles" not in config:
            config["printerProfiles"] = {}
        config["printerProfiles"]["defaultProfile"] = default_profile
    return dirty


def migrate_reverse_proxy_config(settings, config):
    """
    Migrates the old "server > baseUrl" and "server > scheme" configuration entries to
    "server > reverseProxy > prefixFallback" and "server > reverseProxy > schemeFallback".

    Added in 1.2.0
    """
    if "server" in config and (
        "baseUrl" in config["server"] or "scheme" in config["server"]
    ):
        prefix = ""
        if "baseUrl" in config["server"]:
            prefix = config["server"]["baseUrl"]
            del config["server"]["baseUrl"]

        scheme = ""
        if "scheme" in config["server"]:
            scheme = config["server"]["scheme"]
            del config["server"]["scheme"]

        if "reverseProxy" not in config["server"] or not isinstance(
            config["server"]["reverseProxy"], dict
        ):
            config["server"]["reverseProxy"] = {}
        if prefix:
            config["server"]["reverseProxy"]["prefixFallback"] = prefix
        if scheme:
            config["server"]["reverseProxy"]["schemeFallback"] = scheme
        settings._logger.info("Migrated reverse proxy configuration to new structure")
        return True
    else:
        return False


def migrate_event_config(settings, config):
    """
    Migrates the old event configuration format of type "events > gcodeCommandTrigger" and
    "event > systemCommandTrigger" to the new events format.

    Added in 1.2.0
    """
    if "events" in config and (
        "gcodeCommandTrigger" in config["events"]
        or "systemCommandTrigger" in config["events"]
    ):
        settings._logger.info("Migrating config (event subscriptions)...")

        # migrate event hooks to new format
        placeholderRe = re.compile(r"%\((.*?)\)s")

        eventNameReplacements = {
            "ClientOpen": "ClientOpened",
            "TransferStart": "TransferStarted",
        }
        payloadDataReplacements = {
            "Upload": {"data": "{file}", "filename": "{file}"},
            "Connected": {"data": "{port} at {baudrate} baud"},
            "FileSelected": {"data": "{file}", "filename": "{file}"},
            "TransferStarted": {"data": "{remote}", "filename": "{remote}"},
            "TransferDone": {"data": "{remote}", "filename": "{remote}"},
            "ZChange": {"data": "{new}"},
            "CaptureStart": {"data": "{file}"},
            "CaptureDone": {"data": "{file}"},
            "MovieDone": {"data": "{movie}", "filename": "{gcode}"},
            "Error": {"data": "{error}"},
            "PrintStarted": {"data": "{file}", "filename": "{file}"},
            "PrintDone": {"data": "{file}", "filename": "{file}"},
        }

        def migrateEventHook(event, command):
            # migrate placeholders
            command = placeholderRe.sub("{__\\1}", command)

            # migrate event names
            if event in eventNameReplacements:
                event = eventNameReplacements["event"]

            # migrate payloads to more specific placeholders
            if event in payloadDataReplacements:
                for key in payloadDataReplacements[event]:
                    command = command.replace(
                        "{__%s}" % key, payloadDataReplacements[event][key]
                    )

            # return processed tuple
            return event, command

        disableSystemCommands = False
        if (
            "systemCommandTrigger" in config["events"]
            and "enabled" in config["events"]["systemCommandTrigger"]
        ):
            disableSystemCommands = not config["events"]["systemCommandTrigger"][
                "enabled"
            ]

        disableGcodeCommands = False
        if (
            "gcodeCommandTrigger" in config["events"]
            and "enabled" in config["events"]["gcodeCommandTrigger"]
        ):
            disableGcodeCommands = not config["events"]["gcodeCommandTrigger"]["enabled"]

        disableAllCommands = disableSystemCommands and disableGcodeCommands
        newEvents = {"enabled": not disableAllCommands, "subscriptions": []}

        if (
            "systemCommandTrigger" in config["events"]
            and "subscriptions" in config["events"]["systemCommandTrigger"]
        ):
            for trigger in config["events"]["systemCommandTrigger"]["subscriptions"]:
                if not ("event" in trigger and "command" in trigger):
                    continue

                newTrigger = {"type": "system"}
                if disableSystemCommands and not disableAllCommands:
                    newTrigger["enabled"] = False

                newTrigger["event"], newTrigger["command"] = migrateEventHook(
                    trigger["event"], trigger["command"]
                )
                newEvents["subscriptions"].append(newTrigger)

        if (
            "gcodeCommandTrigger" in config["events"]
            and "subscriptions" in config["events"]["gcodeCommandTrigger"]
        ):
            for trigger in config["events"]["gcodeCommandTrigger"]["subscriptions"]:
                if not ("event" in trigger and "command" in trigger):
                    continue

                newTrigger = {"type": "gcode"}
                if disableGcodeCommands and not disableAllCommands:
                    newTrigger["enabled"] = False

                newTrigger["event"], newTrigger["command"] = migrateEventHook(
                    trigger["event"], trigger["command"]
                )
                newTrigger["command"] = newTrigger["command"].split(",")
                newEvents["subscriptions"].append(newTrigger)

        config["events"] = newEvents
        settings._logger.info(
            "Migrated %d event subscriptions to new format and structure"
            % len(newEvents["subscriptions"])
        )
        return True
    else:
        return False


def migrate_core_system_commands(settings, config):
    """
    Migrates system commands for restart, reboot and shutdown as defined on OctoPi or
    according to the official setup guide to new core system commands to remove
    duplication.

    If server commands for action is not yet set, migrates command. Otherwise only
    deletes definition from custom system commands.

    Added in 1.3.0
    """
    changed = False

    migration_map = {
        "shutdown": "systemShutdownCommand",
        "reboot": "systemRestartCommand",
        "restart": "serverRestartCommand",
    }

    if (
        "system" in config
        and "actions" in config["system"]
        and isinstance(config["system"]["actions"], (list, tuple))
    ):
        actions = config["system"]["actions"]
        to_delete = []
        for index, spec in enumerate(actions):
            action = spec.get("action")
            command = spec.get("command")
            if action is None or command is None:
                continue

            migrate_to = migration_map.get(action)
            if migrate_to is not None:
                if (
                    "server" not in config
                    or "commands" not in config["server"]
                    or migrate_to not in config["server"]["commands"]
                ):
                    if "server" not in config:
                        config["server"] = {}
                    if "commands" not in config["server"]:
                        config["server"]["commands"] = {}
                    config["server"]["commands"][migrate_to] = command
                    settings._logger.info(
                        "Migrated {} action to server.commands.{}".format(
                            action, migrate_to
                        )
                    )

                to_delete.append(index)
                settings._logger.info(
                    "Deleting {} action from configured system commands, superseded by server.commands.{}".format(
                        action, migrate_to
                    )
                )

        for index in reversed(to_delete):
            actions.pop(index)
            changed = True

    if changed:
        # let's make a backup of our current config, in case someone wants to roll back to an
        # earlier version and needs to recover the former system commands for that
        backup_path = settings.backup("system_command_migration")
        settings._logger.info(
            "Made a copy of the current config at {} to allow recovery of manual system command configuration".format(
                backup_path
            )
        )

    return changed


def migrate_serial_features(settings, config):
    """
    Migrates feature flags identified as serial specific from the feature to the serial config tree and vice versa.

    If a flag already exists in the target tree, only deletes the copy in the source tree.

    Added in 1.3.7
    """
    changed = False

    FEATURE_TO_SERIAL = (
        "waitForStartOnConnect",
        "alwaysSendChecksum",
        "neverSendChecksum",
        "sendChecksumWithUnknownCommands",
        "unknownCommandsNeedAck",
        "sdRelativePath",
        "sdAlwaysAvailable",
        "swallowOkAfterResend",
        "repetierTargetTemp",
        "externalHeatupDetection",
        "supportWait",
        "ignoreIdenticalResends",
        "identicalResendsCountdown",
        "supportFAsCommand",
        "firmwareDetection",
        "blockWhileDwelling",
    )
    SERIAL_TO_FEATURE = ("autoUppercaseBlacklist",)

    def migrate_key(key, source, target):
        if source in config and key in config[source]:
            if config.get(target) is None:
                # make sure we have a serial tree
                config[target] = {}
            if key not in config[target]:
                # only copy over if it's not there yet
                config[target][key] = config[source][key]
            # delete feature flag
            del config[source][key]
            return True
        return False

    for key in FEATURE_TO_SERIAL:
        changed = migrate_key(key, "feature", "serial") or changed

    for key in SERIAL_TO_FEATURE:
        changed = migrate_key(key, "serial", "feature") or changed

    if changed:
        # let's make a backup of our current config, in case someone wants to roll back to an
        # earlier version and needs a backup of their flags
        backup_path = settings.backup("serial_feature_migration")
        settings._logger.info(
            "Made a copy of the current config at {} to allow recovery of serial feature flags".format(
                backup_path
            )
        )

    return changed


def migrate_resend_without_ok(settings, config):
    """
    Migrates supportResendsWithoutOk flag from boolean to ("always", "detect", "never") value range.

    True gets migrated to "always", False to "detect" (which is the new default).

    Added in 1.3.7
    """
    if (
        "serial" in config
        and "supportResendsWithoutOk" in config["serial"]
        and config["serial"]["supportResendsWithoutOk"]
        not in ("always", "detect", "never")
    ):
        value = config["serial"]["supportResendsWithoutOk"]
        if value:
            config["serial"]["supportResendsWithoutOk"] = "always"
        else:
            config["serial"]["supportResendsWithoutOk"] = "detect"
        return True
    return False


def migrate_string_temperature_profile_values(settings, config):
    """
    Migrates/fixes temperature profile wrongly saved with strings instead of ints as temperature values.

    Added in 1.3.8
    """
    if "temperature" in config and "profiles" in config["temperature"]:
        profiles = config["temperature"]["profiles"]
        if any(
            map(
                lambda x: not isinstance(x.get("extruder", 0), int)
                or not isinstance(x.get("bed", 0), int),
                profiles,
            )
        ):
            result = []
            for profile in profiles:
                try:
                    profile["extruder"] = int(profile["extruder"])
                    profile["bed"] = int(profile["bed"])
                except ValueError:
                    pass
                result.append(profile)
            config["temperature"]["profiles"] = result
            return True
    return False


def migrate_blocked_commands(settings, config):
    if "serial" in config and "blockM0M1" in config["serial"]:
        blockM0M1 = config["serial"]["blockM0M1"]
        blockedCommands = config["serial"].get("blockedCommands", [])
        if blockM0M1:
            blockedCommands = set(blockedCommands)
            blockedCommands.add("M0")
            blockedCommands.add("M1")
            config["serial"]["blockedCommands"] = sorted(blockedCommands)
        else:
            config["serial"]["blockedCommands"] = sorted(
                [v for v in blockedCommands if v not in ("M0", "M1")]
            )
        del config["serial"]["blockM0M1"]
        return True
    return False


def migrate_gcodeviewer_enabled(settings, config):
    if (
        "gcodeViewer" in config
        and "enabled" in config["gcodeViewer"]
        and not config["gcodeViewer"]["enabled"]
    ):
        if "plugins" not in config:
            config["plugins"] = {}
        if "_disabled" not in config["plugins"]:
            config["plugins"]["_disabled"] = []
        config["plugins"]["_disabled"].append("gcodeviewer")
        del config["gcodeViewer"]["enabled"]
        return True
    return False


def migrate_serial_to_connection_profile(settings, config):
    if "serial" in config:
        from octoprint.comm.connectionprofile import ConnectionProfile
        from octoprint.comm.protocol.reprap import ReprapGcodeProtocol
        from octoprint.comm.transport.serialtransport import SerialTransport

        backup_path = settings.backup("serial_to_connection_profile")
        settings._logger.info(
            "Made a copy of the current config at {} to allow recovery of serial settings".format(
                backup_path
            )
        )

        def copy_config_to_profile(
            config_path, profile_path, config, profile, converter=None
        ):
            node = config
            for p in config_path:
                if p not in node:
                    return
                node = node[p]
            value = node
            if callable(converter):
                value = converter(value)

            node = profile
            for p in profile_path[:-1]:
                if p not in node:
                    node[p] = {}
                node = node[p]
            node[profile_path[-1]] = value

        printer_profile = config.get("printerProfiles", {"default": "_default"}).get(
            "default", "_default"
        )

        protocol_parameters = {"flavor": "generic", "flavor_overrides": {}}

        ### flavor overrides
        copy_config_to_profile(
            ["longRunningCommands"],
            ["flavor_overrides", "long_running_commands"],
            config["serial"],
            protocol_parameters,
        )
        copy_config_to_profile(
            ["blockedCommands"],
            ["flavor_overrides", "blocked_commands"],
            config["serial"],
            protocol_parameters,
        )
        copy_config_to_profile(
            ["pausingCommands"],
            ["flavor_overrides", "pausing_commands"],
            config["serial"],
            protocol_parameters,
        )
        copy_config_to_profile(
            ["emergencyCommands"],
            ["flavor_overrides", "emergency_commands"],
            config["serial"],
            protocol_parameters,
        )
        copy_config_to_profile(
            ["checksumRequiringCommands"],
            ["flavor_overrides", "checksum_requiring_commands"],
            config["serial"],
            protocol_parameters,
        )
        copy_config_to_profile(
            ["supportResendsWithoutOk"],
            ["flavor_overrides", "trigger_ok_after_resend"],
            config["serial"],
            protocol_parameters,
        )
        copy_config_to_profile(
            ["unknownCommandsNeedAck"],
            ["flavor_overrides", "unknown_requires_ack"],
            config["serial"],
            protocol_parameters,
        )
        copy_config_to_profile(
            ["sendChecksumWithUnknownCommands"],
            ["flavor_overrides", "unknown_with_checksum"],
            config["serial"],
            protocol_parameters,
        )
        copy_config_to_profile(
            ["externalHeatupDetection"],
            ["flavor_overrides", "detect_external_heatup"],
            config["serial"],
            protocol_parameters,
        )
        copy_config_to_profile(
            ["blockWhileDwelling"],
            ["flavor_overrides", "block_while_dwelling"],
            config["serial"],
            protocol_parameters,
        )
        copy_config_to_profile(
            ["sdRelativePath"],
            ["flavor_overrides", "sd_relative_path"],
            config["serial"],
            protocol_parameters,
        )
        copy_config_to_profile(
            ["sdAlwaysAvailable"],
            ["flavor_overrides", "sd_always_available"],
            config["serial"],
            protocol_parameters,
        )

        if (
            "alwaysSendChecksum" in config["serial"]
            or "neverSendChecksum" in config["serial"]
        ):
            always = config["serial"].get("alwaysSendChecksum", False)
            never = config["serial"].get("neverSendChecksum", False)

            if not always and not never:
                protocol_parameters["flavor_overrides"]["send_checksum"] = "printing"
            elif always:
                protocol_parameters["flavor_overrides"]["send_checksum"] = "always"
            elif never:
                protocol_parameters["flavor_overrides"]["send_checksum"] = "never"

        ### error handling
        copy_config_to_profile(
            ["sendM112OnError"],
            ["error_handling", "send_m112"],
            config["serial"],
            protocol_parameters,
        )
        if (
            "disconnectOnErrors" in config["serial"]
            or "ignoreErrorsFromFirmware" in config["serial"]
        ):
            disconnect = config["serial"].get("disconnectOnErrors", True)
            ignore = config["serial"].get("ignoreErrorsFromFirmware", False)

            if ignore:
                protocol_parameters["error_handling"] = {"firmware_errors": "ignore"}
            elif not disconnect:
                protocol_parameters["error_handling"] = {"firmware_errors": "cancel"}
            else:
                protocol_parameters["error_handling"] = {"firmware_errors": "disconnect"}

        ### pausing
        copy_config_to_profile(
            ["logPositionOnPause"],
            ["pausing", "log_position_on_pause"],
            config["serial"],
            protocol_parameters,
        )

        ### cancelling
        copy_config_to_profile(
            ["logPositionOnCancel"],
            ["cancelling", "log_position_on_cancel"],
            config["serial"],
            protocol_parameters,
        )
        copy_config_to_profile(
            ["abortHeatupOnCancel"],
            ["cancelling", "abort_heatups"],
            config["serial"],
            protocol_parameters,
        )

        ### timeouts
        copy_config_to_profile(
            ["timeout", "communication"],
            ["timeouts", "communication_timeout_normal"],
            config["serial"],
            protocol_parameters,
        )
        copy_config_to_profile(
            ["timeout", "communicationBusy"],
            ["timeouts", "communication_timeout_busy"],
            config["serial"],
            protocol_parameters,
        )
        copy_config_to_profile(
            ["timeout", "connection"],
            ["timeouts", "connection_timeout"],
            config["serial"],
            protocol_parameters,
        )
        copy_config_to_profile(
            ["timeout", "detection"],
            ["timeouts", "detection_timeout"],
            config["serial"],
            protocol_parameters,
        )
        copy_config_to_profile(
            ["timeout", "positionLogWait"],
            ["timeouts", "position_log_wait"],
            config["serial"],
            protocol_parameters,
        )
        copy_config_to_profile(
            ["timeout", "baudrateDetectionPause"],
            ["timeouts", "baudrate_detection_pause"],
            config["serial"],
            protocol_parameters,
        )
        copy_config_to_profile(
            ["timeout", "resendOk"],
            ["timeouts", "resendok_timeout"],
            config["serial"],
            protocol_parameters,
        )
        copy_config_to_profile(
            ["maxCommunicationTimeouts", "idle"],
            ["timeouts", "max_consecutive_timeouts_idle"],
            config["serial"],
            protocol_parameters,
        )
        copy_config_to_profile(
            ["maxCommunicationTimeouts", "printing"],
            ["timeouts", "max_consecutive_timeouts_printing"],
            config["serial"],
            protocol_parameters,
        )
        copy_config_to_profile(
            ["maxCommunicationTimeouts", "long"],
            ["timeouts", "max_consecutive_timeouts_long"],
            config["serial"],
            protocol_parameters,
        )

        ### intervals
        copy_config_to_profile(
            ["timeout", "temperature"],
            ["intervals", "temperature_interval_idle"],
            config["serial"],
            protocol_parameters,
        )
        copy_config_to_profile(
            ["timeout", "temperatureTargetSet"],
            ["intervals", "temperature_interval_target"],
            config["serial"],
            protocol_parameters,
        )
        copy_config_to_profile(
            ["timeout", "temperatureAutoreport"],
            ["intervals", "temperature_interval_auto"],
            config["serial"],
            protocol_parameters,
        )
        copy_config_to_profile(
            ["timeout", "sdStatus"],
            ["intervals", "sdstatus_interval_normal"],
            config["serial"],
            protocol_parameters,
        )
        copy_config_to_profile(
            ["timeout", "sdStatusAutoreport"],
            ["intervals", "sdstatus_interval_auto"],
            config["serial"],
            protocol_parameters,
        )

        ### capabilities
        copy_config_to_profile(
            ["capabilities", "autoreport_temp"],
            ["capabilities", "autoreport_temp"],
            config["serial"],
            protocol_parameters,
        )
        copy_config_to_profile(
            ["capabilities", "autoreport_sdstatus"],
            ["capabilities", "autoreport_sd_status"],
            config["serial"],
            protocol_parameters,
        )
        copy_config_to_profile(
            ["capabilities", "emergency_parser"],
            ["capabilities", "emergency_parser"],
            config["serial"],
            protocol_parameters,
        )
        copy_config_to_profile(
            ["capabilities", "busy_protocol"],
            ["capabilities", "busy_protocol"],
            config["serial"],
            protocol_parameters,
        )

        # TODO: chamber temp?
        # TODO: maxWritePasses
        # TODO: helloCommand
        # TODO: terminalLogSize
        # TODO: logResends
        # TODO: waitForStartOnConnect
        # TODO: maxNotSdPrinting
        # TODO: swallowOkAfterResend
        # TODO: repetierTargetTemp
        # TODO: supportWait
        # TODO: ignoreIdenticalResends
        # TODO: identicalResendsCountdown
        # TODO: supportFAsCommand
        # TODO: firmwareDetection
        # TODO: triggerOkForM29

        ### logging
        if "log" in config["serial"]:
            if "connection" not in config["serial"]:
                config["serial"]["connection"] = {}
            if "log" not in config["serial"]["connection"]:
                config["serial"]["connection"]["log"] = {}
            config["serial"]["connection"]["log"]["connection"] = config["serial"]["log"]

        port = config["serial"].get("port")
        transport_parameters = {}
        if port == "VIRTUAL":
            # special case for the virtual printer plugin
            transport = "virtual"
        else:
            transport = SerialTransport.key
            copy_config_to_profile(
                ["port"],
                ["port"],
                config["serial"],
                transport_parameters,
                converter=lambda x: None if x == "AUTO" else x,
            )
            copy_config_to_profile(
                ["baudrate"], ["baudrate"], config["serial"], transport_parameters
            )
            copy_config_to_profile(
                ["exclusive"], ["exclusive"], config["serial"], transport_parameters
            )
            copy_config_to_profile(
                ["useParityWorkaround"],
                ["parity_workaround"],
                config["serial"],
                transport_parameters,
            )

        profile = ConnectionProfile(
            "migrated",
            name="Migrated from serial settings",
            printer_profile=printer_profile,
            protocol=ReprapGcodeProtocol.key,
            protocol_parameters=protocol_parameters,
            transport=transport,
            transport_parameters=transport_parameters,
        )

        try:
            with atomic_write(
                os.path.join(
                    settings.getBaseFolder("connectionProfiles"), "migrated.profile"
                ),
                mode="wt",
                max_permissions=0o666,
            ) as f:
                yaml.safe_dump(
                    profile.as_dict(),
                    f,
                    default_flow_style=False,
                    indent=2,
                    allow_unicode=True,
                )

            if "connection" not in config:
                config["connection"] = {}
            if "profiles" not in config["connection"]:
                config["connection"]["profiles"] = {}
            if not config["connection"]["profiles"]["default"]:
                config["connection"]["profiles"]["default"] = "migrated"
        except Exception:
            settings._logger.exception(
                "Error while trying to save migrated connection profile"
            )
