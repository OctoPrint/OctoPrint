__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import contextlib
import copy
import logging

from octoprint.comm.transport import TransportListener, TransportState
from octoprint.plugin import plugin_manager
from octoprint.settings import SubSettings
from octoprint.util import CountedEvent, to_unicode
from octoprint.util.listener import ListenerAware

_registry = {}


def register_protocols():
    from .reprap import ReprapGcodeProtocol

    logger = logging.getLogger(__name__)

    # stock protocols
    register_protocol(ReprapGcodeProtocol)

    # more protocols provided by plugins
    hooks = plugin_manager().get_hooks("octoprint.comm.protocol.register")
    for name, hook in hooks.items():
        try:
            protocols = hook()
            for protocol in protocols:
                try:
                    register_protocol(protocol)
                except Exception:
                    logger.exception(
                        "Error while registering protocol class {} for plugin {}".format(
                            protocol, name
                        )
                    )
        except Exception:
            logger.exception(
                "Error executing octoprint.comm.protocol.register hook for plugin {}".format(
                    name
                )
            )


def register_protocol(protocol_class):
    if not hasattr(protocol_class, "key"):
        raise ValueError("Protocol class {} is missing key".format(protocol_class))
    _registry[protocol_class.key] = protocol_class


def lookup_protocol(key):
    return _registry.get(key)


def all_protocols():
    return _registry.values()


class ProtocolErrorStats(ListenerAware):
    def __init__(self, **kwargs):
        super().__init__()

        self._rx = 0
        self._rx_errors = 0
        self._rx_error_rate = 0
        self._rx_arm = -1
        self._rx_threshold = 0
        self._rx_triggered = False

        self._tx = 0
        self._tx_errors = 0
        self._tx_error_rate = 0
        self._tx_arm = -1
        self._tx_threshold = 0
        self._tx_triggered = False

        self.reset(**kwargs)

    def reset(
        self, rx_arm=None, rx_threshold=None, tx_arm=None, tx_threshold=None, **kwargs
    ):
        self._rx = self._rx_errors = self._rx_error_rate = 0
        self._rx_triggered = False
        if rx_arm is not None:
            self._rx_arm = rx_arm
        if rx_threshold is not None:
            self._rx_threshold = rx_threshold

        self._tx = self._tx_errors = self._tx_error_rate = 0
        self._tx_triggered = False
        if tx_arm is not None:
            self._tx_arm = tx_arm
        if tx_threshold is not None:
            self._tx_threshold = tx_threshold

    @property
    def rx(self):
        return self._rx

    @property
    def rx_errors(self):
        return self._rx_errors

    @property
    def rx_error_rate(self):
        return self._rx_error_rate

    @property
    def rx_error_threshold(self):
        return self._rx_threshold

    @property
    def tx(self):
        return self._tx

    @property
    def tx_errors(self):
        return self._tx_errors

    @property
    def tx_error_rate(self):
        return self._tx_error_rate

    @property
    def tx_error_threshold(self):
        return self._tx_threshold

    def inc_rx(self):
        self._rx += 1
        if self._rx > self._rx_arm:
            self.notify_listeners("on_protocol_stats_rx_armed", self)

    def inc_rx_errors(self):
        self._rx_errors += 1
        self._rx_error_rate = (self._rx_errors / self._rx) if self._rx > 0 else 0
        if (
            self._rx > self._rx_arm
            and self._rx_error_rate > self._rx_threshold
            and not self._rx_triggered
        ):
            self._rx_triggered = True
            self.notify_listeners("on_protocol_stats_rx_triggered", self)

    def inc_tx(self):
        self._tx += 1
        if self._tx > self._tx_arm:
            self.notify_listeners("on_protocol_stats_tx_armed", self)

    def inc_tx_errors(self):
        self._tx_errors += 1
        self._tx_error_rate = (self._tx_errors / self._tx) if self._tx > 0 else 0
        if (
            self._tx > self._tx_arm
            and self._tx_error_rate > self._tx_threshold
            and not self._tx_triggered
        ):
            self._tx_triggered = True
            self.notify_listeners("on_protocol_stats_tx_triggered", self)


