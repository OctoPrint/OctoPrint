# coding=utf-8
"""
Unit tests for ``octoprint.filemanager.``.
"""

from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest
import mock

import octoprint.filemanager

class FilemanagerUtilTest(unittest.TestCase):

	def setUp(self):
		# mock plugin manager
		self.plugin_manager_patcher = mock.patch("octoprint.plugin.plugin_manager")
		self.plugin_manager_getter = self.plugin_manager_patcher.start()

		self.plugin_manager = mock.MagicMock()

		hook_extensions = dict(
			some_plugin=lambda: dict(dict(machinecode=dict(foo=["foo", "f"]))),
			other_plugin=lambda: dict(dict(model=dict(amf=["amf"]))),
			mime_map=lambda: dict(
				mime_map=dict(
					mime_map_yes=octoprint.filemanager.ContentTypeMapping(["mime_map_yes"], "application/mime_map_yes")
				)
			),
			mime_detect=lambda: dict(
				dict(
					machinecode=dict(
						mime_detect_yes=octoprint.filemanager.ContentTypeDetector(["mime_detect_yes"], lambda x: "application/mime_detect_yes"),
						mime_detect_no=octoprint.filemanager.ContentTypeDetector(["mime_detect_no"], lambda x: None)
					)
				)
			)
		)
		self.plugin_manager.get_hooks.return_value = hook_extensions

		self.plugin_manager_getter.return_value = self.plugin_manager

	def tearDown(self):
		self.plugin_manager_patcher.stop()

	def test_full_extension_tree(self):
		full = octoprint.filemanager.full_extension_tree()
		self.assertTrue("machinecode" in full)
		self.assertTrue("gcode" in full["machinecode"])
		self.assertTrue(isinstance(full["machinecode"]["gcode"], octoprint.filemanager.ContentTypeMapping))
		self.assertItemsEqual(["gcode", "gco", "g"], full["machinecode"]["gcode"].extensions)
		self.assertTrue("foo" in full["machinecode"])
		self.assertTrue(isinstance(full["machinecode"]["foo"], list))
		self.assertItemsEqual(["f", "foo"], full["machinecode"]["foo"])

		self.assertTrue("model" in full)
		self.assertTrue("stl" in full["model"])
		self.assertTrue(isinstance(full["model"]["stl"], octoprint.filemanager.ContentTypeMapping))
		self.assertItemsEqual(["stl"], full["model"]["stl"].extensions)
		self.assertTrue("amf" in full["model"])
		self.assertTrue(isinstance(full["model"]["amf"], list))
		self.assertItemsEqual(["amf"], full["model"]["amf"])

	def test_get_mimetype(self):
		self.assertEquals(octoprint.filemanager.get_mime_type("foo.stl"), "application/sla")
		self.assertEquals(octoprint.filemanager.get_mime_type("foo.gcode"), "text/plain")
		self.assertEquals(octoprint.filemanager.get_mime_type("foo.unknown"), "application/octet-stream")
		self.assertEquals(octoprint.filemanager.get_mime_type("foo.mime_map_yes"), "application/mime_map_yes")
		self.assertEquals(octoprint.filemanager.get_mime_type("foo.mime_map_no"), "application/octet-stream")
		self.assertEquals(octoprint.filemanager.get_mime_type("foo.mime_detect_yes"), "application/mime_detect_yes")
		self.assertEquals(octoprint.filemanager.get_mime_type("foo.mime_detect_no"), "application/octet-stream")

	def test_valid_file_type(self):
		self.assertTrue(octoprint.filemanager.valid_file_type("foo.stl", type="model"))
		self.assertTrue(octoprint.filemanager.valid_file_type("foo.stl", type="stl"))
		self.assertFalse(octoprint.filemanager.valid_file_type("foo.stl", type="machinecode"))
		self.assertTrue(octoprint.filemanager.valid_file_type("foo.foo", type="machinecode"))
		self.assertTrue(octoprint.filemanager.valid_file_type("foo.foo", type="foo"))
		self.assertTrue(octoprint.filemanager.valid_file_type("foo.foo"))
		self.assertTrue(octoprint.filemanager.valid_file_type("foo.mime_map_yes"))
		self.assertTrue(octoprint.filemanager.valid_file_type("foo.mime_detect_yes"))
		self.assertFalse(octoprint.filemanager.valid_file_type("foo.unknown"))

	def test_get_file_type(self):
		self.assertEquals(["machinecode", "gcode"], octoprint.filemanager.get_file_type("foo.gcode"))
		self.assertEquals(["machinecode", "gcode"], octoprint.filemanager.get_file_type("foo.gco"))
		self.assertEquals(["machinecode", "foo"], octoprint.filemanager.get_file_type("foo.f"))
		self.assertEquals(["model", "stl"], octoprint.filemanager.get_file_type("foo.stl"))
		self.assertEquals(["model", "amf"], octoprint.filemanager.get_file_type("foo.amf"))
		self.assertIsNone(octoprint.filemanager.get_file_type("foo.unknown"))

	def test_hook_failure(self):
		def hook():
			raise RuntimeError("Boo!")
		self.plugin_manager.get_hooks.return_value = dict(hook=hook)

		with mock.patch("octoprint.filemanager.logging") as patched_logging:
			logger = mock.MagicMock()
			patched_logging.getLogger.return_value = logger

			octoprint.filemanager.get_all_extensions()

			self.assertEquals(1, len(logger.mock_calls))
