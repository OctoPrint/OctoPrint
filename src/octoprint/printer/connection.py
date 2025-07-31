import enum
import logging
from collections.abc import Iterable
from gettext import gettext
from typing import Any, Optional, Union, cast

from octoprint.events import Events, eventManager
from octoprint.printer import (
    ConnectedPrinterMixin,
    ErrorInformation,
    FirmwareInformation,
    PrinterMixin,
)
from octoprint.printer.job import PrintJob, UploadJob


class ConnectedPrinterState(enum.Enum):
    DETECTING = gettext("Detecting")
    CONNECTING = gettext("Connecting")
    OPERATIONAL = gettext("Operational")
    STARTING = gettext("Starting")
    PRINTING = gettext("Printing")
    PAUSING = gettext("Pausing")
    PAUSED = gettext("Paused")
    RESUMING = gettext("Resuming")
    CANCELLING = gettext("Cancelling")
    FINISHING = gettext("Finishing")
    CLOSED = gettext("Offline")
    ERROR = gettext("Error")
    CLOSED_WITH_ERROR = gettext("Offline after error")
    TRANSFERRING_FILE = gettext("Transferring file to printer")


ERROR_STATES = {ConnectedPrinterState.ERROR, ConnectedPrinterState.CLOSED_WITH_ERROR}

CLOSED_STATES = {ConnectedPrinterState.CLOSED, ConnectedPrinterState.CLOSED_WITH_ERROR}

OPERATIONAL_STATES = {
    ConnectedPrinterState.OPERATIONAL,
    ConnectedPrinterState.STARTING,
    ConnectedPrinterState.PRINTING,
    ConnectedPrinterState.PAUSING,
    ConnectedPrinterState.PAUSED,
    ConnectedPrinterState.RESUMING,
    ConnectedPrinterState.CANCELLING,
    ConnectedPrinterState.FINISHING,
    ConnectedPrinterState.TRANSFERRING_FILE,
}

PRINTING_STATES = {
    ConnectedPrinterState.STARTING,
    ConnectedPrinterState.PRINTING,
    ConnectedPrinterState.PAUSING,
    ConnectedPrinterState.PAUSED,
    ConnectedPrinterState.RESUMING,
    ConnectedPrinterState.CANCELLING,
    ConnectedPrinterState.FINISHING,
}


class ConnectedPrinterListenerMixin:
    def on_printer_files_available(self, available: bool):
        pass

    def on_printer_files_refreshed(self, files: list):
        pass

    def on_printer_files_upload_start(self, job: UploadJob):
        pass

    def on_printer_files_upload_done(
        self, job: UploadJob, elapsed: float, failed: bool = False
    ):
        pass

    def on_printer_state_changed(
        self, state: ConnectedPrinterState, error_str: str = None
    ):
        pass

    def on_printer_position_changed(self, position, reason=None):
        pass

    def on_printer_temperature_update(self, temperatures):
        pass

    def on_printer_controls_updated(self, controls: list[dict[str, Any]]):
        pass

    def on_printer_logs(self, *lines: str):
        pass

    def on_printer_error(self, info: ErrorInformation):
        pass

    def on_printer_firmware_info(self, info: FirmwareInformation):
        pass

    def on_printer_disconnect(self):
        pass

    def on_printer_record_recovery_position(self, job: PrintJob, pos: int):
        pass

    def on_printer_job_changed(self, job: PrintJob, user: str = None, data: dict = None):
        pass

    def on_printer_job_started(self, suppress_script: bool = False, user: str = None):
        pass

    def on_printer_job_progress(self):
        pass

    def on_printer_job_done(self, suppress_script=False):
        pass

    def on_printer_job_cancelled(self, suppress_script=False, user=None):
        pass

    def on_printer_job_paused(self, suppress_script=False, user=None):
        pass

    def on_printer_job_resumed(self, suppress_script=False, user=None):
        pass


