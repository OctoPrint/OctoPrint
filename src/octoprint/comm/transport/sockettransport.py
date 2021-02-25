__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import socket

from octoprint.comm.transport import Transport
from octoprint.comm.util.parameters import IntegerType, TextType


class TcpTransport(Transport):

    name = "TCP Connection"
    key = "tcpsocket"
    message_integrity = True

    @classmethod
    def get_connection_options(cls):
        return [TextType("host", "Host"), IntegerType("port", "Port", min=1, max=65535)]

    def __init__(self):
        super().__init__()

        self._socket = None

    def create_connection(self, host=None, port=None):
        if host is None:
            raise ValueError("host must not be None")
        if port is None:
            raise ValueError("port must not be None")

        self._socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        self._socket.connect((host, port))
        self.set_current_args(host=host, port=port)

        return True

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
        return self._socket.recv(size)

    def do_write(self, data):
        self._socket.sendall(data)

    def __str__(self):
        return "TcpTransport"


class SerialOverTcpTransport(TcpTransport):

    name = "Serial Connection over TCP"
    key = "serialovertcpsocket"
    message_integrity = False
