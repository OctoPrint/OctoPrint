"""
This module defines the interface for communicating with a connected printer.

The communication is in fact divided into two components, the :class:`PrinterInterface`, the
printer communication specific :class:`~octoprint.printer.connection.ConnectedPrinter`, and possibly deeper lying
communication components. However, plugins should only ever need to use the :class:`PrinterMixin` as the
abstracted version of the actual printer communication.

.. autoclass:: CommonPrinterMixin
   :members:

.. autoclass:: ConnectedPrinterMixin
   :members:

.. autoclass:: PrinterFilesMixin
   :members:

.. autoclass:: PrinterMixin
   : members:

.. autoclass:: PrinterCallback
   :members:
"""

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import re
from typing import IO, TYPE_CHECKING, Optional, Union

from pydantic import computed_field

from octoprint.filemanager.destinations import FileDestinations
from octoprint.filemanager.storage import (
    MetadataEntry,
    StorageCapabilities,
    StorageThumbnail,
)
from octoprint.printer.job import (
    DurationEstimate,
    FilamentEstimate,
    JobProgress,
    PrintJob,
)
from octoprint.schema import BaseModel
from octoprint.schema.config.controls import CustomControl, CustomControlContainer
from octoprint.settings import settings
from octoprint.util import deprecated, natural_key

if TYPE_CHECKING:
    from .connection import ConnectedPrinter


class CommunicationHealth(BaseModel):
    errors: int
    total: int

    @computed_field
    @property
    def ratio(self) -> float:
        if self.total == 0:
            return 0
        return float(self.errors) / float(self.total)


ERROR_FAQS = {
    "mintemp": ("mintemp",),
    "maxtemp": ("maxtemp",),
    "thermal-runaway": ("runaway",),
    "heating-failed": ("heating failed",),
    "probing-failed": (
        "probing failed",
        "bed leveling",
        "reference point",
        "bltouch",
    ),
}


class ErrorInformation(BaseModel):
    error: str
    reason: str
    consequence: str = None
    faq: str = Optional[None]
    logs: list[str] = Optional[None]


class FirmwareInformation(BaseModel):
    name: str
    data: dict


class ConnectedPrinterCapabilities(BaseModel):
    job_on_hold: bool = False
    temperature_offsets: bool = False


