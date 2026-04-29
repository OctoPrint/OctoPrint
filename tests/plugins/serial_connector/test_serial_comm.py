import queue
import unittest
from unittest import mock

import ddt
import pytest
import serial

import octoprint.plugins.serial_connector.serial_comm as comm
from octoprint.util.files import m20_timestamp_to_unix_timestamp


@ddt.ddt
class TestSerialCommErrorHandling(unittest.TestCase):
    def setUp(self):
        self._comm = mock.create_autospec(comm.MachineCom)

        # mocks
        self._comm._handle_errors = (
            lambda *args, **kwargs: comm.MachineCom._handle_errors(
                self._comm, *args, **kwargs
            )
        )
        self._comm._trigger_error = (
            lambda *args, **kwargs: comm.MachineCom._trigger_error(
                self._comm, *args, **kwargs
            )
        )
        self._comm._recoverable_communication_errors = (
            comm.MachineCom._recoverable_communication_errors
        )
        self._comm._resend_request_communication_errors = (
            comm.MachineCom._resend_request_communication_errors
        )
        self._comm._sd_card_errors = comm.MachineCom._sd_card_errors
        self._comm._lastCommError = None
        self._comm._errorValue = None
        self._comm._clear_to_send = mock.Mock()
        self._comm._error_message_hooks = {}
        self._comm._trigger_emergency_stop = mock.Mock()
        self._comm._callback = mock.Mock()

        # settings
        self._comm._error_handling = "disconnect"
        self._comm._send_m112_on_error = True
        self._comm.isPrinting.return_value = True
        self._comm.isSdPrinting.return_value = False
        self._comm.isError.return_value = False

    @ddt.data(
        # Marlin
        "Error: Line Number is not Last Line Number+1, Last Line: 1",
        # Repetier
        "Error: Expected Line 1 got 2",
        # !! error type for good measure
        "!! expected line 1 got 2",
    )
    def test_lineno_mismatch(self, line):
        result = self._comm._handle_errors(line)
        self.assertEqual(line, result)
        self.assert_resend()

    @ddt.data(
        # Marlin
        "Error: No Line Number with checksum, Last Line: 1",
    )
    def test_lineno_missing(self, line):
        """Should simulate OK to force resend request"""
        result = self._comm._handle_errors(line)
        self.assertEqual(line, result)
        self.assert_recoverable()

    @ddt.data(
        # Marlin
        "Error: checksum mismatch",
        # Repetier
        "Error: Wrong checksum",
    )
    def test_checksum_mismatch(self, line):
        """Should prepare receiving resend request"""
        result = self._comm._handle_errors(line)
        self.assertEqual(line, result)
        self.assert_resend()

    @ddt.data(
        # Marlin
        "Error: No Checksum with line number, Last Line: 1",
        # Repetier
        "Error: Missing checksum",
    )
    def test_checksum_missing(self, line):
        """Should prepare receiving resend request"""
        result = self._comm._handle_errors(line)
        self.assertEqual(line, result)
        self.assert_resend()

    @ddt.data(
        # Marlin
        "Error: volume.init failed",
        "Error: openRoot failed",
        "Error: workDir open failed",
        "Error: Cannot enter subdir: folder",
        # Repetier
        "Error: file.open failed",
        # Marlin & Repetier (halleluja!)
        "Error: error writing to file",
        "Error: open failed, File: foo.gco",
        # Legacy?
        "Error: Cannot open foo.gco",
    )
    def test_sd_error(self, line):
        """Should pass"""
        result = self._comm._handle_errors(line)
        self.assertEqual(line, result)
        self.assert_nop()

    @ddt.data(
        # Marlin
        'Error: Unknown command: "ABC"',
        # Repetier
        "Error: Unknown command:ABC",
    )
    def test_unknown_command(self, line):
        """Should pass"""
        result = self._comm._handle_errors(line)
        self.assertEqual(line, result)
        self.assert_nop()

    @ddt.data("Error: This should get handled", "!! This should also get handled")
    def test_unknown_handled(self, line):
        """Should pass"""

        def handler(comm, message, *args, **kwargs):
            return "handled" in message

        self._comm._error_message_hooks["test"] = handler
        result = self._comm._handle_errors(line)
        self.assertEqual(line, result)
        self.assert_nop()

    @ddt.data("Error: Printer on fire")
    def test_other_error_disconnect(self, line):
        """Should trigger escalation"""
        result = self._comm._handle_errors(line)
        self.assertEqual(line, result)

        # what should have happened
        self.assert_m112_sent()
        self.assert_disconnected()

        # what should not have happened
        self.assert_not_handle_ok()
        self.assert_not_last_comm_error()
        self.assert_not_print_cancelled()
        self.assert_not_cleared_to_send()

    @ddt.data("Error: Printer on fire")
    def test_other_error_no_m112(self, line):
        """Should trigger escalation"""
        self._comm._send_m112_on_error = False

        result = self._comm._handle_errors(line)
        self.assertEqual(line, result)

        # what should have happened
        self.assert_disconnected()

        # what should not have happened
        self.assert_not_handle_ok()
        self.assert_not_last_comm_error()
        self.assert_not_print_cancelled()
        self.assert_not_cleared_to_send()
        self.assert_not_m112_sent()

    @ddt.data("Error: Printer on fire")
    def test_other_error_cancel(self, line):
        """Should trigger print cancel"""
        self._comm._error_handling = "cancel"

        result = self._comm._handle_errors(line)
        self.assertEqual(line, result)

        # what should have happened
        self.assert_print_cancelled()
        self.assert_cleared_to_send()

        # what should not have happened
        self.assert_not_handle_ok()
        self.assert_not_last_comm_error()
        self.assert_not_m112_sent()
        self.assert_not_disconnected()

    @ddt.data("Error: Printer on fire")
    def test_other_error_ignored(self, line):
        """Should only log"""
        self._comm._error_handling = "ignore"

        result = self._comm._handle_errors(line)
        self.assertEqual(line, result)

        # what should have happened
        self.assert_cleared_to_send()

        # what should not have happened
        self.assert_not_handle_ok()
        self.assert_not_last_comm_error()
        self.assert_not_print_cancelled()
        self.assert_not_m112_sent()
        self.assert_not_disconnected()

    def test_not_an_error(self):
        """Should pass"""
        result = self._comm._handle_errors("Not an error")
        self.assertEqual("Not an error", result)
        self.assert_nop()

    def test_already_error(self):
        """Should pass"""
        self._comm.isError.return_value = True

        result = self._comm._handle_errors("Error: Printer on fire")
        self.assertEqual("Error: Printer on fire", result)
        self.assert_nop()

    def test_line_none(self):
        """Should pass"""
        self.assertIsNone(self._comm._handle_errors(None))

    ##~~ assertion helpers

    def assert_handle_ok(self):
        self._comm._handle_ok.assert_called_once()

    def assert_not_handle_ok(self):
        self._comm._handle_ok.assert_not_called()

    def assert_last_comm_error(self):
        self.assertIsNotNone(self._comm._lastCommError)

    def assert_not_last_comm_error(self):
        self.assertIsNone(self._comm._lastCommError)

    def assert_m112_sent(self):
        self._comm._trigger_emergency_stop.assert_called_once_with(close=False)

    def assert_not_m112_sent(self):
        self._comm._trigger_emergency_stop.assert_not_called()

    def assert_disconnected(self):
        self.assertIsNotNone(self._comm._errorValue)
        self._comm._changeState.assert_called_with(self._comm.STATE_ERROR)
        self._comm.close.assert_called_once_with(is_error=True)

    def assert_not_disconnected(self):
        self.assertIsNone(self._comm._errorValue)
        self._comm._changeState.assert_not_called()
        self._comm.close.assert_not_called()

    def assert_print_cancelled(self):
        self._comm.cancelPrint.assert_called_once()

    def assert_not_print_cancelled(self):
        self._comm.cancelPrint.assert_not_called()

    def assert_cleared_to_send(self):
        self._comm._clear_to_send.set.assert_called_once()

    def assert_not_cleared_to_send(self):
        self._comm._clear_to_send.set.assert_not_called()

    def assert_nop(self):
        self.assert_not_handle_ok()
        self.assert_not_last_comm_error()
        self.assert_not_disconnected()
        self.assert_not_print_cancelled()
        self.assert_not_cleared_to_send()

    def assert_recoverable(self):
        self.assert_handle_ok()

        self.assert_not_last_comm_error()
        self.assert_not_disconnected()
        self.assert_not_print_cancelled()
        self.assert_not_cleared_to_send()

    def assert_resend(self):
        self.assert_last_comm_error()

        self.assert_not_handle_ok()
        self.assert_not_disconnected()
        self.assert_not_print_cancelled()
        self.assert_not_cleared_to_send()


