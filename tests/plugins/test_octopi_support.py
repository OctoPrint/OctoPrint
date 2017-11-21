
import unittest
import ddt
import mock

OCTOPI_VERSION = "0.14.0"

CPUINFO = """
processor       : 0
model name      : ARMv7 Processor rev 4 (v7l)
BogoMIPS        : 38.40
Features        : half thumb fastmult vfp edsp neon vfpv3 tls vfpv4 idiva idivt vfpd32 lpae evtstrm crc32
CPU implementer : 0x41
CPU architecture: 7
CPU variant     : 0x0
CPU part        : 0xd03
CPU revision    : 4

processor       : 1
model name      : ARMv7 Processor rev 4 (v7l)
BogoMIPS        : 38.40
Features        : half thumb fastmult vfp edsp neon vfpv3 tls vfpv4 idiva idivt vfpd32 lpae evtstrm crc32
CPU implementer : 0x41
CPU architecture: 7
CPU variant     : 0x0
CPU part        : 0xd03
CPU revision    : 4

processor       : 2
model name      : ARMv7 Processor rev 4 (v7l)
BogoMIPS        : 38.40
Features        : half thumb fastmult vfp edsp neon vfpv3 tls vfpv4 idiva idivt vfpd32 lpae evtstrm crc32
CPU implementer : 0x41
CPU architecture: 7
CPU variant     : 0x0
CPU part        : 0xd03
CPU revision    : 4

processor       : 3
model name      : ARMv7 Processor rev 4 (v7l)
BogoMIPS        : 38.40
Features        : half thumb fastmult vfp edsp neon vfpv3 tls vfpv4 idiva idivt vfpd32 lpae evtstrm crc32
CPU implementer : 0x41
CPU architecture: 7
CPU variant     : 0x0
CPU part        : 0xd03
CPU revision    : 4

Hardware        : BCM2835
Revision        : a02082
Serial          : 000000000abcdef1
"""

@ddt.ddt
class OctoPiSupportTestCase(unittest.TestCase):

	def test_get_octopi_version(self):
		from octoprint.plugins.octopi_support import get_octopi_version

		with mock.patch("__builtin__.open", mock.mock_open(), create=True) as m:
			m.return_value.readline.return_value = OCTOPI_VERSION
			version = get_octopi_version()

		m.assert_called_once_with("/etc/octopi_version", "r")
		self.assertEqual(version, "0.14.0")

	def test_get_pi_cpuinfo(self):
		from octoprint.plugins.octopi_support import get_pi_cpuinfo

		with mock.patch("__builtin__.open", mock.mock_open(), create=True) as m:
			m.return_value.__iter__.return_value = CPUINFO.splitlines()
			cpuinfo = get_pi_cpuinfo()

		m.assert_called_once_with("/proc/cpuinfo")
		self.assertDictEqual(cpuinfo, dict(hardware="BCM2835", revision="a02082", serial="000000000abcdef1"))

	@ddt.data(
		("BCM2835", "a02082", "3B"),
		("BCM2835", "1000a02082", "3B"),

		# failures
		("something else", "a02082", "unknown"),
		("BCM2835", "aabbccdd", "unknown")
	)
	@ddt.unpack
	def test_get_pi_model(self, hardware, revision, expected):
		from octoprint.plugins.octopi_support import get_pi_model
		actual = get_pi_model(hardware, revision)
		self.assertEqual(actual, expected)