class CommonPrinterMixin:
    """
    The :class:`PrinterInterface` represents the developer interface to the :class:`~octoprint.printer.standard.Printer`
    instance.
    """

    valid_axes = ("x", "y", "z", "e")
    """Valid axes identifiers."""

    valid_tool_regex = re.compile(r"^(tool\d+)$")
    """Regex for valid tool identifiers."""

    valid_heater_regex = re.compile(r"^(tool\d*|bed|chamber)$")
    """Regex for valid heater identifiers."""

    valid_heater_regex_no_current = re.compile(r"^(tool\d+|bed|chamber)$")
    """Regex for valid heater identifiers without the current heater."""

    def connect(self, *args, **kwargs):
        """
        Connects to the printer, using the specified connection parameters. If a
        connection is already established, that connection will be closed prior to connecting anew with the provided
        parameters.
        """

    def disconnect(self, *args, **kwargs):
        """
        Disconnects from the printer. Does nothing if no connection is currently established.
        """

    def job_on_hold(self, blocking=True, *args, **kwargs):
        """
        Contextmanager that allows executing code while printing while making sure that no commands from the file
        being printed are continued to be sent to the printer. Note that this will only work for local files,
        NOT SD files.

        Example:

        .. code-block:: python

           with printer.job_on_hold():
               park_printhead()
               take_snapshot()
               send_printhead_back()

        It should be used sparingly and only for very specific situations (such as parking the print head somewhere,
        taking a snapshot from the webcam, then continuing). If you abuse this, you WILL cause print quality issues!

        A lock is in place that ensures that the context can only actually be held by one thread at a time. If you
        don't want to block on acquire, be sure to set ``blocking`` to ``False`` and catch the ``RuntimeException`` thrown
        if the lock can't be acquired.

        Args:
                blocking (bool): Whether to block while attempting to acquire the lock (default) or not
        """

    def set_job_on_hold(self, value, blocking=True, *args, **kwargs):
        """
        Setter for finer control over putting jobs on hold. Set to ``True`` to ensure that no commands from the file
        being printed are continued to be sent to the printer. Set to ``False`` to resume. Note that this will only
        work for local files, NOT SD files.

        Make absolutely sure that if you set this flag, you will always also unset it again. If you don't, the job will
        be stuck forever.

        Example:

        .. code-block:: python

           if printer.set_job_on_hold(True):
               try:
                   park_printhead()
                   take_snapshot()
                   send_printhead_back()
               finally:
                   printer.set_job_on_hold(False)

        Just like :func:`~octoprint.printer.PrinterInterface.job_on_hold` this should be used sparingly and only for
        very specific situations. If you abuse this, you WILL cause print quality issues!

        Args:
                value (bool): The value to set
                blocking (bool): Whether to block while attempting to set the value (default) or not

        Returns:
                (bool) Whether the value could be set successfully (True) or a timeout was encountered (False)
        """

    def repair_communication(self, *args, **kwargs):
        """
        Fakes an acknowledgment for the communication layer. If the communication between OctoPrint and the printer
        gets stuck due to lost "ok" responses from the server due to communication issues, this can be used to get
        things going again.
        """

    @property
    def communication_health(self) -> CommunicationHealth:
        return None

    @property
    def firmware_info(self) -> FirmwareInformation:
        return None

    @property
    def error_info(self) -> ErrorInformation:
        return None

    def commands(self, *commands, tags=None, force=False, **kwargs):
        """
        Sends the provided ``commands`` to the printer.

        Arguments:
            commands (str): The commands to send, one or more
            tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle
            force (bool): Whether to force sending of the command right away or allow queuing while printing
        """

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
        """
        Sends the script ``name`` to the printer.

        The script will be run through the template engine, the rendering context can be extended by providing a
        ``context`` with additional template variables to use.

        If the script is unknown, an :class:`UnknownScriptException` will be raised.

        Arguments:
            name (str): The name of the script to render.
            context (dict): An optional context of additional template variables to provide to the renderer.
            tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle

        Raises:
            UnknownScriptException: There is no script with name ``name``
        """

    def get_additional_controls(
        self,
    ) -> list[Union[CustomControl, CustomControlContainer]]:
        return []

    def jog(self, axes, relative=True, speed=None, tags=None, *args, **kwargs):
        """
        Jogs the specified printer ``axis`` by the specified ``amount`` in mm.

        Arguments:
            axes (dict): Axes and distances to jog, keys are axes ("x", "y", "z"), values are distances in mm
            relative (bool): Whether to interpret the distance values as relative (true, default) or absolute (false)
                coordinates
            speed (int, bool or None): Speed at which to jog (F parameter). If set to ``False`` no speed will be set
                specifically. If set to ``None`` (or left out) the minimum of all involved axes speeds from the printer
                profile will be used.
            tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle
        """

    def home(self, axes, tags=None, *args, **kwargs):
        """
        Homes the specified printer ``axes``.

        Arguments:
            axes (str, list): The axis or axes to home, each of which must converted to lower case must match one of
                "x", "y", "z" and "e"
            tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle
        """

    def extrude(self, amount, speed=None, tags=None, *args, **kwargs):
        """
        Extrude ``amount`` millimeters of material from the tool.

        Arguments:
            amount (int, float): The amount of material to extrude in mm
            speed (int, None): Speed at which to extrude (F parameter). If set to ``None`` (or left out)
            the maximum speed of E axis from the printer profile will be used.
            tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle
        """

    def change_tool(self, tool, tags=None, *args, **kwargs):
        """
        Switch the currently active ``tool`` (for which extrude commands will apply).

        Arguments:
            tool (str): The tool to switch to, matching the regex "tool[0-9]+" (e.g. "tool0", "tool1", ...)
            tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle
        """

    def set_temperature(self, heater, value, tags=None, *args, **kwargs):
        """
        Sets the target temperature on the specified ``heater`` to the given ``value`` in celsius.

        Arguments:
            heater (str): The heater for which to set the target temperature. Either "bed" for setting the bed
                temperature, "chamber" for setting the temperature of the heated enclosure or something matching the
                regular expression "tool[0-9]+" (e.g. "tool0", "tool1", ...) for the hotends of the printer. However,
                addressing components that are disabled or unconfigured in the printer profile will result in a
                "Suppressed command" error popup message.
            value (int, float): The temperature in celsius to set the target temperature to.
            tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle.
        """

    def set_temperature_offset(
        self, offsets: dict = None, tags: set = None, *args, **kwargs
    ):
        """
        Sets the temperature ``offsets`` to apply to target temperatures read from a GCODE file while printing.

        Arguments:
            offsets (dict): A dictionary specifying the offsets to apply. Keys must match the format for the ``heater``
                parameter to :func:`set_temperature`, so "bed" for the offset for the bed target temperature and
                "tool[0-9]+" for the offsets to the hotend target temperatures.
            tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle
        """

    @property
    def temperature_offsets(self) -> dict:
        return None

    def feed_rate(self, factor, tags=None, *args, **kwargs):
        """
        Sets the ``factor`` for the printer's feed rate.

        Arguments:
            factor (int, float): The factor for the feed rate to send to the firmware. Percentage expressed as either an
                int between 0 and 100 or a float between 0 and 1.
            tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle
        """

    def flow_rate(self, factor, tags=None, *args, **kwargs):
        """
        Sets the ``factor`` for the printer's flow rate.

        Arguments:
            factor (int, float): The factor for the flow rate to send to the firmware. Percentage expressed as either an
                int between 0 and 100 or a float between 0 and 1.
            tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle
        """

    def emergency_stop(self, *args, **kwargs):
        pass

    def get_files(self, *args, **kwargs) -> list:
        return []

    @property
    def current_job(self):
        return None

    @property
    def active_job(self):
        if self.is_printing() or self.is_pausing or self.is_paused():
            return self.current_job
        return None

    def set_job(
        self,
        job: PrintJob,
        tags: set[str] = None,
        *args,
        **kwargs,
    ):
        pass

    def start_print(self, tags: set[str] = None, params: dict = None, *args, **kwargs):
        """
        Starts printing the currently selected file. If no file is currently selected, does nothing.

        Arguments:
            tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle
        """

    def pause_print(self, tags: set[str] = None, params: dict = None, *args, **kwargs):
        """
        Pauses the current print job if it is currently running, does nothing otherwise.

        Arguments:
            tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle
        """

    def resume_print(self, tags: set[str] = None, params: dict = None, *args, **kwargs):
        """
        Resumes the current print job if it is currently paused, does nothing otherwise.

        Arguments:
            tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle
        """

    def toggle_pause_print(
        self, tags: set[str] = None, params: dict = None, *args, **kwargs
    ):
        """
        Pauses the current print job if it is currently running or resumes it if it is currently paused.

        Arguments:
            tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle
        """
        if self.is_printing():
            self.pause_print(*args, tags=tags, **kwargs)
        elif self.is_paused():
            self.resume_print(*args, tags=tags, **kwargs)

    def cancel_print(self, tags: set[str] = None, params: dict = None, *args, **kwargs):
        """
        Cancels the current print job.

        Arguments:
            tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle
        """

    def log_lines(self, *lines):
        """
        Logs the provided lines to the printer log and serial.log
        Args:
                *lines: the lines to log
        """

    def get_state_string(self, *args, **kwargs):
        """
        Returns:
             (str) A human readable string corresponding to the current communication state.
        """

    def get_state_id(self, *args, **kwargs) -> str:
        """
        Identifier of the current communication state.

        For possible values see :class:`~octoprint.printer.connection.ConnectedPrinterState`.

        Returns:
             (str) A unique identifier corresponding to the current communication state.
        """
        raise NotImplementedError()

    def get_error(self, *args, **kwargs):
        """
        Returns:
            (str) The current error
        """

    def get_current_data(self, *args, **kwargs):
        """
        Returns:
            (dict) The current state data.
        """

    def get_current_job(self, *args, **kwargs):
        """
        Returns:
            (dict) The data of the current job.
        """

    def get_current_temperatures(self, *args, **kwargs):
        """
        Returns:
            (dict) The current temperatures.
        """

    def get_temperature_history(self, *args, **kwargs):
        """
        Returns:
            (list) The temperature history.
        """

    def get_current_connection(self, *args, **kwargs):
        """
        Returns:
            (tuple) The current connection information as a 4-tuple ``(connection_string, port, baudrate, printer_profile)``.
                If the printer is currently not connected, the tuple will be ``("Closed", None, None, None)``.
        """

    def is_closed_or_error(self, *args, **kwargs):
        """
        Returns:
            (boolean) Whether the printer is currently disconnected and/or in an error state.
        """

    def is_operational(self, *args, **kwargs):
        """
        Returns:
            (boolean) Whether the printer is currently connected and available.
        """

    def is_printing(self, *args, **kwargs):
        """
        Returns:
            (boolean) Whether the printer is currently printing.
        """

    def is_cancelling(self, *args, **kwargs):
        """
        Returns:
            (boolean) Whether the printer is currently cancelling a print.
        """

    def is_finishing(self, *args, **kwargs):
        """
        Returns:
            (boolean) Whether the printer is currently finishing a print.
        """

    def is_pausing(self, *args, **kwargs):
        """
        Returns:
                (boolean) Whether the printer is currently pausing a print.
        """

    def is_paused(self, *args, **kwargs):
        """
        Returns:
            (boolean) Whether the printer is currently paused.
        """

    def is_resuming(self, *args, **kwargs):
        """
        Returns:
            (boolean) Whether the printer is currently resuming a print.
        """

    def is_error(self, *args, **kwargs):
        """
        Returns:
            (boolean) Whether the printer is currently in an error state.
        """

    def is_ready(self, *args, **kwargs):
        """
        Returns:
            (boolean) Whether the printer is currently operational and ready for new print jobs (not printing).
        """


