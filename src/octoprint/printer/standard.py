"""
This module holds the standard implementation of the :class:`PrinterInterface` and it helpers.
"""

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import copy
import logging
import os
import threading
import time
from typing import List

from frozendict import frozendict

import octoprint.util.json
from octoprint import util as util
from octoprint.events import Events, eventManager
from octoprint.filemanager import FileDestinations, NoSuchStorage, valid_file_type
from octoprint.plugin import ProgressPlugin, plugin_manager
from octoprint.printer import (
    InvalidFileLocation,
    InvalidFileType,
    PrinterCallback,
    PrinterInterface,
    UnknownScript,
)
from octoprint.printer.estimation import PrintTimeEstimator
from octoprint.schema import BaseModel
from octoprint.settings import settings
from octoprint.util import InvariantContainer
from octoprint.util import comm as comm
from octoprint.util import get_fully_qualified_classname as fqcn
from octoprint.util import to_unicode


class ErrorInformation(BaseModel):
    error: str
    reason: str
    consequence: str = None
    faq: str = None
    logs: List[str] = None


class Printer(PrinterInterface, comm.MachineComPrintCallback):
    """
    Default implementation of the :class:`PrinterInterface`. Manages the communication layer object and registers
    itself with it as a callback to react to changes on the communication layer.
    """

    def __init__(self, fileManager, analysisQueue, printerProfileManager):
        from collections import deque

        self._logger = logging.getLogger(__name__)
        self._logger_job = logging.getLogger(f"{__name__}.job")

        self._dict = (
            frozendict
            if settings().getBoolean(["devel", "useFrozenDictForPrinterState"])
            else dict
        )

        self._analysisQueue = analysisQueue
        self._fileManager = fileManager
        self._printerProfileManager = printerProfileManager

        self._temps = DataHistory(
            cutoff=settings().getInt(["temperature", "cutoff"]) * 60
        )
        self._markings = DataHistory(
            cutoff=settings().getInt(["temperature", "cutoff"]) * 60
        )

        self._messages = deque([], 300)
        self._log = deque([], 300)

        self._state = None

        self._currentZ = None

        self._printAfterSelect = False
        self._posAfterSelect = None

        self._firmware_info = None
        self._error_info = None

        # sd handling
        self._sdPrinting = False
        self._sdStreaming = False
        self._streamingFinishedCallback = None
        self._streamingFailedCallback = None

        # job handling & estimation
        self._selectedFileMutex = threading.RLock()
        self._selectedFile = None

        self._estimator_factory = PrintTimeEstimator
        self._estimator = None
        analysis_queue_hooks = plugin_manager().get_hooks(
            "octoprint.printer.estimation.factory"
        )
        for name, hook in analysis_queue_hooks.items():
            try:
                estimator = hook()
                if estimator is not None:
                    self._logger.info(f"Using print time estimator provided by {name}")
                    self._estimator_factory = estimator
            except Exception:
                self._logger.exception(
                    f"Error while processing analysis queues from {name}",
                    extra={"plugin": name},
                )

        # hook card upload
        self.sd_card_upload_hooks = plugin_manager().get_hooks(
            "octoprint.printer.sdcardupload"
        )

        # comm
        self._comm = None

        # callbacks
        self._callbacks = []

        # progress plugins
        self._lastProgressReport = None
        self._progressPlugins = plugin_manager().get_implementations(ProgressPlugin)

        self._additional_data_hooks = plugin_manager().get_hooks(
            "octoprint.printer.additional_state_data"
        )
        self._blacklisted_data_hooks = []

        self._stateMonitor = StateMonitor(
            interval=0.5,
            on_update=self._sendCurrentDataCallbacks,
            on_add_temperature=self._sendAddTemperatureCallbacks,
            on_add_log=self._sendAddLogCallbacks,
            on_add_message=self._sendAddMessageCallbacks,
            on_get_progress=self._updateProgressDataCallback,
            on_get_resends=self._updateResendDataCallback,
        )
        self._stateMonitor.reset(
            state=self._dict(
                text=self.get_state_string(),
                flags=self._getStateFlags(),
                error=self.get_error(),
            ),
            job_data=self._dict(
                file=self._dict(name=None, path=None, size=None, origin=None, date=None),
                estimatedPrintTime=None,
                lastPrintTime=None,
                filament=self._dict(length=None, volume=None),
                user=None,
            ),
            progress=self._dict(
                completion=None,
                filepos=None,
                printTime=None,
                printTimeLeft=None,
                printTimeLeftOrigin=None,
            ),
            current_z=None,
            offsets=self._dict(),
            resends=self._dict(count=0, ratio=0),
        )

        eventManager().subscribe(
            Events.METADATA_ANALYSIS_FINISHED, self._on_event_MetadataAnalysisFinished
        )
        eventManager().subscribe(
            Events.METADATA_STATISTICS_UPDATED, self._on_event_MetadataStatisticsUpdated
        )
        eventManager().subscribe(Events.CONNECTED, self._on_event_Connected)
        eventManager().subscribe(Events.DISCONNECTED, self._on_event_Disconnected)
        eventManager().subscribe(Events.CHART_MARKED, self._on_event_ChartMarked)

        self._handle_connect_hooks = plugin_manager().get_hooks(
            "octoprint.printer.handle_connect"
        )

    def _create_estimator(self, job_type=None):
        if job_type is None:
            with self._selectedFileMutex:
                if self._selectedFile is None:
                    return

                if self._selectedFile["sd"]:
                    job_type = "sdcard"
                else:
                    job_type = "local"

        self._estimator = self._estimator_factory(job_type)

    @property
    def firmware_info(self):
        return frozendict(self._firmware_info) if self._firmware_info else None

    @property
    def error_info(self):
        return self._error_info.dict() if self._error_info else None

    # ~~ handling of PrinterCallbacks

    def register_callback(self, callback, *args, **kwargs):
        if not isinstance(callback, PrinterCallback):
            self._logger.warning(
                "Registering an object as printer callback which doesn't implement the PrinterCallback interface"
            )
        self._callbacks.append(callback)

    def unregister_callback(self, callback, *args, **kwargs):
        try:
            self._callbacks.remove(callback)
        except ValueError:
            # not registered
            pass

    def send_initial_callback(self, callback):
        if callback in self._callbacks:
            self._sendInitialStateUpdate(callback)

    def _sendAddTemperatureCallbacks(self, data):
        for callback in self._callbacks:
            try:
                callback.on_printer_add_temperature(data)
            except Exception:
                self._logger.exception(
                    "Exception while adding temperature data point to callback {}".format(
                        callback
                    ),
                    extra={"callback": fqcn(callback)},
                )

    def _sendAddLogCallbacks(self, data):
        for callback in self._callbacks:
            try:
                callback.on_printer_add_log(data)
            except Exception:
                self._logger.exception(
                    "Exception while adding communication log entry to callback {}".format(
                        callback
                    ),
                    extra={"callback": fqcn(callback)},
                )

    def _sendAddMessageCallbacks(self, data):
        for callback in self._callbacks:
            try:
                callback.on_printer_add_message(data)
            except Exception:
                self._logger.exception(
                    "Exception while adding printer message to callback {}".format(
                        callback
                    ),
                    extra={"callback": fqcn(callback)},
                )

    def _sendCurrentDataCallbacks(self, data):
        plugin_data = self._get_additional_plugin_data(initial=False)
        for callback in self._callbacks:
            try:
                data_copy = copy.deepcopy(data)
                if plugin_data:
                    data_copy.update(plugins=copy.deepcopy(plugin_data))
                callback.on_printer_send_current_data(data_copy)
            except Exception:
                self._logger.exception(
                    "Exception while pushing current data to callback {}".format(
                        callback
                    ),
                    extra={"callback": fqcn(callback)},
                )

    def _get_additional_plugin_data(self, initial=False):
        plugin_data = {}

        for name, hook in self._additional_data_hooks.items():
            if name in self._blacklisted_data_hooks:
                continue
            try:
                additional = hook(initial=initial)
                if additional and isinstance(additional, dict):
                    octoprint.util.json.dumps({name: additional})
                    plugin_data[name] = additional
            except ValueError:
                self._logger.exception(
                    f"Invalid additional data from plugin {name}",
                    extra={"plugin": name},
                )
            except Exception:
                self._logger.exception(
                    "Error while retrieving additional data from plugin {}, blacklisting it for further loops".format(
                        name
                    ),
                    extra={"plugin": name},
                )
                self._blacklisted_data_hooks.append(name)

        return plugin_data

    # ~~ callback from metadata analysis event

    def _on_event_MetadataAnalysisFinished(self, event, data):
        with self._selectedFileMutex:
            if self._selectedFile:
                self._setJobData(
                    self._selectedFile["filename"],
                    self._selectedFile["filesize"],
                    self._selectedFile["sd"],
                    self._selectedFile["user"],
                )

    def _on_event_MetadataStatisticsUpdated(self, event, data):
        with self._selectedFileMutex:
            if self._selectedFile:
                self._setJobData(
                    self._selectedFile["filename"],
                    self._selectedFile["filesize"],
                    self._selectedFile["sd"],
                    self._selectedFile["user"],
                )

    # ~~ connection events

    def _on_event_Connected(self, event, data):
        self._markings.append(
            {"type": "connected", "label": "Connected", "time": time.time()}
        )

    def _on_event_Disconnected(self, event, data):
        self._markings.append(
            {"type": "disconnected", "label": "Disconnected", "time": time.time()}
        )

    # ~~ chart marking insertions

    def _on_event_ChartMarked(self, event, data):
        self._markings.append(
            {
                "type": data.get("type", "unknown"),
                "label": data.get("label"),
                "time": data.get("time", time.time()),
            }
        )

    # ~~ progress plugin reporting

    def _reportPrintProgressToPlugins(self, progress):
        with self._selectedFileMutex:
            if (
                progress is None
                or not self._selectedFile
                or "sd" not in self._selectedFile
                or "filename" not in self._selectedFile
            ):
                return

            storage = "sdcard" if self._selectedFile["sd"] else "local"
            filename = self._selectedFile["filename"]

        def call_plugins(storage, filename, progress):
            for plugin in self._progressPlugins:
                try:
                    plugin.on_print_progress(storage, filename, progress)
                except Exception:
                    self._logger.exception(
                        "Exception while sending print progress to plugin %s"
                        % plugin._identifier,
                        extra={"plugin": plugin._identifier},
                    )

        thread = threading.Thread(target=call_plugins, args=(storage, filename, progress))
        thread.daemon = False
        thread.start()

    # ~~ PrinterInterface implementation

    def connect(self, port=None, baudrate=None, profile=None, *args, **kwargs):
        """
        Connects to the printer. If port and/or baudrate is provided, uses these settings, otherwise autodetection
        will be attempted.
        """
        if self._comm is not None:
            return

        for name, hook in self._handle_connect_hooks.items():
            try:
                if hook(
                    self, *args, port=port, baudrate=baudrate, profile=profile, **kwargs
                ):
                    self._logger.info(f"Connect signalled as handled by plugin {name}")
                    return
            except Exception:
                self._logger.exception(
                    f"Exception while handling connect in plugin {name}",
                    extra={"plugin": name},
                )

        self._error_info = None

        eventManager().fire(Events.CONNECTING)
        self._printerProfileManager.select(profile)

        from octoprint.logging.handlers import SerialLogHandler

        SerialLogHandler.arm_rollover()
        if not logging.getLogger("SERIAL").isEnabledFor(logging.DEBUG):
            # if serial.log is not enabled, log a line to explain that to reduce "serial.log is empty" in tickets...
            logging.getLogger("SERIAL").info(
                "serial.log is currently not enabled, you can enable it via Settings > Serial Connection > Log communication to serial.log"
            )

        self._firmware_info = None
        self._comm = comm.MachineCom(
            port,
            baudrate,
            callbackObject=self,
            printerProfileManager=self._printerProfileManager,
        )
        self._comm.start()

    def disconnect(self, *args, **kwargs):
        """
        Closes the connection to the printer.
        """
        eventManager().fire(Events.DISCONNECTING)
        if self._comm is not None:
            self._comm.close()
        else:
            eventManager().fire(Events.DISCONNECTED)
        self._firmware_info = None

    def get_transport(self, *args, **kwargs):
        if self._comm is None:
            return None

        return self._comm.getTransport()

    getTransport = util.deprecated(
        "getTransport has been renamed to get_transport",
        since="1.2.0-dev-590",
        includedoc="Replaced by :func:`get_transport`",
    )

    def job_on_hold(self, blocking=True, *args, **kwargs):
        if self._comm is None:
            raise RuntimeError("No connection to the printer")
        return self._comm.job_put_on_hold(blocking=blocking)

    def set_job_on_hold(self, value, blocking=True, *args, **kwargs):
        if self._comm is None:
            raise RuntimeError("No connection to the printer")
        return self._comm.set_job_on_hold(value, blocking=blocking)

    def fake_ack(self, *args, **kwargs):
        if self._comm is None:
            return

        self._comm.fakeOk()

    def commands(self, commands, tags=None, force=False, *args, **kwargs):
        """
        Sends one or more gcode commands to the printer.
        """
        if self._comm is None:
            return

        if not isinstance(commands, (list, tuple)):
            commands = [commands]

        if tags is None:
            tags = set()
        tags |= {"trigger:printer.commands"}

        for command in commands:
            self._comm.sendCommand(command, tags=tags, force=force)

    def script(
        self, name, context=None, must_be_set=True, part_of_job=False, *args, **kwargs
    ):
        if self._comm is None:
            return

        if name is None or not name:
            raise ValueError("name must be set")

        # .capitalize() will lowercase all letters but the first
        # this code preserves existing CamelCase
        event_name = name[0].upper() + name[1:]

        event_start = f"GcodeScript{event_name}Running"
        payload = context.get("event", None) if isinstance(context, dict) else None

        eventManager().fire(event_start, payload)

        result = self._comm.sendGcodeScript(
            name,
            part_of_job=part_of_job,
            replacements=context,
            tags=kwargs.get("tags", set()) | {"trigger:printer.script"},
        )
        if not result and must_be_set:
            raise UnknownScript(name)

        event_end = f"GcodeScript{event_name}Finished"
        eventManager().fire(event_end, payload)

    def jog(self, axes, relative=True, speed=None, *args, **kwargs):
        if isinstance(axes, str):
            # legacy parameter format, there should be an amount as first anonymous positional arguments too
            axis = axes

            if not len(args) >= 1:
                raise ValueError("amount not set")
            amount = args[0]
            if not isinstance(amount, (int, float)):
                raise ValueError(f"amount must be a valid number: {amount}")

            axes = {}
            axes[axis] = amount

        if not axes:
            raise ValueError("At least one axis to jog must be provided")

        for axis in axes:
            if axis not in PrinterInterface.valid_axes:
                raise ValueError(
                    "Invalid axis {}, valid axes are {}".format(
                        axis, ", ".join(PrinterInterface.valid_axes)
                    )
                )

        command = "G0 {}".format(
            " ".join([f"{axis.upper()}{amt}" for axis, amt in axes.items()])
        )

        if speed is None:
            printer_profile = self._printerProfileManager.get_current_or_default()
            speed = min(printer_profile["axes"][axis]["speed"] for axis in axes)

        if speed and not isinstance(speed, bool):
            command += f" F{speed}"

        if relative:
            commands = ["G91", command, "G90"]
        else:
            commands = ["G90", command]

        self.commands(commands, tags=kwargs.get("tags", set()) | {"trigger:printer.jog"})

    def home(self, axes, *args, **kwargs):
        if not isinstance(axes, (list, tuple)):
            if isinstance(axes, str):
                axes = [axes]
            else:
                raise ValueError(f"axes is neither a list nor a string: {axes}")

        validated_axes = list(
            filter(
                lambda x: x in PrinterInterface.valid_axes, map(lambda x: x.lower(), axes)
            )
        )
        if len(axes) != len(validated_axes):
            raise ValueError(f"axes contains invalid axes: {axes}")

        self.commands(
            [
                "G91",
                "G28 %s" % " ".join(map(lambda x: "%s0" % x.upper(), validated_axes)),
                "G90",
            ],
            tags=kwargs.get("tags", set) | {"trigger:printer.home"},
        )

    def extrude(self, amount, speed=None, *args, **kwargs):
        if not isinstance(amount, (int, float)):
            raise ValueError(f"amount must be a valid number: {amount}")

        printer_profile = self._printerProfileManager.get_current_or_default()

        # Use specified speed (if any)
        max_e_speed = printer_profile["axes"]["e"]["speed"]

        if speed is None:
            # No speed was specified so default to value configured in printer profile
            extrusion_speed = max_e_speed
        else:
            # Make sure that specified value is not greater than maximum as defined in printer profile
            extrusion_speed = min([speed, max_e_speed])

        self.commands(
            ["G91", "M83", "G1 E%s F%d" % (amount, extrusion_speed), "M82", "G90"],
            tags=kwargs.get("tags", set()) | {"trigger:printer.extrude"},
        )

    def change_tool(self, tool, *args, **kwargs):
        if not PrinterInterface.valid_tool_regex.match(tool):
            raise ValueError(f'tool must match "tool[0-9]+": {tool}')

        tool_num = int(tool[len("tool") :])
        self.commands(
            "T%d" % tool_num,
            tags=kwargs.get("tags", set()) | {"trigger:printer.change_tool"},
        )

    def set_temperature(self, heater, value, *args, **kwargs):
        if not PrinterInterface.valid_heater_regex.match(heater):
            raise ValueError(
                'heater must match "tool[0-9]+", "bed" or "chamber": {heater}'.format(
                    heater=heater
                )
            )

        if not isinstance(value, (int, float)) or value < 0:
            raise ValueError(f"value must be a valid number >= 0: {value}")

        tags = kwargs.get("tags", set()) | {"trigger:printer.set_temperature"}

        if heater.startswith("tool"):
            printer_profile = self._printerProfileManager.get_current_or_default()
            extruder_count = printer_profile["extruder"]["count"]
            shared_nozzle = printer_profile["extruder"]["sharedNozzle"]
            if extruder_count > 1 and not shared_nozzle:
                toolNum = int(heater[len("tool") :])
                self.commands(f"M104 T{toolNum} S{value}", tags=tags)
            else:
                self.commands(f"M104 S{value}", tags=tags)

        elif heater == "bed":
            self.commands(f"M140 S{value}", tags=tags)

        elif heater == "chamber":
            self.commands(f"M141 S{value}", tags=tags)

    def set_temperature_offset(self, offsets=None, *args, **kwargs):
        if offsets is None:
            offsets = {}

        if not isinstance(offsets, dict):
            raise ValueError("offsets must be a dict")

        validated_keys = list(
            filter(lambda x: PrinterInterface.valid_heater_regex.match(x), offsets.keys())
        )
        validated_values = list(
            filter(lambda x: isinstance(x, (int, float)), offsets.values())
        )

        if len(validated_keys) != len(offsets):
            raise ValueError(f"offsets contains invalid keys: {offsets}")
        if len(validated_values) != len(offsets):
            raise ValueError(f"offsets contains invalid values: {offsets}")

        if self._comm is None:
            return

        self._comm.setTemperatureOffset(offsets)
        self._setOffsets(self._comm.getOffsets())

    def _convert_rate_value(self, factor, min_val=None, max_val=None):
        if not isinstance(factor, (int, float)):
            raise ValueError("factor is not a number")

        if isinstance(factor, float):
            factor = int(factor * 100)

        if min_val and factor < min_val:
            raise ValueError(f"factor must be a value >={min_val}")
        elif max_val and factor > max_val:
            raise ValueError(f"factor must be a value <={max_val}")

        return factor

    def feed_rate(self, factor, *args, **kwargs):
        factor = self._convert_rate_value(factor, min_val=1)
        self.commands(
            "M220 S%d" % factor,
            tags=kwargs.get("tags", set()) | {"trigger:printer.feed_rate"},
        )

    def flow_rate(self, factor, *args, **kwargs):
        factor = self._convert_rate_value(factor, min_val=1)
        self.commands(
            "M221 S%d" % factor,
            tags=kwargs.get("tags", set()) | {"trigger:printer.flow_rate"},
        )

    def select_file(
        self, path, sd, printAfterSelect=False, user=None, pos=None, *args, **kwargs
    ):
        if self._comm is None or (self._comm.isBusy() or self._comm.isStreaming()):
            self._logger.info("Cannot load file: printer not connected or currently busy")
            return

        self._validateJob(path, sd)

        origin = FileDestinations.SDCARD if sd else FileDestinations.LOCAL
        if sd:
            path_on_disk = "/" + path
            path_in_storage = path
        else:
            path_on_disk = self._fileManager.path_on_disk(origin, path)
            path_in_storage = self._fileManager.path_in_storage(origin, path_on_disk)

        try:
            recovery_data = self._fileManager.get_recovery_data()
            if recovery_data:
                # clean up recovery data if we just selected a different file
                actual_origin = recovery_data.get("origin", None)
                actual_path = recovery_data.get("path", None)

                if (
                    actual_origin is None
                    or actual_path is None
                    or actual_origin != origin
                    or actual_path != path_in_storage
                ):
                    self._fileManager.delete_recovery_data()
        except Exception:
            # anything goes wrong with the recovery data, we ignore it
            self._logger.exception(
                "Something was wrong with processing the recovery data"
            )

        self._printAfterSelect = printAfterSelect
        self._posAfterSelect = pos
        self._comm.selectFile(
            "/" + path if sd else path_on_disk,
            sd,
            user=user,
            tags=kwargs.get("tags", set()) | {"trigger:printer.select_file"},
        )
        self._updateProgressData()
        self._setCurrentZ(None)

    def unselect_file(self, *args, **kwargs):
        if self._comm is not None and (self._comm.isBusy() or self._comm.isStreaming()):
            return

        self._comm.unselectFile()
        self._updateProgressData()
        self._setCurrentZ(None)

    def get_file_position(self):
        if self._comm is None:
            return None

        with self._selectedFileMutex:
            if self._selectedFile is None:
                return None

        return self._comm.getFilePosition()

    def get_markings(self):
        return self._markings

    def start_print(self, pos=None, user=None, *args, **kwargs):
        """
        Starts the currently loaded print job.
        Only starts if the printer is connected and operational, not currently printing and a printjob is loaded
        """
        if (
            self._comm is None
            or not self._comm.isOperational()
            or self._comm.isPrinting()
        ):
            return

        with self._selectedFileMutex:
            if self._selectedFile is None:
                return

        self._fileManager.delete_recovery_data()

        self._lastProgressReport = None
        self._updateProgressData()
        self._setCurrentZ(None)
        self._comm.startPrint(
            pos=pos,
            user=user,
            tags=kwargs.get("tags", set()) | {"trigger:printer.start_print"},
        )

    def pause_print(self, user=None, *args, **kwargs):
        """
        Pause the current printjob.
        """
        if self._comm is None:
            return

        if self._comm.isPaused():
            return

        self._comm.setPause(
            True,
            user=user,
            tags=kwargs.get("tags", set()) | {"trigger:printer.pause_print"},
        )

    def resume_print(self, user=None, *args, **kwargs):
        """
        Resume the current printjob.
        """
        if self._comm is None:
            return

        if not self._comm.isPaused():
            return

        self._comm.setPause(
            False,
            user=user,
            tags=kwargs.get("tags", set()) | {"trigger:printer.resume_print"},
        )

    def cancel_print(self, user=None, *args, **kwargs):
        """
        Cancel the current printjob.
        """
        if self._comm is None:
            return

        # tell comm layer to cancel - will also trigger our cancelled handler
        # for further processing
        self._comm.cancelPrint(
            user=user, tags=kwargs.get("tags", set()) | {"trigger:printer.cancel_print"}
        )

    def log_lines(self, *lines):
        serial_logger = logging.getLogger("SERIAL")
        self.on_comm_log("\n".join(lines))
        for line in lines:
            serial_logger.debug(line)

    def get_state_string(self, state=None, *args, **kwargs):
        if self._comm is None:
            return "Offline"
        else:
            return self._comm.getStateString(state=state)

    def get_state_id(self, state=None, *args, **kwargs):
        if self._comm is None:
            return "OFFLINE"
        else:
            return self._comm.getStateId(state=state)

    def get_error(self):
        if self._comm is None:
            return ""
        else:
            return self._comm.getErrorString()

    def get_current_data(self, *args, **kwargs):
        return util.thaw_frozendict(self._stateMonitor.get_current_data())

    def get_current_job(self, *args, **kwargs):
        currentData = self._stateMonitor.get_current_data()
        return util.thaw_frozendict(currentData["job"])

    def get_current_temperatures(self, *args, **kwargs):
        if self._comm is not None:
            offsets = self._comm.getOffsets()
        else:
            offsets = {}

        last = self._temps.last
        if last is None:
            return {}

        return {
            key: {
                "actual": value["actual"],
                "target": value["target"],
                "offset": offsets[key] if offsets.get(key) is not None else 0,
            }
            for key, value in last.items()
            if key != "time"
        }

    def get_temperature_history(self, *args, **kwargs):
        return list(self._temps)

    def get_current_connection(self, *args, **kwargs):
        if self._comm is None:
            return "Closed", None, None, None

        port, baudrate = self._comm.getConnection()
        printer_profile = self._printerProfileManager.get_current_or_default()
        return self._comm.getStateString(), port, baudrate, printer_profile

    def is_closed_or_error(self, *args, **kwargs):
        return self._comm is None or self._comm.isClosedOrError()

    def is_operational(self, *args, **kwargs):
        return self._comm is not None and self._comm.isOperational()

    def is_printing(self, *args, **kwargs):
        return self._comm is not None and self._comm.isPrinting()

    def is_cancelling(self, *args, **kwargs):
        return self._comm is not None and self._comm.isCancelling()

    def is_pausing(self, *args, **kwargs):
        return self._comm is not None and self._comm.isPausing()

    def is_paused(self, *args, **kwargs):
        return self._comm is not None and self._comm.isPaused()

    def is_resuming(self, *args, **kwargs):
        return self._comm is not None and self._comm.isResuming()

    def is_finishing(self, *args, **kwargs):
        return self._comm is not None and self._comm.isFinishing()

    def is_error(self, *args, **kwargs):
        return self._comm is not None and self._comm.isError()

    def is_ready(self, *args, **kwargs):
        return (
            self.is_operational()
            and not self._comm.isBusy()
            # isBusy is true when paused
            and not self._comm.isStreaming()
        )

    def is_sd_ready(self, *args, **kwargs):
        if not settings().getBoolean(["feature", "sdSupport"]) or self._comm is None:
            return False
        else:
            return self._comm.isSdReady()

    # ~~ sd file handling

    def get_sd_files(self, *args, **kwargs):
        if not self.is_sd_ready():
            return []

        if kwargs.get("refresh"):
            self.refresh_sd_files(blocking=True)

        return list(
            map(
                lambda x: {"name": x[0][1:], "size": x[1], "display": x[2], "date": x[3]},
                self._comm.getSdFiles(),
            )
        )

    def add_sd_file(
        self, filename, path, on_success=None, on_failure=None, *args, **kwargs
    ):
        if not self._comm or self._comm.isBusy() or not self._comm.isSdReady():
            self._logger.error("No connection to printer or printer is busy")
            return

        self._streamingFinishedCallback = on_success
        self._streamingFailedCallback = on_failure

        def sd_upload_started(local_filename, remote_filename):
            eventManager().fire(
                Events.TRANSFER_STARTED,
                {"local": local_filename, "remote": remote_filename},
            )

        def sd_upload_succeeded(local_filename, remote_filename, elapsed):
            payload = {
                "local": local_filename,
                "remote": remote_filename,
                "time": elapsed,
            }
            eventManager().fire(Events.TRANSFER_DONE, payload)
            if callable(self._streamingFinishedCallback):
                self._streamingFinishedCallback(
                    remote_filename, remote_filename, FileDestinations.SDCARD
                )

        def sd_upload_failed(local_filename, remote_filename, elapsed):
            payload = {
                "local": local_filename,
                "remote": remote_filename,
                "time": elapsed,
            }
            eventManager().fire(Events.TRANSFER_FAILED, payload)
            if callable(self._streamingFailedCallback):
                self._streamingFailedCallback(
                    remote_filename, remote_filename, FileDestinations.SDCARD
                )

        for name, hook in self.sd_card_upload_hooks.items():
            # first sd card upload plugin that feels responsible gets the job
            try:
                result = hook(
                    self,
                    filename,
                    path,
                    sd_upload_started,
                    sd_upload_succeeded,
                    sd_upload_failed,
                    *args,
                    **kwargs,
                )
                if result is not None:
                    return result
            except Exception:
                self._logger.exception(
                    "There was an error running the sd upload "
                    "hook provided by plugin {}".format(name),
                    extra={"plugin": name},
                )

        else:
            # no plugin feels responsible, use the default implementation
            return self._add_sd_file(filename, path, tags=kwargs.get("tags"))

    def _get_free_remote_name(self, filename):
        self.refresh_sd_files(blocking=True)
        existingSdFiles = list(map(lambda x: x[0], self._comm.getSdFiles()))

        if valid_file_type(filename, "gcode"):
            # figure out remote filename
            remote_name = util.get_dos_filename(
                filename,
                existing_filenames=existingSdFiles,
                extension="gco",
                whitelisted_extensions=["gco", "g"],
            )
        else:
            # probably something else added through a plugin, use it's basename as-is
            remote_name = os.path.basename(filename)

        return remote_name

    def _add_sd_file(self, filename, path, tags=None):
        if tags is None:
            tags = set()

        self._create_estimator("stream")
        remote_name = self._comm.startFileTransfer(
            path,
            filename,
            special=not valid_file_type(filename, "gcode"),
            tags=tags | {"trigger:printer.add_sd_file"},
        )

        return remote_name

    def delete_sd_file(self, filename, *args, **kwargs):
        if not self._comm or not self._comm.isSdReady():
            return
        self._comm.deleteSdFile(
            "/" + filename,
            tags=kwargs.get("tags", set()) | {"trigger:printer.delete_sd_file"},
        )

    def init_sd_card(self, *args, **kwargs):
        if not self._comm or self._comm.isSdReady():
            return
        self._comm.initSdCard(
            tags=kwargs.get("tags", set()) | {"trigger:printer.init_sd_card"}
        )

    def release_sd_card(self, *args, **kwargs):
        if not self._comm or not self._comm.isSdReady():
            return
        self._comm.releaseSdCard(
            tags=kwargs.get("tags", set()) | {"trigger:printer.release_sd_card"}
        )

    def refresh_sd_files(self, blocking=False, *args, **kwargs):
        """
        Refreshes the list of file stored on the SD card attached to printer (if available and printer communication
        available). Optional blocking parameter allows making the method block (max 10s) until the file list has been
        received (and can be accessed via self._comm.getSdFiles()). Defaults to an asynchronous operation.
        """
        if not self._comm or not self._comm.isSdReady():
            return
        self._comm.refreshSdFiles(
            tags=kwargs.get("tags", set()) | {"trigger:printer.refresh_sd_files"},
            blocking=blocking,
            timeout=kwargs.get("timeout", 10),
        )

    # ~~ state monitoring

    def _setOffsets(self, offsets):
        self._stateMonitor.set_temp_offsets(offsets)

    def _setCurrentZ(self, currentZ):
        self._currentZ = currentZ
        self._stateMonitor.set_current_z(self._currentZ)

    def _setState(self, state, state_string=None, error_string=None):
        if state_string is None:
            state_string = self.get_state_string()
        if error_string is None:
            error_string = self.get_error()

        self._state = state
        self._stateMonitor.set_state(
            self._dict(text=state_string, flags=self._getStateFlags(), error=error_string)
        )

        payload = {
            "state_id": self.get_state_id(self._state),
            "state_string": self.get_state_string(self._state),
        }
        eventManager().fire(Events.PRINTER_STATE_CHANGED, payload)

    def _addLog(self, log):
        self._log.append(log)
        self._stateMonitor.add_log(log)

    def _addMessage(self, message):
        self._messages.append(message)
        self._stateMonitor.add_message(message)

    def _updateProgressData(
        self,
        completion=None,
        filepos=None,
        printTime=None,
        printTimeLeft=None,
        printTimeLeftOrigin=None,
    ):
        self._stateMonitor.set_progress(
            self._dict(
                completion=int(completion * 100) if completion is not None else None,
                filepos=filepos,
                printTime=int(printTime) if printTime is not None else None,
                printTimeLeft=int(printTimeLeft) if printTimeLeft is not None else None,
                printTimeLeftOrigin=printTimeLeftOrigin,
            )
        )

    def _updateProgressDataCallback(self):
        if self._comm is None:
            progress = None
            filepos = None
            printTime = None
            cleanedPrintTime = None
        else:
            progress = self._comm.getPrintProgress()
            filepos = self._comm.getPrintFilepos()
            printTime = self._comm.getPrintTime()
            cleanedPrintTime = self._comm.getCleanedPrintTime()

        printTimeLeft = printTimeLeftOrigin = None
        estimator = self._estimator
        if progress is not None:
            progress_int = int(progress * 100)
            if self._lastProgressReport != progress_int:
                self._lastProgressReport = progress_int
                self._reportPrintProgressToPlugins(progress_int)

            if progress == 0:
                printTimeLeft = None
                printTimeLeftOrigin = None
            elif progress == 1:
                printTimeLeft = 0
                printTimeLeftOrigin = None
            elif estimator is not None:
                statisticalTotalPrintTime = None
                statisticalTotalPrintTimeType = None
                with self._selectedFileMutex:
                    if (
                        self._selectedFile
                        and "estimatedPrintTime" in self._selectedFile
                        and self._selectedFile["estimatedPrintTime"]
                    ):
                        statisticalTotalPrintTime = self._selectedFile[
                            "estimatedPrintTime"
                        ]
                        statisticalTotalPrintTimeType = self._selectedFile.get(
                            "estimatedPrintTimeType", None
                        )

                try:
                    printTimeLeft, printTimeLeftOrigin = estimator.estimate(
                        progress,
                        printTime,
                        cleanedPrintTime,
                        statisticalTotalPrintTime,
                        statisticalTotalPrintTimeType,
                    )
                    if printTimeLeft is not None:
                        printTimeLeft = int(printTimeLeft)
                except Exception:
                    self._logger.exception(
                        f"Error while estimating print time via {estimator}"
                    )

        return self._dict(
            completion=progress * 100 if progress is not None else None,
            filepos=filepos,
            printTime=int(printTime) if printTime is not None else None,
            printTimeLeft=int(printTimeLeft) if printTimeLeft is not None else None,
            printTimeLeftOrigin=printTimeLeftOrigin,
        )

    def _updateResendDataCallback(self):
        if not self._comm:
            return self._dict(count=0, transmitted=0, ratio=0)
        return self._dict(
            count=self._comm.received_resends,
            transmitted=self._comm.transmitted_lines,
            ratio=int(self._comm.resend_ratio * 100),
        )

    def _addTemperatureData(self, tools=None, bed=None, chamber=None, custom=None):
        if tools is None:
            tools = {}
        if custom is None:
            custom = {}

        data = {"time": int(time.time())}
        for tool in tools.keys():
            data["tool%d" % tool] = self._dict(
                actual=tools[tool][0], target=tools[tool][1]
            )
        if bed is not None and isinstance(bed, tuple):
            data["bed"] = self._dict(actual=bed[0], target=bed[1])
        if chamber is not None and isinstance(chamber, tuple):
            data["chamber"] = self._dict(actual=chamber[0], target=chamber[1])
        for identifier, values in custom.items():
            data[identifier] = self._dict(actual=values[0], target=values[1])

        self._temps.append(data)

        self._stateMonitor.add_temperature(self._dict(**data))

    def _validateJob(self, filename, sd):
        if not valid_file_type(filename, type="machinecode"):
            raise InvalidFileType(f"{filename} is not a machinecode file, cannot print")

        if sd:
            return

        path_on_disk = self._fileManager.path_on_disk(FileDestinations.LOCAL, filename)
        if os.path.isabs(filename) and not filename == path_on_disk:
            raise InvalidFileLocation(
                "{} is not located within local storage, cannot select for printing".format(
                    filename
                )
            )
        if not os.path.isfile(path_on_disk):
            raise InvalidFileLocation(
                "{} does not exist in local storage, cannot select for printing".format(
                    filename
                )
            )

    def _setJobData(self, filename, filesize, sd, user=None, data=None):
        with self._selectedFileMutex:
            if filename is not None:
                if sd:
                    name_in_storage = filename
                    if name_in_storage.startswith("/"):
                        name_in_storage = name_in_storage[1:]
                    path_in_storage = name_in_storage
                    path_on_disk = None
                else:
                    path_in_storage = self._fileManager.path_in_storage(
                        FileDestinations.LOCAL, filename
                    )
                    path_on_disk = self._fileManager.path_on_disk(
                        FileDestinations.LOCAL, filename
                    )
                    _, name_in_storage = self._fileManager.split_path(
                        FileDestinations.LOCAL, path_in_storage
                    )
                self._selectedFile = {
                    "filename": path_in_storage,
                    "filesize": filesize,
                    "sd": sd,
                    "estimatedPrintTime": None,
                    "user": user,
                }
            else:
                self._selectedFile = None
                self._stateMonitor.set_job_data(
                    self._dict(
                        file=self._dict(
                            name=None,
                            path=None,
                            display=None,
                            origin=None,
                            size=None,
                            date=None,
                        ),
                        estimatedPrintTime=None,
                        averagePrintTime=None,
                        lastPrintTime=None,
                        filament=None,
                        user=None,
                    )
                )
                return

            estimatedPrintTime = None
            lastPrintTime = None
            averagePrintTime = None
            date = None
            filament = None
            display_name = name_in_storage

            if path_on_disk:
                # Use an int for mtime because it could be float and the
                # javascript needs to exact match
                date = int(os.stat(path_on_disk).st_mtime)

                try:
                    fileData = self._fileManager.get_metadata(
                        FileDestinations.SDCARD if sd else FileDestinations.LOCAL,
                        path_on_disk,
                    )
                except Exception:
                    self._logger.exception("Error generating fileData")
                    fileData = None
                if fileData is not None:
                    if fileData.get("display"):
                        display_name = fileData["display"]
                    if isinstance(fileData.get("analysis"), dict):
                        if estimatedPrintTime is None and fileData["analysis"].get(
                            "estimatedPrintTime"
                        ):
                            estimatedPrintTime = fileData["analysis"][
                                "estimatedPrintTime"
                            ]
                        if fileData["analysis"].get("filament"):
                            filament = fileData["analysis"]["filament"]
                    if isinstance(fileData.get("statistics"), dict):
                        printer_profile = (
                            self._printerProfileManager.get_current_or_default()["id"]
                        )
                        if printer_profile in fileData["statistics"].get(
                            "averagePrintTime", {}
                        ):
                            averagePrintTime = fileData["statistics"]["averagePrintTime"][
                                printer_profile
                            ]
                        if printer_profile in fileData["statistics"].get(
                            "lastPrintTime", {}
                        ):
                            lastPrintTime = fileData["statistics"]["lastPrintTime"][
                                printer_profile
                            ]

                    if averagePrintTime is not None:
                        self._selectedFile["estimatedPrintTime"] = averagePrintTime
                        self._selectedFile["estimatedPrintTimeType"] = "average"
                    elif estimatedPrintTime is not None:
                        # TODO apply factor which first needs to be tracked!
                        self._selectedFile["estimatedPrintTime"] = estimatedPrintTime
                        self._selectedFile["estimatedPrintTimeType"] = "analysis"

            elif data:
                display_name = data.longname
                date = data.timestamp

            self._stateMonitor.set_job_data(
                self._dict(
                    file=self._dict(
                        name=name_in_storage,
                        path=path_in_storage,
                        display=display_name,
                        origin=FileDestinations.SDCARD if sd else FileDestinations.LOCAL,
                        size=filesize,
                        date=date,
                    ),
                    estimatedPrintTime=estimatedPrintTime,
                    averagePrintTime=averagePrintTime,
                    lastPrintTime=lastPrintTime,
                    filament=filament,
                    user=user,
                )
            )

    def _updateJobUser(self, user):
        with self._selectedFileMutex:
            if (
                self._selectedFile is not None
                and self._selectedFile.get("user", None) != user
            ):
                self._selectedFile["user"] = user

                job_data = self.get_current_job()
                self._stateMonitor.set_job_data(
                    self._dict(
                        file=job_data["file"],
                        estimatedPrintTime=job_data["estimatedPrintTime"],
                        averagePrintTime=job_data["averagePrintTime"],
                        lastPrintTime=job_data["lastPrintTime"],
                        filament=job_data["filament"],
                        user=user,
                    )
                )

    def _sendInitialStateUpdate(self, callback):
        try:
            data = self._stateMonitor.get_current_data()
            data.update(
                temps=list(self._temps),
                logs=list(self._log),
                messages=list(self._messages),
                markings=list(self._markings),
            )

            plugin_data = self._get_additional_plugin_data(initial=False)
            if plugin_data:
                data.update(plugins=copy.deepcopy(plugin_data))

            callback.on_printer_send_initial_data(data)
        except Exception:
            self._logger.exception(
                "Error while pushing initial state update to callback {}".format(
                    callback
                ),
                extra={"callback": fqcn(callback)},
            )

    def _getStateFlags(self):
        return self._dict(
            operational=self.is_operational(),
            printing=self.is_printing(),
            cancelling=self.is_cancelling(),
            pausing=self.is_pausing(),
            resuming=self.is_resuming(),
            finishing=self.is_finishing(),
            closedOrError=self.is_closed_or_error(),
            error=self.is_error(),
            paused=self.is_paused(),
            ready=self.is_ready(),
            sdReady=self.is_sd_ready(),
        )

    # ~~ comm.MachineComPrintCallback implementation

    def on_comm_log(self, message):
        """
        Callback method for the comm object, called upon log output.
        """
        self._addLog(to_unicode(message, "utf-8", errors="replace"))

    def on_comm_temperature_update(self, tools, bed, chamber, custom=None):
        if custom is None:
            custom = {}
        self._addTemperatureData(
            tools=copy.deepcopy(tools),
            bed=copy.deepcopy(bed),
            chamber=copy.deepcopy(chamber),
            custom=copy.deepcopy(custom),
        )

    def on_comm_position_update(self, position, reason=None):
        payload = {"reason": reason}
        payload.update(position)
        eventManager().fire(Events.POSITION_UPDATE, payload)

    def on_comm_state_change(self, state):
        """
        Callback method for the comm object, called if the connection state changes.
        """
        oldState = self._state

        state_string = None
        error_string = None
        if self._comm is not None:
            state_string = self._comm.getStateString()
            error_string = self._comm.getErrorString()

        if oldState in (comm.MachineCom.STATE_PRINTING,):
            # if we were still printing and went into an error state, mark the print as failed
            if state in (
                comm.MachineCom.STATE_CLOSED,
                comm.MachineCom.STATE_ERROR,
                comm.MachineCom.STATE_CLOSED_WITH_ERROR,
            ):
                with self._selectedFileMutex:
                    if self._selectedFile is not None:
                        payload = self._payload_for_print_job_event()
                        if payload:
                            payload["time"] = self._comm.getPrintTime()
                            payload["reason"] = "error"
                            payload["error"] = self._comm.getErrorString()
                            payload["progress"] = self._comm.getPrintProgress()

                            def finalize():
                                self._fileManager.log_print(
                                    payload["origin"],
                                    payload["path"],
                                    time.time(),
                                    payload["time"],
                                    False,
                                    self._printerProfileManager.get_current_or_default()[
                                        "id"
                                    ],
                                )
                                eventManager().fire(Events.PRINT_FAILED, payload)

                            thread = threading.Thread(target=finalize)
                            thread.daemon = True
                            thread.start()

            try:
                self._analysisQueue.resume()  # printing done, put those cpu cycles to good use
            except Exception:
                self._logger.exception("Error while resuming the analysis queue")

        elif state == comm.MachineCom.STATE_PRINTING:
            if settings().get(["gcodeAnalysis", "runAt"]) == "idle":
                try:
                    self._analysisQueue.pause()  # only analyse files while idle
                except Exception:
                    self._logger.exception("Error while pausing the analysis queue")

        if (
            state == comm.MachineCom.STATE_CLOSED
            or state == comm.MachineCom.STATE_CLOSED_WITH_ERROR
        ):
            if self._comm is not None:
                self._comm = None

            with self._selectedFileMutex:
                if self._selectedFile is not None:
                    eventManager().fire(Events.FILE_DESELECTED)
                self._setJobData(None, None, None)

            self._updateProgressData()
            self._setCurrentZ(None)
            self._setOffsets(None)
            self._addTemperatureData()
            self._printerProfileManager.deselect()

            eventManager().fire(Events.DISCONNECTED)

        self._setState(state, state_string=state_string, error_string=error_string)

    def on_comm_error(self, error, reason, consequence=None, faq=None, logs=None):
        # store error info
        self._error_info = ErrorInformation(
            error=error, reason=reason, consequence=consequence, faq=faq, logs=logs
        )

    def on_comm_message(self, message):
        """
        Callback method for the comm object, called upon message exchanges via serial.
        Stores the message in the message buffer, truncates buffer to the last 300 lines.
        """
        self._addMessage(to_unicode(message, "utf-8", errors="replace"))

    def on_comm_progress(self):
        """
        Callback method for the comm object, called upon any change in progress of the printjob.
        Triggers storage of new values for printTime, printTimeLeft and the current progress.
        """

        self._stateMonitor.trigger_progress_update()

    def on_comm_z_change(self, newZ):
        """
        Callback method for the comm object, called upon change of the z-layer.
        """
        oldZ = self._currentZ
        if newZ != oldZ:
            # we have to react to all z-changes, even those that might "go backward" due to a slicer's retraction or
            # anti-backlash-routines. Event subscribes should individually take care to filter out "wrong" z-changes
            eventManager().fire(Events.Z_CHANGE, {"new": newZ, "old": oldZ})

        self._setCurrentZ(newZ)

    def on_comm_sd_state_change(self, sdReady):
        self._stateMonitor.set_state(
            self._dict(
                text=self.get_state_string(),
                flags=self._getStateFlags(),
                error=self.get_error(),
            )
        )

    def on_comm_sd_files(self, files):
        eventManager().fire(Events.UPDATED_FILES, {"type": "printables"})

    def on_comm_file_selected(self, full_path, size, sd, user=None, data=None):
        if full_path is not None:
            payload = self._payload_for_print_job_event(
                location=FileDestinations.SDCARD if sd else FileDestinations.LOCAL,
                print_job_file=full_path,
                print_job_user=user,
                action_user=user,
            )
            eventManager().fire(Events.FILE_SELECTED, payload)
            self._logger_job.info(
                "Print job selected - origin: {}, path: {}, owner: {}, user: {}".format(
                    payload.get("origin"),
                    payload.get("path"),
                    payload.get("owner"),
                    payload.get("user"),
                )
            )
        else:
            eventManager().fire(Events.FILE_DESELECTED)
            self._logger_job.info(
                "Print job deselected - user: {}".format(user if user else "n/a")
            )

        self._setJobData(full_path, size, sd, user=user, data=data)
        self._stateMonitor.set_state(
            self._dict(
                text=self.get_state_string(),
                flags=self._getStateFlags(),
                error=self.get_error(),
            )
        )

        self._create_estimator()

        if self._printAfterSelect:
            self._printAfterSelect = False
            self.start_print(pos=self._posAfterSelect, user=user)

    def on_comm_print_job_started(self, suppress_script=False, user=None):
        # clear error info
        self._error_info = None

        self._updateJobUser(
            user
        )  # the final job owner should always be whoever _started_ the job
        self._stateMonitor.trigger_progress_update()
        payload = self._payload_for_print_job_event(print_job_user=user, action_user=user)
        if payload:
            eventManager().fire(Events.PRINT_STARTED, payload)
            eventManager().fire(
                Events.CHART_MARKED,
                {"type": "print", "label": "Start"},
            )
            self._logger_job.info(
                "Print job started - origin: {}, path: {}, owner: {}, user: {}".format(
                    payload.get("origin"),
                    payload.get("path"),
                    payload.get("owner"),
                    payload.get("user"),
                )
            )

            if not suppress_script:
                self.script(
                    "beforePrintStarted",
                    context={"event": payload},
                    part_of_job=True,
                    must_be_set=False,
                )

    def on_comm_print_job_done(self, suppress_script=False):
        self._fileManager.delete_recovery_data()

        payload = self._payload_for_print_job_event()
        if payload:
            payload["time"] = self._comm.getPrintTime()
            eventManager().fire(
                Events.CHART_MARKED,
                {"type": "done", "label": "Done"},
            )
            self._updateProgressData(
                completion=1.0,
                filepos=payload["size"],
                printTime=payload["time"],
                printTimeLeft=0,
            )
            self._stateMonitor.set_state(
                self._dict(
                    text=self.get_state_string(),
                    flags=self._getStateFlags(),
                    error=self.get_error(),
                )
            )

            eventManager().fire(Events.PRINT_DONE, payload)
            self._logger_job.info(
                "Print job done - origin: {}, path: {}, owner: {}".format(
                    payload.get("origin"),
                    payload.get("path"),
                    payload.get("owner"),
                )
            )

            if not suppress_script:
                self.script(
                    "afterPrintDone",
                    context={"event": payload},
                    part_of_job=True,
                    must_be_set=False,
                )

            def log_print():
                self._fileManager.log_print(
                    payload["origin"],
                    payload["path"],
                    time.time(),
                    payload["time"],
                    True,
                    self._printerProfileManager.get_current_or_default()["id"],
                )

            thread = threading.Thread(target=log_print)
            thread.daemon = True
            thread.start()

        else:
            self._updateProgressData()
            self._stateMonitor.set_state(
                self._dict(
                    text=self.get_state_string(),
                    flags=self._getStateFlags(),
                    error=self.get_error(),
                )
            )

    def on_comm_print_job_cancelling(self, firmware_error=None, user=None):
        payload = self._payload_for_print_job_event(action_user=user)
        if payload:
            if firmware_error:
                payload["firmwareError"] = firmware_error
            eventManager().fire(Events.PRINT_CANCELLING, payload)

    def on_comm_print_job_cancelled(self, suppress_script=False, user=None):
        self._setCurrentZ(None)
        self._updateProgressData()

        fileposition = self._comm.getFilePosition() if self._comm else None
        progress = self._comm.getPrintProgress() if self._comm else None
        payload = self._payload_for_print_job_event(
            position=self._comm.cancel_position.as_dict()
            if self._comm and self._comm.cancel_position
            else None,
            fileposition=fileposition["pos"] if fileposition else None,
            progress=progress,
            action_user=user,
        )
        if payload:
            payload["time"] = self._comm.getPrintTime()

            eventManager().fire(Events.PRINT_CANCELLED, payload)
            eventManager().fire(
                Events.CHART_MARKED,
                {"type": "cancel", "label": "Cancel"},
            )
            self._logger_job.info(
                "Print job cancelled - origin: {}, path: {}, owner: {}, user: {}, fileposition: {}, position: {}".format(
                    payload.get("origin"),
                    payload.get("path"),
                    payload.get("owner"),
                    payload.get("user"),
                    payload.get("fileposition"),
                    payload.get("position"),
                )
            )

            if not suppress_script:
                self.script(
                    "afterPrintCancelled",
                    context={"event": payload},
                    part_of_job=True,
                    must_be_set=False,
                )

            payload["reason"] = "cancelled"

            def finalize():
                self._fileManager.log_print(
                    payload["origin"],
                    payload["path"],
                    time.time(),
                    payload["time"],
                    False,
                    self._printerProfileManager.get_current_or_default()["id"],
                )
                eventManager().fire(Events.PRINT_FAILED, payload)

            thread = threading.Thread(target=finalize)
            thread.daemon = True
            thread.start()

    def on_comm_print_job_paused(self, suppress_script=False, user=None):
        fileposition = self._comm.getFilePosition() if self._comm else None
        progress = self._comm.getPrintProgress() if self._comm else None
        payload = self._payload_for_print_job_event(
            position=self._comm.pause_position.as_dict()
            if self._comm and self._comm.pause_position and not suppress_script
            else None,
            fileposition=fileposition["pos"] if fileposition else None,
            progress=progress,
            action_user=user,
        )
        if payload:
            eventManager().fire(Events.PRINT_PAUSED, payload)
            self._logger_job.info(
                "Print job paused - origin: {}, path: {}, owner: {}, user: {}, fileposition: {}, position: {}".format(
                    payload.get("origin"),
                    payload.get("path"),
                    payload.get("owner"),
                    payload.get("user"),
                    payload.get("fileposition"),
                    payload.get("position"),
                )
            )
            eventManager().fire(
                Events.CHART_MARKED,
                {"type": "pause", "label": "Pause"},
            )
            if not suppress_script:
                self.script(
                    "afterPrintPaused",
                    context={"event": payload},
                    part_of_job=True,
                    must_be_set=False,
                )

    def on_comm_print_job_resumed(self, suppress_script=False, user=None):
        payload = self._payload_for_print_job_event(action_user=user)
        if payload:
            eventManager().fire(Events.PRINT_RESUMED, payload)
            eventManager().fire(
                Events.CHART_MARKED,
                {"type": "resume", "label": "Resume"},
            )
            self._logger_job.info(
                "Print job resumed - origin: {}, path: {}, owner: {}, user: {}".format(
                    payload.get("origin"),
                    payload.get("path"),
                    payload.get("owner"),
                    payload.get("user"),
                )
            )

            if not suppress_script:
                self.script(
                    "beforePrintResumed",
                    context={"event": payload},
                    part_of_job=True,
                    must_be_set=False,
                )

    def on_comm_file_transfer_started(
        self, local_filename, remote_filename, filesize, user=None
    ):
        eventManager().fire(
            Events.TRANSFER_STARTED, {"local": local_filename, "remote": remote_filename}
        )

        self._sdStreaming = True

        self._setJobData(remote_filename, filesize, True, user=user)
        self._updateProgressData(completion=0.0, filepos=0, printTime=0)
        self._stateMonitor.set_state(
            self._dict(
                text=self.get_state_string(),
                flags=self._getStateFlags(),
                error=self.get_error(),
            )
        )

    def on_comm_file_transfer_done(
        self, local_filename, remote_filename, elapsed, failed=False
    ):
        self._sdStreaming = False

        payload = {"local": local_filename, "remote": remote_filename, "time": elapsed}

        if failed:
            eventManager().fire(Events.TRANSFER_FAILED, payload)
            if callable(self._streamingFailedCallback):
                self._streamingFailedCallback(
                    remote_filename, remote_filename, FileDestinations.SDCARD
                )
        else:
            eventManager().fire(Events.TRANSFER_DONE, payload)
            if callable(self._streamingFinishedCallback):
                self._streamingFinishedCallback(
                    remote_filename, remote_filename, FileDestinations.SDCARD
                )

        self._setCurrentZ(None)
        self._setJobData(None, None, None)
        self._updateProgressData()
        self._stateMonitor.set_state(
            self._dict(
                text=self.get_state_string(),
                flags=self._getStateFlags(),
                error=self.get_error(),
            )
        )

    def on_comm_file_transfer_failed(self, local_filename, remote_filename, elapsed):
        self.on_comm_file_transfer_done(
            local_filename, remote_filename, elapsed, failed=True
        )

    def on_comm_force_disconnect(self):
        self.disconnect()

    def on_comm_record_fileposition(self, origin, name, pos):
        try:
            self._fileManager.save_recovery_data(origin, name, pos)
        except NoSuchStorage:
            pass
        except Exception:
            self._logger.exception("Error while trying to persist print recovery data")

    def on_comm_firmware_info(self, firmware_name, firmware_data):
        self._firmware_info = {"name": firmware_name, "data": firmware_data}

    def _payload_for_print_job_event(
        self,
        location=None,
        print_job_file=None,
        print_job_size=None,
        print_job_user=None,
        position=None,
        fileposition=None,
        progress=None,
        action_user=None,
    ):
        if print_job_file is None:
            with self._selectedFileMutex:
                selected_file = self._selectedFile
                if not selected_file:
                    return {}

                print_job_file = selected_file.get("filename", None)
                print_job_size = selected_file.get("filesize", None)
                print_job_user = selected_file.get("user", None)
                location = (
                    FileDestinations.SDCARD
                    if selected_file.get("sd", False)
                    else FileDestinations.LOCAL
                )

        if not print_job_file or not location:
            return {}

        if location == FileDestinations.SDCARD:
            full_path = print_job_file
            if full_path.startswith("/"):
                full_path = full_path[1:]
            name = path = full_path
            origin = FileDestinations.SDCARD

        else:
            full_path = self._fileManager.path_on_disk(
                FileDestinations.LOCAL, print_job_file
            )
            path = self._fileManager.path_in_storage(
                FileDestinations.LOCAL, print_job_file
            )
            _, name = self._fileManager.split_path(FileDestinations.LOCAL, path)
            origin = FileDestinations.LOCAL

        result = {"name": name, "path": path, "origin": origin, "size": print_job_size}

        if position is not None:
            result["position"] = position

        if fileposition is not None:
            result["fileposition"] = fileposition

        if progress is not None:
            result["progress"] = int(progress * 100)

        if print_job_user is not None:
            result["owner"] = print_job_user

        if action_user is not None:
            result["user"] = action_user

        return result


