__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import copy
import logging
import time
from typing import Union

from octoprint.plugin import plugin_manager
from octoprint.settings import SubSettings
from octoprint.settings.parameters import get_param_dict, register_settings_overlay
from octoprint.util.listener import ListenerAware

SETTINGS_PATH = ["connection", "transports"]


_registry = {}


def register_transports(settings):
    from .serialtransport import SerialTransport
    from .sockettransport import SerialOverTcpTransport, TcpTransport

    # stock transports
    for transport in (
        SerialTransport,
        TcpTransport,
        SerialOverTcpTransport,
    ):
        register_transport(transport, settings, SETTINGS_PATH)

    # more transports provided by plugins
    logger = logging.getLogger(__name__)
    hooks = plugin_manager().get_hooks("octoprint.comm.transport.register")
    for name, hook in hooks.items():
        try:
            transports = hook()
            for transport in transports:
                try:
                    register_transport(transport, settings, SETTINGS_PATH)
                except Exception:
                    logger.exception(
                        "Error while registering transport class {} for plugin {}".format(
                            transport, name
                        )
                    )
        except Exception:
            logger.exception(
                "Error executing octoprint.comm.transport.register hook for plugin {}".format(
                    name
                )
            )


def register_transport(transport_class, settings, path):
    logger = logging.getLogger(__name__)

    if not hasattr(transport_class, "key"):
        raise ValueError(f"Transport class {transport_class} is missing key")

    # register settings overlay
    overlay = register_transport_overlay(transport_class, settings, path)
    logger.debug(
        "Registered settings overlay for transport {} under key {}".format(
            transport_class, overlay
        )
    )

    # register transport
    key = transport_class.key
    overrides = settings.get(path, merged=True)
    _registry[key] = (
        transport_class,
        transport_class.with_settings(**overrides.get(key, {})),
    )


def register_transport_overlay(transport_class, settings, path):
    if not hasattr(transport_class, "key"):
        raise ValueError(f"Transport class {transport_class} is missing key")
    if not hasattr(transport_class, "settings"):
        raise ValueError(f"Transport class {transport_class} is missing settings")

    params = transport_class.settings
    return register_settings_overlay(settings, path + [transport_class.key], params)


def refresh_transports(settings, path):
    for key in _registry:
        refresh_transport(key, settings, path)


def refresh_transport(key, settings, path):
    transport_class, _ = _registry[key]
    overrides = settings.get(path, merged=True)
    _registry[key] = (
        transport_class,
        transport_class.with_settings(**overrides.get(key, {})),
    )


def lookup_transport(key):
    return _registry.get(key, (None, None))[1]


def all_transports():
    return map(lambda x: x[1], _registry.values())


