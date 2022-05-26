"""
Tests for OctoPrint's Settings class

.. todo::

     * tests for base folder management
     * tests for script management
     * tests for settings migration
"""

import contextlib
import hashlib
import os
import re
import shutil
import tempfile
import time
import unittest

import ddt
import pytest
import yaml

import octoprint.settings
from octoprint.util import dict_merge

base_path = os.path.join(os.path.dirname(__file__), "_files")


def _load_yaml(fname):
    with open(fname, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _dump_yaml(fname, config):
    with open(fname, "wt", encoding="utf-8") as f:
        yaml.safe_dump(config, f)


@ddt.ddt
class SettingsTest(unittest.TestCase):
    def setUp(self):
        self.config_path = os.path.realpath(os.path.join(base_path, "config.yaml"))
        self.overlay_path = os.path.realpath(os.path.join(base_path, "overlay.yaml"))
        self.defaults_path = os.path.realpath(os.path.join(base_path, "defaults.yaml"))

        self.config = _load_yaml(self.config_path)
        self.overlay = _load_yaml(self.overlay_path)
        self.defaults = _load_yaml(self.defaults_path)

        self.expected_effective = dict_merge(
            dict_merge(self.defaults, self.overlay), self.config
        )
        self.expected_effective[octoprint.settings.Settings.OVERLAY_KEY] = "overlay"

    def test_basedir_initialization(self):
        with self.mocked_basedir() as basedir:
            # construct settings
            settings = octoprint.settings.Settings()

            # verify
            self.assertTrue(os.path.isdir(basedir))
            self.assertTrue(os.path.isfile(os.path.join(basedir, "config.yaml")))
            self.assertIsNotNone(settings.get(["api", "key"]))

    def test_basedir_folder_creation(self):
        with self.mocked_basedir() as basedir:
            # construct settings
            settings = octoprint.settings.Settings()

            expected_upload_folder = os.path.join(basedir, "uploads")
            expected_timelapse_folder = os.path.join(basedir, "timelapse")
            expected_timelapse_tmp_folder = os.path.join(basedir, "timelapse", "tmp")

            # test
            upload_folder = settings.getBaseFolder("uploads")
            timelapse_folder = settings.getBaseFolder("timelapse")
            timelapse_tmp_folder = settings.getBaseFolder("timelapse_tmp")

            for folder, expected in (
                (upload_folder, expected_upload_folder),
                (timelapse_folder, expected_timelapse_folder),
                (timelapse_tmp_folder, expected_timelapse_tmp_folder),
            ):
                self.assertIsNotNone(folder)
                self.assertEqual(folder, expected)
                self.assertTrue(os.path.isdir(folder))

    def test_basedir_initialization_with_custom_basedir(self):
        with self.mocked_basedir() as default_basedir:
            my_basedir = None

            try:
                my_basedir = tempfile.mkdtemp("octoprint-settings-test-custom")
                self.assertNotEqual(my_basedir, default_basedir)

                octoprint.settings.Settings(basedir=my_basedir)

                self.assertFalse(
                    os.path.isfile(os.path.join(default_basedir, "config.yaml"))
                )
                self.assertTrue(os.path.isfile(os.path.join(my_basedir, "config.yaml")))

            finally:
                try:
                    shutil.rmtree(my_basedir)
                except Exception:
                    self.fail("Could not remove temporary custom basedir")

    def test_basedir_initialization_with_custom_config(self):
        config_path = os.path.realpath(
            os.path.join(os.path.dirname(__file__), "_files", "config.yaml")
        )

        with self.mocked_basedir() as basedir:
            my_configdir = None

            try:
                my_configdir = tempfile.mkdtemp("octoprint-settings-test-custom")
                my_configfile = os.path.join(my_configdir, "config.yaml")
                shutil.copy(config_path, my_configfile)

                expected_upload_folder = os.path.join(basedir, "uploads")

                settings = octoprint.settings.Settings(configfile=my_configfile)
                upload_folder = settings.getBaseFolder("uploads")

                self.assertFalse(os.path.isfile(os.path.join(basedir, "config.yaml")))
                self.assertTrue(os.path.isfile(my_configfile))
                self.assertIsNotNone(upload_folder)
                self.assertTrue(os.path.isdir(upload_folder))
                self.assertEqual(expected_upload_folder, upload_folder)

            finally:
                try:
                    shutil.rmtree(my_configdir)
                except Exception:
                    self.fail("Could not remove temporary custom basedir")

    ##~~ regexes
    def test_should_have_regex_filters(self):
        # we don't want the mocked_config, because we're testing the actual value.
        # with self.mocked_config():

        filters = octoprint.settings.Settings().get(["terminalFilters"])

        # we *should* have at least three, but we'll ensure there's at least one as a sanity check.
        self.assertGreater(len(filters), 0)

    def test_should_have_suppress_temperature_regex(self):
        # we don't want the mocked_config, because we're testing the actual value.
        # with self.mocked_config():

        filters = octoprint.settings.Settings().get(["terminalFilters"])
        temperature_regex_filters = [
            x for x in filters if x.get("name") == "Suppress temperature messages"
        ]
        self.assertEqual(len(temperature_regex_filters), 1)

        # we know there's a 'name' by now, so just ensure we have the regex key
        temperature_regex_filter = temperature_regex_filters[0]
        self.assertIn("regex", temperature_regex_filter)

    def test_temperature_regex_should_not_match(self):
        """random entries that aren't temperature regex entries"""
        # we don't want the mocked_config, because we're testing the actual value.
        # with self.mocked_config():
        bad_terminal_entries = [
            "Send: N71667 G1 X163.151 Y35.424 E0.02043*83",
            "Send: N85343 G1 Z29.880 F10800.000*15",
            "Recv: ok",
            "Recv: FIRMWARE_NAME:Marlin 1.1.7-C2 (Github) SOURCE_CODE_URL:https://github.com/Robo3D/Marlin-C2 PROTOCOL_VERSION:C2 MACHINE_TYPE:RoboC2 EXTRUDER_COUNT:1 UUID:cede2a2f-41a2-4748-9b12-c55c62f367ff EMERGENCY_CODES:M108,M112,M410",
        ]

        filters = octoprint.settings.Settings().get(["terminalFilters"])
        temperature_pattern = [
            x for x in filters if x.get("name") == "Suppress temperature messages"
        ][0]["regex"]

        matcher = re.compile(temperature_pattern)
        for terminal_string in bad_terminal_entries:
            match_result = matcher.match(terminal_string)
            # can switch to assertIsNone after 3.x upgrade.
            self.assertFalse(
                match_result,
                f"string matched and it shouldn't have: {terminal_string!r}",
            )

    def test_temperature_regex_matches(self):
        # we don't want the mocked_config, because we're testing the actual value.
        # with self.mocked_config():

        common_terminal_entries = [
            "Send: M105",
            "Send: N123 M105*456",
            "Recv: ok N5993 P15 B15 T:59.2 /0.0 B:31.8 /0.0 T0:59.2 /0.0 @:0 B@:100:",  # monoprice mini delta
            "Recv: ok T:210.3 /210.0 B:60.3 /60.0 T0:210.3 /210.0 @:79 B@:0 P:35.9 A:40.0",  # Prusa mk3
            "Recv:  T:210.3 /210.0",
        ]

        filters = octoprint.settings.Settings().get(["terminalFilters"])
        temperature_pattern = [
            x for x in filters if x.get("name") == "Suppress temperature messages"
        ][0]["regex"]

        matcher = re.compile(temperature_pattern)
        for terminal_string in common_terminal_entries:
            match_result = matcher.match(terminal_string)
            # can switch to assertIsNotNone after 3.x upgrade.
            self.assertTrue(
                match_result,
                f"string did not match and it should have: {terminal_string!r}",
            )

    ##~~ test getters

    def test_get(self):
        with self.settings() as settings:
            expected_api_key = "test"

            api_key = settings.get(["api", "key"])

            self.assertIsNotNone(api_key)
            self.assertEqual(api_key, expected_api_key)

    def test_get_int(self):
        with self.settings() as settings:
            expected_server_port = 8080

            server_port = settings.get(["server", "port"])

            self.assertIsNotNone(server_port)
            self.assertEqual(server_port, expected_server_port)

    def test_get_int_converted(self):
        with self.settings() as settings:
            value = settings.getInt(["serial", "timeout", "connection"])
            self.assertEqual(5, value)

    def test_get_int_invalid(self):
        with self.settings() as settings:
            value = settings.getInt(["server", "host"])
            self.assertIsNone(value)

    def test_get_float(self):
        with self.settings() as settings:
            expected_serial_timeout = 1.0

            serial_timeout = settings.get(["serial", "timeout", "detection"])

            self.assertIsNotNone(serial_timeout)
            self.assertEqual(serial_timeout, expected_serial_timeout)

    def test_get_float_converted(self):
        with self.settings() as settings:
            value = settings.getFloat(["serial", "timeout", "connection"])
            self.assertEqual(5.0, value)

    def test_get_float_invalid(self):
        with self.settings() as settings:
            value = settings.getFloat(["server", "host"])
            self.assertIsNone(value)

    def test_get_boolean(self):
        with self.settings() as settings:
            value = settings.get(["devel", "virtualPrinter", "enabled"])
            self.assertTrue(value)

    def test_get_list(self):
        with self.settings() as settings:
            data = settings.get(["serial", "additionalPorts"])
            self.assertEqual(len(data), 2)
            self.assertListEqual(["/dev/portA", "/dev/portB"], data)

    def test_get_map(self):
        with self.settings() as settings:
            data = settings.get(["devel", "virtualPrinter"])
            self.assertDictEqual(self.config["devel"]["virtualPrinter"], data)

    def test_get_map_merged(self):
        with self.settings() as settings:
            data = settings.get(["devel", "virtualPrinter"], merged=True)
            expected = dict_merge(
                self.overlay["devel"]["virtualPrinter"],
                self.config["devel"]["virtualPrinter"],
            )
            self.assertEqual(expected, data)

    def test_get_multiple(self):
        with self.settings() as settings:
            data = settings.get(["serial", ["timeout", "additionalPorts"]])

            self.assertIsInstance(data, list)
            self.assertEqual(len(data), 2)

            self.assertIsInstance(data[0], dict)
            self.assertIsInstance(data[1], list)

    def test_get_multiple_asdict(self):
        with self.settings() as settings:
            data = settings.get(["serial", ["timeout", "additionalPorts"]], asdict=True)

            self.assertIsInstance(data, dict)
            self.assertEqual(len(data), 2)

            self.assertTrue("timeout" in data)
            self.assertTrue("additionalPorts" in data)

    def test_get_invalid(self):
        with self.settings() as settings:
            value = settings.get(["i", "do", "not", "exist"])

            self.assertIsNone(value)

    def test_get_invalid_error(self):
        with self.settings() as settings:
            try:
                settings.get(["i", "do", "not", "exist"], error_on_path=True)
                self.fail("Expected NoSuchSettingsPath")
            except octoprint.settings.NoSuchSettingsPath:
                pass

    def test_get_custom_config(self):
        with self.settings() as settings:
            server_port = settings.getInt(
                ["server", "port"], config={"server": {"port": 9090}}
            )

            self.assertEqual(9090, server_port)

    def test_get_custom_defaults(self):
        with self.settings() as settings:
            api_enabled = settings.getBoolean(
                ["api", "enabled"], defaults={"api": {"enabled": False}}
            )

            self.assertFalse(api_enabled)

    def test_get_empty_path(self):
        with self.settings() as settings:
            self.assertIsNone(settings.get([]))

            try:
                settings.get([], error_on_path=True)
                self.fail("Expected NoSuchSettingsPath")
            except octoprint.settings.NoSuchSettingsPath:
                pass

    ##~~ test setters

    def test_set(self):
        with self.settings() as settings:
            settings.set(["server", "host"], "127.0.0.1")
            self.assertEqual("127.0.0.1", settings._config["server"]["host"])

    def test_set_int(self):
        with self.settings() as settings:
            settings.setInt(["server", "port"], 8181)
            self.assertEqual(8181, settings._config["server"]["port"])

    def test_set_int_convert(self):
        with self.settings() as settings:
            settings.setInt(["server", "port"], "8181")
            self.assertEqual(8181, settings._config["server"]["port"])

    def test_set_float(self):
        with self.settings() as settings:
            settings.setFloat(["serial", "timeout", "detection"], 1.2)
            self.assertEqual(1.2, settings._config["serial"]["timeout"]["detection"])

    def test_set_float_convert(self):
        with self.settings() as settings:
            settings.setFloat(["serial", "timeout", "detection"], "1.2")
            self.assertEqual(1.2, settings._config["serial"]["timeout"]["detection"])

    def test_set_boolean(self):
        with self.settings() as settings:
            settings.setBoolean(["devel", "virtualPrinter", "sendWait"], False)
            self.assertEqual(
                False, settings._config["devel"]["virtualPrinter"]["sendWait"]
            )

    @ddt.data("1", "yes", "true", "TrUe", "y", "Y", "YES")
    def test_set_boolean_convert_string_true(self, value):
        with self.settings() as settings:
            settings.setBoolean(
                ["devel", "virtualPrinter", "repetierStyleResends"], value
            )

            self.assertEqual(
                True, settings._config["devel"]["virtualPrinter"]["repetierStyleResends"]
            )

    @ddt.data("0", "no", "false", ["some", "list"], {"a": "dictionary"}, lambda: None)
    def test_set_boolean_convert_any_false(self, value):
        with self.settings() as settings:
            settings.setBoolean(["api", "enabled"], value)

            self.assertEqual(False, settings._config["api"]["enabled"])

    def test_set_default(self):
        with self.settings() as settings:
            self.assertEqual(8080, settings._config["server"]["port"])

            settings.set(["server", "port"], 5000)

            self.assertNotIn("server", settings._config)
            self.assertEqual(5000, settings.get(["server", "port"]))

    def test_set_default_subtree(self):
        with self.settings() as settings:
            default = {"host": "0.0.0.0", "port": 5000}
            self.assertEqual(
                {"host": "0.0.0.0", "port": 8080}, settings.get(["server"], merged=True)
            )

            settings.set(["server"], default)

            self.assertNotIn("server", settings._config)
            self.assertEqual(default, settings.get(["server"], merged=True))

    def test_set_none(self):
        with self.settings() as settings:
            self.assertTrue("port" in settings._config["server"])

            settings.set(["server", "port"], None)

            self.assertIs(settings.get(["server", "port"]), None)

    @ddt.data(
        [], ["api", "lock"], ["api", "lock", "door"], ["serial", "additionalPorts", "key"]
    )
    def test_set_invalid(self, path):
        with self.settings() as settings:
            try:
                settings.set(path, "value", error_on_path=True)
                self.fail("Expected NoSuchSettingsPath")
            except octoprint.settings.NoSuchSettingsPath:
                pass

    ##~~ test remove

    def test_remove(self):
        with self.settings() as settings:
            self.assertTrue("port" in settings._config["server"])

            settings.remove(["server", "port"])

            self.assertFalse(
                "server" in settings._config and "port" in settings._config["server"]
            )
            self.assertEqual(5000, settings.get(["server", "port"]))

    @ddt.data([], ["server", "lock"], ["serial", "additionalPorts", "key"])
    def test_remove_invalid(self, path):
        with self.settings() as settings:
            try:
                settings.remove(path, error_on_path=True)
                self.fail("Expected NoSuchSettingsPath")
            except octoprint.settings.NoSuchSettingsPath:
                pass

    ##~~ test has

    def test_has(self):
        with self.settings() as settings:
            self.assertTrue(settings.has(["api", "key"]))
            self.assertFalse(settings.has(["api", "lock"]))

    ##~~ test properties

    def test_effective(self):
        with self.settings() as settings:
            effective = settings.effective
            self.assertDictEqual(self.expected_effective, effective)

    def test_effective_hash(self):
        with self.settings() as settings:
            hash = hashlib.md5()
            hash.update(yaml.safe_dump(self.expected_effective).encode("utf-8"))
            expected_effective_hash = hash.hexdigest()
            print(yaml.safe_dump(self.expected_effective))

            effective_hash = settings.effective_hash
            print(yaml.safe_dump(settings.effective))

            self.assertEqual(expected_effective_hash, effective_hash)

    def test_config_hash(self):
        with self.settings() as settings:
            hash = hashlib.md5()
            hash.update(yaml.safe_dump(self.config).encode("utf-8"))
            expected_config_hash = hash.hexdigest()

            config_hash = settings.config_hash

            self.assertEqual(expected_config_hash, config_hash)

    def test_last_modified(self):
        with self.settings() as settings:
            configfile = settings._configfile
            last_modified = os.stat(configfile).st_mtime
            self.assertEqual(settings.last_modified, last_modified)

    ##~~ test preprocessors

    def test_get_preprocessor(self):
        with self.settings() as settings:
            config = {}
            defaults = {"test_preprocessor": "some string"}
            preprocessors = {"test_preprocessor": lambda x: x.upper()}

            value = settings.get(
                ["test_preprocessor"],
                config=config,
                defaults=defaults,
                preprocessors=preprocessors,
            )

            self.assertEqual("SOME STRING", value)

    def test_set_preprocessor(self):
        with self.settings() as settings:
            config = {}
            defaults = {"foo_preprocessor": {"bar": "fnord"}}
            preprocessors = {"foo_preprocessor": {"bar": lambda x: x.upper()}}

            settings.set(
                ["foo_preprocessor", "bar"],
                "value",
                config=config,
                defaults=defaults,
                preprocessors=preprocessors,
            )

            self.assertEqual("VALUE", config["foo_preprocessor"]["bar"])

    def test_set_external_modification(self):
        with self.settings() as settings:
            configfile = settings._configfile

            # Make sure the config files last modified time changes
            time.sleep(1.0)

            self.assertEqual("0.0.0.0", settings.get(["server", "host"]))

            # modify yaml file externally
            config = _load_yaml(configfile)
            config["server"]["host"] = "127.0.0.1"
            _dump_yaml(configfile, config)

            # set some value, should also reload file before setting new api key
            settings.set(["api", "key"], "key")

            # verify updated values
            self.assertEqual("127.0.0.1", settings.get(["server", "host"]))
            self.assertEqual("key", settings.get(["api", "key"]))

    ##~~ test save

    def test_save(self):
        with self.settings() as settings:
            config_path = settings._configfile

            # current modification date of config.yaml
            current_modified = os.stat(config_path).st_mtime

            # sleep a bit to make sure we do have a change in the timestamp
            time.sleep(1.0)

            # set a new value
            settings.set(["api", "key"], "newkey")

            # should not be written automatically
            self.assertEqual(current_modified, os.stat(config_path).st_mtime)

            # should be updated after calling save though
            settings.save()
            self.assertNotEqual(current_modified, os.stat(config_path).st_mtime)

    def test_save_unmodified(self):
        with self.settings() as settings:
            last_modified = settings.last_modified

            # sleep a bit to make sure we do have a change in the timestamp
            time.sleep(1.0)

            settings.save()
            self.assertEqual(settings.last_modified, last_modified)

            settings.save(force=True)
            self.assertGreater(settings.last_modified, last_modified)

    ##~~ helpers

    @contextlib.contextmanager
    def mocked_basedir(self):
        orig_default_basedir = octoprint.settings._default_basedir
        directory = None

        try:
            directory = tempfile.mkdtemp("octoprint-settings-test")
            octoprint.settings._default_basedir = lambda *args, **kwargs: directory
            yield directory
        finally:
            octoprint.settings._default_basedir = orig_default_basedir
            if directory is not None:
                try:
                    shutil.rmtree(directory)
                except Exception:
                    self.fail("Could not remove temporary basedir")

    @contextlib.contextmanager
    def mocked_config(self):
        orig_defaults = octoprint.settings.default_settings

        with self.mocked_basedir() as basedir:
            fresh_config_path = os.path.join(basedir, "config.yaml")
            shutil.copy(self.config_path, fresh_config_path)
            try:
                octoprint.settings.default_settings = self.defaults
                yield
            finally:
                octoprint.settings.default_settings = orig_defaults

    @contextlib.contextmanager
    def settings(self):
        with self.mocked_config():
            settings = octoprint.settings.Settings()
            settings.add_overlay(self.overlay, key="overlay")
            yield settings


@ddt.ddt
class HelpersTest(unittest.TestCase):
    @ddt.data(
        (True, True),
        ("true", True),
        ("True", True),
        ("tRuE", True),
        ("yes", True),
        ("YES", True),
        ("y", True),
        ("Y", True),
        ("1", True),
        (1, True),
        (False, False),
        ("Truuuuuuuuue", False),
        ("Nope", False),
        (None, False),
    )
    @ddt.unpack
    def test_valid_boolean_trues(self, value, expected):
        self.assertEqual(expected, value in octoprint.settings.valid_boolean_trues)


def _key(*path):
    return octoprint.settings._CHAINMAP_SEP.join(path)


@ddt.ddt
class ChainmapTest(unittest.TestCase):
    def setUp(self):
        self.config_path = os.path.realpath(os.path.join(base_path, "config.yaml"))
        self.overlay_path = os.path.realpath(os.path.join(base_path, "overlay.yaml"))
        self.defaults_path = os.path.realpath(os.path.join(base_path, "defaults.yaml"))

        self.config = _load_yaml(self.config_path)
        self.overlay = _load_yaml(self.overlay_path)
        self.defaults = _load_yaml(self.defaults_path)

        self.chainmap = octoprint.settings.HierarchicalChainMap(
            self.config, self.overlay, self.defaults
        )

    def test_has_path(self):
        self.assertTrue(self.chainmap.has_path(["api", "key"]))
        self.assertTrue(self.chainmap.has_path(["devel"]))
        self.assertTrue(self.chainmap.has_path(["devel", "virtualPrinter"]))
        self.assertTrue(self.chainmap.has_path(["devel", "virtualPrinter", "enabled"]))
        self.assertTrue(self.chainmap.has_path(["plugins", "foo", "bar"]))

        self.assertFalse(self.chainmap.has_path(["api", "lock"]))

    def test_get_by_path(self):
        self.assertEqual(
            True, self.chainmap.get_by_path(["devel", "virtualPrinter", "enabled"])
        )
        self.assertEqual(
            False,
            self.chainmap.get_by_path(
                ["devel", "virtualPrinter", "enabled"], only_defaults=True
            ),
        )

        with pytest.raises(KeyError):
            self.assertEqual(None, self.chainmap.get_by_path(["test"], only_local=True))
        self.assertEqual(self.overlay["test"], self.chainmap.get_by_path(["test"]))
        self.assertEqual(
            dict_merge(self.defaults["test"], self.overlay["test"]),
            self.chainmap.get_by_path(["test"], merged=True),
        )

        self.assertEqual(
            self.config["plugins"]["foo"]["bar"],
            self.chainmap.get_by_path(["plugins", "foo", "bar"]),
        )

        self.assertEqual(
            self.config["plugins"]["fnord"]["bar"],
            self.chainmap.get_by_path(["plugins", "fnord", "bar"]),
        )
        self.assertEqual(
            dict_merge(
                self.overlay["plugins"]["fnord"]["bar"],
                self.config["plugins"]["fnord"]["bar"],
            ),
            self.chainmap.get_by_path(["plugins", "fnord", "bar"], merged=True),
        )

    def test_set_by_path(self):
        self.chainmap.set_by_path(["devel", "virtualPrinter", "sendWait"], False)

        updated = dict(self.config)
        updated["devel"]["virtualPrinter"]["sendWait"] = False
        flattened = octoprint.settings.HierarchicalChainMap._flatten(updated)

        self.assertEqual(flattened, self.chainmap._chainmap.maps[0])

    def test_del_by_path(self):
        self.chainmap.del_by_path(
            ["devel", "virtualPrinter", "capabilities", "autoreport_temp"]
        )

        # make sure we only see the empty default now
        self.assertEqual(
            {}, self.chainmap.get_by_path(["devel", "virtualPrinter", "capabilities"])
        )

        # make sure the whole (empty) tree is gone from top layer
        path = ["devel", "virtualPrinter", "capabilities", "autoreport_temp"]
        while len(path):
            self.assertFalse(_key(*path) in self.chainmap._chainmap.maps[0])
            path = path[:-1]

    def test_del_by_path_with_subtree(self):
        self.chainmap.del_by_path(["devel", "virtualPrinter", "capabilities"])

        # make sure we only see the empty default now
        self.assertEqual(
            {}, self.chainmap.get_by_path(["devel", "virtualPrinter", "capabilities"])
        )

        # make sure the whole (empty) tree is gone from top layer
        path = ["devel", "virtualPrinter", "capabilities", "autoreport_temp"]
        while len(path):
            self.assertFalse(_key(*path) in self.chainmap._chainmap.maps[0])
            path = path[:-1]

    @ddt.data(
        (
            {"a": 1},
            {_key("a"): 1},
        ),
        ({"a": {"b": "b"}}, {_key("a", "b"): "b"}),
        (
            {"a": {"b": "b", "c": "c", "d": {"e": "e"}}},
            {_key("a", "b"): "b", _key("a", "c"): "c", _key("a", "d", "e"): "e"},
        ),
    )
    @ddt.unpack
    def test_flatten(self, value, expected):
        self.assertEqual(
            expected, octoprint.settings.HierarchicalChainMap._flatten(value)
        )

    @ddt.data(
        (
            {_key("a"): 1},
            {"a": 1},
        ),
        (
            {_key("a", "b"): "b"},
            {"a": {"b": "b"}},
        ),
        (
            {_key("a", "b"): "b", _key("a", "c"): "c", _key("a", "d", "e"): "e"},
            {"a": {"b": "b", "c": "c", "d": {"e": "e"}}},
        ),
        (
            {_key("a"): None, _key("a", "b"): "b"},
            {"a": {"b": "b"}},
        ),
        (
            {_key("a"): "", _key("a", "b"): "b"},
            {"a": {"b": "b"}},
        ),
    )
    @ddt.unpack
    def test_unflatten(self, value, expected):
        self.assertEqual(
            expected, octoprint.settings.HierarchicalChainMap._unflatten(value)
        )