class ConnectedPrinterMixin(CommonPrinterMixin):
    printer_capabilities = ConnectedPrinterCapabilities()

    def supports_job(self, job: PrintJob) -> bool:
        return False

    @property
    def current_printer_capabilities(self) -> ConnectedPrinterCapabilities:
        return self.printer_capabilities

    @property
    def job_progress(self) -> JobProgress:
        return None

    @property
    def cancel_position(self) -> dict:
        return None

    @property
    def pause_position(self) -> dict:
        return None

    def connect(self, *args, **kwargs):
        raise NotImplementedError()

    def disconnect(self, *args, **kwargs):
        raise NotImplementedError()

    def job_on_hold(self, blocking=True, *args, **kwargs):
        if self.current_printer_capabilities.job_on_hold:
            raise NotImplementedError()

    def set_job_on_hold(self, value, blocking=True, *args, **kwargs):
        if self.current_printer_capabilities.job_on_hold:
            raise NotImplementedError()


class PrinterFile(BaseModel):
    path: str
    display: str
    size: Optional[int] = None
    date: Optional[int] = None
    metadata: Optional[MetadataEntry] = None
    thumbnails: list[str] = []


class PrinterFilesError(Exception):
    pass


class PrinterFilesUnavailableError(PrinterFilesError):
    pass