class ProtocolErrorStatsListener:
    def on_protocol_stats_tx_armed(self, stats):
        pass

    def on_protocol_stats_tx_triggered(self, stats):
        pass

    def on_protocol_stats_rx_armed(self, stats):
        pass

    def on_protocol_stats_rx_triggered(self, stats):
        pass


class Protocol(ListenerAware, TransportListener, ProtocolErrorStatsListener):

    name = None
    key = None

    supported_jobs = []

    @classmethod
    def get_connection_options(cls):
        return []

    @classmethod
    def get_settings_defaults(cls):
        return {}

    def __init__(self, *args, **kwargs):
        super(Protocol, self).__init__()

        self._logger = logging.getLogger(__name__)
        self._connection_logger = logging.getLogger("CONNECTION")
        self._state = ProtocolState.DISCONNECTED
        self._error = None
        self._stats = ProtocolErrorStats()

        self._printer_profile = kwargs.get("printer_profile")
        self._plugin_manager = kwargs.get("plugin_manager")
        self._event_bus = kwargs.get("event_bus")
        self._settings = kwargs.get("settings")
        if not isinstance(self._settings, ProtocolSettings):
            self._settings = ProtocolSettings(self._settings, self)

        self._job = None
        self._transport = None

        self._job_on_hold = CountedEvent()

        self._args = {}

    def args(self):
        return copy.deepcopy(self._args)

    def set_current_args(self, **value):
        self._args = copy.deepcopy(value)

    @contextlib.contextmanager
    def job_put_on_hold(self, blocking=True):
        if not self._job_on_hold.acquire(blocking=blocking):
            raise RuntimeError("Could not acquire job_on_hold lock")

        self._job_on_hold.set()
        try:
            yield
        finally:
            self._job_on_hold.clear()
            if self._job_on_hold.counter == 0:
                self._job_on_hold_cleared()
            self._job_on_hold.release()

    @property
    def job_on_hold(self):
        return self._job_on_hold.counter > 0

    def set_job_on_hold(self, value, blocking=True):
        if not self._job_on_hold.acquire(blocking=blocking):
            return False

        try:
            if value:
                self._job_on_hold.set()
            else:
                self._job_on_hold.clear()
                if self._job_on_hold.counter == 0:
                    self._job_on_hold_cleared()
        finally:
            self._job_on_hold.release()

        return True

    @property
    def transport(self):
        return self._transport

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, new_state):
        old_state = self._state
        if old_state == new_state:
            return

        self._state = new_state

        name = "_on_switching_state_{}".format(new_state)
        method = getattr(self, name, None)
        if method is not None:
            method(old_state)

        self.process_protocol_log(
            "--- Protocol state changed from '{}' to '{}'".format(old_state, new_state)
        )
        self.notify_listeners("on_protocol_state", self, old_state, new_state)

        name = "_on_switched_state_{}".format(new_state)
        method = getattr(self, name, None)
        if method is not None:
            method(old_state)

    @property
    def error(self):
        return self._error

    @error.setter
    def error(self, new_error):
        self._error = new_error

    @property
    def stats(self):
        return self._stats

    def connect(self, transport, transport_args=None, transport_kwargs=None):
        if self.state not in (
            ProtocolState.DISCONNECTED,
            ProtocolState.DISCONNECTED_WITH_ERROR,
        ):
            raise ProtocolAlreadyConnectedError("Already connected, disconnect first")

        self.process_protocol_log(
            "--- Protocol {} connecting via transport {}...".format(self, transport)
        )

        if transport_args is None:
            transport_args = []
        if transport_kwargs is None:
            transport_kwargs = {}

        self._transport = transport
        self._transport.register_listener(self)

        if self._transport.state == TransportState.DISCONNECTED:
            self._transport.connect(*transport_args, **transport_kwargs)
        self.state = ProtocolState.CONNECTING

    def disconnect(self, error=False, wait=True, timeout=10.0):
        if self.state in (
            ProtocolState.DISCONNECTED,
            ProtocolState.DISCONNECTED_WITH_ERROR,
            ProtocolState.DISCONNECTING,
            ProtocolState.DISCONNECTING_WITH_ERROR,
        ):
            raise ProtocolNotConnectedError("Already disconnecting or disconnected")

        if error:
            self.state = ProtocolState.DISCONNECTING_WITH_ERROR
        else:
            self.state = ProtocolState.DISCONNECTING

        self.process_protocol_log(
            "--- Protocol {} disconnecting from transport {}...".format(
                self, self._transport
            )
        )

        if wait:
            self.join(timeout=timeout)

        self._transport.unregister_listener(self)
        if self._transport.state == TransportState.CONNECTED:
            try:
                self._transport.disconnect(wait=wait)
            except Exception:
                self._logger.exception(
                    "Error while disconnecting from transport {}".format(self._transport)
                )
                error = True

        if error:
            self.state = ProtocolState.DISCONNECTED_WITH_ERROR
        else:
            self.state = ProtocolState.DISCONNECTED

    def process(self, job, position=0, user=None, tags=None, **kwargs):
        if not job.can_process(self):
            raise ValueError(
                "Job {} cannot be processed with protocol {}".format(job, self)
            )

        self._job = job
        self._job.register_listener(self)

        self.state = ProtocolState.STARTING
        self.notify_listeners(
            "on_protocol_job_starting", self, self._job, user=user, tags=tags, **kwargs
        )
        self._job.process(self, position=position, user=user, tags=tags, **kwargs)

    def pause_processing(self, user=None, tags=None, **kwargs):
        if self._job is None or self.state not in ProtocolState.PROCESSING_STATES:
            return
        self.state = ProtocolState.PAUSING
        self.notify_listeners(
            "on_protocol_job_pausing", self, self._job, user=user, tags=tags, **kwargs
        )
        self._job.pause(user=user, tags=tags)

    def resume_processing(self, user=None, tags=None, **kwargs):
        if self._job is None or self.state not in (
            ProtocolState.PAUSING,
            ProtocolState.PAUSED,
        ):
            return
        self.state = ProtocolState.RESUMING
        self.notify_listeners(
            "on_protocol_job_resuming", self, self._job, user=user, tags=tags, **kwargs
        )
        self._job.resume(user=user, tags=tags, **kwargs)

    def cancel_processing(self, error=False, user=None, tags=None, **kwargs):
        if self._job is not None and self.state in ProtocolState.PROCESSING_STATES + (
            ProtocolState.PAUSED,
        ):
            self.state = ProtocolState.CANCELLING
            self.notify_listeners(
                "on_protocol_job_cancelling",
                self,
                self._job,
                user=user,
                tags=tags,
                **kwargs
            )
            self._job.cancel(error=error, user=user, tags=tags, **kwargs)

    def can_send(self):
        return True

    def send_commands(self, command_type=None, tags=None, *commands):
        pass

    def send_script(self, script, context=None, user=None, tags=None):
        """
        Sends the specified script/the GCODE script with the specified name.

        Args:
                script (GcodeScript or unicode): Script or name of the script to send
                context (dict): Additional render context
                user (str): The user on whose behalf the script is being sent. May be None
                tags (set): And tags to send with the script commands. May be None
        """
        pass

    def repair(self):
        pass

    def join(self, timeout=None):
        pass

    def on_job_started(self, job, *args, **kwargs):
        self.notify_listeners("on_protocol_job_started", self, job, *args, **kwargs)
        self.state = ProtocolState.PROCESSING

    def on_job_paused(self, job, *args, **kwargs):
        self.notify_listeners("on_protocol_job_paused", self, job, *args, **kwargs)
        self.state = ProtocolState.PAUSED

    def on_job_resumed(self, job, *args, **kwargs):
        self.notify_listeners("on_protocol_job_resumed", self, job, *args, **kwargs)
        self.state = ProtocolState.PROCESSING

    def on_job_done(self, job, *args, **kwargs):
        self.notify_listeners("on_protocol_job_done", self, job, *args, **kwargs)
        self._job_processed(job)

    def on_job_cancelled(self, job, *args, **kwargs):
        self.notify_listeners("on_protocol_job_cancelled", self, job, *args, **kwargs)
        self._job_processed(job)

    def on_job_failed(self, job, *args, **kwargs):
        self.notify_listeners("on_protocol_job_failed", self, job, *args, **kwargs)
        self._job_processed(job)

    def _job_processed(self, job, *args, **kwargs):
        self._job.unregister_listener(self)
        self.state = ProtocolState.CONNECTED

    def on_transport_disconnected(self, transport, error=None):
        self.disconnect(error=error is not None)

    def on_transport_log_received_data(self, transport, data):
        message = to_unicode(data, errors="replace").strip()
        self.notify_listeners("on_protocol_log_received", self, message)

        message = "<<< {}".format(message)
        self.process_protocol_log(message)

    def on_transport_log_sent_data(self, transport, data):
        message = to_unicode(data, errors="replace").strip()
        self.notify_listeners("on_protocol_log_sent", self, message)

        message = ">>> {}".format(message)
        self.process_protocol_log(message)

    def on_transport_log_message(self, transport, data):
        message = to_unicode(data, errors="replace").strip()
        self.notify_listeners("on_protocol_log_message", self, message)

        message = "--- {}".format(message)
        self.process_protocol_log(message)

    def process_protocol_log(self, message):
        self._connection_logger.debug(message)
        self.notify_listeners("on_protocol_log", self, message)

    def _job_on_hold_cleared(self):
        pass

    def __str__(self):
        return self.__class__.__name__


