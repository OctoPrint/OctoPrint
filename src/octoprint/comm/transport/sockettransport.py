__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import select
import socket

from octoprint.comm.transport import Transport
from octoprint.settings.parameters import IntegerType, TextType


class SocketTransport(Transport):

    name = "Socket Connection"
    key = "socket"

    @classmethod
    def get_connection_options(cls):
        return [TextType("host", "Host"), IntegerType("port", "Port", min=1, max=65535)]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._socket = None

    def create_connection(self, **kwargs):
        result = self.create_socket(**kwargs)
        self.set_current_args(**kwargs)
        return result

    def drop_connection(self, wait=True):
        try:
            self._socket.close()
            return True
        except Exception:
            self._logger.exception("Error closing socket")
            return False

    def do_read(self, size=None, timeout=None):
        if size is None:
            size = 16

        if timeout is not None:
            self._socket.setblocking(0)
            ready = select.select([self._socket], [], [], timeout)
            if ready[0]:
                return self._socket.recv(size)
            raise socket.timeout()
        else:
            return self._socket.recv(size)

    def do_write(self, data):
        self._socket.sendall(data)

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
        return [TextType("host", "Host"), IntegerType("port", "Port", min=1, max=65535)]

    def create_socket(self, host=None, port=None):
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
            return [TextType("path", "Path")]

        def create_socket(self, path=None):
            if path is None:
                raise ValueError("path must not be None")

            self._socket = self._socket_factory(socket.AF_UNIX, socket.SOCK_STREAM, path)
            return True

        def __str__(self):
            return "UnixDomainSocketTransport"