class PrinterFilesConflict(PrinterFilesError):
    pass


class PrinterFilesMixin:
    storage_capabilities = StorageCapabilities()

    @property
    def printer_files_mounted(self) -> bool:
        return False

    @property
    def current_storage_capabilities(self) -> StorageCapabilities:
        return self.storage_capabilities

    def mount_printer_files(self, *args, **kwargs) -> None:
        pass

    def unmount_printer_files(self, *args, **kwargs) -> None:
        pass

    def refresh_printer_files(self, blocking=False, timeout=10, *args, **kwargs) -> None:
        pass

    def get_printer_file(self, path: str, refresh=False, *args, **kwargs) -> PrinterFile:
        return None

    def get_printer_files(
        self, refresh=False, recursive=False, *args, **kwargs
    ) -> list[PrinterFile]:
        return []

    def create_printer_folder(self, target: str, *args, **kwargs) -> str:
        pass

    def delete_printer_folder(
        self, target: str, recursive: bool = False, *args, **kwargs
    ) -> None:
        pass

    def copy_printer_folder(self, source: str, target: str, *args, **kwargs) -> str:
        pass

    def move_printer_folder(self, source: str, target: str, *args, **kwargs) -> str:
        pass

    def upload_printer_file(
        self,
        path_or_file: Union[str, IO],
        path: str,
        upload_callback: callable,
        *args,
        **kwargs,
    ) -> str:
        pass

    def download_printer_file(
        self,
        path: str,
        *args,
        **kwargs,
    ) -> IO:
        return None

    def delete_printer_file(self, path: str, *args, **kwargs) -> None:
        pass

    def copy_printer_file(self, source: str, target: str, *args, **kwargs) -> str:
        pass

    def move_printer_file(self, source: str, target: str, *args, **kwargs) -> str:
        pass

    def sanitize_file_name(self, name: str, *args, **kwargs) -> str:
        return name

    def get_printer_file_metadata(
        self, path: str, printer_file: PrinterFile = None, *args, **kwargs
    ) -> Optional[MetadataEntry]:
        if printer_file is None:
            printer_file = self.get_printer_file(path)
        if not printer_file:
            return None
        return MetadataEntry(display=printer_file.display)

    def set_printer_file_metadata(
        self, path: str, metadata: MetadataEntry, *args, **kwargs
    ) -> None:
        pass

    def has_thumbnail(self, path: str, *args, **kwargs) -> bool:
        return False

    def get_thumbnail(
        self, path: str, sizehint: str = None, *args, **kwargs
    ) -> Optional[StorageThumbnail]:
        return None

    def download_thumbnail(
        self, path: str, sizehint: str = None, *args, **kwargs
    ) -> Optional[tuple[StorageThumbnail, IO]]:
        return None

    def create_job(self, path: str, owner: str = None, params: dict = None) -> PrintJob:
        printer_file = self.get_printer_file(path)
        if not printer_file:
            return None

        duration_estimate = None
        filament_estimate = {}
        if self.storage_capabilities.metadata:
            meta = self.get_printer_file_metadata(path, printer_file=printer_file)
            if meta and meta.analysis:
                if meta.analysis.estimatedPrintTime:
                    duration_estimate = DurationEstimate(
                        estimate=meta.analysis.estimatedPrintTime, source="analysis"
                    )
                if meta.analysis.filament:
                    filament_estimate = {
                        k: FilamentEstimate(
                            length=v.length, volume=v.volume, weight=v.weight
                        )
                        for k, v in meta.analysis.filament.items()
                    }

        return PrintJob(
            storage="printer",
            path=path,
            display=printer_file.display,
            size=printer_file.size,
            date=printer_file.date,
            owner=owner,
            duration_estimate=duration_estimate,
            filament_estimate=filament_estimate,
            params=params,
        )


