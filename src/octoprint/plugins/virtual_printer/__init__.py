__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

import octoprint.plugin
from octoprint.comm.transport.serialtransport import SerialTransport


class VirtualSerialTransport(SerialTransport):
    name = "Virtual Connection"
    key = "virtual"

    settings = []

    pluginSettings = None
    datafolder = None

    @classmethod
    def with_settings_and_data(cls, settings, datafolder):
        return type(
            f"{cls.__name__}WithSettingsAndData",
            (cls,),
            {"pluginSettings": settings, "datafolder": datafolder},
        )

    @classmethod
    def get_connection_options(cls):
        return []

    def create_connection(self, *args, **kwargs):
        from . import virtual

        self._serial = virtual.VirtualPrinter(self.pluginSettings, self.datafolder)

    def check_connection(self, *args, **kwargs):
        return True

    def do_init_autodetection(self, *args, **kwargs):
        pass

    def do_autodetection_step(self):
        pass

    def __str__(self):
        return "VirtualSerialTransport"


class VirtualPrinterPlugin(
    octoprint.plugin.SettingsPlugin, octoprint.plugin.TemplatePlugin
):
    def get_template_configs(self):
        return [{"type": "settings", "custom_bindings": False}]

    def get_settings_defaults(self):
        return {
            "enabled": False,
            "okAfterResend": False,
            "forceChecksum": False,
            "numExtruders": 1,
            "pinnedExtruders": None,
            "includeCurrentToolInTemps": True,
            "includeFilenameInOpened": True,
            "hasBed": True,
            "hasChamber": False,
            "repetierStyleTargetTemperature": False,
            "okBeforeCommandOutput": False,
            "smoothieTemperatureReporting": False,
            "klipperTemperatureReporting": False,
            "reprapfwM114": False,
            "sdFiles": {"size": True, "longname": False},
            "throttle": 0.01,
            "sendWait": True,
            "waitInterval": 1.0,
            "rxBuffer": 64,
            "commandBuffer": 4,
            "supportM112": True,
            "echoOnM117": True,
            "brokenM29": True,
            "brokenResend": False,
            "supportF": False,
            "firmwareName": "Virtual Marlin 1.0",
            "sharedNozzle": False,
            "sendBusy": False,
            "busyInterval": 2.0,
            "simulateReset": True,
            "resetLines": ["start", "Marlin: Virtual Marlin!", "\x80", "SD card ok"],
            "preparedOks": [],
            "okFormatString": "ok",
            "m115FormatString": "FIRMWARE_NAME:{firmware_name} PROTOCOL_VERSION:1.0",
            "m115ReportCapabilities": True,
            "capabilities": {
                "AUTOREPORT_TEMP": True,
                "AUTOREPORT_SD_STATUS": True,
                "EMERGENCY_PARSER": True,
            },
            "m114FormatString": "X:{x} Y:{y} Z:{z} E:{e[current]} Count: A:{a} B:{b} C:{c}",
            "m105TargetFormatString": "{heater}:{actual:.2f}/ {target:.2f}",
            "m105NoTargetFormatString": "{heater}:{actual:.2f}",
            "ambientTemperature": 21.3,
            "errors": {
                "checksum_mismatch": "Checksum mismatch",
                "checksum_missing": "Missing checksum",
                "lineno_mismatch": "expected line {} got {}",
                "lineno_missing": "No Line Number with checksum, Last Line: {}",
                "maxtemp": "MAXTEMP triggered!",
                "mintemp": "MINTEMP triggered!",
                "command_unknown": "Unknown command {}",
            },
            "enable_eeprom": True,
            "support_M503": True,
            "resend_ratio": 0,
        }

    def get_settings_version(self):
        return 1

    def on_settings_migrate(self, target, current):
        if current is None:
            config = self._settings.global_get(["devel", "virtualPrinter"])
            if config:
                self._logger.info(
                    "Migrating settings from devel.virtualPrinter to plugins.virtual_printer..."
                )
                self._settings.global_set(
                    ["plugins", "virtual_printer"], config, force=True
                )
                self._settings.global_remove(["devel", "virtualPrinter"])

    def register_transport_hook(self, *args, **kwargs):
        return [
            VirtualSerialTransport.with_settings_and_data(
                self._settings, self.get_plugin_data_folder()
            )
        ]

    def cli_commands(self, cli_group, pass_octoprint_ctx, *args, **kwargs):
        import os
        import select
        import socket
        import threading

        import click

        from octoprint.util import to_bytes

        from . import virtual

        settings = octoprint.plugin.plugin_settings_for_settings_plugin(
            "virtual_printer",
            self,
            settings=cli_group.settings,
            defaults=self.get_settings_defaults(),
        )
        datafolder = os.path.join(settings.getBaseFolder("data"), "virtual_printer")

        class VirtualPrinterWrapper(virtual.VirtualPrinter):
            TERMINATOR = b"\n"
            CHUNK_SIZE = 16

            def __init__(self, *args, **kwargs):
                self._reader = threading.Thread(
                    target=self._copy_to_incoming, name="reader"
                )
                self._reader.daemon = True
                self._reader.start()

                super().__init__(*args, **kwargs)

            def wait(self):
                self._read_thread.join()

            def _copy_to_incoming(self):
                """Copies received lines to incoming queue"""
                buffered = bytearray()
                termlen = len(self.TERMINATOR)

                try:
                    while True:
                        try:
                            chunk = self._do_read(self.CHUNK_SIZE)
                        except socket.timeout:
                            continue

                        buffered.extend(chunk)

                        # check for terminator, if it's there we have found our line
                        termpos = buffered.find(self.TERMINATOR)
                        if termpos >= 0:
                            # line: everything up to and incl. the terminator, buffered: rest
                            line = buffered[: termpos + termlen]
                            del buffered[: termpos + termlen]
                            received = bytes(line)

                            print(f"<<< {received.rstrip()}")
                            self.incoming.put(received)
                except ConnectionAbortedError:
                    self.close()
                except ValueError as ex:
                    self.close()
                    if "file descriptor cannot be a negative number" in str(ex):
                        pass
                    else:
                        raise
                except Exception:
                    self.close()
                    raise

            def _send(self, line):
                # type: (str) -> None
                if not line.endswith("\n"):
                    line += "\n"

                try:
                    self._do_write(to_bytes(line, encoding="ascii", errors="replace"))
                    print(f">>> {line.rstrip()}")
                except Exception:
                    self.close()
                    raise

            def _do_read(self, size):
                raise NotImplementedError()

            def _do_write(self, data):
                raise NotImplementedError()

        class SocketVirtualPrinterWrapper(VirtualPrinterWrapper):
            def __init__(self, socket, *args, **kwargs):
                self._socket = socket
                self._socket.setblocking(False)
                super().__init__(*args, **kwargs)

            def _do_read(self, size):
                ready = select.select([self._socket], [], [], 2)
                if self._socket not in ready[0]:
                    raise socket.timeout()
                return self._socket.recv(size)

            def _do_write(self, data):
                ready = select.select([], [self._socket], [], 10)
                if self._socket not in ready[1]:
                    raise socket.timeout()
                self._socket.sendall(data)

        ##~~ TCP Socket

        @click.command("tcp")
        @click.option("--host", "host", type=str, default="127.0.0.1")
        @click.option("--port", "port", type=int, default=5543)
        def tcp_command(host, port):
            click.echo(f"Creating TCP server on {host}:{port}...")
            with socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM) as s:
                s.bind((host, port))
                s.listen()
                while True:
                    conn, addr = s.accept()
                    print(f"Connection from {addr}")
                    with conn:
                        virtual = SocketVirtualPrinterWrapper(conn, settings, datafolder)
                        virtual.wait()
                    print(f"Connection closed from {addr}")

        commands = [
            tcp_command,
        ]

        ##~~ Unix Domain Socket

        if hasattr(socket, "AF_UNIX"):

            @click.command("uds")
            @click.argument("path", type=click.Path)
            def uds_command(path):
                click.echo(f"Creating Unix Domain Socket server on {path}...")
                with socket.socket(family=socket.AF_UNIX, type=socket.SOCK_STREAM) as s:
                    s.bind(path)
                    s.listen()
                    while True:
                        conn, addr = s.accept()
                        print(f"Connection from {addr}")
                        with conn:
                            virtual = SocketVirtualPrinterWrapper(
                                conn, settings, datafolder
                            )
                            virtual.wait()
                        print(f"Connection closed from {addr}")

            commands.append(uds_command)

        ##~~ Win32 Named Pipe

        # Commented out for now since this is far from working
        # try:
        #    from win32 import win32file, win32pipe
        #
        #    class PipeVirtualPrinterWrapper(VirtualPrinterWrapper):
        #        def __init__(self, pipe, *args, **kwargs):
        #            self._pipe = pipe
        #            super().__init__(*args, **kwargs)
        #
        #        def _do_read(self, size):
        #            result, data = win32file.ReadFile(self._pipe, size, None)
        #            return data
        #
        #        def _do_write(self, data):
        #            win32file.WriteFile(self._pipe, data)
        #
        #    @click.command("win32pipe")
        #    @click.option("--name", "name", default="OctoPrint-VirtualPrinter")
        #    def win32pipe_command(name):
        #        click.echo(f"Creating named pipe {name}...")
        #        p = win32pipe.CreateNamedPipe(
        #            r"\\.\pipe\\" + name,
        #            win32pipe.PIPE_ACCESS_DUPLEX,
        #            win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_WAIT,
        #            1,
        #            65536,
        #            65536,
        #            300,
        #            None,
        #        )
        #        win32pipe.ConnectNamedPipe(p, None)
        #        virtual = PipeVirtualPrinterWrapper(p, settings, datafolder)
        #        virtual.wait()
        #
        #    commands.append(win32pipe_command)
        # except ImportError:
        #    # not supported on this platform
        #    pass

        # return collected commands
        return commands


__plugin_name__ = "Virtual Printer"
__plugin_author__ = "Gina Häußge, based on work by Daid Braam"
__plugin_homepage__ = (
    "https://docs.octoprint.org/en/master/development/virtual_printer.html"
)
__plugin_license__ = "AGPLv3"
__plugin_description__ = "Provides a virtual printer via a virtual serial port for development and testing purposes"
__plugin_pythoncompat__ = ">=2.7,<4"


def __plugin_load__():
    plugin = VirtualPrinterPlugin()

    global __plugin_implementation__
    __plugin_implementation__ = plugin

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.comm.transport.register": plugin.register_transport_hook,
        "octoprint.cli.commands": plugin.cli_commands,
    }
