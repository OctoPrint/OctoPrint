__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import os

import serial

from octoprint.comm.transport import Transport
from octoprint.comm.util.parameters import (
    BooleanType,
    ChoiceType,
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
            SuggestionType(
                "port",
                gettext("Port"),
                cls.get_available_serial_ports(),
                lambda value: Value(value),
            ),
            SuggestionType(
                "baudrate",
                gettext("Baudrate"),
                cls.get_available_baudrates(),
                lambda value: Value(value),
                default=0,
            ),
        ] + cls._get_common_options()

    @classmethod
    def _get_common_options(cls):
        return [
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
    def get_available_serial_ports(cls):
        from serial.tools.list_ports import comports

        def port_title(port):
            if port.vid and port.pid:
                # usb
                return "{desc} [{vid:04x}:{pid:04x}]".format(
                    desc=port.description, vid=port.vid, pid=port.pid
                )
            else:
                return port.description

        port_values = [Value(None, title="Auto detect")] + sorted(
            [
                Value(port.device, title=port_title(port))
                for port in comports()
                if port.device not in cls.ignored_ports
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

    def do_read(self, size=None, timeout=None):
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

    def _default_serial_factory(self, **kwargs):
        serial_obj = self._create_serial(**kwargs)
        self._apply_parity_workaround(serial_obj, **kwargs)
        serial_obj.open()
        self._set_close_exec(serial_obj, **kwargs)

        return serial_obj

    @classmethod
    def _create_serial(cls, **kwargs):
        serial_obj = serial.Serial(
            baudrate=kwargs.get("baudrate"),
            exclusive=kwargs.get("exclusive"),
            parity=kwargs.get("parity"),
            write_timeout=kwargs.get("write_timeout", 10) * 1000,
        )
        serial_obj.port = kwargs.get("port")  # set port only now to prevent auto open
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

    def __str__(self):
        return "SerialTransport"


class SerialUrlTransport(SerialTransport):
    name = "Serial URL Connection"
    key = "serialurl"
    message_integrity = False

    @classmethod
    def get_connection_options(cls):
        return [
            UrlType(
                "url",
                "URL",
                help=gettext(
                    "See [here](https://pythonhosted.org/pyserial/url_handlers.html#urls) for supported URL schemes"
                ),
            )
        ] + cls._get_common_options()

    @classmethod
    def _create_serial(cls, **kwargs):
        serial_obj = serial.serial_for_url(kwargs.get("url"), do_not_open=True)
        return serial_obj


if __name__ == "__main__":
    # list ports
    ports = SerialTransport.get_available_serial_ports()
    for port in ports:
        print(port.title + ": " + port.value)