class PrinterMixin(CommonPrinterMixin):
    def connect(
        self,
        connector: str = None,
        parameters: dict = None,
        profile: str = None,
        *args,
        **kwargs,
    ):
        """
        Connects to the printer, using the specified serial ``port``, ``baudrate`` and printer ``profile``. If a
        connection is already established, that connection will be closed prior to connecting anew with the provided
        parameters.

        Arguments:
            connector (str): Name of the connector to use
            parameters (dict): Connection parameters to use against the connector
            profile (str): Name of the printer profile to use for this connection. If not provided, the default
                will be retrieved from the :class:`PrinterProfileManager`.
        """

    @property
    def current_connection(
        self,
    ) -> Optional["ConnectedPrinter"]:
        return None

    def set_job(
        self, job: PrintJob, print_after_select=False, pos=None, tags=None, user=None
    ):
        pass

    def register_callback(self, callback, *args, **kwargs):
        """
        Registers a :class:`PrinterCallback` with the instance.

        Arguments:
            callback (PrinterCallback): The callback object to register.
        """

    def unregister_callback(self, callback, *args, **kwargs):
        """
        Unregisters a :class:`PrinterCallback` from the instance.

        Arguments:
            callback (PrinterCallback): The callback object to unregister.
        """

    def send_initial_callback(self, callback):
        """
        Sends the initial printer update to :class:`PrinterCallback`.

        Arguments:
                callback (PrinterCallback): The callback object to send initial data to.
        """

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
        pass

    @property
    def connection_state(self) -> dict:
        return None

    @classmethod
    @deprecated(
        message="get_connection_option has been deprecated and will be removed in a future version. Please use ConnectedPrinter.all() in combination with get_connection_option on the returned ConnectPrinter instances instead.",
        since="1.12.0",
    )
    def get_connection_options(cls):
        from .connection import ConnectedPrinter

        serial_connector = ConnectedPrinter.find("serial")
        if serial_connector is None:
            return {
                "ports": [],
                "baudrates": [],
                "portPreference": None,
                "baudratePreference": None,
                "autoconnect": False,
            }

        preferred = {}
        if settings().get(["printerConnection", "preferred", "connector"]) == "serial":
            preferred = settings().get(["printerConnection", "preferred", "parameters"])

        connection_options = serial_connector.get_connection_options()
        ports = connection_options.get("ports", [])
        baudrates = connection_options.get("baudrates", [])

        return {
            "ports": sorted(ports, key=natural_key),
            "baudrates": sorted(baudrates, reverse=True),
            "portPreference": preferred.get("port"),
            "baudratePreference": preferred.get("baudrate"),
            "autoconnect": settings().getBoolean(["printerConnection", "autoconnect"]),
        }

    @deprecated(
        message="select_file has been deprecated and will be removed in a future version. Please use set_job instead.",
        includedoc="Replaced by :func:`PrinterInterface.set_job`",
        since="1.12.0",
    )
    def select_file(
        self,
        path,
        sd,
        printAfterSelect=False,
        pos=None,
        tags=None,
        user=None,
        *args,
        **kwargs,
    ):
        """
        Selects the specified ``path`` for printing, specifying if the file is to be found on the ``sd`` or not.
        Optionally can also directly start the print after selecting the file.

        Arguments:
            path (str): The path to select for printing. Either an absolute path or relative path to a  local file in
                the uploads folder or a filename on the printer's SD card.
            sd (boolean): Indicates whether the file is on the printer's SD card or not.
            printAfterSelect (boolean): Indicates whether a print should be started
                after the file is selected.
            tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle

        Raises:
            InvalidFileType: if the file is not a machinecode file and hence cannot be printed
            InvalidFileLocation: if an absolute path was provided and not contained within local storage or
                doesn't exist
        """
        from octoprint.server import fileManager

        job = fileManager.create_job(
            FileDestinations.PRINTER if sd else FileDestinations.LOCAL, path, owner=user
        )
        self.set_job(job, print_after_select=printAfterSelect, pos=pos, tags=tags)

    @deprecated(
        message="unselect_file has been deprecated and will be removed in a future version. Please use set_job instead.",
        includedoc="Replaced by :func:`PrinterInterface.set_job`",
        since="1.12.0",
    )
    def unselect_file(self, *args, **kwargs):
        """
        Unselects and currently selected file.
        """
        self.set_job(None)

    @deprecated(
        message="fake_ack has been renamed to repair_communication. This compatibility layer will be removed in a future version. Please use repair_communication instead.",
        includedoc="Replaced by :func:`PrinterInterface.repair_communication`",
        since="1.12.0",
    )
    def fake_ack(self, *args, **kwargs):
        self.repair_communication(*args, **kwargs)

    @deprecated(
        message="get_transport is non-functional. There is currently no alternative implementation. This compatibility layer will be removed in a future version.",
        includedoc="No longer functional",
        since="1.12.0",
    )
    def get_transport(self, *args, **kwargs):
        """
        Returns the communication layer's transport object, if a connection is currently established.

        Note that this doesn't have to necessarily be a :class:`serial.Serial` instance, it might also be something
        different, so take care to do instance checks before attempting to access any properties or methods.

        Returns:
            object: The communication layer's transport object
        """


