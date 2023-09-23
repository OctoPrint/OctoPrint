"""
Unit tests for Python bugs.
"""

import unittest
from datetime import datetime


class PythonBugsTest(unittest.TestCase):
    """Tests for Python bugs"""

    def test_datetime_fromtimestamp_accepts_arguments_below_86400(self):
        """
        Python bug 29097 affecting versions 3.6 and 3.7
        See https://bugs.python.org/issue29097
        Testing that it's safe to supply arguments below 86400 to datetime.fromtimestamp() starting v3.8
        """
        for subject in [0, 1, 100, 1000, 86000, 86399, 86400]:
            self.assertIsInstance(datetime.fromtimestamp(subject), datetime)