class ProtocolState:
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    STARTING = "starting"
    PROCESSING = "processing"
    FINISHING = "finishing"
    CANCELLING = "cancelling"
    PAUSING = "pausing"
    RESUMING = "resuming"
    PAUSED = "paused"
    ERROR = "error"
    DISCONNECTING_WITH_ERROR = "disconnecting_with_error"
    DISCONNECTED_WITH_ERROR = "disconnected_with_error"

    PROCESSING_STATES = (STARTING, PROCESSING, CANCELLING, PAUSING, RESUMING, FINISHING)
    OPERATIONAL_STATES = (CONNECTED, PAUSED) + PROCESSING_STATES


class ProtocolSettings(SubSettings):
    def __init__(self, settings, protocol):
        SubSettings.__init__(
            self,
            settings,
            ["comm", "protocol", protocol.key],
            defaults=protocol.get_settings_defaults(),
        )


class ProtocolAlreadyConnectedError(Exception):
    pass


class ProtocolNotConnectedError(Exception):
    pass


class ThreeAxisProtocolMixin:
    def move(
        self, x=None, y=None, z=None, feedrate=None, relative=False, *args, **kwargs
    ):
        pass

    def home(self, x=False, y=False, z=False, *args, **kwargs):
        pass

    def set_feedrate_multiplier(self, multiplier, *args, **kwargs):
        pass


