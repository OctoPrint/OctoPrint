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
from typing import cast

from frozendict import frozendict

import octoprint.util.json
from octoprint import util as util
from octoprint.events import Events, eventManager
from octoprint.filemanager import (
    FileDestinations,
    FileManager,
    NoSuchStorage,
)
from octoprint.filemanager.analysis import AnalysisQueue
from octoprint.filemanager.storage.printer import PrinterFileStorage
from octoprint.plugin import ProgressPlugin, plugin_manager
from octoprint.printer import (
    PrinterCallback,
    PrinterFilesMixin,
    PrinterMixin,
)
from octoprint.printer.connection import (
    ConnectedPrinter,
    ConnectedPrinterListenerMixin,
    ConnectedPrinterState,
)
from octoprint.printer.estimation import PrintTimeEstimator
from octoprint.printer.job import PrintJob, UploadJob
from octoprint.settings import settings
from octoprint.util import InvariantContainer
from octoprint.util import comm as comm
from octoprint.util import get_fully_qualified_classname as fqcn


class Printer(PrinterMixin, ConnectedPrinterListenerMixin):
    """
    Default implementation of the :class:`PrinterInterface`. Encapsulates the :class:`~octoprint.printer.connection.ConnectedPrinter`,
    registers itself as a callback for it and forwards calls as necessary.
    """

    def __init__(
        self,
        file_manager: FileManager,
        analysis_queue: AnalysisQueue,
        printer_profile_manager,
    ):
        from collections import deque

        self._logger = logging.getLogger(__name__)
        self._logger_job = logging.getLogger(f"{__name__}.job")

        self._dict = (
            frozendict
            if settings().getBoolean(["devel", "useFrozenDictForPrinterState"])
            else dict
        )

        self._analysis_queue = analysis_queue
        self._file_manager = file_manager
        self._printer_profile_manager = printer_profile_manager

        self._temps = DataHistory(
            cutoff=settings().getInt(["temperature", "cutoff"]) * 60
        )
        self._markings = DataHistory(
            cutoff=settings().getInt(["temperature", "cutoff"]) * 60
        )

        self._messages = deque([], 300)
        self._log = deque([], 300)

        self._state = None

        self._printAfterSelect = False
        self._posAfterSelect = None

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
        self._connection: ConnectedPrinter = None

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
                    job_type = "printer"
                else:
                    job_type = "local"

        self._estimator = self._estimator_factory(job_type)

    @property
    def firmware_info(self):
        if not self._connection:
            return None
        firmware_info = self._connection.firmware_info
        if firmware_info is None:
            return None
        return firmware_info.model_dump()

    @property
    def error_info(self):
        if not self._connection:
            return None
        error_info = self._connection.error_info
        if error_info is None:
            return None
        return error_info.model_dump()

    @property
    def connection_state(self) -> dict:
        if self._connection is None:
            return {"state": "Offline"}

        parameters = self._connection.connection_parameters
        parameters["state"] = self._connection.get_state_string()
        return parameters

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

    def connect(self, connector=None, parameters=None, profile=None, *args, **kwargs):
        """
        Connects to the printer. If port and/or baudrate is provided, uses these settings, otherwise autodetection
        will be attempted.
        """
        if self._connection is not None:
            return

        if connector is None:
            connector = "serial"

        if parameters is None:
            parameters = {}
            if "port" in kwargs:
                parameters["port"] = kwargs["port"]
            if "baudrate" in kwargs:
                parameters["baudrate"] = kwargs["baudrate"]

        for name, hook in self._handle_connect_hooks.items():
            try:
                if hook(
                    self,
                    *args,
                    connector=connector,
                    parameters=parameters,
                    profile=profile,
                    **kwargs,
                ):
                    self._logger.info(f"Connect signalled as handled by plugin {name}")
                    return
            except Exception:
                self._logger.exception(
                    f"Exception while handling connect in plugin {name}",
                    extra={"plugin": name},
                )

        eventManager().fire(Events.CONNECTING)
        self._printer_profile_manager.select(profile)
        printer_profile = self._printer_profile_manager.get_current_or_default()

        connector_class = ConnectedPrinter.find(connector)
        try:
            self._connection = connector_class(
                self,
                **parameters,
                profile=printer_profile,
            )
            self._connection.connect()
        except Exception as exc:
            self._connection = None
            self._setState(
                ConnectedPrinterState.ERROR, state_string="Error", error_string=str(exc)
            )
            raise exc

    def disconnect(self, *args, **kwargs):
        """
        Closes the connection to the printer.
        """
        self._file_manager.remove_storage(FileDestinations.PRINTER)

        eventManager().fire(Events.DISCONNECTING)
        if self._connection is not None:
            self._connection.disconnect()
            self._connection = None
        else:
            eventManager().fire(Events.DISCONNECTED)

    def emergency_stop(self, *args, **kwargs):
        if self._connection is None:
            return

        tags = kwargs.get("tags", set()) | {"trigger:printer.emergency_stop"}

        self._connection.emergency_stop(tags=tags)

    def job_on_hold(self, blocking=True, *args, **kwargs):
        if self._connection is None:
            raise RuntimeError("No connection to the printer")
        return self._connection.job_on_hold(blocking=blocking)

    def set_job_on_hold(self, value, blocking=True, *args, **kwargs):
        if self._connection is None:
            raise RuntimeError("No connection to the printer")
        return self._connection.set_job_on_hold(value, blocking=blocking)

    def repair_communication(self, *args, **kwargs):
        if self._connection is None:
            return

        self._connection.repair_communication()

    def commands(self, *commands, tags=None, force=False, **kwargs):
        """
        Sends one or more gcode commands to the printer.
        """
        if self._connection is None:
            return

        if len(commands) == 1 and isinstance(commands[0], (list, tuple)):
            commands = commands[0]

        if tags is None:
            tags = set()
        tags |= {"trigger:printer.commands"}

        self._connection.commands(commands, tags=tags, force=force)

    def script(
        self,
        name,
        context=None,
        tags=None,
        must_be_set=True,
        part_of_job=False,
        *args,
        **kwargs,
    ):
        if self._connection is None:
            return

        if name is None or not name:
            raise ValueError("name must be set")

        if tags is None:
            tags = set()
        tags |= {"trigger:printer.script"}

        self._connection.script(
            name,
            context=context,
            must_be_set=must_be_set,
            part_of_job=part_of_job,
            tags=tags,
        )

    def jog(self, axes, relative=True, speed=None, tags=None, *args, **kwargs):
        if self._connection is None:
            return

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
            if axis not in PrinterMixin.valid_axes:
                raise ValueError(
                    "Invalid axis {}, valid axes are {}".format(
                        axis, ", ".join(PrinterMixin.valid_axes)
                    )
                )

        if tags is None:
            tags = set()
        tags |= {"trigger:printer.jog"}

        self._connection.jog(axes, relative=True, speed=speed, tags=tags)

    def home(self, axes, tags=None, *args, **kwargs):
        if self._connection is None:
            return

        if not isinstance(axes, (list, tuple)):
            if isinstance(axes, str):
                axes = [axes]
            else:
                raise ValueError(f"axes is neither a list nor a string: {axes}")

        validated_axes = list(
            filter(lambda x: x in PrinterMixin.valid_axes, (x.lower() for x in axes))
        )
        if len(axes) != len(validated_axes):
            raise ValueError(f"axes contains invalid axes: {axes}")

        if tags is None:
            tags = set()
        tags |= {"trigger:printer.home"}

        self._connection.home(axes, tags=tags)

    def extrude(self, amount, speed=None, tags=None, *args, **kwargs):
        if self._connection is None:
            return

        if not isinstance(amount, (int, float)):
            raise ValueError(f"amount must be a valid number: {amount}")

        if tags is None:
            tags = set()
        tags |= {"trigger:printer.extrude"}

        self._connection.extrude(amount, speed=speed, tags=tags)

    def change_tool(self, tool, tags=None, *args, **kwargs):
        if not PrinterMixin.valid_tool_regex.match(tool):
            raise ValueError(f'tool must match "tool[0-9]+": {tool}')

        if tags is None:
            tags = set()
        tags |= {"trigger:printer.change_tool"}

        self._connection.change_tool(tool, tags=tags)

    def set_temperature(self, heater, value, tags=None, *args, **kwargs):
        if not PrinterMixin.valid_heater_regex.match(heater):
            raise ValueError(
                'heater must match "tool", "tool([0-9])", "bed" or "chamber": {heater}'.format(
                    heater=heater
                )
            )

        if not isinstance(value, (int, float)) or value < 0:
            raise ValueError(f"value must be a valid number >= 0: {value}")

        if tags is None:
            tags = set()
        tags |= {"trigger:printer.set_temperature"}

        self._connection.set_temperature(heater, value, tags=tags)

        if heater == "tool":
            # set current tool, whatever that might be
            self.commands(f"M104 S{value}", tags=tags)

        elif heater.startswith("tool"):
            # set specific tool
            printer_profile = self._printer_profile_manager.get_current_or_default()
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

    def set_temperature_offset(self, offsets=None, tags=None, *args, **kwargs):
        if self._connection is None:
            return

        if offsets is None:
            offsets = {}

        if not isinstance(offsets, dict):
            raise ValueError("offsets must be a dict")

        validated_keys = list(
            filter(
                lambda x: PrinterMixin.valid_heater_regex_no_current.match(x),
                offsets.keys(),
            )
        )
        validated_values = list(
            filter(lambda x: isinstance(x, (int, float)), offsets.values())
        )

        if len(validated_keys) != len(offsets):
            raise ValueError(f"offsets contains invalid keys: {offsets}")
        if len(validated_values) != len(offsets):
            raise ValueError(f"offsets contains invalid values: {offsets}")

        if tags is None:
            tags = set()
        tags |= {"trigger:printer.set_temperature_offset"}

        self._connection.set_temperature_offset(offsets=offsets, tags=tags)

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

    def feed_rate(self, factor, tags=None, *args, **kwargs):
        if self._connection is None:
            return

        factor = self._convert_rate_value(factor, min_val=1)

        if tags is None:
            tags = set()
        tags |= {"trigger:printer.feed_rate"}

        self._connection.feed_rate(factor, tags=tags)

    def flow_rate(self, factor, tags=None, *args, **kwargs):
        if self._connection is None:
            return

        factor = self._convert_rate_value(factor, min_val=1)

        if tags is None:
            tags = set()
        tags |= {"trigger:printer.flow_rate"}

        self._connection.flow_rate(factor, tags=tags)

    def set_job(
        self,
        job: PrintJob,
        print_after_select=False,
        pos=None,
        tags=None,
        user=None,
        *args,
        **kwargs,
    ):
        if self._connection is None or not self._connection.is_ready():
            self._logger.info("Cannot load job: printer not connected or currently busy")
            return

        if job is None:
            return

        if job.storage == FileDestinations.LOCAL:
            job.path_on_disk = self._file_manager.path_on_disk(job.storage, job.path)
            job.path = self._file_manager.path_in_storage(
                job.storage, job.path_on_disk
            )  # canonicalize

        if not self._connection.supports_job(job):
            self._logger.info("Cannot load job: printer doesn't support it")
            return

        if tags is None:
            tags = set()
        tags |= {"trigger:printer.set_job"}

        try:
            recovery_data = self._file_manager.get_recovery_data()
            if recovery_data:
                # clean up recovery data if we just selected a different file
                actual_origin = recovery_data.get("origin", None)
                actual_path = recovery_data.get("path", None)

                if (
                    actual_origin is None
                    or actual_path is None
                    or actual_origin != job.storage
                    or actual_path != job.path
                ):
                    self._file_manager.delete_recovery_data()
        except Exception:
            # anything goes wrong with the recovery data, we ignore it
            self._logger.exception(
                "Something was wrong with processing the recovery data"
            )

        self._printAfterSelect = print_after_select
        self._posAfterSelect = pos

        super().set_job(
            job, print_after_select=print_after_select, pos=pos, tags=tags, user=user
        )
        self._connection.set_job(
            job, print_after_select=print_after_select, pos=pos, tags=tags, user=user
        )

        self._updateProgressData()

    def get_file_position(self):
        if self._connection is None:
            return None

        with self._selectedFileMutex:
            if self._selectedFile is None:
                return None

        job_progress = self._connection.job_progress
        return job_progress.pos

    def get_markings(self):
        return self._markings

    def start_print(self, pos=None, user=None, tags=None, *args, **kwargs):
        """
        Starts the currently loaded print job.
        Only starts if the printer is connected and operational, not currently printing and a printjob is loaded
        """
        if self._connection is None or not self._connection.is_ready():
            return

        with self._selectedFileMutex:
            if self._selectedFile is None:
                return

        self._file_manager.delete_recovery_data()

        self._lastProgressReport = None
        self._updateProgressData()

        if tags is None:
            tags = set()
        tags |= {"trigger:printer.start_print"}

        self._connection.start_print(pos=pos, user=user, tags=tags)

    def pause_print(self, user=None, tags=None, *args, **kwargs):
        """
        Pause the current printjob.
        """
        if self._connection is None:
            return

        if self._connection.is_paused():
            return

        if tags is None:
            tags = set()
        tags |= {"trigger:printer.pause_print"}

        self._connection.pause_print(user=user, tags=tags)

    def resume_print(self, user=None, tags=None, *args, **kwargs):
        if self._connection is None:
            return

        if not self._connection.is_paused():
            return

        if tags is None:
            tags = set()
        tags |= {"trigger:printer.resume_print"}

        self._connection.resume_print(user=user, tags=tags)

    def cancel_print(self, user=None, tags=None, *args, **kwargs):
        if self._connection is None:
            return

        if tags is None:
            tags = set()
        tags |= {"trigger:printer.cancel_print"}

        self._connection.cancel_print(user=user, tags=tags)

    def get_state_string(self, state=None, *args, **kwargs):
        if self._connection is None:
            return "Offline"
        else:
            return self._connection.get_state_string(state=state)

    def get_state_id(self, state=None, *args, **kwargs):
        if self._connection is None:
            return "OFFLINE"
        else:
            return self._connection.get_state_id(state=state)

    def get_error(self):
        if self._connection is None:
            return ""
        else:
            return self._connection.get_error()

    def get_current_data(self, *args, **kwargs):
        return util.thaw_frozendict(self._stateMonitor.get_current_data())

    def get_current_job(self, *args, **kwargs):
        currentData = self._stateMonitor.get_current_data()
        return util.thaw_frozendict(currentData["job"])

    def get_current_temperatures(self, *args, **kwargs):
        if self._connection is None:
            offsets = {}
        else:
            offsets = self._connection.temperature_offsets

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
        if self._connection is None:
            return "Closed", None, None, None

        parameters = self._connection.connection_parameters

        port = parameters.get("port")
        baudrate = parameters.get("baudrate")
        profile = parameters.get("profile")

        return self._connection.state_string(), port, baudrate, profile

    def is_closed_or_error(self, *args, **kwargs):
        return self._connection is None or self._connection.is_closed_or_error()

    def is_operational(self, *args, **kwargs):
        return self._connection is not None and self._connection.is_operational()

    def is_printing(self, *args, **kwargs):
        return self._connection is not None and self._connection.is_printing()

    def is_cancelling(self, *args, **kwargs):
        return self._connection is not None and self._connection.is_cancelling()

    def is_pausing(self, *args, **kwargs):
        return self._connection is not None and self._connection.is_pausing()

    def is_paused(self, *args, **kwargs):
        return self._connection is not None and self._connection.is_paused()

    def is_resuming(self, *args, **kwargs):
        return self._connection is not None and self._connection.is_resuming()

    def is_finishing(self, *args, **kwargs):
        return self._connection is not None and self._connection.is_finishing()

    def is_error(self, *args, **kwargs):
        return self._connection is not None and self._connection.is_error()

    def is_ready(self, *args, **kwargs):
        return self._connection is not None and self._connection.is_ready()

    # ~~ sd file handling

    def is_sd_ready(self, *args, **kwargs):
        if (
            not settings().getBoolean(["feature", "sdSupport"])
            or self._connection is None
            or not isinstance(self._connection, PrinterFilesMixin)
        ):
            return False

        return self._connection.printer_files_mounted

    def get_sd_files(self, *args, **kwargs):
        if not self.is_sd_ready():
            return []

        refresh = kwargs.get("refresh", False)

        return [
            {"name": x.path, "size": x.size, "display": x.display, "date": x.date}
            for x in cast(PrinterFilesMixin, self._connection).get_printer_files(
                refresh=refresh
            )
        ]

    def add_sd_file(
        self, filename, path, on_success=None, on_failure=None, *args, **kwargs
    ):
        if not self.is_sd_ready() or not self._connection.is_ready():
            self._logger.error("No connection to printer or printer is busy")
            return

        connection = cast(PrinterFilesMixin, self._connection)
        if not connection.current_storage_capabilities.write_file:
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
                    remote_filename, remote_filename, FileDestinations.PRINTER
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
                    remote_filename, remote_filename, FileDestinations.PRINTER
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
            tags = kwargs.get("tags", set()) | {"trigger:printer.add_sd_file"}
            local = self._file_manager.path_on_disk(FileDestinations.LOCAL, filename)
            remote = connection.upload_printer_file(local, path, tags=tags)
            return remote

    def delete_sd_file(self, filename, *args, **kwargs):
        if not self.is_sd_ready():
            return

        tags = kwargs.get("tags", set()) | {"trigger:printer.delete_sd_file"}

        cast(PrinterFilesMixin, self._connection).delete_printer_file(
            "/" + filename, tags=tags
        )

    def init_sd_card(self, *args, **kwargs):
        if (
            not self._connection
            or not isinstance(self._connection, PrinterFilesMixin)
            or self.is_sd_ready()
        ):
            return

        tags = kwargs.get("tags", set()) | {"trigger:printer.init_sd_card"}

        self._connection.mount_printer_files(tags=tags)

    def release_sd_card(self, *args, **kwargs):
        if not self.is_sd_ready():
            return

        tags = kwargs.get("tags", set()) | {"trigger:printer.release_sd_card"}

        cast(PrinterFilesMixin, self._connection).unmount_printer_files(tags=tags)

    def refresh_sd_files(self, blocking=False, *args, **kwargs):
        if not self.is_sd_ready():
            return

        tags = kwargs.get("tags", set()) | {"trigger:printer.refresh_sd_files"}
        timeout = kwargs.get("timeout", 10)

        cast(PrinterFilesMixin, self._connection).refresh_printer_files(
            blocking=blocking, timeout=timeout, tags=tags
        )

    # ~~ ConnectedPrinterListenerMixin

    def on_printer_state_changed(
        self, state: ConnectedPrinterState, state_str: str = None, error_str: str = None
    ):
        old_state = self._state

        if old_state in (ConnectedPrinterState.PRINTING,):
            # if we were still printing and went into an error state, mark the print as failed
            if state in (
                ConnectedPrinterState.CLOSED,
                ConnectedPrinterState.ERROR,
                ConnectedPrinterState.CLOSED_WITH_ERROR,
            ):
                with self._selectedFileMutex:
                    if self._selectedFile is not None:
                        payload = self._payload_for_print_job_event()
                        if payload:
                            job_progress = self._connection.job_progress
                            error_info = self._connection.error_info

                            payload["reason"] = "error"
                            payload["error"] = (
                                error_info.error if error_info else "unknown"
                            )
                            payload["time"] = job_progress.elapsed
                            payload["progress"] = job_progress.progress

                            def finalize():
                                self._file_manager.log_print(
                                    payload["origin"],
                                    payload["path"],
                                    time.time(),
                                    payload["time"],
                                    False,
                                    self._printer_profile_manager.get_current_or_default()[
                                        "id"
                                    ],
                                )
                                eventManager().fire(Events.PRINT_FAILED, payload)

                            thread = threading.Thread(target=finalize)
                            thread.daemon = True
                            thread.start()

            try:
                self._analysis_queue.resume()  # printing done, put those cpu cycles to good use
            except Exception:
                self._logger.exception("Error while resuming the analysis queue")

        elif state == ConnectedPrinterState.PRINTING:
            if settings().get(["gcodeAnalysis", "runAt"]) == "idle":
                try:
                    self._analysis_queue.pause()  # only analyse files while idle
                except Exception:
                    self._logger.exception("Error while pausing the analysis queue")

        if (
            state == ConnectedPrinterState.CLOSED
            or state == ConnectedPrinterState.CLOSED_WITH_ERROR
        ):
            if self._connection is not None:
                self._connection = None

            with self._selectedFileMutex:
                if self._selectedFile is not None:
                    eventManager().fire(Events.FILE_DESELECTED)
                self._setJobData(None, None, None)

            self._updateProgressData()
            self._setOffsets(None)
            self._addTemperatureData()
            self._printer_profile_manager.deselect()

            eventManager().fire(Events.DISCONNECTED)

        self._setState(state, state_string=state_str, error_string=error_str)

    def on_printer_job_changed(self, job, user=None, data=None):
        if job is not None:
            payload = self._payload_for_print_job_event(
                location=job.storage,
                print_job_file=job.path,
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

        self._setJobData(
            job.path if job else None,
            job.size if job else None,
            job.storage == FileDestinations.PRINTER if job else False,
            user=user,
            data=data,
        )
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

    def on_printer_job_started(self, suppress_script=False, user=None):
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

    def on_printer_job_paused(self, suppress_script=False, user=None):
        job_progress = self._connection.job_progress if self._connection else None

        if job_progress:
            fileposition = job_progress.pos
            progress = job_progress.progress
        else:
            fileposition = None
            progress = None

        payload = self._payload_for_print_job_event(
            position=self._connection.pause_position if self._connection else None,
            fileposition=fileposition,
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

    def on_printer_job_resumed(self, suppress_script=False, user=None):
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

    def on_printer_job_progress(self):
        self._stateMonitor.trigger_progress_update()

    def on_printer_job_done(self, suppress_script=False):
        self._file_manager.delete_recovery_data()

        payload = self._payload_for_print_job_event()
        if payload:
            job_progress = self._connection.job_progress
            payload["time"] = job_progress.elapsed
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
                self._file_manager.log_print(
                    payload["origin"],
                    payload["path"],
                    time.time(),
                    payload["time"],
                    True,
                    self._printer_profile_manager.get_current_or_default()["id"],
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

    def on_printer_job_cancelled(self, suppress_script=False, user=None):  # TODO
        self._updateProgressData()

        job_progress = self._connection.job_progress if self._connection else None

        if job_progress:
            fileposition = job_progress.pos
            progress = job_progress.progress
        else:
            fileposition = None
            progress = None

        payload = self._payload_for_print_job_event(
            position=self._connection.cancel_position if self._connection else None,
            fileposition=fileposition,
            progress=progress,
            action_user=user,
        )
        if payload:
            payload["time"] = job_progress.elapsed

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
                self._file_manager.log_print(
                    payload["origin"],
                    payload["path"],
                    time.time(),
                    payload["time"],
                    False,
                    self._printer_profile_manager.get_current_or_default()["id"],
                )
                eventManager().fire(Events.PRINT_FAILED, payload)

            thread = threading.Thread(target=finalize)
            thread.daemon = True
            thread.start()

    def on_printer_position_changed(self, position, reason=None):
        payload = {"reason": reason}
        payload.update(position)
        eventManager().fire(Events.POSITION_UPDATE, payload)

    def on_printer_temperature_update(self, temperatures):
        self._addTemperatureData(temperatures)

    def on_printer_logs(self, *lines):
        for line in lines:
            self._addLog(line)

    def on_printer_disconnect(self):
        self.disconnect()

    def on_printer_record_recovery_position(self, job: PrintJob, pos: int):
        try:
            self._file_manager.save_recovery_data(job.storage, job.path, pos)
        except NoSuchStorage:
            pass
        except Exception:
            self._logger.exception("Error while trying to persist print recovery data")

    def on_printer_files_available(self, available):
        if available:
            storage = PrinterFileStorage(self._connection)
            self._file_manager.add_storage(FileDestinations.PRINTER, storage)
        else:
            self._file_manager.remove_storage(FileDestinations.PRINTER)

        self._stateMonitor.set_state(
            self._dict(
                text=self.get_state_string(),
                flags=self._getStateFlags(),
                error=self.get_error(),
            )
        )

    def on_printer_files_refreshed(self, files):
        eventManager().fire(Events.UPDATED_FILES, {"type": "printables"})

    def on_printer_files_upload_start(self, job: UploadJob):
        eventManager().fire(
            Events.TRANSFER_STARTED,
            {"local": job.path, "remote": job.remote_path},
        )

        self._sdStreaming = True

        self._setJobData(job.path, job.size, True, user=job.owner)
        self._updateProgressData(completion=0.0, filepos=0, printTime=0)
        self._stateMonitor.set_state(
            self._dict(
                text=self.get_state_string(),
                flags=self._getStateFlags(),
                error=self.get_error(),
            )
        )

    def on_printer_files_upload_done(
        self, job: UploadJob, elapsed: float, failed: bool = False
    ):
        self._sdStreaming = False

        payload = {"local": job.path, "remote": job.remote_path, "time": elapsed}

        if failed:
            eventManager().fire(Events.TRANSFER_FAILED, payload)
            if callable(self._streamingFailedCallback):
                self._streamingFailedCallback(
                    job.path, job.remote_path, FileDestinations.PRINTER
                )
        else:
            eventManager().fire(Events.TRANSFER_DONE, payload)
            if callable(self._streamingFinishedCallback):
                self._streamingFinishedCallback(
                    job.path, job.remote_path, FileDestinations.PRINTER
                )

        self._setJobData(None, None, None)
        self._updateProgressData()
        self._stateMonitor.set_state(
            self._dict(
                text=self.get_state_string(),
                flags=self._getStateFlags(),
                error=self.get_error(),
            )
        )

    def trigger_printjob_event(
        self,
        event,
        job: PrintJob = None,
        print_head_position: dict = None,
        job_position: dict = None,
        progress: float = None,
        user: str = None,
        payload: dict = None,
    ):
        kwargs = {
            "position": print_head_position,
            "fileposition": job_position,
            "progress": progress,
            "action_user": user,
        }
        if job is not None:
            kwargs["location"] = job.storage
            kwargs["print_job_file"] = job.path
            kwargs["print_job_size"] = job.size
            kwargs["print_job_user"] = job.owner
        if payload is not None:
            kwargs.update(**payload)

        event_payload = self._payload_for_print_job_event(**kwargs)
        if event_payload:
            eventManager().fire(event, event_payload)
        return event_payload

    # ~~ state monitoring

    def _setOffsets(self, offsets):
        self._stateMonitor.set_temp_offsets(offsets)

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
        if self._connection is None:
            progress = None
            filepos = None
            printTime = None
            cleanedPrintTime = None
        else:
            job_progress = self._connection.job_progress
            progress = job_progress.progress
            filepos = job_progress.pos
            printTime = job_progress.elapsed
            cleanedPrintTime = job_progress.cleaned_elapsed

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
        if self._connection is None:
            return self._dict(count=0, transmitted=0, ratio=0)

        communication_health = self._connection.communication_health
        return self._dict(
            count=communication_health.errors,
            transmitted=communication_health.total,
            ratio=round(communication_health.ratio * 100),
        )

    def _addTemperatureData(self, temperatures=None):
        data = {"time": int(time.time())}
        if temperatures:
            for key, value in temperatures.items():
                if not isinstance(value, tuple) or not len(value) == 2:
                    continue
                data[key] = self._dict(actual=value[0], target=value[1])

        self._temps.append(data)
        self._stateMonitor.add_temperature(self._dict(**data))

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
                    path_in_storage = self._file_manager.path_in_storage(
                        FileDestinations.LOCAL, filename
                    )
                    path_on_disk = self._file_manager.path_on_disk(
                        FileDestinations.LOCAL, filename
                    )
                    _, name_in_storage = self._file_manager.split_path(
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
                    fileData = self._file_manager.get_metadata(
                        FileDestinations.PRINTER if sd else FileDestinations.LOCAL,
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
                            self._printer_profile_manager.get_current_or_default()["id"]
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
                        origin=FileDestinations.PRINTER if sd else FileDestinations.LOCAL,
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
                    FileDestinations.PRINTER
                    if selected_file.get("sd", False)
                    else FileDestinations.LOCAL
                )

        if not print_job_file or not location:
            return {}

        if location == FileDestinations.PRINTER:
            full_path = print_job_file
            if full_path.startswith("/"):
                full_path = full_path[1:]
            name = path = full_path
            origin = FileDestinations.PRINTER

        else:
            full_path = self._file_manager.path_on_disk(
                FileDestinations.LOCAL, print_job_file
            )
            path = self._file_manager.path_in_storage(
                FileDestinations.LOCAL, print_job_file
            )
            _, name = self._file_manager.split_path(FileDestinations.LOCAL, path)
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
        offsets=None,
        resends=None,
    ):
        self.set_state(state)
        self.set_job_data(job_data)
        self.set_progress(progress)
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