PrinterInterface = PrinterMixin


class PrinterCallback:
    def on_printer_add_log(self, data):
        """
        Called when the :class:`PrinterInterface` receives a new communication log entry from the communication layer.

        Arguments:
            data (str): The received log line.
        """

    def on_printer_add_message(self, data):
        """
        Called when the :class:`PrinterInterface` receives a new message from the communication layer.

        Arguments:
            data (str): The received message.
        """

    def on_printer_add_temperature(self, data):
        """
        Called when the :class:`PrinterInterface` receives a new temperature data set from the communication layer.

        ``data`` is a ``dict`` of the following structure::

            tool0:
                actual: <temperature of the first hotend, in degC>
                target: <target temperature of the first hotend, in degC>
            ...
            bed:
                actual: <temperature of the bed, in degC>
                target: <target temperature of the bed, in degC>
            chamber:
                actual: <temperature of the chamber, in degC>
                target: <target temperature of the chamber, in degC>

        Arguments:
            data (dict): A dict of all current temperatures in the format as specified above
        """

    def on_printer_received_registered_message(self, name, output):
        """
        Called when the :class:`PrinterInterface` received a registered message, e.g. from a feedback command.

        Arguments:
            name (str): Name of the registered message (e.g. the feedback command)
            output (str): Output for the registered message
        """

    def on_printer_send_initial_data(self, data):
        """
        Called when registering as a callback with the :class:`PrinterInterface` to receive the initial data (state,
        log and temperature history etc) from the printer.

        ``data`` is a ``dict`` of the following structure::

            temps:
              - time: <timestamp of the temperature data point>
                tool0:
                    actual: <temperature of the first hotend, in degC>
                    target: <target temperature of the first hotend, in degC>
                ...
                bed:
                    actual: <temperature of the bed, in degC>
                    target: <target temperature of the bed, in degC>
              - ...
            logs: <list of current communication log lines>
            messages: <list of current messages from the firmware>

        Arguments:
            data (dict): The initial data in the format as specified above.
        """

    def on_printer_send_current_data(self, data):
        """
        Called when the internal state of the :class:`PrinterInterface` changes, due to changes in the printer state,
        temperatures, log lines, job progress etc. Updates via this method are guaranteed to be throttled to a maximum
        of 2 calls per second.

        ``data`` is a ``dict`` of the following structure::

            state:
                text: <current state string>
                flags:
                    operational: <whether the printer is currently connected and responding>
                    printing: <whether the printer is currently printing>
                    closedOrError: <whether the printer is currently disconnected and/or in an error state>
                    error: <whether the printer is currently in an error state>
                    paused: <whether the printer is currently paused>
                    ready: <whether the printer is operational and ready for jobs>
                    sdReady: <whether an SD card is present>
            job:
                file:
                    name: <name of the file>,
                    size: <size of the file in bytes>,
                    origin: <origin of the file, "local" or "printer">,
                    date: <last modification date of the file>
                estimatedPrintTime: <estimated print time of the file in seconds>
                lastPrintTime: <last print time of the file in seconds>
                filament:
                    length: <estimated length of filament needed for this file, in mm>
                    volume: <estimated volume of filament needed for this file, in ccm>
            progress:
                completion: <progress of the print job in percent (0-100)>
                filepos: <current position in the file in bytes>
                printTime: <current time elapsed for printing, in seconds>
                printTimeLeft: <estimated time left to finish printing, in seconds>
            currentZ: <current position of the z axis, in mm>
            offsets: <current configured temperature offsets, keys are "bed" or "tool[0-9]+", values the offset in degC>

        Arguments:
            data (dict): The current data in the format as specified above.
        """


class UnknownScript(Exception):
    def __init__(self, name, *args, **kwargs):
        self.name = name


class InvalidFileLocation(Exception):
    pass


class InvalidFileType(Exception):
    pass