class Transport(ListenerAware):
    """
    Transport base class.

    Implement at least ``in_waiting``, ``do_read`` and ``do_write``.
    """

    name = None
    key = None

    message_integrity = False

    settings = []

    @classmethod
    def with_settings(cls, **settings):
        return type(
            cls.__name__ + "WithSettings",
            (cls,),
            settings,
        )

    @classmethod
    def get_connection_options(cls):
        return []

    def __init__(self, *args, **kwargs):
        super().__init__()

        self._logger = logging.getLogger(__name__)
        self._state = TransportState.DISCONNECTED
        self._args = {}

        self._printer_profile = kwargs.get("printer_profile")
        self._plugin_manager = kwargs.get("plugin_manager")
        self._event_bus = kwargs.get("event_bus")
        self._settings = kwargs.get("settings")
        if not isinstance(self._settings, TransportSettings):
            self._settings = TransportSettings(self._settings, self)

    def args(self):
        return copy.deepcopy(self._args)

    def set_current_args(self, **value):
        self._args = copy.deepcopy(value)

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        old_state = self.state
        self._state = value
        self.notify_listeners(
            "on_transport_log_message",
            self,
            f"Transport state changed from '{old_state}' to '{value}'",
        )

    def can_connect(self, **params):
        options = self.get_connection_options()
        param_dict = get_param_dict(params, options)
        return self.check_connection(**param_dict)

    def connect(self, **params):
        if self.state == TransportState.CONNECTED:
            raise TransportAlreadyConnectedError("Already connected, disconnect first")
        options = self.get_connection_options()
        param_dict = get_param_dict(params, options)

        self.state = TransportState.CONNECTING
        if self.create_connection(**param_dict):
            self.signal_connected()

    def signal_connected(self):
        self.state = TransportState.CONNECTED
        self.notify_listeners("on_transport_connected", self)

    def disconnect(self, error=None, wait=True):
        if self.state == TransportState.DISCONNECTED:
            raise TransportNotConnectedError("Already disconnected")

        success = self.drop_connection(wait=wait)
        if not success and not error:
            error = "Error disconnecting transport"

        if error:
            self.state = TransportState.DISCONNECTED_WITH_ERROR
            self.notify_listeners("on_transport_log_message", self, error)
        else:
            self.state = TransportState.DISCONNECTED

        self.notify_listeners("on_transport_disconnected", self, error=error)

    def create_connection(self, *args, **kwargs):
        return True

    def drop_connection(self, wait=True):
        return True

    def check_connection(self, *args, **kwargs):
        return True

    def start_autodetection(self, *args, **kwargs):
        self.do_init_autodetection(*args, **kwargs)
        self.autodetection_step()

    def autodetection_step(self):
        self.do_autodetection_step()
        self.notify_listeners("on_transport_validate_connection", self)

    def read(self, size=None, timeout=None):
        data = self.do_read(size=size, timeout=timeout)
        self.notify_listeners("on_transport_log_received_data", self, data)
        return data

    def write(self, data):
        self.do_write(data)
        self.notify_listeners("on_transport_log_sent_data", self, data)

    @property
    def in_waiting(self):
        return 0

    def do_read(self, size=None, timeout=None):
        return b""

    def do_write(self, data):
        pass

    def do_init_autodetection(self, *args, **kwargs):
        pass

    def do_autodetection_step(self):
        pass

    def process_transport_log(self, message):
        self.notify_listeners("on_protocol_log", self, message)

    def log_message(self, message: str, level: Union[int, None] = logging.DEBUG):
        if level is not None:
            self._logger.log(level, message)
        self.process_transport_log(message)

    def __str__(self):
        return self.__class__.__name__


class TransportState:
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    DISCONNECTED_WITH_ERROR = "disconnected_with_error"


class TransportSettings(SubSettings):
    def __init__(self, settings, transport):
        self.transport = transport.key
        SubSettings.__init__(self, settings, SETTINGS_PATH + [transport.key])


class TransportNotConnectedError(Exception):
    pass


class TransportAlreadyConnectedError(Exception):
    pass


class TransportWrapper(ListenerAware):

    unforwarded_handlers = []
    """Allows to explicitly disable certain transport listener handlers on sub classes."""

    def __init__(self, transport):
        ListenerAware.__init__(self)
        self.transport = transport
        self.transport.register_listener(self)

        # make sure we forward any transport listener calls to our own registered listeners

        def forward_handler(name):
            def f(*args, **kwargs):
                # replace references to self.transport with self
                args = [self if arg == self.transport else arg for arg in args]
                kwargs = {
                    key: self if value == self.transport else value
                    for key, value in kwargs.items()
                }

                # forward
                self.notify_listeners(name, *args, **kwargs)

            return f

        for handler in filter(
            lambda x: x.startswith("on_transport_"), dir(TransportListener)
        ):
            if handler not in self.__class__.unforwarded_handlers:
                setattr(self, handler, forward_handler(handler))

    def __getattr__(self, item):
        return getattr(self.transport, item)


