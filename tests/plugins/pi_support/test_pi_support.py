
import unittest
import ddt
import mock

OCTOPI_VERSION = "0.14.0"

DT_MODEL = "Raspberry Pi Model F Rev 1.1"

VCGENCMD = "/usr/bin/vcgencmd get_throttled"

class PiSupportTestCase(unittest.TestCase):

	def test_get_octopi_version(self):
		from octoprint.plugins.pi_support import get_octopi_version

		with mock.patch("__builtin__.open", mock.mock_open(), create=True) as m:
			m.return_value.readline.return_value = OCTOPI_VERSION
			version = get_octopi_version()

		m.assert_called_once_with("/etc/octopi_version", "r")
		self.assertEqual(version, OCTOPI_VERSION)

	def test_get_proc_dt_model(self):
		from octoprint.plugins.pi_support import get_proc_dt_model

		with mock.patch("__builtin__.open", mock.mock_open(), create=True) as m:
			m.return_value.readline.return_value = DT_MODEL
			model = get_proc_dt_model()

		m.assert_called_once_with("/proc/device-tree/model", "r")
		self.assertEqual(model, DT_MODEL)

	def test_get_vcgencmd_throttle_state(self):
		from octoprint.plugins.pi_support import get_vcgencmd_throttled_state

		with mock.patch("sarge.get_stdout", mock.MagicMock()) as m:
			m.return_value = "throttled=0x70005"
			state = get_vcgencmd_throttled_state(VCGENCMD)

		m.assert_called_once_with(VCGENCMD)
		self.assertTrue(state.current_undervoltage)
		self.assertFalse(state.current_overheat)
		self.assertTrue(state.current_issue)
		self.assertTrue(state.past_undervoltage)
		self.assertTrue(state.past_overheat)
		self.assertTrue(state.past_issue)

	def test_get_vcgencmd_throttle_state_unparseable1(self):
		from octoprint.plugins.pi_support import get_vcgencmd_throttled_state

		with mock.patch("sarge.get_stdout", mock.MagicMock()) as m:
			m.return_value = "invalid"

			try:
				get_vcgencmd_throttled_state(VCGENCMD)
			except ValueError:
				# expected
				pass
			else:
				self.fail("Expected ValueError")

	def test_get_vcgencmd_throttle_state_unparseable2(self):
		from octoprint.plugins.pi_support import get_vcgencmd_throttled_state

		with mock.patch("sarge.get_stdout", mock.MagicMock()) as m:
			m.return_value = "throttled=0xinvalid"

			try:
				get_vcgencmd_throttled_state(VCGENCMD)
			except ValueError:
				# expected
				pass
			else:
				self.fail("Expected ValueError")


@ddt.ddt
class ThrottleStateTestCase(unittest.TestCase):

	@ddt.data(
		(0x00000, dict(_undervoltage=False,
		               _freq_capped=False,
		               _throttled=False,
		               _past_undervoltage=False,
		               _past_freq_capped=False,
		               _past_throttled=False,
		               current_undervoltage=False,
		               past_undervoltage=False,
		               current_overheat=False,
		               past_overheat=False,
		               current_issue=False,
		               past_issue=False)),

		(0x50005, dict(_undervoltage=True,
		               _freq_capped=False,
		               _throttled=True,
		               _past_undervoltage=True,
		               _past_freq_capped=False,
		               _past_throttled=True,
		               current_undervoltage=True,
		               past_undervoltage=True,
		               current_overheat=False,
		               past_overheat=False,
		               current_issue=True,
		               past_issue=True)),

		(0x50000, dict(_undervoltage=False,
		               _freq_capped=False,
		               _throttled=False,
		               _past_undervoltage=True,
		               _past_freq_capped=False,
		               _past_throttled=True,
		               current_undervoltage=False,
		               past_undervoltage=True,
		               current_overheat=False,
		               past_overheat=False,
		               current_issue=False,
		               past_issue=True)),

		(0x00006, dict(_undervoltage=False,
		               _freq_capped=True,
		               _throttled=True,
		               _past_undervoltage=False,
		               _past_freq_capped=False,
		               _past_throttled=False,
		               current_undervoltage=False,
		               past_undervoltage=False,
		               current_overheat=True,
		               past_overheat=False,
		               current_issue=True,
		               past_issue=False)),
	)
	@ddt.unpack
	def test_conversion(self, input, expected_flags):
		from octoprint.plugins.pi_support import ThrottleState

		output = ThrottleState.from_value(input)

		for key, value in expected_flags.items():
			self.assertEqual(getattr(output, key), value)

	def test_as_dict(self):
		from octoprint.plugins.pi_support import ThrottleState

		state = ThrottleState(undervoltage=True, throttled=True, past_undervoltage=True, past_freq_capped=True, past_throttled=True)

		self.assertDictEqual(state.as_dict(), dict(current_undervoltage=True,
		                                           past_undervoltage=True,
		                                           current_overheat=False,
		                                           past_overheat=True,
		                                           current_issue=True,
		                                           past_issue=True,
		                                           raw_value=-1))
