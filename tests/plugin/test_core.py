import unittest
import mock
import ddt

import octoprint.plugin
import octoprint.plugin.core

@ddt.ddt
class PluginTestCase(unittest.TestCase):

	def setUp(self):
		import logging
		logging.basicConfig(level=logging.DEBUG)

		# TODO mock pkg_resources to return some defined entry_points

		import os
		self.plugin_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), "_plugins")

		plugin_folders = [self.plugin_folder]
		plugin_types = [octoprint.plugin.SettingsPlugin,
		                octoprint.plugin.StartupPlugin,
		                octoprint.plugin.AssetPlugin]
		plugin_entry_points = None
		self.plugin_manager = octoprint.plugin.core.PluginManager(plugin_folders,
		                                                          plugin_types,
		                                                          plugin_entry_points,
		                                                          plugin_disabled_list=[],
		                                                          logging_prefix="logging_prefix.")
		self.plugin_manager.reload_plugins(startup=True, initialize_implementations=False)
		self.plugin_manager.initialize_implementations()

	def test_plugin_loading(self):
		self.assertEqual(7, len(self.plugin_manager.enabled_plugins))
		self.assertEqual(2, len(self.plugin_manager.plugin_hooks))
		self.assertEqual(4, len(self.plugin_manager.plugin_implementations))
		self.assertEqual(3, len(self.plugin_manager.plugin_implementations_by_type))

		# hook_plugin
		self.assertTrue("octoprint.core.startup" in self.plugin_manager.plugin_hooks)
		self.assertEqual(1, len(self.plugin_manager.plugin_hooks["octoprint.core.startup"]))

		# ordered hook plugins
		self.assertTrue("some.ordered.callback" in self.plugin_manager.plugin_hooks)
		self.assertEqual(3, len(self.plugin_manager.plugin_hooks["some.ordered.callback"]))

		# TestStartupPlugin & TestMixedPlugin
		self.assertTrue(octoprint.plugin.StartupPlugin in self.plugin_manager.plugin_implementations_by_type)
		self.assertEqual(2, len(self.plugin_manager.plugin_implementations_by_type[octoprint.plugin.StartupPlugin]))

		# TestSettingsPlugin & TestMixedPlugin
		self.assertTrue(octoprint.plugin.SettingsPlugin in self.plugin_manager.plugin_implementations_by_type)
		self.assertEqual(2, len(self.plugin_manager.plugin_implementations_by_type[octoprint.plugin.SettingsPlugin]))

		# TestDeprecatedAssetPlugin, NOT TestSecondaryDeprecatedAssetPlugin
		self.assertTrue(octoprint.plugin.AssetPlugin in self.plugin_manager.plugin_implementations_by_type)
		self.assertEqual(1, len(self.plugin_manager.plugin_implementations_by_type[octoprint.plugin.AssetPlugin]))

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
		self.assertEqual(4, len(all_implementations))
		for name, impl in all_implementations.items():
			self.assertTrue(name in self.plugin_manager.enabled_plugins)
			plugin = self.plugin_manager.enabled_plugins[name]

			# test that the standard fields were properly initialized
			self.assertTrue(hasattr(impl, "_identifier"))
			self.assertEqual(name, impl._identifier)
			self.assertTrue(hasattr(impl, "_plugin_name"))
			self.assertEqual(plugin.name, impl._plugin_name)
			self.assertTrue(hasattr(impl, "_plugin_version"))
			self.assertEqual(plugin.version, impl._plugin_version)
			self.assertTrue(hasattr(impl, "_logger"))
			self.assertIsNotNone(impl._logger)
			self.assertEqual("logging_prefix.%s" % name, impl._logger.name)
			self.assertTrue(hasattr(impl, "_basefolder"))
			self.assertTrue(impl._basefolder.startswith(self.plugin_folder))

			# test that the additional injects were properly injected
			self.assertTrue(hasattr(impl, "_additional_inject"))
			self.assertEqual("additional_inject", impl._additional_inject)

			# test that the injection factory was properly executed and the result injected
			self.assertTrue(hasattr(impl, "_test_factory"))
			self.assertEqual("test_factory_%s" % name, impl._test_factory)


	def test_get_plugin(self):
		plugin = self.plugin_manager.get_plugin("hook_plugin")
		self.assertIsNotNone(plugin)
		self.assertEqual("Hook Plugin", plugin.__plugin_name__)

		plugin = self.plugin_manager.get_plugin("mixed_plugin")
		self.assertIsNotNone(plugin)
		self.assertEqual("Mixed Plugin", plugin.__plugin_name__)

		plugin = self.plugin_manager.get_plugin("unknown_plugin")
		self.assertIsNone(plugin)

	def test_get_plugin_info(self):
		plugin_info = self.plugin_manager.get_plugin_info("hook_plugin")
		self.assertIsNotNone(plugin_info)
		self.assertEqual("Hook Plugin", plugin_info.name)

		plugin_info = self.plugin_manager.get_plugin_info("unknown_plugin")
		self.assertIsNone(plugin_info)

	def test_get_hooks(self):
		hooks = self.plugin_manager.get_hooks("octoprint.core.startup")
		self.assertEqual(1, len(hooks))
		self.assertTrue("hook_plugin" in hooks)
		self.assertEqual("success", hooks["hook_plugin"]())

		hooks = self.plugin_manager.get_hooks("octoprint.printing.print")
		self.assertEqual(0, len(hooks))

	def test_sorted_hooks(self):
		hooks = self.plugin_manager.get_hooks("some.ordered.callback")
		self.assertEqual(3, len(hooks))
		self.assertListEqual(["one_ordered_hook_plugin", "another_ordered_hook_plugin", "hook_plugin"], hooks.keys())

	def test_get_implementations(self):
		implementations = self.plugin_manager.get_implementations(octoprint.plugin.StartupPlugin)
		self.assertListEqual(["mixed_plugin", "startup_plugin"], map(lambda x: x._identifier, implementations))

		implementations = self.plugin_manager.get_implementations(octoprint.plugin.SettingsPlugin)
		self.assertListEqual(["mixed_plugin", "settings_plugin"], map(lambda x: x._identifier, implementations))

		implementations = self.plugin_manager.get_implementations(octoprint.plugin.StartupPlugin, octoprint.plugin.SettingsPlugin)
		self.assertListEqual(["mixed_plugin"], map(lambda x: x._identifier, implementations))

		implementations = self.plugin_manager.get_implementations(octoprint.plugin.AssetPlugin)
		self.assertListEqual(["deprecated_plugin"], map(lambda x: x._identifier, implementations))

	def test_get_filtered_implementations(self):
		implementations = self.plugin_manager.get_filtered_implementations(lambda x: x._identifier.startswith("startup"), octoprint.plugin.StartupPlugin)
		self.assertEqual(1, len(implementations))

	def test_get_sorted_implementations(self):
		implementations = self.plugin_manager.get_implementations(octoprint.plugin.StartupPlugin, sorting_context="sorting_test")
		self.assertListEqual(["startup_plugin", "mixed_plugin"], map(lambda x: x._identifier, implementations))

	def test_client_registration(self):
		def test_client(*args, **kwargs):
			pass

		self.assertEqual(0, len(self.plugin_manager.registered_clients))

		self.plugin_manager.register_message_receiver(test_client)

		self.assertEqual(1, len(self.plugin_manager.registered_clients))
		self.assertIn(test_client, self.plugin_manager.registered_clients)

		self.plugin_manager.unregister_message_receiver(test_client)

		self.assertEqual(0, len(self.plugin_manager.registered_clients))
		self.assertNotIn(test_client, self.plugin_manager.registered_clients)

	def test_send_plugin_message(self):
		client1 = mock.Mock()
		client2 = mock.Mock()

		self.plugin_manager.register_message_receiver(client1.on_plugin_message)
		self.plugin_manager.register_message_receiver(client2.on_plugin_message)

		plugin = "some plugin"
		data = "some data"
		self.plugin_manager.send_plugin_message(plugin, data)
		client1.on_plugin_message.assert_called_once_with(plugin, data)
		client2.on_plugin_message.assert_called_once_with(plugin, data)

	def test_validate_plugin(self):
		self.assertTrue("deprecated_plugin" in self.plugin_manager.enabled_plugins)

		plugin = self.plugin_manager.enabled_plugins["deprecated_plugin"]
		self.assertTrue(hasattr(plugin.instance, plugin.__class__.attr_implementation))
		self.assertFalse(hasattr(plugin.instance, plugin.__class__.attr_implementations))

	@ddt.data(
		(["octoprint.some_hook"], ["octoprint.some_hook", "octoprint.another_hook"], True),
		(["octoprint.*"], ["octoprint.some_hook", "octoprint.another_hook"], True),
		(["octoprint.some_hook"], ["octoprint.another_hook"], False),
		(["octoprint.some_hook"], [], False),
		([], ["octoprint.some_hook"], False)
	)
	@ddt.unpack
	def test_has_any_of_hooks(self, hooks_to_test_for, plugin_hooks, expected):
		plugin = mock.MagicMock()
		plugin.hooks = dict((hook, hook) for hook in plugin_hooks)

		actual = octoprint.plugin.core.PluginManager.has_any_of_hooks(plugin, hooks_to_test_for)
		self.assertEqual(actual, expected)

	def test_has_any_of_hooks_varargs(self):
		plugin = mock.MagicMock()
		plugin.hooks = dict((hook, hook) for hook in ["octoprint.some_hook", "octoprint.another_hook"])

		result = octoprint.plugin.core.PluginManager.has_any_of_hooks(plugin, "octoprint.some_hook", "octoprint.some_other_hook")
		self.assertTrue(result)

	def test_has_any_of_hooks_nohooks(self):
		plugin = mock.MagicMock()

		result = octoprint.plugin.core.PluginManager.has_any_of_hooks(plugin, "octoprint.some_hook", "octoprint.some_other_hook")
		self.assertFalse(result)

	@ddt.data(
		("octoprint.some_hook", ["octoprint.another_hook", "octoprint.some_hook"], True),
		("octoprint.some_hook", ["octoprint.*"], True),
		("octoprint.some_hook", ["octoprint.some_hook*"], True),
		("octoprint.some_hook", ["octoprint.*_hook"], True),
		("octoprint.some_hook", ["octoprint.another_hook.*"], False),
		("", ["octoprint.some_hook"], False),
		(None, ["octoprint.some_hook"], False),
		("octoprint.some_hook", [], False),
		("octoprint.some_hook", None, False),
		("octoprint.some_hook", [None], False)
	)
	@ddt.unpack
	def test_hook_matches_hooks(self, hook, hooks, expected):
		actual = octoprint.plugin.core.PluginManager.hook_matches_hooks(hook, hooks)
		self.assertEqual(actual, expected)

	def test_hook_matches_hooks_varargs(self):
		result = octoprint.plugin.core.PluginManager.hook_matches_hooks("octoprint.some_hook",
		                                                                "octoprint.another_hook", "octoprint.some_hook")
		self.assertTrue(result)

	@ddt.data(
		([octoprint.plugin.RestartNeedingPlugin], [octoprint.plugin.Plugin, octoprint.plugin.RestartNeedingPlugin], True),
		([octoprint.plugin.RestartNeedingPlugin], [octoprint.plugin.Plugin], False),
		([], [octoprint.plugin.Plugin], False),
		([octoprint.plugin.RestartNeedingPlugin], [], False)
	)
	@ddt.unpack
	def test_has_any_of_mixins(self, mixins_to_test_for, plugin_mixins, expected):
		plugin = mock.MagicMock()
		plugin.implementation = mock.MagicMock()

		for mixin in plugin_mixins:
			plugin.implementation.mock_add_spec(mixin)

		actual = octoprint.plugin.core.PluginManager.has_any_of_mixins(plugin, mixins_to_test_for)
		self.assertEqual(actual, expected)

	def test_has_any_of_mixins_varargs(self):
		plugin = mock.MagicMock()
		plugin.implementation = mock.MagicMock()
		plugin.implementation.mock_add_spec(octoprint.plugin.Plugin)
		plugin.implementation.mock_add_spec(octoprint.plugin.RestartNeedingPlugin)

		result = octoprint.plugin.core.PluginManager.has_any_of_mixins(plugin, octoprint.plugin.RestartNeedingPlugin)
		self.assertTrue(result)

	def test_has_any_of_mixins_noimplementation(self):
		plugin = mock.MagicMock()

		result = octoprint.plugin.core.PluginManager.has_any_of_mixins(plugin, octoprint.plugin.RestartNeedingPlugin)
		self.assertFalse(result)