class SeparatorAwareTransportWrapper(TransportWrapper):

    unforwarded_handlers = ["on_transport_log_received_data"]
    """We have read overwritten and hence send our own received_data notification."""

    def __init__(self, transport, terminator):
        TransportWrapper.__init__(self, transport)

        self.terminator = terminator

        self._buffered = bytearray()

    def read(self, size=None, timeout=None):
        start = time.monotonic()
        termlen = len(self.terminator)
        data = self._buffered

        while True:
            # make sure we always read everything that is waiting
            data += bytearray(self.transport.read(self.transport.in_waiting))

            # check for terminator, if it's there we have found our line
            termpos = data.find(self.terminator)
            if termpos >= 0:
                # line: everything up to and incl. the terminator
                line = data[: termpos + termlen]

                # buffered: everything after the terminator
                self._buffered = data[termpos + termlen :]

                received = bytes(line)
                self.notify_listeners("on_transport_log_received_data", self, received)
                return received

            # check if timeout expired
            if timeout and time.monotonic() > start + timeout:
                break

            # if we arrive here we so far couldn't read a full line, wait for more data
            c = self.transport.read(1)
            if not c:
                # EOF
                break

            # add to data and loop
            data += c

        self._buffered = data

        raise TimeoutTransportException()

    def __str__(self):
        return "SeparatorAwareTransportWrapper({}, separator={})".format(
            self.transport, self.terminator
        )


class LineAwareTransportWrapper(SeparatorAwareTransportWrapper):
    def __init__(self, transport):
        SeparatorAwareTransportWrapper.__init__(self, transport, b"\n")

    def __str__(self):
        return f"LineAwareTransportWrapper({self.transport})"


class PushingTransportWrapper(TransportWrapper):
    def __init__(
        self, transport, name=b"PushingTransportWrapper.receiver_loop", timeout=None
    ):
        super().__init__(transport)
        self.name = name
        self.timeout = timeout

        self._receiver_active = False
        self._receiver_thread = None

    @property
    def active(self):
        return self._receiver_active

    def connect(self, **kwargs):
        try:
            self.transport.connect(**kwargs)
        except TransportRequiresAutodetection:
            self.transport.start_autodetection(**kwargs)

        import threading

        self._receiver_active = True
        self._receiver_thread = threading.Thread(
            target=self._receiver_loop, name=self.name
        )
        self._receiver_thread.daemon = True
        self._receiver_thread.start()

    def disconnect(self, *args, **kwargs):
        self._receiver_active = False
        self.transport.disconnect(*args, **kwargs)

    def wait(self, timeout=None):
        self._receiver_thread.join(timeout)

    def _receiver_loop(self):
        while self._receiver_active:
            try:
                data = self.transport.read(timeout=self.timeout)
                self.notify_listeners("on_transport_data_pushed", self, data)
            except TimeoutTransportException as ex:
                self.notify_listeners("on_transport_data_exception", self, ex)
            except Exception:
                if self._receiver_active:
                    raise

    def __str__(self):
        return f"PushingTransportWrapper({self.transport})"


class TransportListener:
    def on_transport_connected(self, transport):
        pass

    def on_transport_disconnected(self, transport, error=None):
        pass

    def on_transport_autodetecting(self, transport):
        pass

    def on_transport_validate_connection(self, transport):
        pass

    def on_transport_log_sent_data(self, transport, data):
        pass

    def on_transport_log_received_data(self, transport, data):
        pass

    def on_transport_log_message(self, transport, data):
        pass


class PushingTransportWrapperListener:
    def on_transport_data_pushed(self, transport, data):
        pass

    def on_transport_data_exception(self, transport, exception):
        pass


class TransportException(Exception):
    pass


class TimeoutTransportException(TransportException):
    pass


class EofTransportException(TransportException):
    pass


class TransportRequiresAutodetection(TransportException):
    pass


class TransportOutOfAutodetectionCandidates(TransportException):
    pass
