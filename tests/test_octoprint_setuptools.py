import unittest

import ddt

import octoprint_setuptools


@ddt.ddt
class OctoPrintSetuptoolsTest(unittest.TestCase):
    @ddt.data(
        ("OctoPrint", ["OctoPrint", "flask"], True),
        ("OctoPrint", ["OctoPrint<1.3.7", "flask"], True),
        ("OctoPrint", ["OctoPrint<=1.3.7", "flask"], True),
        ("OctoPrint", ["OctoPrint==1.3.7", "flask"], True),
        ("OctoPrint", ["OctoPrint!=1.3.7", "flask"], True),
        ("OctoPrint", ["OctoPrint>=1.3.7", "flask"], True),
        ("OctoPrint", ["OctoPrint>1.3.7", "flask"], True),
        ("OctoPrint", ["OctoPrint~=1.3.7", "flask"], True),
        ("OctoPrint", ["OctoPrint===1.3.7", "flask"], True),
        ("OctoPrint", ["oCTOpRINT>=1.3.7", "flask"], True),
        ("OctoPrint", ["flask"], False),
        ("OctoPrint", [], False),
        ("OctoPrint", None, False),
        (None, [], False),
    )
    @ddt.unpack
    def test_has_requirement(self, requirement, requirements, expected):
        actual = octoprint_setuptools.has_requirement(requirement, requirements)
        self.assertEqual(actual, expected)
