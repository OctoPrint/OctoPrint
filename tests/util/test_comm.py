
import unittest
import mock
import ddt

import octoprint.util.comm

@ddt.ddt
class TestCommErrorHandling(unittest.TestCase):

	def setUp(self):
		self._comm = mock.create_autospec(octoprint.util.comm.MachineCom)

		# mocks
		self._comm._handle_errors = lambda *args, **kwargs: octoprint.util.comm.MachineCom._handle_errors(self._comm, *args, **kwargs)
		self._comm._recoverable_communication_errors = octoprint.util.comm.MachineCom._recoverable_communication_errors
		self._comm._resend_request_communication_errors = octoprint.util.comm.MachineCom._resend_request_communication_errors
		self._comm._sd_card_errors = octoprint.util.comm.MachineCom._sd_card_errors
		self._comm._lastCommError = None
		self._comm._errorValue = None
		self._comm._clear_to_send = mock.Mock()

		# settings
		self._comm._ignore_errors = False
		self._comm._disconnect_on_errors = True
		self._comm.isPrinting.return_value = True
		self._comm.isError.return_value = False

	@ddt.data(
		# Marlin
		"Error: Line Number is not Last Line Number+1, Last Line: 1",

		# Repetier
		"Error: Expected Line 1 got 2",

		# !! error type for good measure
		"!! expected line 1 got 2"
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
		"Error: Unknown command: \"ABC\"",

		# Repetier
		"Error: Unknown command:ABC",
	)
	def test_unknown_command(self, line):
		"""Should pass"""
		result = self._comm._handle_errors(line)
		self.assertEqual(line, result)
		self.assert_nop()

	@ddt.data("Error: Printer on fire")
	def test_other_error_disconnect(self, line):
		"""Should trigger escalation"""
		result = self._comm._handle_errors(line)
		self.assertEqual(line, result)

		# what should have happened
		self.assert_disconnected()

		# what should not have happened
		self.assert_not_handle_ok()
		self.assert_not_last_comm_error()
		self.assert_not_print_cancelled()
		self.assert_not_cleared_to_send()

	@ddt.data("Error: Printer on fire")
	def test_other_error_cancel(self, line):
		"""Should trigger print cancel"""
		self._comm._disconnect_on_errors = False

		result = self._comm._handle_errors(line)
		self.assertEqual(line, result)

		# what should have happened
		self.assert_print_cancelled()
		self.assert_cleared_to_send()

		# what should not have happened
		self.assert_not_handle_ok()
		self.assert_not_last_comm_error()
		self.assert_not_disconnected()

	@ddt.data("Error: Printer on fire")
	def test_other_error_ignored(self, line):
		"""Should only log"""
		self._comm._ignore_errors = True

		result = self._comm._handle_errors(line)
		self.assertEqual(line, result)

		# what should have happened
		self.assert_cleared_to_send()

		# what should not have happened
		self.assert_not_handle_ok()
		self.assert_not_last_comm_error()
		self.assert_not_print_cancelled()

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

	def assert_disconnected(self):
		self.assertIsNotNone(self._comm._errorValue)
		self._comm._changeState.assert_called_once()

	def assert_not_disconnected(self):
		self.assertIsNone(self._comm._errorValue)
		self._comm._changeState.assert_not_called()

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
