import copy
import logging
import os

import octoprint.util as util
from octoprint.events import Events, eventManager
from octoprint.filemanager import valid_file_type
from octoprint.filemanager.destinations import FileDestinations
from octoprint.filemanager.storage import StorageCapabilities
from octoprint.printer import (
    CommunicationHealth,
    ErrorInformation,
    FirmwareInformation,
    PrinterFile,
    PrinterFilesMixin,
    UnknownScript,
)
from octoprint.printer.connection import ConnectedPrinter, ConnectedPrinterState
from octoprint.printer.job import JobProgress, PrintJob, UploadJob

from .serial_comm import MachineCom, baudrateList, serialList


class ConnectedSerialPrinter(ConnectedPrinter, PrinterFilesMixin):
    connector = "serial"
    name = "Serial Connection"

    storage_capabilities = StorageCapabilities(
        write_file=True, remove_file=True, metadata=True
    )

    @classmethod
    def connection_options(cls) -> dict:
        return {"port": serialList(), "baudrate": baudrateList()}

    STATE_LOOKUP = {
        MachineCom.STATE_CANCELLING: ConnectedPrinterState.CANCELLING,
        MachineCom.STATE_CLOSED: ConnectedPrinterState.CLOSED,
        MachineCom.STATE_CLOSED_WITH_ERROR: ConnectedPrinterState.CLOSED_WITH_ERROR,
        MachineCom.STATE_CONNECTING: ConnectedPrinterState.CONNECTING,
        MachineCom.STATE_DETECT_SERIAL: ConnectedPrinterState.DETECTING,
        MachineCom.STATE_ERROR: ConnectedPrinterState.ERROR,
        MachineCom.STATE_FINISHING: ConnectedPrinterState.FINISHING,
        MachineCom.STATE_OPEN_SERIAL: ConnectedPrinterState.CONNECTING,
        MachineCom.STATE_OPERATIONAL: ConnectedPrinterState.OPERATIONAL,
        MachineCom.STATE_PAUSED: ConnectedPrinterState.PAUSED,
        MachineCom.STATE_PAUSING: ConnectedPrinterState.PAUSING,
        MachineCom.STATE_PRINTING: ConnectedPrinterState.PRINTING,
        MachineCom.STATE_RESUMING: ConnectedPrinterState.RESUMING,
        MachineCom.STATE_STARTING: ConnectedPrinterState.STARTING,
        MachineCom.STATE_TRANSFERING_FILE: ConnectedPrinterState.TRANSFERING_FILE,
    }

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self._port = kwargs.get("port")
        self._baudrate = kwargs.get("baudrate")

        self._comm = None

        self._upload_callback = None
        self._last_position = None

    @property
    def current_storage_capabilities(self):
        return self.storage_capabilities.model_copy(
            update={"write_file": self.is_ready()}
        )

    @property
    def connection_parameters(self):
        parameters = super().connection_parameters
        parameters.update(
            {
                "port": self._port,
                "baudrate": self._baudrate,
            }
        )
        return parameters

    def connect(self, *args, **kwargs):
        if self._comm is not None:
            return

        from octoprint.logging.handlers import SerialLogHandler

        SerialLogHandler.arm_rollover()
        if not logging.getLogger("SERIAL").isEnabledFor(logging.DEBUG):
            # if serial.log is not enabled, log a line to explain that to reduce "serial.log is empty" in tickets...
            logging.getLogger("SERIAL").info(
                "serial.log is currently not enabled, you can enable it via Settings > Serial Connection > Log communication to serial.log"
            )

        self._comm = MachineCom(
            self._profile,
            port=self._port,
            baudrate=self._baudrate,
            callback=self,
        )
        self._comm.start()

    def disconnect(self, *args, **kwargs):
        if self._comm is not None:
            self._comm.close()

    def emergency_stop(self, *args, **kwargs):
        self.commands("M112", tags=kwargs.get("tags", set()))

    def job_on_hold(self, blocking=True, *args, **kwargs):
        if self._comm is None:
            raise RuntimeError("No connection to the printer")
        return self._comm.job_put_on_hold(blocking=blocking)

    def set_job_on_hold(self, value, blocking=True, *args, **kwargs):
        if self._comm is None:
            raise RuntimeError("No connection to the printer")
        return self._comm.set_job_on_hold(value, blocking=blocking)

    def repair_communication(self, *args, **kwargs):
        if self._comm is None:
            return

        self._comm.fakeOk()

    @property
    def communication_health(self) -> CommunicationHealth:
        if self._comm is None:
            return CommunicationHealth(errors=0, total=0)

        return CommunicationHealth(
            errors=self._comm.received_resends, total=self._comm.transmitted_lines
        )

    def commands(self, *commands, tags=None, force=False, **kwargs):
        """
        Sends one or more gcode commands to the printer.
        """
        if self._comm is None:
            return

        if len(commands) == 1 and isinstance(commands[0], (list, tuple)):
            commands = commands[0]

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
            tags=kwargs.get("tags"),
        )
        if not result and must_be_set:
            raise UnknownScript(name)

        event_end = f"GcodeScript{event_name}Finished"
        eventManager().fire(event_end, payload)

    def jog(self, axes, relative=True, speed=None, *args, **kwargs):
        command = "G0 {}".format(
            " ".join([f"{axis.upper()}{amt}" for axis, amt in axes.items()])
        )

        if speed is None:
            speed = min(self._profile["axes"][axis]["speed"] for axis in axes)

        if speed and not isinstance(speed, bool):
            command += f" F{speed}"

        if relative:
            commands = ["G91", command, "G90"]
        else:
            commands = ["G90", command]

        self.commands(*commands, tags=kwargs.get("tags", set()) | {"trigger:printer.jog"})

    def home(self, axes, *args, **kwargs):
        self.commands(
            "G91",
            "G28 {}".format(" ".join(f"{x.upper()}0" for x in axes)),
            "G90",
            tags=kwargs.get("tags", set) | {"trigger:printer.home"},
        )

    def extrude(self, amount, speed=None, *args, **kwargs):
        # Use specified speed (if any)
        max_e_speed = self._profile["axes"]["e"]["speed"]

        if speed is None:
            # No speed was specified so default to value configured in printer profile
            extrusion_speed = max_e_speed
        else:
            # Make sure that specified value is not greater than maximum as defined in printer profile
            extrusion_speed = min([speed, max_e_speed])

        self.commands(
            "G91",
            "M83",
            f"G1 E{amount} F{extrusion_speed}",
            "M82",
            "G90",
            tags=kwargs.get("tags", set()) | {"trigger:printer.extrude"},
        )

    def change_tool(self, tool, *args, **kwargs):
        tool = int(tool[len("tool") :])
        self.commands(
            f"T{tool}",
            tags=kwargs.get("tags", set()) | {"trigger:printer.change_tool"},
        )

    def set_temperature(self, heater, value, tags=None, *args, **kwargs):
        if heater == "tool":
            # set current tool, whatever that might be
            self.commands(f"M104 S{value}", tags=tags)

        elif heater.startswith("tool"):
            # set specific tool
            extruder_count = self._profile["extruder"]["count"]
            shared_nozzle = self._profile["extruder"]["sharedNozzle"]
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
        if self._comm is None:
            return

        self._comm.setTemperatureOffset(offsets)
        self._setOffsets(self._comm.getOffsets())

    @property
    def temperature_offsets(self) -> dict:
        if self._comm is None:
            return {}

        return copy.deepcopy(self._comm.getOffsets())

    def feed_rate(self, factor, tags=None, *args, **kwargs):
        self.commands(
            f"M220 S{factor}",
            tags=tags,
        )

    def flow_rate(self, factor, tags=None, *args, **kwargs):
        self.commands(
            f"M221 S{factor}",
            tags=tags,
        )

    def set_job(
        self,
        job: PrintJob,
        tags=None,
        user=None,
        *args,
        **kwargs,
    ):
        if self._comm is None or not self.is_ready():
            self._logger.info(
                "Cannot change job: printer not connected or currently busy"
            )
            return

        if job is None:
            # shortcut for deselecting
            self._comm.unselectFile()
            self._updateProgressData()
            self._setCurrentZ(None)
            super().set_job(job)
            return

        self._comm.selectFile(
            job.path if job.storage != FileDestinations.LOCAL else job.path_on_disk,
            job.storage != FileDestinations.LOCAL,
            user=user,
            tags=tags,
        )

    def supports_job(self, job: PrintJob) -> bool:
        if not valid_file_type(job.path, type="machinecode"):
            return False

        if job.storage not in (FileDestinations.LOCAL, FileDestinations.PRINTER):
            return False

        if job.storage != FileDestinations.PRINTER and not os.path.isfile(
            job.path_on_disk
        ):
            return False

        return True

    @property
    def job_progress(self) -> JobProgress:
        if self._comm is None:
            return None

        return JobProgress(
            job=self.current_job,
            progress=self._comm.getPrintProgress(),
            pos=self._comm.getPrintFilepos(),
            elapsed=self._comm.getPrintTime(),
            cleaned_elapsed=self._comm.getCleanedPrintTime(),
        )

    def get_file_position(self):
        if self._comm is None:
            return None

        with self._selectedFileMutex:
            if self._selectedFile is None:
                return None

        return self._comm.getFilePosition()

    def start_print(self, pos=None, user=None, tags=None, *args, **kwargs):
        self._comm.startPrint(
            pos=pos,
            user=user,
            tags=tags,
        )

    def pause_print(self, user=None, tags=None, *args, **kwargs):
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
            tags=tags,
        )

    def resume_print(self, user=None, tags=None, *args, **kwargs):
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
            tags=tags,
        )

    def cancel_print(self, user=None, tags=None, *args, **kwargs):
        """
        Cancel the current printjob.
        """
        if self._comm is None:
            return

        # tell comm layer to cancel - will also trigger our cancelled handler
        # for further processing
        self._comm.cancelPrint(user=user, tags=tags)

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

    def get_current_data(self, *args, **kwargs):  # TODO
        return util.thaw_frozendict(self._stateMonitor.get_current_data())

    def get_current_connection(self, *args, **kwargs):  # TODO
        if self._comm is None:
            return "Closed", None, None, None

        port, baudrate = self._comm.getConnection()
        return self._comm.getStateString(), port, baudrate, self._profile

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

    @property
    def cancel_position(self) -> dict:
        if self._comm is None:
            return None
        pos = self._comm.cancel_position
        return pos if pos is None else pos.as_dict()

    @property
    def pause_position(self) -> dict:
        if self._comm is None:
            return None
        pos = self._comm.pause_position
        return pos if pos is None else pos.as_dict()

    # ~~ sd file handling

    @property
    def printer_files_mounted(self):
        if self._comm is None:
            return False
        return self._comm.isSdReady()

    def refresh_printer_files(self, blocking=False, timeout=10, *args, **kwargs):
        self._comm.refreshSdFiles(blocking=blocking, timeout=timeout)

    def get_printer_files(self, refresh=False, *args, **kwargs):
        if not self.printer_files_mounted:
            return []

        if refresh:
            self.refresh_printer_files(blocking=True)

        files = self._comm.getSdFiles()

        result = []
        for f in files:
            pf = PrinterFile(path=f[0], display=f[2], size=f[1], date=f[3])
            if (
                pf.size is None
                and self._job
                and self._job.storage == FileDestinations.PRINTER
                and self._job.path == pf.path
            ):
                pf.size = self._job.size
            result.append(pf)
        return result

    def upload_printer_file(
        self, source, target, progress_callback: callable = None, *args, **kwargs
    ):
        if not self._comm or self._comm.isBusy() or not self._comm.isSdReady():
            self._logger.error("No connection to printer or printer is busy")
            return

        if progress_callback is not None:
            self._upload_callback = progress_callback

        try:
            return self._comm.startFileTransfer(
                source,
                target,
                special=not valid_file_type(target, "gcode"),
                tags=kwargs.get("tags", set()),
            )
        except Exception:
            self._logger.exception("Error while starting file transfer")
            if self._upload_callback:
                self._upload_callback(failed=True)

    def delete_printer_file(self, path, *args, **kwargs):
        if not self._comm or not self._comm.isSdReady():
            return
        self._comm.deleteSdFile(
            path,
            tags=kwargs.get("tags", set()) | {"trigger:printer.delete_sd_file"},
        )

    def mount_printer_files(self, *args, **kwargs):
        if not self._comm or self._comm.isSdReady():
            return
        self._comm.initSdCard(
            tags=kwargs.get("tags", set()) | {"trigger:printer.init_sd_card"}
        )

    def unmount_printer_files(self, *args, **kwargs):
        if not self._comm or not self._comm.isSdReady():
            return
        self._comm.releaseSdCard(
            tags=kwargs.get("tags", set()) | {"trigger:printer.release_sd_card"}
        )

    def refresh_sd_files(self, blocking=False, timeout=10, *args, **kwargs):
        if not self._comm or not self._comm.isSdReady():
            return

        self._comm.refreshSdFiles(
            blocking=blocking,
            timeout=timeout,
            tags=kwargs.get("tags", set()),
        )

    def sanitize_file_name(self, name, *args, **kwargs):
        if not self._comm:
            raise RuntimeError("Printer is not connected")

        return self._comm.get_remote_name(name)

    # ~~ comm.MachineComPrintCallback implementation

    def on_comm_log(self, message):
        self._listener.on_printer_logs(
            util.to_unicode(message, "utf-8", errors="replace")
        )

    def on_comm_temperature_update(self, tools, bed, chamber, custom=None):
        if custom is None:
            custom = {}

        temperatures = {}
        if tools:
            temperatures.update(
                {f"tool{tool}": copy.deepcopy(data) for tool, data in tools.items()}
            )
        if bed:
            temperatures["bed"] = copy.deepcopy(bed)
        if chamber:
            temperatures["chamber"] = copy.deepcopy(chamber)
        if custom:
            temperatures.update(
                {key: copy.deepcopy(data) for key, data in custom.items()}
            )

        self._listener.on_printer_temperature_update(temperatures)

    def on_comm_position_update(self, position, reason=None):
        self._listener.on_printer_position_changed(position, reason=reason)

    def on_comm_state_change(self, state):
        translated_state = self.STATE_LOOKUP.get(state)

        state_str = None
        error_str = None
        if self._comm is not None:
            state_str = self._comm.getStateString()
            error_str = self._comm.getErrorString()

        if translated_state in (
            ConnectedPrinterState.CLOSED,
            ConnectedPrinterState.CLOSED_WITH_ERROR,
        ):
            if self._comm is not None:
                self._comm = None

            self._firmware_info = None
            self._error_info = None

            super().set_job(None)

        self._listener.on_printer_state_changed(
            translated_state, state_str=state_str, error_str=error_str
        )

    def on_comm_error(self, error, reason, consequence=None, faq=None, logs=None):
        self._error_info = ErrorInformation(
            error=error, reason=reason, consequence=consequence, faq=faq, logs=logs
        )
        self._listener.on_printer_error(self._error_info)

    def on_comm_message(self, message):
        # intentionally disabled - we only use logs now
        pass

    def on_comm_progress(self):
        self._listener.on_printer_job_progress()
        if self._upload_callback:
            self._upload_callback(progress=int(self.job_progress.progress * 100))

    def on_comm_z_change(self, newZ):
        # intentionally disabled - event now gets triggered in comm, no more push upwards
        pass

    def on_comm_sd_state_change(self, sdReady):
        self._listener.on_printer_files_available(sdReady)

    def on_comm_sd_files(self, files):
        self._listener.on_printer_files_refreshed(files)

    def on_comm_file_selected(self, full_path, size, sd, user=None, data=None):
        job = PrintJob(
            storage=FileDestinations.PRINTER if sd else FileDestinations.LOCAL,
            path=full_path,
            size=size,
            owner=user,
        )

        super().set_job(job)
        self._listener.on_printer_job_changed(job, user=user, data=data)

    def on_comm_print_job_started(self, suppress_script=False, user=None):
        self._error_info = None
        self._listener.on_printer_job_started(suppress_script=suppress_script, user=user)

    def on_comm_print_job_done(self, suppress_script=False):
        self._listener.on_printer_job_done(suppress_script=suppress_script)

    def on_comm_print_job_cancelling(self, firmware_error=None, user=None):
        payload = {}
        if firmware_error:
            payload["firmwareError"] = firmware_error
        self._owner.trigger_printjob_event(
            Events.PRINT_CANCELLING, user=user, payload=payload
        )

    def on_comm_print_job_cancelled(self, suppress_script=False, user=None):
        self._listener.on_printer_job_cancelled(
            suppress_script=suppress_script, user=user
        )

    def on_comm_print_job_paused(self, suppress_script=False, user=None):
        self._listener.on_printer_job_paused(suppress_script=suppress_script, user=user)

    def on_comm_print_job_resumed(self, suppress_script=False, user=None):
        self._listener.on_printer_job_resumed(suppress_script=suppress_script, user=user)

    def on_comm_file_transfer_started(
        self, local_filename, remote_filename, filesize, user=None
    ):
        job = UploadJob(
            storage=FileDestinations.LOCAL,
            path=local_filename,
            size=filesize,
            owner=user,
            remote_path=remote_filename,
        )
        super().set_job(job)
        self._listener.on_printer_files_upload_start(job)
        if self._upload_callback:
            self._upload_callback(progress=0)

    def on_comm_file_transfer_done(
        self, local_filename, remote_filename, elapsed, failed=False
    ):
        self._listener.on_printer_files_upload_done(
            self.current_job, elapsed, failed=failed
        )
        if self._upload_callback:
            if failed:
                self._upload_callback(failed=True)
            else:
                self._upload_callback(done=True)
            self._upload_callback = None
        super().set_job(None)

    def on_comm_file_transfer_failed(self, local_filename, remote_filename, elapsed):
        self.on_comm_file_transfer_done(
            local_filename, remote_filename, elapsed, failed=True
        )

    def on_comm_force_disconnect(self):
        self._listener.on_printer_disconnected()

    def on_comm_record_fileposition(self, origin, name, pos):  # TODO
        self._listener.on_printer_record_recovery_position(self.current_job, pos)

    def on_comm_firmware_info(self, firmware_name, firmware_data):
        self._firmware_info = FirmwareInformation(name=firmware_name, data=firmware_data)
        self._listener.on_printer_firmware_info(self._firmware_info)
