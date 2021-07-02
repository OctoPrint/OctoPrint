__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import select
import socket
import time

from flask_babel import gettext

from octoprint.comm.transport import TimeoutTransportException, Transport
from octoprint.settings.parameters import IntegerType, TextType


class SocketTransport(Transport):

    name = "Socket Connection"
    key = "socket"

    BUFSIZE = 4096

    @classmethod
    def get_connection_options(cls):
        return [
            TextType("host", "Host"),
            IntegerType("port", "Port", min=1, max=65535),
        ] + cls.get_common_connection_options()

    @classmethod
    def get_common_connection_options(cls):
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
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._socket = None

    def create_connection(self, **kwargs):
        result = self.create_socket(**kwargs)
        self._socket.setblocking(False)
        self.set_current_args(**kwargs)
        return result

    def in_waiting(self):
        return 0  # we don't know how many bytes are waiting, we'll ignore size on do_read

    def drop_connection(self, wait=True):
        try:
            self._logger.debug(f"Closing down socket {self._socket}...")
            self._socket.close()
            return True
        except Exception:
            self._logger.exception("Error closing socket")
            return False

    def do_read(self, size=None, timeout=None):
        if timeout is None:
            timeout = self._args.get("read_timeout", 2)

        # size is unused here, but is used by other transports
        ready = select.select([self._socket], [], [], timeout)
        if not ready[0]:
            raise TimeoutTransportException()
        return self._socket.recv(self.BUFSIZE)

    def do_write(self, data):
        start = time.monotonic()
        timeout = self._args.get("write_timeout", 10)

        total_sent = 0
        while total_sent < len(data):
            ready = select.select(
                [], [self._socket], [], timeout - (time.monotonic() - start)
            )
            if not ready[1]:
                raise TimeoutTransportException()

            sent = self._socket.send(data[total_sent:])
            if sent == 0:
                raise OSError("Connection closed")
            total_sent += sent

    def create_socket(self, **kwargs):
        raise NotImplementedError()

    @classmethod
    def _socket_factory(cls, family, type, address):
        s = socket.socket(family=family, type=type)
        s.connect(address)
        return s

    def __str__(self):
        return "SocketTransport"


class TCPSocketTransport(SocketTransport):
    name = "TCP Connection"
    key = "tcpsocket"
    message_integrity = True

    @classmethod
    def get_connection_options(cls):
        return [
            TextType("host", "Host"),
            IntegerType("port", "Port", min=1, max=65535),
        ] + cls.get_common_connection_options()

    def create_socket(self, host=None, port=None, **kwargs):
        if host is None:
            raise ValueError("host must not be None")
        if port is None:
            raise ValueError("port must not be None")

        self._socket = self._socket_factory(
            socket.AF_INET, socket.SOCK_STREAM, (host, port)
        )
        return True

    def __str__(self):
        return "TCPSocketTransport"


if hasattr(socket, "AF_UNIX"):

    class UnixDomainSocketTransport(SocketTransport):

        name = "Unix Domain Socket"
        key = "unixdomainsocket"
        message_integrity = True

        @classmethod
        def get_connection_options(cls):
            return [TextType("path", "Path")] + cls.get_common_connection_options()

        def create_socket(self, path=None, **kwargs):
            if path is None:
                raise ValueError("path must not be None")

            self._socket = self._socket_factory(socket.AF_UNIX, socket.SOCK_STREAM, path)
            return True

        def __str__(self):
            return "UnixDomainSocketTransport"
