import unittest

import octoprint.plugin
import octoprint.plugin.core


class PluginTestCase(unittest.TestCase):

	def setUp(self):
		import logging
		logging.basicConfig(level=logging.DEBUG)

		# TODO mock pkg_resources to return some defined entry_points

		import os
		plugin_folders = [os.path.join(os.path.dirname(os.path.realpath(__file__)), "_plugins")]
		plugin_types = [octoprint.plugin.SettingsPlugin, octoprint.plugin.StartupPlugin]
		plugin_entry_points = None
		self.plugin_manager = octoprint.plugin.core.PluginManager(plugin_folders, plugin_types, plugin_entry_points, plugin_disabled_list=[])

	def test_plugin_loading(self):
		self.assertEquals(4, len(self.plugin_manager.plugins))
		self.assertEquals(1, len(self.plugin_manager.plugin_hooks))
		self.assertEquals(2, len(self.plugin_manager.plugin_implementations))

		self.assertTrue("octoprint.core.startup" in self.plugin_manager.plugin_hooks)
		self.assertEquals(1, len(self.plugin_manager.plugin_hooks["octoprint.core.startup"]))

		self.assertTrue(octoprint.plugin.StartupPlugin in self.plugin_manager.plugin_implementations)
		self.assertEquals(2, len(self.plugin_manager.plugin_implementations[octoprint.plugin.StartupPlugin]))

		self.assertTrue(octoprint.plugin.SettingsPlugin in self.plugin_manager.plugin_implementations)
		self.assertEquals(2, len(self.plugin_manager.plugin_implementations[octoprint.plugin.SettingsPlugin]))

	def test_get_plugin(self):
		plugin = self.plugin_manager.get_plugin("hook_plugin")
		self.assertIsNotNone(plugin)
		self.assertEquals("Hook Plugin", plugin.__plugin_name__)

		plugin = self.plugin_manager.get_plugin("mixed_plugin")
		self.assertIsNotNone(plugin)
		self.assertEquals("Mixed Plugin", plugin.__plugin_name__)

		plugin = self.plugin_manager.get_plugin("unknown_plugin")
		self.assertIsNone(plugin)

	def test_get_hooks(self):
		hooks = self.plugin_manager.get_hooks("octoprint.core.startup")
		self.assertEquals(1, len(hooks))
		self.assertTrue("hook_plugin" in hooks)
		self.assertEquals("success", hooks["hook_plugin"]())

		hooks = self.plugin_manager.get_hooks("octoprint.printing.print")
		self.assertEquals(0, len(hooks))

	def test_get_implementation(self):
		implementations = self.plugin_manager.get_implementations(octoprint.plugin.StartupPlugin)
		self.assertEquals(2, len(implementations))
		self.assertTrue('startup_plugin' in implementations)
		self.assertTrue('mixed_plugin' in implementations)

		implementations = self.plugin_manager.get_implementations(octoprint.plugin.SettingsPlugin)
		self.assertEquals(2, len(implementations))
		self.assertTrue('settings_plugin' in implementations)
		self.assertTrue('mixed_plugin' in implementations)

		implementations = self.plugin_manager.get_implementations(octoprint.plugin.StartupPlugin, octoprint.plugin.SettingsPlugin)
		self.assertEquals(1, len(implementations))
		self.assertTrue('mixed_plugin' in implementations)
