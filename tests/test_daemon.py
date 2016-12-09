# coding=utf-8
from __future__ import absolute_import, division, print_function

import unittest
import mock

import octoprint.daemon

class ExpectedExit(BaseException):
	pass

class DaemonTest(unittest.TestCase):
	def setUp(self):

		run_method = mock.MagicMock()
		echo_method = mock.MagicMock()
		error_method = mock.MagicMock()

		class TestDaemon(octoprint.daemon.Daemon):

			def run(self):
				run_method()

			def echo(cls, line):
				echo_method(line)

			def error(cls, line):
				error_method(line)

		self.pidfile = "/my/pid/file"
		self.daemon = TestDaemon(self.pidfile)
		self.run_method = run_method
		self.echo_method = echo_method
		self.error_method = error_method

	@mock.patch("os.fork", create=True)
	@mock.patch("os.chdir")
	@mock.patch("os.setsid", create=True)
	@mock.patch("os.umask")
	@mock.patch("sys.exit")
	def test_double_fork(self, mock_exit, mock_umask, mock_setsid, mock_chdir, mock_fork):
		# setup
		pid1 = 1234
		pid2 = 2345
		mock_fork.side_effect = [pid1, pid2]

		# test
		self.daemon._double_fork()

		# assert
		self.assertListEqual(mock_fork.mock_calls, [mock.call(), mock.call()])
		self.assertListEqual(mock_exit.mock_calls, [mock.call(0), mock.call(0)])
		mock_chdir.assert_called_once_with("/")
		mock_setsid.assert_called_once_with()
		mock_umask.assert_called_once_with(0o002)

	@mock.patch("os.fork", create=True)
	@mock.patch("sys.exit")
	def test_double_fork_failed_first(self, mock_exit, mock_fork):
		# setup
		mock_fork.side_effect = OSError()
		mock_exit.side_effect = ExpectedExit()

		# test
		try:
			self.daemon._double_fork()
			self.fail("Expected an exit")
		except ExpectedExit:
			pass

		# assert
		self.assertListEqual(mock_fork.mock_calls, [mock.call()])
		self.assertListEqual(mock_exit.mock_calls, [mock.call(1)])
		self.assertEqual(len(self.error_method.mock_calls), 1)

	@mock.patch("os.fork", create=True)
	@mock.patch("os.chdir")
	@mock.patch("os.setsid", create=True)
	@mock.patch("os.umask")
	@mock.patch("sys.exit")
	def test_double_fork_failed_second(self, mock_exit, mock_umask, mock_setsid, mock_chdir, mock_fork):
		# setup
		mock_fork.side_effect = [1234, OSError()]
		mock_exit.side_effect = [None, ExpectedExit()]

		# test
		try:
			self.daemon._double_fork()
			self.fail("Expected an exit")
		except ExpectedExit:
			pass

		# assert
		self.assertEqual(mock_fork.call_count, 2)
		self.assertListEqual(mock_exit.mock_calls, [mock.call(0), mock.call(1)])
		self.assertEqual(self.error_method.call_count, 1)
		mock_chdir.assert_called_once_with("/")
		mock_setsid.assert_called_once_with()
		mock_umask.assert_called_once_with(0o002)

	@mock.patch("sys.stdin")
	@mock.patch("sys.stdout")
	@mock.patch("sys.stderr")
	@mock.patch("os.devnull")
	@mock.patch("__builtin__.open")
	@mock.patch("os.dup2")
	def test_redirect_io(self, mock_dup2, mock_open, mock_devnull, mock_stderr, mock_stdout, mock_stdin):
		# setup
		mock_stdin.fileno.return_value = "stdin"
		mock_stdout.fileno.return_value = "stdout"
		mock_stderr.fileno.return_value = "stderr"

		new_stdin = mock.MagicMock()
		new_stdout = mock.MagicMock()
		new_stderr = mock.MagicMock()
		new_stdin.fileno.return_value = "new_stdin"
		new_stdout.fileno.return_value = "new_stdout"
		new_stderr.fileno.return_value = "new_stderr"

		mock_open.side_effect = [new_stdin, new_stdout, new_stderr]

		# test
		self.daemon._redirect_io()

		# assert
		mock_stdout.flush.assert_called_once_with()
		mock_stderr.flush.assert_called_once_with()

		self.assertListEqual(mock_open.mock_calls,
		                     [mock.call(mock_devnull, "r"),
		                      mock.call(mock_devnull, "a+"),
		                      mock.call(mock_devnull, "a+")])
		self.assertListEqual(mock_dup2.mock_calls,
		                     [mock.call("new_stdin", "stdin"),
		                      mock.call("new_stdout", "stdout"),
		                      mock.call("new_stderr", "stderr")])

	@mock.patch("os.getpid")
	@mock.patch("signal.signal")
	def test_daemonize(self, mock_signal, mock_getpid):
		# setup
		self.daemon._double_fork = mock.MagicMock()
		self.daemon._redirect_io = mock.MagicMock()
		self.daemon.set_pid = mock.MagicMock()

		pid = 1234
		mock_getpid.return_value = pid

		# test
		self.daemon.start()

		# assert
		import signal

		self.daemon._double_fork.assert_called_once_with()
		self.daemon._redirect_io.assert_called_once_with()
		self.daemon.set_pid.assert_called_once_with(str(pid))

	def test_terminated(self):
		# setup
		self.daemon.remove_pidfile = mock.MagicMock()

		# test
		self.daemon.terminated()

		# assert
		self.daemon.remove_pidfile.assert_called_once_with()

	def test_start(self):
		# setup
		self.daemon._daemonize = mock.MagicMock()

		self.daemon.get_pid = mock.MagicMock()
		self.daemon.get_pid.return_value = None

		# test
		self.daemon.start()

		# assert
		self.daemon._daemonize.assert_called_once_with()
		self.daemon.get_pid.assert_called_once_with()
		self.echo_method.assert_called_once_with("Starting daemon...")
		self.assertTrue(self.run_method.called)

	@mock.patch("sys.exit")
	def test_start_running(self, mock_exit):
		# setup
		pid = "1234"
		self.daemon.get_pid = mock.MagicMock()
		self.daemon.get_pid.return_value = pid

		mock_exit.side_effect = ExpectedExit()

		# test
		try:
			self.daemon.start()
			self.fail("Expected an exit")
		except ExpectedExit:
			pass

		# assert
		self.daemon.get_pid.assert_called_once_with()
		self.assertTrue(self.error_method.called)
		mock_exit.assert_called_once_with(1)

	@mock.patch("os.kill")
	@mock.patch("time.sleep")
	def test_stop(self, mock_sleep, mock_kill):
		import signal

		# setup
		pid = "1234"
		self.daemon.get_pid = mock.MagicMock()
		self.daemon.get_pid.return_value = pid
		self.daemon.remove_pidfile = mock.MagicMock()

		mock_kill.side_effect = [None, OSError("No such process")]

		# test
		self.daemon.stop()

		# assert
		self.daemon.get_pid.assert_called_once_with()
		self.assertListEqual(mock_kill.mock_calls,
		                     [mock.call(pid, signal.SIGTERM),
		                      mock.call(pid, signal.SIGTERM)])
		mock_sleep.assert_called_once_with(0.1)
		self.daemon.remove_pidfile.assert_called_once_with()

	@mock.patch("sys.exit")
	def test_stop_not_running(self, mock_exit):
		# setup
		self.daemon.get_pid = mock.MagicMock()
		self.daemon.get_pid.return_value = None
		mock_exit.side_effect = ExpectedExit()

		# test
		try:
			self.daemon.stop()
			self.fail("Expected an exit")
		except ExpectedExit:
			pass

		# assert
		self.daemon.get_pid.assert_called_once_with()
		self.assertEqual(self.error_method.call_count, 1)
		mock_exit.assert_called_once_with(1)

	@mock.patch("sys.exit")
	def test_stop_not_running_no_error(self, mock_exit):
		# setup
		self.daemon.get_pid = mock.MagicMock()
		self.daemon.get_pid.return_value = None

		# test
		self.daemon.stop(check_running=False)

		# assert
		self.daemon.get_pid.assert_called_once_with()
		self.assertFalse(mock_exit.called)

	@mock.patch("os.kill")
	@mock.patch("sys.exit")
	def test_stop_unknown_error(self, mock_exit, mock_kill):
		# setup
		pid = "1234"
		self.daemon.get_pid = mock.MagicMock()
		self.daemon.get_pid.return_value = pid

		mock_exit.side_effect = ExpectedExit()
		mock_kill.side_effect = OSError("Unknown")

		# test
		try:
			self.daemon.stop()
			self.fail("Expected an exit")
		except ExpectedExit:
			pass

		# assert
		self.assertTrue(self.error_method.called)
		mock_exit.assert_called_once_with(1)

	def test_restart(self):
		# setup
		self.daemon.start = mock.MagicMock()
		self.daemon.stop = mock.MagicMock()

		# test
		self.daemon.restart()

		# assert
		self.daemon.stop.assert_called_once_with(check_running=False)
		self.daemon.start.assert_called_once_with()

	def test_status_running(self):
		# setup
		self.daemon.is_running = mock.MagicMock()
		self.daemon.is_running.return_value = True

		# test
		self.daemon.status()

		# assert
		self.echo_method.assert_called_once_with("Daemon is running")

	def test_status_not_running(self):
		# setup
		self.daemon.is_running = mock.MagicMock()
		self.daemon.is_running.return_value = False

		# test
		self.daemon.status()

		# assert
		self.echo_method.assert_called_once_with("Daemon is not running")

	@mock.patch("os.kill")
	def test_is_running_true(self, mock_kill):
		# setup
		pid = "1234"
		self.daemon.get_pid = mock.MagicMock()
		self.daemon.get_pid.return_value = pid

		self.daemon.remove_pidfile = mock.MagicMock()

		# test
		result = self.daemon.is_running()

		# assert
		self.assertTrue(result)
		mock_kill.assert_called_once_with(pid, 0)
		self.assertFalse(self.daemon.remove_pidfile.called)
		self.assertFalse(self.error_method.called)

	def test_is_running_false_no_pid(self):
		# setup
		self.daemon.get_pid = mock.MagicMock()
		self.daemon.get_pid.return_value = None

		# test
		result = self.daemon.is_running()

		# assert
		self.assertFalse(result)

	@mock.patch("os.kill")
	def test_is_running_false_pidfile_removed(self, mock_kill):
		# setup
		pid = "1234"
		self.daemon.get_pid = mock.MagicMock()
		self.daemon.get_pid.return_value = pid

		mock_kill.side_effect = OSError()

		self.daemon.remove_pidfile = mock.MagicMock()

		# test
		result = self.daemon.is_running()

		# assert
		self.assertFalse(result)
		mock_kill.assert_called_once_with(pid, 0)
		self.daemon.remove_pidfile.assert_called_once_with()
		self.assertFalse(self.error_method.called)

	@mock.patch("os.kill")
	def test_is_running_false_pidfile_error(self, mock_kill):
		# setup
		pid = "1234"
		self.daemon.get_pid = mock.MagicMock()
		self.daemon.get_pid.return_value = pid

		mock_kill.side_effect = OSError()

		self.daemon.remove_pidfile = mock.MagicMock()
		self.daemon.remove_pidfile.side_effect = IOError()

		# test
		result = self.daemon.is_running()

		# assert
		self.assertFalse(result)
		mock_kill.assert_called_once_with(pid, 0)
		self.daemon.remove_pidfile.assert_called_once_with()
		self.assertTrue(self.error_method.called)

	def test_get_pid(self):
		# setup
		pid = 1234

		# test
		with mock.patch("__builtin__.open", mock.mock_open(read_data="{}\n".format(pid)), create=True) as m:
			result = self.daemon.get_pid()

		# assert
		self.assertEqual(result, pid)
		m.assert_called_once_with(self.pidfile, "r")

	def test_get_pid_ioerror(self):
		# setup
		handle = mock.MagicMock()
		handle.__enter__.side_effect = IOError()

		# test
		with mock.patch("__builtin__.open", mock.mock_open(), create=True) as m:
			result = self.daemon.get_pid()

		# assert
		self.assertIsNone(result)
		m.assert_called_once_with(self.pidfile, "r")

	def test_get_pid_valueerror(self):
		# setup
		pid = "not an integer"

		# test
		with mock.patch("__builtin__.open", mock.mock_open(read_data="{}\n".format(pid)), create=True) as m:
			result = self.daemon.get_pid()

		# assert
		self.assertIsNone(result)
		m.assert_called_once_with(self.pidfile, "r")

	def test_set_pid(self):
		# setup
		pid = "1234"

		# test
		with mock.patch("__builtin__.open", mock.mock_open(), create=True) as m:
			self.daemon.set_pid(pid)

		# assert
		m.assert_called_once_with(self.pidfile, "w+")
		handle = m()
		handle.write.assert_called_once_with("{}\n".format(pid))

	def test_set_pid_int(self):
		# setup
		pid = 1234

		# test
		with mock.patch("__builtin__.open", mock.mock_open(), create=True) as m:
			self.daemon.set_pid(pid)

		# assert
		m.assert_called_once_with(self.pidfile, "w+")
		handle = m()
		handle.write.assert_called_once_with("{}\n".format(pid))

	@mock.patch("os.path.isfile")
	@mock.patch("os.remove")
	def test_remove_pidfile_exists(self, mock_remove, mock_isfile):
		# setup
		mock_isfile.return_value = True

		# test
		self.daemon.remove_pidfile()

		# assert
		mock_isfile.assert_called_once_with(self.pidfile)
		mock_remove.assert_called_once_with(self.pidfile)

	@mock.patch("os.path.isfile")
	@mock.patch("os.remove")
	def test_remove_pidfile_doesnt_exist(self, mock_remove, mock_isfile):
		# setup
		mock_isfile.return_value = False

		# test
		self.daemon.remove_pidfile()

		# assert
		mock_isfile.assert_called_once_with(self.pidfile)
		self.assertFalse(mock_remove.called)
