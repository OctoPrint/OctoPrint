__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2021 The OctoPrint Project - Released under terms of the AGPLv3 License"

from os import scandir

from flask_babel import gettext

from octoprint.comm.transport import Transport
from octoprint.settings.parameters import SuggestionType, Value
from octoprint.util import to_bytes, to_unicode

try:
    from win32 import win32file, win32pipe

    class NamedPipeTransport(Transport):
        PIPE_BASE = r"\\.\pipe"

        name = "Named Pipe"
        key = "namedpipe"

        message_integrity = True

        @classmethod
        def get_pipe_path(cls, name):
            return cls.PIPE_BASE + "\\" + name

        @classmethod
        def get_connection_options(cls):
            return [
                SuggestionType(
                    "name",
                    gettext("Pipe name"),
                    cls.get_available_pipes(),
                    lambda value: Value(value),
                ),
            ]

        @classmethod
        def get_available_pipes(cls):
            pipes = []
            for item in scandir(cls.PIPE_BASE):
                if not item.is_file():
                    continue
                pipes.append(item.name)
            return [Value(pipe) for pipe in sorted(pipes)]

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            self._pipe = None

        def create_connection(self, name=None):
            if name is None:
                raise ValueError("name must not be None")

            self._pipe = win32file.CreateFile(
                self.get_pipe_path(name),
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0,
                None,
                win32file.OPEN_EXISTING,
                0,
                None,
            )
            win32pipe.SetNamedPipeHandleState(
                self._pipe, win32pipe.PIPE_READMODE_MESSAGE, None, None
            )

            self.set_current_args(name=name)

            return True

        def drop_connection(self, wait=True):
            try:
                self._pipe.close()
            except Exception:
                self._logger.exception("Error closing pipe")
                return False

        def do_read(self, size=None, timeout=None):
            if size is None:
                size = 16
            result, data = win32file.ReadFile(self._pipe, size, None)
            return data

        def do_write(self, data):
            win32file.WriteFile(self._pipe, data)

        def __str__(self):
            return "NamedPipeTransport"

    if __name__ == "__main__":
        import sys

        if len(sys.argv) < 3:
            print("Usage: namedpipetransport.py client|server <name>", file=sys.stderr)
            print()
            print(repr(NamedPipeTransport.get_available_pipes()))
            sys.exit(-1)

        mode = sys.argv[1]
        name = sys.argv[2]

        if mode == "client":
            client = NamedPipeTransport()
            client.create_connection(name=name)
            counter = 0

            while counter < 10:
                message = f"Counter={counter}"
                counter += 1
                print(">>> " + message)

                client.do_write(to_bytes(message + "\n"))

                reply = to_unicode(client.do_read(16))
                print("<<< " + reply)

            client.drop_connection()

        elif mode == "server":
            p = win32pipe.CreateNamedPipe(
                NamedPipeTransport.get_pipe_path(name),
                win32pipe.PIPE_ACCESS_DUPLEX,
                win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_WAIT,
                1,
                65536,
                65536,
                300,
                None,
            )
            win32pipe.ConnectNamedPipe(p, None)
            while True:
                result, data = win32file.ReadFile(p, 16, None)
                if result != 0:
                    break

                data = to_unicode(data)

                print("<<< " + data)
                reply = f"Echo:{data}"
                print(">>> " + reply)

                win32file.WriteFile(p, to_bytes(reply + "\n"))

            p.close()

except ImportError:
    # no NamedPipeTransport
    pass