class ConnectedPrinterMetaClass(type):
    connectors: dict[str, "ConnectedPrinter"] = {}

    def __new__(mcs, name: str, bases: tuple[type, ...], args: dict[str, Any]):
        cls = type.__new__(mcs, name, bases, args)

        connector = cast(str, args.get("connector"))
        if connector:
            mcs.connectors[connector] = cls

        return cls

    def find(cls, connector: str) -> Optional["ConnectedPrinter"]:
        return cls.connectors.get(connector)

    def all(cls) -> Iterable["ConnectedPrinter"]:
        return cls.connectors.values()


class ConnectedPrinter(ConnectedPrinterMixin, metaclass=ConnectedPrinterMetaClass):
    connector = None
    name = None

    @classmethod
    def connection_options(cls) -> dict:
        return {}

    @classmethod
    def connection_preconditions_met(cls, params: dict[str, Any]) -> bool:
        """
        Returns True if a connection with the provided parameters *might* be possible.

        Note that an actual connection attempt might still fail even if this returns True,
        connectors will only check if the parameters meet any basic preconditions that can easily
        be checked.
        """
        return True

    def __init__(
        self,
        owner: PrinterMixin,
        listener: ConnectedPrinterListenerMixin = None,
        profile=None,
        *args,
        **kwargs,
    ):
        self._owner = owner
        if listener is None and isinstance(owner, ConnectedPrinterListenerMixin):
            self._listener = owner
        else:
            self._listener = listener

        self._state = ConnectedPrinterState.CLOSED
        self._profile = profile
        self._job = None
        self._firmware_info = None
        self._error_info = None

        self._printer_profile_manager = None

        self._logger = logging.getLogger(__name__)

    @property
    def current_job(self) -> PrintJob:
        return self._job

    def set_job(self, job: PrintJob, *args, **kwargs) -> None:
        self._job = job
        self._listener.on_printer_job_changed(job, user=kwargs.get("user"))

    @property
    def connection_parameters(self) -> dict:
        return {"connector": self.connector, "profile": self._profile}

    @property
    def firmware_info(self) -> Union[FirmwareInformation, None]:
        return self._firmware_info

    @firmware_info.setter
    def firmware_info(self, value: Union[FirmwareInformation, None]) -> None:
        self._firmware_info = value
        if self._firmware_info:
            eventManager().fire(
                Events.FIRMWARE_DATA,
                self._firmware_info.model_dump(exclude_none=True),
            )
            self._listener.on_printer_firmware_info(self._firmware_info)

    @property
    def error_info(self) -> Union[ErrorInformation, None]:
        return self._error_info

    @error_info.setter
    def error_info(self, value: Union[ErrorInformation, None]) -> None:
        self._error_info = value
        if self._error_info:
            eventManager().fire(
                Events.ERROR, self._error_info.model_dump(exclude_none=True)
            )
            self._listener.on_printer_error(self._error_info)

    @property
    def state(self) -> ConnectedPrinterState:
        return self._state

    @state.setter
    def state(self, value: ConnectedPrinterState) -> None:
        self.set_state(value)

    def set_state(self, state: ConnectedPrinterState, error: str = None):
        self._state = state
        self._listener.on_printer_state_changed(state, error_str=error)

    def get_state_string(self, state: ConnectedPrinterState = None):
        if state is None:
            state = self.state
        return state.value

    def is_closed_or_error(self, *args, **kwargs):
        return self.state in CLOSED_STATES or self.state in ERROR_STATES

    def is_operational(self, *args, **kwargs):
        return self.state in OPERATIONAL_STATES

    def is_printing(self, *args, **kwargs):
        return self.state in PRINTING_STATES

    def is_cancelling(self, *args, **kwargs):
        return self.state == ConnectedPrinterState.CANCELLING

    def is_pausing(self, *args, **kwargs):
        return self.state == ConnectedPrinterState.PAUSING

    def is_paused(self, *args, **kwargs):
        return self.state == ConnectedPrinterState.PAUSED

    def is_resuming(self, *args, **kwargs):
        return self.state == ConnectedPrinterState.RESUMING

    def is_finishing(self, *args, **kwargs):
        return self.state == ConnectedPrinterState.FINISHING

    def is_error(self, *args, **kwargs):
        return self.state == ConnectedPrinterState.ERROR

    def is_ready(self, *args, **kwargs):
        return self.is_operational()
