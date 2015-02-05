import unittest
import mock

import octoprint.plugin
import octoprint.plugin.core


class PluginTestCase(unittest.TestCase):

	def setUp(self):
		import logging
		logging.basicConfig(level=logging.DEBUG)

		# TODO mock pkg_resources to return some defined entry_points

		import os
		self.plugin_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), "_plugins")

		plugin_folders = [self.plugin_folder]
		plugin_types = [octoprint.plugin.SettingsPlugin, octoprint.plugin.StartupPlugin]
		plugin_entry_points = None
		self.plugin_manager = octoprint.plugin.core.PluginManager(plugin_folders, plugin_types, plugin_entry_points, plugin_disabled_list=[], logging_prefix="logging_prefix.")

	def test_plugin_loading(self):
		self.assertEquals(4, len(self.plugin_manager.plugins))
		self.assertEquals(1, len(self.plugin_manager.plugin_hooks))
		self.assertEquals(3, len(self.plugin_manager.plugin_implementations))
		self.assertEquals(2, len(self.plugin_manager.plugin_implementations_by_type))

		self.assertTrue("octoprint.core.startup" in self.plugin_manager.plugin_hooks)
		self.assertEquals(1, len(self.plugin_manager.plugin_hooks["octoprint.core.startup"]))

		self.assertTrue(octoprint.plugin.StartupPlugin in self.plugin_manager.plugin_implementations_by_type)
		self.assertEquals(2, len(self.plugin_manager.plugin_implementations_by_type[octoprint.plugin.StartupPlugin]))

		self.assertTrue(octoprint.plugin.SettingsPlugin in self.plugin_manager.plugin_implementations_by_type)
		self.assertEquals(2, len(self.plugin_manager.plugin_implementations_by_type[octoprint.plugin.SettingsPlugin]))

	def test_plugin_initializing(self):

		def test_factory(name, implementation):
			return dict(test_factory="test_factory_%s" % name)

		def verify_injection_order(name, implementation):
			self.assertTrue(hasattr(implementation, "_basefolder"))
			return dict()

		additional_injects = dict(
			additional_inject="additional_inject"
		)
		additional_inject_factories = [test_factory, verify_injection_order]
		self.plugin_manager.initialize_implementations(
			additional_injects=additional_injects,
			additional_inject_factories=additional_inject_factories
		)

		all_implementations = self.plugin_manager.plugin_implementations
		self.assertEquals(3, len(all_implementations))
		for name, implementations in all_implementations.items():
			self.assertEquals(1, len(implementations))
			impl = implementations.pop()

			self.assertTrue(name in self.plugin_manager.plugins)
			plugin = self.plugin_manager.plugins[name]

			# test that the standard fields were properly initialized
			self.assertTrue(hasattr(impl, "_identifier"))
			self.assertEquals(name, impl._identifier)
			self.assertTrue(hasattr(impl, "_plugin_name"))
			self.assertEquals(plugin.name, impl._plugin_name)
			self.assertTrue(hasattr(impl, "_plugin_version"))
			self.assertEquals(plugin.version, impl._plugin_version)
			self.assertTrue(hasattr(impl, "_logger"))
			self.assertIsNotNone(impl._logger)
			self.assertEquals("logging_prefix.%s" % name, impl._logger.name)
			self.assertTrue(hasattr(impl, "_basefolder"))
			self.assertTrue(impl._basefolder.startswith(self.plugin_folder))

			# test that the additional injects were properly injected
			self.assertTrue(hasattr(impl, "_additional_inject"))
			self.assertEquals("additional_inject", impl._additional_inject)

			# test that the injection factory was properly executed and the result injected
			self.assertTrue(hasattr(impl, "_test_factory"))
			self.assertEquals("test_factory_%s" % name, impl._test_factory)


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

	def test_client_registration(self):
		client = mock.Mock()

		self.assertEquals(0, len(self.plugin_manager.registered_clients))

		self.plugin_manager.register_client(client)

		self.assertEquals(1, len(self.plugin_manager.registered_clients))
		self.assertIn(client, self.plugin_manager.registered_clients)

		self.plugin_manager.unregister_client(client)

		self.assertEquals(0, len(self.plugin_manager.registered_clients))
		self.assertNotIn(client, self.plugin_manager.registered_clients)

	def test_send_plugin_message(self):
		client1 = mock.Mock()
		client2 = mock.Mock()

		self.plugin_manager.register_client(client1)
		self.plugin_manager.register_client(client2)

		plugin = "some plugin"
		data = "some data"
		self.plugin_manager.send_plugin_message(plugin, data)
		client1.sendPluginMessage.assert_called_once_with(plugin, data)
		client2.sendPluginMessage.assert_called_once_with(plugin, data)