class HeaterProtocolMixin:
    def set_temperature(self, heater, temperature, wait=False, *args, **kwargs):
        pass

    def set_temperature_offset(self, heater, offset, *args, **kwargs):
        pass

    def get_temperature_offsets(self):
        return {}


class MultiToolProtocolMixin:
    def change_tool(self, tool, *args, **kwargs):
        pass


class Fdm3dPrinterProtocolMixin(
    ThreeAxisProtocolMixin, HeaterProtocolMixin, MultiToolProtocolMixin
):
    def move(
        self,
        x=None,
        y=None,
        z=None,
        e=None,
        feedrate=None,
        relative=False,
        *args,
        **kwargs
    ):
        pass

    def set_extrusion_multiplier(self, multiplier, *args, **kwargs):
        pass


class FanControlProtocolMixin:
    def set_fan_speed(self, speed, *args, **kwargs):
        pass

    def get_fan_speed(self, speed, *args, **kwargs):
        pass


class MotorControlProtocolMixin:
    def enable_motors(self, *args, **kwargs):
        self.set_motor_state(True)

    def disable_motors(self, *args, **kwargs):
        self.set_motor_state(False)

    def set_motor_state(self, enabled, *args, **kwargs):
        pass

    def get_motor_state(self, *args, **kwargs):
        pass


