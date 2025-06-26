import enum
import logging

from octoprint.printer import (
    ConnectedPrinterMixin,
    ErrorInformation,
    FirmwareInformation,
    PrinterMixin,
)
from octoprint.printer.job import PrintJob, UploadJob


class ConnectedPrinterState(enum.Enum):
    DETECTING = "detecting"
    CONNECTING = "connecting"
    OPERATIONAL = "operational"
    STARTING = "starting"
    PRINTING = "printing"
    PAUSING = "pausing"
    PAUSED = "paused"
    RESUMING = "resuming"
    CANCELLING = "cancelling"
    FINISHING = "finishing"
    CLOSED = "closed"
    ERROR = "error"
    CLOSED_WITH_ERROR = "closed_with_error"
    TRANSFERING_FILE = "transfering_file"


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
        self, state: ConnectedPrinterState, state_str: str = None, error_str: str = None
    ):
        pass

    def on_printer_position_changed(self, position, reason=None):
        pass

    def on_printer_temperature_update(self, temperatures):
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
    connectors = {}

    def __new__(mcs, name, bases, args):
        cls = type.__new__(mcs, name, bases, args)

        connector = args.get("connector")
        if connector:
            mcs.connectors[connector] = cls

        return cls

    def find(cls, connector):
        return cls.connectors.get(connector)

    def all(cls):
        return cls.connectors.values()


class ConnectedPrinter(ConnectedPrinterMixin, metaclass=ConnectedPrinterMetaClass):
    connector = None
    name = None

    @classmethod
    def connection_options(cls) -> dict:
        return {}

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

        self._profile = profile
        self._job = None
        self._firmware_info = None
        self._error_info = None

        self._printer_profile_manager = None

        self._logger = logging.getLogger(__name__)

    @property
    def current_job(self):
        return self._job

    def set_job(self, job, *args, **kwargs):
        self._job = job

    @property
    def connection_parameters(self) -> dict:
        return {"connector": self.connector, "profile": self._profile}