def test_autodetection():
    """
    Basic serial autodetection test.

    Simulates four available ports and two baudrates:
      - port_unopenable: triggers a SerialException on open
      - port_unwritable: always returns 0 bytes written
      - port_works_at_250k: only works @ 250000 baudrate
      - port_unreached: should never be reached

    The test sets up a MachineCom instance and starts a detection run. In the
    end, an operational state should be reached on port_works_at_250k, at a
    baudrate of 250000k.
    """
    from threading import Event

    from octoprint.plugins.serial_connector.config_schema import (
        SerialConfig,
    )

    # mock settings

    serial_config = SerialConfig().model_dump()

    def settings_get(path, *args, **kwargs):
        node = serial_config
        for p in path:
            if p not in node:
                return None
            node = node[p]
        return node

    def settings_global_get(path, *args, **kwargs):
        return None

    mock_settings = mock.Mock()
    mock_settings.get.side_effect = settings_get
    mock_settings.get_boolean.side_effect = settings_get
    mock_settings.get_int.side_effect = settings_get
    mock_settings.get_float.side_effect = settings_get
    mock_settings.global_get.side_effect = settings_global_get
    mock_settings.loadScript.return_value = None

    # mock plugin manager

    mock_plugin_manager = mock.Mock()
    mock_plugin_manager.get_hooks.return_value = {}

    # mock serial port

    mock_serial = mock.Mock()
    mock_serial.timeout = 2.0

    mock_serial_read_buffer = queue.SimpleQueue()

    def mock_serial_write(data, *args, **kwargs):
        if mock_serial.port == "port_unwritable":
            return 0

        if mock_serial.port == "port_works_at_250k" and data == b"N0 M110 N0*125\n":
            if mock_serial.baudrate == 250000:
                mock_serial_read_buffer.put(b"ok\n")
            else:
                mock_serial_read_buffer.put(b"@\x00~~")

        return len(data)

    def mock_serial_readline(*args, **kwargs):
        try:
            return mock_serial_read_buffer.get(timeout=mock_serial.timeout)
        except queue.Empty:
            return b""

    mock_serial.write.side_effect = mock_serial_write
    mock_serial.readline.side_effect = mock_serial_readline

    # mock serial & baudrate list

    def mock_serial_list(*args, **kwargs):
        return [
            "port_unopenable",
            "port_unwritable",
            "port_works_at_250k",
            "port_unreached",
        ]

    def mock_baudrate_list(*args, **kwargs):
        return [115200, 250000]

    with mock.patch(
        "octoprint.plugins.serial_connector.serial_comm.serialList", mock_serial_list
    ):
        with mock.patch(
            "octoprint.plugins.serial_connector.serial_comm.baudrateList",
            mock_baudrate_list,
        ):

            class TestCallback(comm.MachineComPrintCallback):
                def __init__(self, *args, **kwargs):
                    self.entered_detection_state = Event()
                    self.left_detection_state = Event()

                    self.current_state = comm.MachineCom.STATE_CLOSED

                    super().__init__(*args, **kwargs)

                def on_comm_state_change(self, state):
                    print(f"State change {self.current_state} -> {state}")

                    if state == comm.MachineCom.STATE_DETECT_SERIAL:
                        print("Entered detection state...")
                        self.entered_detection_state.set()
                    elif (
                        self.entered_detection_state.is_set()
                        and state != comm.MachineCom.STATE_DETECT_SERIAL
                    ):
                        print("Left detection state...")
                        self.left_detection_state.set()

                    self.current_state = state

                    return super().on_comm_state_change(state)

            callback = TestCallback()
            comm_instance = comm.MachineCom(
                "_default",
                callback=callback,
                settings=mock_settings,
                plugin_manager=mock_plugin_manager,
            )

            # override self._open_serial
            open_serial_counter = mock.Mock()

            def mock_open_serial(port, baudrate, *args, **kwargs):
                open_serial_counter.open(port, baudrate)

                if port == "port_unopenable":
                    raise serial.SerialException(f"Port {port} can't be opened")

                mock_serial.port = port
                mock_serial.baudrate = baudrate
                comm_instance._serial = mock_serial
                return True

            comm_instance._open_serial = mock_open_serial

            # "connect"
            comm_instance.start()

            # wait for state transition
            callback.entered_detection_state.wait(30)
            if callback.entered_detection_state.is_set():
                callback.left_detection_state.wait(30)

    # assertions
    assert comm_instance._state == comm.MachineCom.STATE_OPERATIONAL
    assert mock_serial.port == "port_works_at_250k"
    assert mock_serial.baudrate == 250000

    open_serial_counter.open.assert_has_calls(
        [
            # error, self._serial unset, so two calls
            mock.call("port_unopenable", 115200),
            mock.call("port_unopenable", 250000),
            # error, self._serial unset, so two calls
            mock.call("port_unwritable", 115200),
            mock.call("port_unwritable", 250000),
            # only byte garbage, self._serial set, so only one call, second baudrate set directly
            mock.call("port_works_at_250k", 115200),
        ]
    )


