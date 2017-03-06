# coding=utf-8
"""
Tests for OctoPrint's Settings class

.. todo::

     * tests for base folder management
     * tests for script management
     * tests for settings migration
"""

import unittest
import shutil
import contextlib
import os
import tempfile
import yaml
import hashlib
import ddt
import time

import octoprint.settings

@ddt.ddt
class TestSettings(unittest.TestCase):

	def setUp(self):
		self.base_path = os.path.join(os.path.dirname(__file__), "_files")
		self.config_path = os.path.realpath(os.path.join(self.base_path, "config.yaml"))
		self.defaults_path = os.path.realpath(os.path.join(self.base_path, "defaults.yaml"))

		with open(self.config_path, "r+b") as f:
			self.config = yaml.safe_load(f)
		with open(self.defaults_path, "r+b") as f:
			self.defaults = yaml.safe_load(f)

		from octoprint.util import dict_merge
		self.expected_effective = dict_merge(self.defaults, self.config)

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
			self.assertFalse(os.path.isdir(expected_upload_folder))

			upload_folder = settings.getBaseFolder("uploads")
			timelapse_folder = settings.getBaseFolder("timelapse")
			timelapse_tmp_folder = settings.getBaseFolder("timelapse_tmp")

			for folder, expected in ((upload_folder, expected_upload_folder),
			                         (timelapse_folder, expected_timelapse_folder),
			                         (timelapse_tmp_folder, expected_timelapse_tmp_folder)):
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

				self.assertFalse(os.path.isfile(os.path.join(default_basedir, "config.yaml")))
				self.assertTrue(os.path.isfile(os.path.join(my_basedir, "config.yaml")))

			finally:
				try:
					shutil.rmtree(my_basedir)
				except:
					self.fail("Could not remove temporary custom basedir")

	def test_basedir_initialization_with_custom_config(self):
		config_path = os.path.realpath(os.path.join(os.path.dirname(__file__), "_files", "config.yaml"))

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
				except:
					self.fail("Could not remove temporary custom basedir")

	##~~ test getters

	def test_get(self):
		with self.mocked_config():
			expected_api_key = "test"

			settings = octoprint.settings.Settings()

			api_key = settings.get(["api", "key"])

			self.assertIsNotNone(api_key)
			self.assertEqual(api_key, expected_api_key)

	def test_get_int(self):
		with self.mocked_config():
			expected_server_port = 8080

			settings = octoprint.settings.Settings()

			server_port = settings.get(["server", "port"])

			self.assertIsNotNone(server_port)
			self.assertEqual(server_port, expected_server_port)

	def test_get_int_converted(self):
		with self.mocked_config():
			settings = octoprint.settings.Settings()

			value = settings.getInt(["serial", "timeout", "connection"])

			self.assertEqual(5, value)

	def test_get_int_invalid(self):
		with self.mocked_config():
			settings = octoprint.settings.Settings()

			value = settings.getInt(["server", "host"])

			self.assertIsNone(value)

	def test_get_float(self):
		with self.mocked_config():
			expected_serial_timeout = 1.0

			settings = octoprint.settings.Settings()

			serial_timeout = settings.get(["serial", "timeout", "detection"])

			self.assertIsNotNone(serial_timeout)
			self.assertEqual(serial_timeout, expected_serial_timeout)

	def test_get_float_converted(self):
		with self.mocked_config():
			settings = octoprint.settings.Settings()

			value = settings.getFloat(["serial", "timeout", "connection"])

			self.assertEqual(5.0, value)

	def test_get_float_invalid(self):
		with self.mocked_config():
			settings = octoprint.settings.Settings()

			value = settings.getFloat(["server", "host"])

			self.assertIsNone(value)

	def test_get_boolean(self):
		with self.mocked_config():
			settings = octoprint.settings.Settings()

			value = settings.get(["devel", "virtualPrinter", "enabled"])

			self.assertTrue(value)

	def test_get_list(self):
		with self.mocked_config():
			settings = octoprint.settings.Settings()

			data = settings.get(["serial", "additionalPorts"])

			self.assertEqual(len(data), 2)
			self.assertListEqual(["/dev/portA", "/dev/portB"], data)

	def test_get_map(self):
		with self.mocked_config():
			settings = octoprint.settings.Settings()

			data = settings.get(["devel", "virtualPrinter"])

			self.assertEqual(len(data), 1)
			self.assertDictEqual(dict(enabled=True), data)

	def test_get_map_merged(self):
		with self.mocked_config():
			settings = octoprint.settings.Settings()

			data = settings.get(["devel", "virtualPrinter"], merged=True)

			self.assertGreater(len(data), 1)
			self.assertDictContainsSubset(dict(enabled=True,
			                                   sendWait=True,
			                                   waitInterval=1.0),
			                              data)

	def test_get_multiple(self):
		with self.mocked_config():
			settings = octoprint.settings.Settings()

			data = settings.get(["serial", ["timeout", "additionalPorts"]])

			self.assertIsInstance(data, list)
			self.assertEqual(len(data), 2)

			self.assertIsInstance(data[0], dict)
			self.assertIsInstance(data[1], list)


	def test_get_multiple_asdict(self):
		with self.mocked_config():
			settings = octoprint.settings.Settings()

			data = settings.get(["serial", ["timeout", "additionalPorts"]], asdict=True)

			self.assertIsInstance(data, dict)
			self.assertEqual(len(data), 2)

			self.assertTrue("timeout" in data)
			self.assertTrue("additionalPorts" in data)

	def test_get_invalid(self):
		with self.mocked_config():
			settings = octoprint.settings.Settings()

			value = settings.get(["i", "do", "not", "exist"])

			self.assertIsNone(value)

	def test_get_invalid_error(self):
		with self.mocked_config():
			settings = octoprint.settings.Settings()

			try:
				settings.get(["i", "do", "not", "exist"], error_on_path=True)
				self.fail("Expected NoSuchSettingsPath")
			except octoprint.settings.NoSuchSettingsPath:
				pass

	def test_get_custom_config(self):
		with self.mocked_config():
			settings = octoprint.settings.Settings()

			server_port = settings.getInt(["server", "port"], config=dict(server=dict(port=9090)))

			self.assertEqual(9090, server_port)

	def test_get_custom_defaults(self):
		with self.mocked_config():
			settings = octoprint.settings.Settings()

			api_enabled = settings.getBoolean(["api", "enabled"], defaults=dict(api=dict(enabled=False)))

			self.assertFalse(api_enabled)

	def test_get_empty_path(self):
		with self.mocked_config():
			settings = octoprint.settings.Settings()
			self.assertIsNone(settings.get([]))

			try:
				settings.get([], error_on_path=True)
				self.fail("Expected NoSuchSettingsPath")
			except octoprint.settings.NoSuchSettingsPath:
				pass

	##~~ test setters

	def test_set(self):
		with self.mocked_config():
			settings = octoprint.settings.Settings()

			settings.set(["server", "host"], "127.0.0.1")

			self.assertEqual("127.0.0.1", settings._config["server"]["host"])

	def test_set_int(self):
		with self.mocked_config():
			settings = octoprint.settings.Settings()

			settings.setInt(["server", "port"], 8181)

			self.assertEqual(8181, settings._config["server"]["port"])

	def test_set_int_convert(self):
		with self.mocked_config():
			settings = octoprint.settings.Settings()

			settings.setInt(["server", "port"], "8181")

			self.assertEqual(8181, settings._config["server"]["port"])

	def test_set_float(self):
		with self.mocked_config():
			settings = octoprint.settings.Settings()

			settings.setFloat(["serial", "timeout", "detection"], 1.2)

			self.assertEqual(1.2, settings._config["serial"]["timeout"]["detection"])

	def test_set_float_convert(self):
		with self.mocked_config():
			settings = octoprint.settings.Settings()

			settings.setFloat(["serial", "timeout", "detection"], "1.2")

			self.assertEqual(1.2, settings._config["serial"]["timeout"]["detection"])

	def test_set_boolean(self):
		with self.mocked_config():
			settings = octoprint.settings.Settings()

			settings.setBoolean(["devel", "virtualPrinter", "sendWait"], False)

			self.assertEqual(False, settings._config["devel"]["virtualPrinter"]["sendWait"])

	@ddt.data("1", "yes", "true", "TrUe", "y", "Y", "YES")
	def test_set_boolean_convert_string_true(self, value):
		with self.mocked_config():
			settings = octoprint.settings.Settings()

			settings.setBoolean(["devel", "virtualPrinter", "repetierStyleResends"], value)

			self.assertEqual(True, settings._config["devel"]["virtualPrinter"]["repetierStyleResends"])

	@ddt.data("0", "no", "false", ["some", "list"], dict(a="dictionary"), lambda: None)
	def test_set_boolean_convert_any_false(self, value):
		with self.mocked_config():
			settings = octoprint.settings.Settings()

			settings.setBoolean(["api", "enabled"], value)

			self.assertEqual(False, settings._config["api"]["enabled"])

	def test_set_default(self):
		with self.mocked_config():
			settings = octoprint.settings.Settings()

			self.assertEqual(8080, settings._config["server"]["port"])

			settings.set(["server", "port"], 5000)

			self.assertNotIn("port", settings._config["server"])
			self.assertEqual(5000, settings.get(["server", "port"]))

	def test_set_none(self):
		with self.mocked_config():
			settings = octoprint.settings.Settings()

			self.assertTrue("port" in settings._config["server"])

			settings.set(["server", "port"], None)

			self.assertFalse("port" in settings._config["server"])

	@ddt.data([], ["api", "lock"], ["api", "lock", "door"], ["serial", "additionalPorts", "key"])
	def test_set_invalid(self, path):
		with self.mocked_config():
			settings = octoprint.settings.Settings()

			try:
				settings.set(path, "value", error_on_path=True)
				self.fail("Expected NoSuchSettingsPath")
			except octoprint.settings.NoSuchSettingsPath:
				pass

	##~~ test remove

	def test_remove(self):
		with self.mocked_config():
			settings = octoprint.settings.Settings()

			self.assertTrue("port" in settings._config["server"])

			settings.remove(["server", "port"])

			self.assertFalse("port" in settings._config["server"])
			self.assertEqual(5000, settings.get(["server", "port"]))

	@ddt.data([], ["server", "lock"], ["serial", "additionalPorts", "key"])
	def test_remove_invalid(self, path):
		with self.mocked_config():
			settings = octoprint.settings.Settings()

			try:
				settings.remove(path, error_on_path=True)
				self.fail("Expected NoSuchSettingsPath")
			except octoprint.settings.NoSuchSettingsPath:
				pass

	##~~ test has

	def test_has(self):
		with self.mocked_config():
			settings = octoprint.settings.Settings()

			self.assertTrue(settings.has(["api", "key"]))
			self.assertFalse(settings.has(["api", "lock"]))

	##~~ test properties

	def test_effective(self):
		with self.mocked_config():
			settings = octoprint.settings.Settings()
			effective = settings.effective

			self.assertDictEqual(self.expected_effective, effective)

	def test_effective_hash(self):
		with self.mocked_config():
			hash = hashlib.md5()
			hash.update(yaml.safe_dump(self.expected_effective))
			expected_effective_hash = hash.hexdigest()
			print(yaml.safe_dump(self.expected_effective))

			settings = octoprint.settings.Settings()
			effective_hash = settings.effective_hash
			print(yaml.safe_dump(settings.effective))

			self.assertEqual(expected_effective_hash, effective_hash)

	def test_config_hash(self):
		with self.mocked_config():
			hash = hashlib.md5()
			hash.update(yaml.safe_dump(self.config))
			expected_config_hash = hash.hexdigest()

			settings = octoprint.settings.Settings()
			config_hash = settings.config_hash

			self.assertEqual(expected_config_hash, config_hash)

	def test_last_modified(self):
		with self.mocked_config() as paths:
			basedir, configfile = paths
			settings = octoprint.settings.Settings()

			last_modified = os.stat(configfile).st_mtime
			self.assertEqual(settings.last_modified, last_modified)

	##~~ test preprocessors

	def test_get_preprocessor(self):
		with self.mocked_config():
			config = dict()
			defaults = dict(test="some string")
			preprocessors = dict(test=lambda x: x.upper())

			settings = octoprint.settings.Settings()
			value = settings.get(["test"],
			                     config=config,
			                     defaults=defaults,
			                     preprocessors=preprocessors)

			self.assertEqual("SOME STRING", value)

	def test_set_preprocessor(self):
		with self.mocked_config():
			config = dict()
			defaults = dict(foo=dict(bar="fnord"))
			preprocessors = dict(foo=dict(bar=lambda x: x.upper()))

			settings = octoprint.settings.Settings()
			settings.set(["foo", "bar"],
			             "value",
			             config=config,
			             defaults=defaults,
			             preprocessors=preprocessors)

			self.assertEqual("VALUE", config["foo"]["bar"])

	def test_set_external_modification(self):
		with self.mocked_config() as paths:
			basedir, configfile = paths
			settings = octoprint.settings.Settings()

			self.assertEqual("0.0.0.0", settings.get(["server", "host"]))

			# modify yaml file externally
			with open(configfile, "r+b") as f:
				config = yaml.safe_load(f)
			config["server"]["host"] = "127.0.0.1"
			with open(configfile, "w+b") as f:
				yaml.safe_dump(config, f)

			# set some value, should also reload file before setting new api key
			settings.set(["api", "key"], "key")

			# verify updated values
			self.assertEqual("127.0.0.1", settings.get(["server", "host"]))
			self.assertEqual("key", settings.get(["api", "key"]))

	##~~ test save

	def test_save(self):
		with self.mocked_config() as paths:
			basedir, config_path = paths
			settings = octoprint.settings.Settings()

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
		with self.mocked_config():
			settings = octoprint.settings.Settings()
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
				except:
					self.fail("Could not remove temporary basedir")

	@contextlib.contextmanager
	def mocked_config(self):
		orig_defaults = octoprint.settings.default_settings

		with self.mocked_basedir() as basedir:
			fresh_config_path = os.path.join(basedir, "config.yaml")
			shutil.copy(self.config_path, fresh_config_path)
			try:
				octoprint.settings.default_settings = self.defaults
				yield basedir, fresh_config_path
			finally:
				octoprint.settings.default_settings = orig_defaults