class PowerControlProtocolMixin:
    def enable_power(self, *args, **kwargs):
        self.set_power_state(True)

    def disable_power(self, *args, **kwargs):
        self.set_power_state(False)

    def set_power_state(self, enabled, *args, **kwargs):
        pass

    def get_power_state(self, *args, **kwargs):
        return None


class FileAwareProtocolMixin:
    def init_file_storage(self, *args, **kwargs):
        pass

    def eject_file_storage(self, *args, **kwargs):
        pass

    def list_files(self, *args, **kwargs):
        pass

    def start_file_print(self, name, position=0, tags=None, *args, **kwargs):
        pass

    def pause_file_print(self, *args, **kwargs):
        pass

    def resume_file_print(self, *args, **kwargs):
        pass

    def get_file_print_status(self, *args, **kwargs):
        pass

    def start_file_print_status_monitor(self, *args, **kwargs):
        pass

    def stop_file_print_status_monitor(self, *args, **kwargs):
        pass


class FileManagementProtocolMixin(FileAwareProtocolMixin):
    def delete_file(self, name, *args, **kwargs):
        pass


class FileStreamingProtocolMixin(FileManagementProtocolMixin):
    def record_file(self, name, *args, **kwargs):
        pass

    def stop_recording_file(self, *args, **kwargs):
        pass


class ProtocolListener:
    def on_protocol_state(self, protocol, old_state, new_state, *args, **kwargs):
        pass

    def on_protocol_temperature(self, protocol, temperatures, *args, **kwargs):
        pass

    def on_protocol_log(self, protocol, message, *args, **kwargs):
        pass

    def on_protocol_log_received(self, protocol, message, *args, **kwargs):
        pass

    def on_protocol_log_sent(self, protocol, message, *args, **kwargs):
        pass

    def on_protocol_log_message(self, protocol, message, *args, **kwargs):
        pass

    def on_protocol_reset(self, protocol, idle, *args, **kwargs):
        pass

    def on_protocol_job_started(self, protocol, job, *args, **kwargs):
        pass

    def on_protocol_job_pausing(self, protocol, job, *args, **kwargs):
        pass

    def on_protocol_job_paused(self, protocol, job, *args, **kwargs):
        pass

    def on_protocol_job_resuming(self, protocol, job, *args, **kwargs):
        pass

    def on_protocol_job_resumed(self, protocol, job, *args, **kwargs):
        pass

    def on_protocol_job_cancelling(self, protocol, job, *args, **kwargs):
        pass

    def on_protocol_job_cancelled(self, protocol, job, *args, **kwargs):
        pass

    def on_protocol_job_finishing(self, protocol, job, *args, **kwargs):
        pass

    def on_protocol_job_done(self, protocol, job, *args, **kwargs):
        pass

    def on_protocol_job_failed(self, protocol, job, *args, **kwargs):
        pass


class FileAwareProtocolListener:
    def on_protocol_file_storage_available(self, protocol, available, *args, **kwargs):
        pass

    def on_protocol_file_list(self, protocol, files, *args, **kwargs):
        pass

    def on_protocol_file_status(self, protocol, pos, total, *args, **kwargs):
        pass

    def on_protocol_file_print_started(
        self, protocol, name, long_name, size, *args, **kwargs
    ):
        pass

    def on_protocol_file_print_done(self, protocol, *args, **kwargs):
        pass

    def on_protocol_file_print_paused(self, protocol, *args, **kwargs):
        pass

    def on_protocol_file_print_resumed(self, protocol, *args, **kwargs):
        pass


class PositionAwareProtocolListener:
    def on_protocol_position_all_update(self, protocol, position, *args, **kwargs):
        pass

    def on_protocol_position_z_update(self, protocol, z, *args, **kwargs):
        pass


class FirmwareDataAwareProtocolListener:
    def on_protocol_firmware_info(self, protocol, info, *args, **kwargs):
        pass

    def on_protocol_firmware_capability(
        self, protocol, capability, enabled, capabilities, *args, **kwargs
    ):
        pass