@pytest.mark.parametrize(
    "val,expected",
    [
        ("aaa", False),
        ("1234", False),
        ("0x21bf7d", True),
        ("0xghijk", False),
        ("0x28210800", True),
    ],
)
def test__validate_m20_timestamp(val, expected):
    assert comm._validate_m20_timestamp(val) == expected


@pytest.mark.parametrize(
    "val,expected",
    [
        (
            "line that makes little sense",
            ("line that makes little sense", None, None, None),
        ),
        ("name.gco", ("name.gco", None, None, None)),
        ("name.gco invalid-size", ("name.gco invalid-size", None, None, None)),
        (
            "name.gco 3424324",
            ("name.gco", 3424324, None, None),
        ),
        (
            "name.gco 3424324 longname.gcode",
            ("name.gco", 3424324, None, "longname.gcode"),
        ),
        (
            "name.gco 3424324 0x21bf7d",
            (
                "name.gco",
                3424324,
                m20_timestamp_to_unix_timestamp("0x21bf7d"),
                None,
            ),
        ),
        (
            "name.gco 3424324 0xinvalid_timestamp_as_longname",
            ("name.gco", 3424324, None, "0xinvalid_timestamp_as_longname"),
        ),
        (
            "longname.gcode 3424324 0x21bf7d",
            (
                "longname.gcode",
                3424324,
                m20_timestamp_to_unix_timestamp("0x21bf7d"),
                None,
            ),
        ),
        (
            "longname.gcode 3424324 longname.gcode",
            ("longname.gcode", 3424324, None, "longname.gcode"),
        ),
        (
            "name.gco 32424 0x21bf7d long name without quoting",
            (
                "name.gco",
                32424,
                m20_timestamp_to_unix_timestamp("0x21bf7d"),
                "long name without quoting",
            ),
        ),
        (
            "name.gco 32424 0x21bf7d long   name   without   quoting",
            (
                "name.gco",
                32424,
                m20_timestamp_to_unix_timestamp("0x21bf7d"),
                "long   name   without   quoting",
            ),
        ),
        (
            'name.gco 32424 0x21bf7d "long name with quoting"',
            (
                "name.gco",
                32424,
                m20_timestamp_to_unix_timestamp("0x21bf7d"),
                "long name with quoting",
            ),
        ),
        (
            'name.gco 32424 0x21bf7d "long   name   with   quoting"',
            (
                "name.gco",
                32424,
                m20_timestamp_to_unix_timestamp("0x21bf7d"),
                "long   name   with   quoting",
            ),
        ),
    ],
)
def test_parse_file_list_line(val, expected):
    assert comm.parse_file_list_line(val) == expected
