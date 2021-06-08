__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import os

import serial
from serial.tools.list_ports import comports

from octoprint.comm.transport import (
    Transport,
    TransportRequiresAutodetection,
    TransportState,
)
from octoprint.comm.util.parameters import (
    BooleanType,
    ChoiceType,
    ConditionalGroup,
    IntegerType,
    ListType,
    SmallChoiceType,
    SuggestionType,
    UrlType,
    Value,
)
from octoprint.util import dummy_gettext as gettext
from octoprint.util.platform import get_os, set_close_exec


class SerialTransport(Transport):
    name = "Serial Connection"
    key = "serial"
    message_integrity = False

    max_write_passes = 5

    baudrates = [250000, 230400, 115200, 57600, 38400, 19200, 9600]
    autodetection_baudrates = [115200, 250000]
    ignored_ports = [
        "/dev/ttyAMA0",
        "/dev/ttyS*",
    ]

    settings = [
        ListType(
            "baudrates",
            gettext("Baudrates"),
            sep="\n",
            factory=int,
            default=baudrates,
        ),
        ListType(
            "autodetection_baudrates",
            gettext("Autodetection baudrates"),
            sep="\n",
            factory=int,
            default=autodetection_baudrates,
        ),
        ListType(
            "ignored_ports",
            gettext("Ignored ports"),
            help=gettext("Serial ports you'd like to ignore"),
            sep="\n",
            default=ignored_ports,
        ),
    ]

    @classmethod
    def get_connection_options(cls):
        return [
            ConditionalGroup(
                "connect_via",
                gettext("Connect via"),
                [
                    Value("port", title=gettext("Port & baudrate")),
                    Value("usbid", title=gettext("USB ID & baudrate")),
                    Value("usbserial", title=gettext("USB serial number")),
                    Value("usbloc", title=gettext("USB port")),
                    Value("url", title=gettext("URL")),
                ],
                {
                    "port": [
                        SuggestionType(
                            "port",
                            gettext("Port"),
                            cls.get_available_serial_ports("port"),
                            lambda value: Value(value),
                        ),
                        SuggestionType(
                            "baudrate",
                            gettext("Baudrate"),
                            cls.get_available_baudrates(),
                            lambda value: Value(value),
                            default=0,
                        ),
                    ],
                    "usbid": [
                        SuggestionType(
                            "usbid",
                            gettext("USB ID"),
                            cls.get_available_serial_ports("usbid"),
                            lambda value: Value(value),
                        ),
                        SuggestionType(
                            "baudrate",
                            gettext("Baudrate"),
                            cls.get_available_baudrates(),
                            lambda value: Value(value),
                            default=0,
                        ),
                    ],
                    "usbserial": [
                        SuggestionType(
                            "usbserial",
                            gettext("USB serial number"),
                            cls.get_available_serial_ports("usbserial"),
                            lambda value: Value(value),
                        ),
                        SuggestionType(
                            "baudrate",
                            gettext("Baudrate"),
                            cls.get_available_baudrates(),
                            lambda value: Value(value),
                            default=0,
                        ),
                    ],
                    "usbloc": [
                        SuggestionType(
                            "usbloc",
                            gettext("USB port"),
                            cls.get_available_serial_ports("usbloc"),
                            lambda value: Value(value),
                        ),
                        SuggestionType(
                            "baudrate",
                            gettext("Baudrate"),
                            cls.get_available_baudrates(),
                            lambda value: Value(value),
                            default=0,
                        ),
                    ],
                    "url": [
                        UrlType(
                            "url",
                            "URL",
                            help=gettext(
                                "See [here](https://pythonhosted.org/pyserial/url_handlers.html#urls) for supported URL schemes"
                            ),
                        )
                    ],
                },
                default="port",
            ),
        ] + cls._get_common_options()

    @classmethod
    def _get_common_options(cls):
        return [
            IntegerType(
                "read_timeout",
                gettext("Read Timeout"),
                min=1,
                unit="sec",
                default=2,
                advanced=True,
            ),
            IntegerType(
                "write_timeout",
                gettext("Write Timeout"),
                min=1,
                unit="sec",
                default=10,
                advanced=True,
            ),
            BooleanType(
                "exclusive",
                gettext("Request exclusive access to the serial port"),
                help=gettext(
                    "Uncheck this if you are having problems connecting to your printer."
                ),
                default=True,
                advanced=True,
            ),
            BooleanType(
                "low_latency",
                gettext("Request low latency mode on the serial port (if supported)"),
                help=gettext(""),
                default=True,
                advanced=True,
            ),
            ChoiceType(
                "parity",
                gettext("Parity"),
                [
                    Value(serial.PARITY_NONE, gettext("none")),
                    Value(serial.PARITY_ODD, gettext("odd")),
                    Value(serial.PARITY_EVEN, gettext("even")),
                ],
                default=serial.PARITY_NONE,
                advanced=True,
                expert=True,
            ),
            SmallChoiceType(
                "parity_workaround",
                gettext("Apply parity double open workaround"),
                [
                    Value(
                        "always",
                        title=gettext("Always"),
                        help=gettext(
                            "Use this if you are running into [this problem](https://forum.arduino.cc/index.php?topic=91291.0)."
                        ),
                    ),
                    Value("detect", title=gettext("If detected as potentially needed")),
                    Value(
                        "never",
                        title=gettext("Never"),
                        help=gettext(
                            "Use this if connecting to your printer fails with `(22, 'Invalid argument')`."
                        ),
                    ),
                ],
                default="detect",
                advanced=True,
                expert=True,
            ),
        ]

    @classmethod
    def get_available_serial_ports(cls, focus):
        matcher = lambda x: True
        if focus == "usbid":
            matcher = lambda x: x.vid and x.pid
        elif focus == "usbserial":
            matcher = lambda x: x.serial_number
        elif focus == "usbloc":
            matcher = lambda x: x.location

        def port_value(port):
            if focus == "usbid":
                vidpid = f"{port.vid:04x}:{port.pid:04x}"
                return Value(vidpid, title=f"{port.description} [{vidpid}]")
            elif focus == "usbserial":
                usbserial = port.serial_number
                return Value(usbserial, title=f"{port.description} [{usbserial}]")
            elif focus == "usbloc":
                usbloc = port.location
                return Value(usbloc, title=f"{port.description} [{usbloc}]")
            else:
                return Value(port.device, title=f"{port.description} [{port.device}]")

        port_values = [Value(None, title="Auto detect")] + sorted(
            [
                port_value(port)
                for port in comports()
                if port.device not in cls.ignored_ports and matcher(port)
            ],
            key=lambda x: x.title,
        )
        return port_values

    @classmethod
    def get_available_baudrates(cls):
        return [Value(0, title="Auto detect")] + sorted(
            [Value(baudrate) for baudrate in cls.baudrates],
            key=lambda x: x.title,
            reverse=True,
        )

    def __init__(self, *args, **kwargs):
        super().__init__()

        self.serial_factory = kwargs.get("serial_factory", None)

        self._logger = logging.getLogger(__name__)
        self._serial = None

        self._closing = False

        self._autodetect_candidates = None
        self._autodetect_kwargs = None
        self._autodetect_timer = None

    def create_connection(self, **kwargs):
        factory = self.serial_factory
        if self.serial_factory is None:
            factory = self._default_serial_factory

        self._closing = False
        self._serial = factory(**kwargs)
        self.set_current_args(**kwargs)

        return True

    def drop_connection(self, wait=True):
        error = False

        if self._serial is not None:
            self._closing = True

            try:
                if callable(getattr(self._serial, "cancel_read", None)):
                    self._serial.cancel_read()
            except Exception:
                self._logger.exception(
                    "Error while cancelling pending reads from the serial port"
                )

            try:
                if callable(getattr(self._serial, "cancel_write", None)):
                    self._serial.cancel_write()
            except Exception:
                self._logger.exception(
                    "Error while cancelling pending writes to the serial port"
                )

            try:
                self._serial.close()
            except Exception:
                self._logger.exception("Error while closing the serial port")
                error = True

            self._serial = None

        return not error

    def check_connection(self, *args, **kwargs):
        try:
            self._create_serial(**kwargs)
            return True
        except ValueError:
            return False

    def do_read(self, size=None, timeout=None):
        if timeout is not None:
            self._serial.timeout = timeout
        return self._serial.read(size=size)

    def do_write(self, data):
        written = 0
        passes = 0

        def try_to_write(d):
            result = self._serial.write(d)
            if result is None or not isinstance(result, int):
                # probably some plugin not returning the written bytes, assuming all of them
                return len(data)
            else:
                return result

        while written < len(data):
            to_send = data[written:]
            old_written = written

            try:
                written += try_to_write(to_send)
            except serial.SerialTimeoutException:
                self._logger.warning(
                    "Serial timeout while writing to serial port, trying again."
                )
                try:
                    # second try
                    written += try_to_write(to_send)
                except Exception:
                    if not self._closing:
                        message = "Unexpected error while writing to serial port"
                        self._logger.exception(message)
                        self.disconnect(error=message)
                    break
            except Exception:
                if not self._closing:
                    message = "Unexpected error while writing to serial port"
                    self._logger.exception(message)
                    self.disconnect(error=message)
                break

            if old_written == written:
                passes += 1
                if passes > self.max_write_passes:
                    message = (
                        "Could not write anything to the serial port in {} tries, "
                        "something appears to be wrong with the communication".format(
                            self.max_write_passes
                        )
                    )
                    self._logger.error(message)
                    self.disconnect(error=message)
                    break

    @property
    def in_waiting(self):
        return getattr(self._serial, "in_waiting", 0)

    def do_init_autodetection(self, *args, **kwargs):
        self._autodetect_kwargs = {
            k: v
            for k, v in kwargs.items()
            if k not in ("connect_via", "port", "baudrate")
        }
        port = self._find_serial_port(focus=kwargs.get("connect_via"))
        baudrate = kwargs.get("baudrate")

        if port:
            port_candidates = [
                port.device,
            ]
        else:
            port_candidates = [port.device for port in comports()]

        if baudrate:
            baudrate_candidates = [
                baudrate,
            ]
        else:
            baudrate_candidates = [*self.autodetection_baudrates]

        self._autodetect_candidates = [
            (p, b) for b in baudrate_candidates for p in port_candidates
        ]

        self.process_transport_log(
            "Performing autodetection with {} port/baudrate candidates: {}".format(
                len(self._autodetect_candidates),
                ", ".join(map(lambda x: "{}@{}".format(*x), self._autodetect_candidates)),
            )
        )

        return True

    def do_autodetection_step(self):
        while (
            len(self._autodetect_candidates) > 0
            and self.state == TransportState.CONNECTING
        ):
            (p, b) = self._autodetect_candidates.pop(0)

            try:
                self.process_transport_log(f"Trying port {p}@{b}")
                if self._serial is None or self._serial.port != p:
                    if not self.create_connection(
                        connect_via="port",
                        port=p,
                        baudrate=b,
                        **self._autodetect_kwargs,
                    ):
                        self.process_transport_log(f"Could not open {p}@{b}, skipping")
                        continue
                else:
                    self._serial.baudrate = b

                return
            except Exception:
                self._logger.exception(f"Unexpected error while setting baudrate {b}")

    def _default_serial_factory(self, **kwargs):
        serial_obj = self._create_serial(**kwargs)
        self._apply_parity_workaround(serial_obj, **kwargs)
        serial_obj.open()
        self._set_close_exec(serial_obj, **kwargs)
        self._set_low_latency(serial_obj, **kwargs)

        return serial_obj

    @classmethod
    def _find_serial_port(cls, focus="port", **kwargs):
        value = kwargs.get(focus)
        if value is None:
            return None

        if focus == "port":
            matcher = lambda p: p.device == value
        elif focus == "usbid":
            vid, pid = value.split(":")
            matcher = lambda p: f"{p.vid:04x}" == vid and f"{p.pid:04x}" == pid
        elif focus == "usbserial":
            matcher = lambda p: p.serial_number == value
        elif focus == "usbloc":
            matcher = lambda p: p.location == value
        else:
            return None

        try:
            return match_port(matcher)
        except PortNotFound:
            return None

    @classmethod
    def _create_serial(cls, **kwargs):
        focus = kwargs.pop("connect_via")

        port_based = ("port", "usbid", "usbserial", "usbloc")
        if focus in port_based:
            port = cls._find_serial_port(focus=focus, **kwargs)
            for k in port_based:
                if k in kwargs:
                    kwargs.pop(k)

            baudrate = kwargs.pop("baudrate", 0)

            if port is None or baudrate == 0:
                raise TransportRequiresAutodetection()

            return cls._create_serial_for_port_and_baudrate(
                port.device, baudrate, **kwargs
            )

        elif focus == "url":
            return serial.serial_for_url(kwargs.get("url"), do_not_open=True)

        else:
            raise ValueError(f"Invalid focus: {focus}")

    @classmethod
    def _create_serial_for_port_and_baudrate(cls, port, baudrate, **kwargs):
        serial_obj = serial.Serial(
            baudrate=baudrate,
            exclusive=kwargs.get("exclusive", True),
            parity=kwargs.get("parity", serial.PARITY_NONE),
            timeout=kwargs.get("read_timeout", 2),
            write_timeout=kwargs.get("write_timeout", 10),
        )
        serial_obj.port = port  # set port only now to prevent auto open
        return serial_obj

    @classmethod
    def _apply_parity_workaround(cls, serial_obj, **kwargs):
        use_parity_workaround = kwargs.get("parity_workaround")
        needs_parity_workaround = get_os() == "linux" and os.path.exists(
            "/etc/debian_version"
        )  # See #673

        if use_parity_workaround == "always" or (
            needs_parity_workaround and use_parity_workaround == "detect"
        ):
            serial_obj.parity = serial.PARITY_ODD
            serial_obj.open()
            serial_obj.close()
            serial_obj.parity = kwargs.get("parity")

        return serial_obj

    @classmethod
    def _set_close_exec(cls, serial_obj, **kwargs):
        if hasattr(serial_obj, "fd"):
            # posix
            set_close_exec(serial_obj.fd)
        elif hasattr(serial_obj, "_port_handle"):
            # win32
            # noinspection PyProtectedMember
            set_close_exec(serial_obj._port_handle)

        return serial_obj

    @classmethod
    def _set_low_latency(cls, serial_obj, **kwargs):
        use_low_latency = kwargs.get("low_latency", False)
        if hasattr(serial_obj, "set_low_latency_mode"):
            if use_low_latency:
                try:
                    serial_obj.set_low_latency_mode(True)
                except Exception:
                    logging.getLogger(__name__).exception(
                        "Could not set low latency mode on serial port"
                    )
        else:
            logging.getLogger(__name__).info(
                "Platform doesn't support low latency mode on serial port"
            )
        return serial_obj

    def __str__(self):
        return "SerialTransport"


class PortNotFound(Exception):
    pass


def match_port(matcher):
    for port in comports():
        if matcher(port):
            return port
    else:
        raise PortNotFound()


if __name__ == "__main__":
    # list ports
    ports = SerialTransport.get_available_serial_ports()
    for port in ports:
        print(port.title + ": " + port.value)
