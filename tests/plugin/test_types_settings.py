import unittest
from unittest import mock

import octoprint.plugin


class TestSettingsPlugin(unittest.TestCase):
    def setUp(self):
        self.settings = mock.MagicMock()

        self.plugin = octoprint.plugin.SettingsPlugin()
        self.plugin._settings = self.settings

    def test_on_settings_cleanup(self):
        """Tests that after cleanup only minimal config is left in storage."""

        ### setup

        # settings defaults
        defaults = {
            "foo": {"a": 1, "b": 2, "l1": ["some", "list"], "l2": ["another", "list"]},
            "bar": True,
            "fnord": None,
        }
        self.plugin.get_settings_defaults = mock.MagicMock()
        self.plugin.get_settings_defaults.return_value = defaults

        # stored config, containing one redundant entry (bar=True, same as default)
        in_config = {
            "foo": {
                "l1": ["some", "other", "list"],
                "l2": ["another", "list"],
                "l3": ["a", "third", "list"],
            },
            "bar": True,
            "fnord": {"c": 3, "d": 4},
        }
        self.settings.get_all_data.return_value = in_config

        ### execute

        self.plugin.on_settings_cleanup()

        ### assert

        # minimal config (current without redundant value) should have been set
        expected = {
            "foo": {"l1": ["some", "other", "list"], "l3": ["a", "third", "list"]},
            "fnord": {"c": 3, "d": 4},
        }
        self.settings.set.assert_called_once_with([], expected)

    def test_on_settings_cleanup_configversion(self):
        """Tests that set config version is always left stored."""

        ### setup

        defaults = {"foo": "fnord"}
        self.plugin.get_settings_defaults = mock.MagicMock()
        self.plugin.get_settings_defaults.return_value = defaults

        in_config = {"_config_version": 1, "foo": "fnord"}
        self.settings.get_all_data.return_value = in_config

        ### execute

        self.plugin.on_settings_cleanup()

        ### assert

        # minimal config incl. config version should have been set
        self.settings.set.assert_called_once_with([], {"_config_version": 1})

    def test_on_settings_cleanup_noconfigversion(self):
        """Tests that config versions of None are cleaned from stored data."""

        ### setup

        defaults = {"foo": "bar"}
        self.plugin.get_settings_defaults = mock.MagicMock()
        self.plugin.get_settings_defaults.return_value = defaults

        # stored config version is None
        in_config = {"_config_version": None, "foo": "fnord"}
        self.settings.get_all_data.return_value = in_config

        ### execute

        self.plugin.on_settings_cleanup()

        ### assert

        # minimal config without config version should have been set
        self.settings.set.assert_called_once_with([], {"foo": "fnord"})

    def test_on_settings_cleanup_emptydiff(self):
        """Tests that settings are cleaned up if the diff data <-> defaults is empty."""

        ### setup

        defaults = {"foo": "bar"}
        self.plugin.get_settings_defaults = mock.MagicMock()
        self.plugin.get_settings_defaults.return_value = defaults

        # current stored config, same as defaults
        in_config = {"foo": "bar"}
        self.settings.get_all_data.return_value = in_config

        ### execute

        self.plugin.on_settings_cleanup()

        ### assert

        # should have been cleared
        self.settings.clean_all_data.assert_called_once_with()

    def test_on_settings_cleanup_nosuchpath(self):
        """Tests that no processing is done if nothing is stored in settings."""

        from octoprint.settings import NoSuchSettingsPath

        ### setup
        # simulate no settings stored in config.yaml
        self.settings.get_all_data.side_effect = NoSuchSettingsPath()

        ### execute

        self.plugin.on_settings_cleanup()

        ### assert

        # only get_all_data should have been called
        self.settings.get_all_data.assert_called_once_with(
            merged=False, incl_defaults=False, error_on_path=True
        )
        self.assertTrue(len(self.settings.method_calls) == 1)

    def test_on_settings_cleanup_none(self):
        """Tests the None entries in config get cleaned up."""

        ### setup

        # simulate None entry in config.yaml
        self.settings.get_all_data.return_value = None

        ### execute

        self.plugin.on_settings_cleanup()

        ### assert

        # should have been cleaned
        self.settings.clean_all_data.assert_called_once_with()

    def test_on_settings_save(self):
        """Tests that only the diff is saved."""

        ### setup

        current = {"foo": "bar"}
        self.settings.get_all_data.return_value = current

        defaults = {"foo": "foo", "bar": {"a": 1, "b": 2}}
        self.plugin.get_settings_defaults = mock.MagicMock()
        self.plugin.get_settings_defaults.return_value = defaults

        ### execute

        data = {"foo": "fnord", "bar": {"a": 1, "b": 2}}
        diff = self.plugin.on_settings_save(data)

        ### assert

        # the minimal diff should have been saved
        expected = {"foo": "fnord"}
        self.settings.set.assert_called_once_with([], expected)

        self.assertEqual(diff, expected)

    def test_on_settings_save_nodiff(self):
        """Tests that data is cleaned if there's not difference between data and defaults."""

        ### setup

        self.settings.get_all_data.return_value = None

        defaults = {"foo": "bar", "bar": {"a": 1, "b": 2, "l": ["some", "list"]}}
        self.plugin.get_settings_defaults = mock.MagicMock()
        self.plugin.get_settings_defaults.return_value = defaults

        ### execute

        data = {"foo": "bar"}
        diff = self.plugin.on_settings_save(data)

        ### assert

        self.settings.clean_all_data.assert_called_once_with()
        self.assertEqual(diff, {})

    def test_on_settings_save_configversion(self):
        """Tests that saved data gets stripped config version and set correct one."""

        ### setup

        self.settings.get_all_data.return_value = None

        defaults = {"foo": "bar"}
        self.plugin.get_settings_defaults = mock.MagicMock()
        self.plugin.get_settings_defaults.return_value = defaults

        version = 1
        self.plugin.get_settings_version = mock.MagicMock()
        self.plugin.get_settings_version.return_value = version

        ### execute

        data = {"_config_version": None, "foo": "bar"}
        diff = self.plugin.on_settings_save(data)

        ### assert

        expected_diff = {}
        expected_set = {"_config_version": version}

        # while there was no diff, we should still have saved the new config version
        self.settings.set.assert_called_once_with([], expected_set)

        self.assertEqual(diff, expected_diff)

    def test_on_settings_load(self):
        """Tests that on_settings_load returns what's stored in the config, without config version."""

        ### setup

        # current data incl. config version
        current = {
            "_config_version": 3,
            "foo": "bar",
            "fnord": {"a": 1, "b": 2, "l": ["some", "list"]},
        }

        # expected is current without _config_version - we make the copy now
        # since our current dict will be modified by the test
        expected = dict(current)
        del expected["_config_version"]

        self.settings.get_all_data.return_value = expected

        ### execute

        result = self.plugin.on_settings_load()

        ### assert

        self.assertEqual(result, expected)