class StateMonitor:
    def __init__(
        self,
        interval=0.5,
        on_update=None,
        on_add_temperature=None,
        on_add_log=None,
        on_add_message=None,
        on_get_progress=None,
        on_get_resends=None,
    ):
        self._interval = interval
        self._update_callback = on_update
        self._on_add_temperature = on_add_temperature
        self._on_add_log = on_add_log
        self._on_add_message = on_add_message
        self._on_get_progress = on_get_progress
        self._on_get_resends = on_get_resends

        self._state = None
        self._job_data = None
        self._current_z = None
        self._offsets = {}
        self._progress = None
        self._resends = None

        self._progress_dirty = False
        self._resends_dirty = False

        self._change_event = threading.Event()
        self._state_lock = threading.Lock()
        self._progress_lock = threading.Lock()
        self._resends_lock = threading.Lock()

        self._last_update = time.monotonic()
        self._worker = threading.Thread(target=self._work)
        self._worker.daemon = True
        self._worker.start()

    def _get_current_progress(self):
        if callable(self._on_get_progress):
            return self._on_get_progress()
        return self._progress

    def _get_current_resends(self):
        if callable(self._on_get_resends):
            return self._on_get_resends()
        return self._resends

    def reset(
        self,
        state=None,
        job_data=None,
        progress=None,
        current_z=None,
        offsets=None,
        resends=None,
    ):
        self.set_state(state)
        self.set_job_data(job_data)
        self.set_progress(progress)
        self.set_current_z(current_z)
        self.set_temp_offsets(offsets)
        self.set_resends(resends)

    def add_temperature(self, temperature):
        self._on_add_temperature(temperature)
        self._change_event.set()

    def add_log(self, log):
        self._on_add_log(log)
        with self._resends_lock:
            self._resends_dirty = True
        self._change_event.set()

    def add_message(self, message):
        self._on_add_message(message)
        self._change_event.set()

    def set_current_z(self, current_z):
        self._current_z = current_z
        self._change_event.set()

    def set_state(self, state):
        with self._state_lock:
            self._state = state
            self._change_event.set()

    def set_job_data(self, job_data):
        self._job_data = job_data
        self._change_event.set()

    def trigger_progress_update(self):
        with self._progress_lock:
            self._progress_dirty = True
            self._change_event.set()

    def set_progress(self, progress):
        with self._progress_lock:
            self._progress_dirty = False
            self._progress = progress
            self._change_event.set()

    def set_resends(self, resend_ratio):
        with self._resends_lock:
            self._resends_dirty = False
            self._resends = resend_ratio
            self._change_event.set()

    def set_temp_offsets(self, offsets):
        if offsets is None:
            offsets = {}
        self._offsets = offsets
        self._change_event.set()

    def _work(self):
        try:
            while True:
                self._change_event.wait()

                now = time.monotonic()
                delta = now - self._last_update
                additional_wait_time = self._interval - delta
                if additional_wait_time > 0:
                    time.sleep(additional_wait_time)

                with self._state_lock:
                    data = self.get_current_data()
                    self._update_callback(data)
                    self._last_update = time.monotonic()
                    self._change_event.clear()
        except Exception:
            logging.getLogger(__name__).exception(
                "Looks like something crashed inside the state update worker. "
                "Please report this on the OctoPrint issue tracker (make sure "
                "to include logs!)"
            )

    def get_current_data(self):
        with self._progress_lock:
            if self._progress_dirty:
                self._progress = self._get_current_progress()
                self._progress_dirty = False

        with self._resends_lock:
            if self._resends_dirty:
                self._resends = self._get_current_resends()
                self._resends_dirty = False

        return {
            "state": self._state,
            "job": self._job_data,
            "currentZ": self._current_z,
            "progress": self._progress,
            "offsets": self._offsets,
            "resends": self._resends,
        }


class DataHistory(InvariantContainer):
    def __init__(self, cutoff=30 * 60):
        def data_invariant(data):
            data.sort(key=lambda x: x["time"])
            now = int(time.time())
            return [item for item in data if item["time"] >= now - cutoff]

        InvariantContainer.__init__(self, guarantee_invariant=data_invariant)
        self._last = None

    @property
    def last(self):
        return self._last

    def append(self, item):
        try:
            return super().append(item)
        finally:
            self._last = self._data[-1] if len(self._data) else None
