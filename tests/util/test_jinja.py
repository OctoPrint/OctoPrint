# coding=utf-8
from __future__ import absolute_import

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import unittest
import os
import jinja2

from ddt import ddt, data, unpack

import octoprint.util.jinja

NONE_FILTER = None
HIDDEN_FILTER = lambda x: not os.path.basename(x).startswith(".")
NO_TXT_FILTER = lambda x: x.endswith(".txt")
COMBINED_FILTER = lambda x: HIDDEN_FILTER(x) and NO_TXT_FILTER(x)

@ddt
class FilteredFileSystemLoaderTest(unittest.TestCase):

	def setUp(self):
		self.basepath = os.path.join(os.path.abspath(os.path.dirname(__file__)), "_files", "jinja_test_data")
		self.environment = jinja2.Environment()

	def loader_factory(self, path_filter):
		return octoprint.util.jinja.FilteredFileSystemLoader(self.basepath,
		                                                     path_filter=path_filter)

	@data(
		(NONE_FILTER, [".hidden_everywhere.txt", "normal_text.txt", "not_a_text.dat"]),
		(HIDDEN_FILTER, ["normal_text.txt", "not_a_text.dat"]),
		(NO_TXT_FILTER, [".hidden_everywhere.txt", "normal_text.txt"]),
		(COMBINED_FILTER, ["normal_text.txt"])
	)
	@unpack
	def test_list_templates(self, path_filter, expected):
		loader = self.loader_factory(path_filter=path_filter)
		templates = loader.list_templates()
		self.assertListEqual(templates, expected)

	@data(
		(NONE_FILTER, ((".hidden_everywhere.txt", True),
		               ("normal_text.txt", True),
		               ("not_a_text.dat", True))),
		(HIDDEN_FILTER, ((".hidden_everywhere.txt", False),
		                 ("normal_text.txt", True),
		                 ("not_a_text.dat", True))),
		(NO_TXT_FILTER, ((".hidden_everywhere.txt", True),
		                 ("normal_text.txt", True),
		                 ("not_a_text.dat", False))),
		(COMBINED_FILTER, ((".hidden_everywhere.txt", False),
		                   ("normal_text.txt", True),
		                   ("not_a_text.dat", False)))
	)
	@unpack
	def test_get_source_none_filter(self, path_filter, param_sets):
		loader = self.loader_factory(path_filter=path_filter)
		for param_set in param_sets:
			template, success = param_set
			if success:
				self._test_get_source_success(loader, template)
			else:
				self._test_get_source_notfound(loader, template)

	def _test_get_source_success(self, loader, template):
		loader.get_source(self.environment, template)

	def _test_get_source_notfound(self, loader, template):
		try:
			loader.get_source(self.environment, template)
			self.fail("Expected an exception")
		except jinja2.TemplateNotFound:
			pass
