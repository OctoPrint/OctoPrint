__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import unittest
import warnings
from unittest import mock

from ddt import data, ddt, unpack

import octoprint.plugin
import octoprint.settings


@ddt
class SettingsTestCase(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("always")

        self.plugin_key = "test_plugin"

        self.settings = mock.create_autospec(octoprint.settings.Settings)

        self.defaults = {
            "some_raw_key": "some_raw_value",
            "some_int_key": 1,
            "some_float_key": 2.5,
            "some_boolean_key": True,
            "preprocessed": {"get": "PreProcessed", "set": "PreProcessed"},
        }

        self.get_preprocessors = {"preprocessed": {"get": lambda x: x.upper()}}

        self.set_preprocessors = {"preprocessed": {"set": lambda x: x.lower()}}

        self.plugin_settings = octoprint.plugin.PluginSettings(
            self.settings,
            self.plugin_key,
            defaults=self.defaults,
            get_preprocessors=self.get_preprocessors,
            set_preprocessors=self.set_preprocessors,
        )

    @data(
        (
            "get",
            (
                [
                    "some_raw_key",
                ],
            ),
            {},
            "get",
        ),
        (
            "get",
            (
                [
                    "some_raw_key",
                ],
            ),
            {"merged": True},
            "get",
        ),
        (
            "get",
            (
                [
                    "some_raw_key",
                ],
            ),
            {"asdict": True},
            "get",
        ),
        (
            "get",
            (
                [
                    "some_raw_key",
                ],
            ),
            {"merged": True, "asdict": True},
            "get",
        ),
        ("get_int", (["some_int_key,"],), {}, "getInt"),
        ("get_float", (["some_float_key"],), {}, "getFloat"),
        (
            "get_boolean",
            (
                [
                    "some_boolean_key",
                ],
            ),
            {},
            "getBoolean",
        ),
    )
    @unpack
    def test_forwarded_getter(self, getter, getter_args, getter_kwargs, forwarded):
        method_under_test = getattr(self.plugin_settings, getter)
        self.assertTrue(callable(method_under_test))

        method_under_test(*getter_args, **getter_kwargs)

        forwarded_method = getattr(self.settings, forwarded)
        forwarded_args = (["plugins", self.plugin_key] + getter_args[0],)
        forwarded_kwargs = getter_kwargs
        forwarded_kwargs.update(
            {
                "defaults": {"plugins": {"test_plugin": self.defaults}},
                "preprocessors": {"plugins": {"test_plugin": self.get_preprocessors}},
            }
        )
        forwarded_method.assert_called_once_with(*forwarded_args, **forwarded_kwargs)

    @data(
        ("global_get", (["some_raw_key"],), {}, "get"),
        ("global_get", (["some_raw_key"],), {"merged": True}, "get"),
        ("global_get", (["some_raw_key"],), {"asdict": True}, "get"),
        ("global_get", (["some_raw_key"],), {"merged": True, "asdict": True}, "get"),
        ("global_get_int", (["some_int_key"],), {}, "getInt"),
        ("global_get_float", (["some_float_key"],), {}, "getFloat"),
        ("global_get_boolean", (["some_boolean_key"],), {}, "getBoolean"),
    )
    @unpack
    def test_global_getter(self, getter, getter_args, getter_kwargs, forwarded):
        method_under_test = getattr(self.plugin_settings, getter)
        self.assertTrue(callable(method_under_test))

        method_under_test(*getter_args, **getter_kwargs)

        forwarded_method = getattr(self.settings, forwarded)
        forwarded_method.assert_called_once_with(*getter_args, **getter_kwargs)

    @data(
        ("getInt", "get_int", "getInt"),
        ("getFloat", "get_float", "getFloat"),
        ("getBoolean", "get_boolean", "getBoolean"),
    )
    @unpack
    def test_deprecated_forwarded_getter(self, deprecated, current, forwarded):
        with warnings.catch_warnings(record=True) as w:
            called_method = getattr(self.settings, forwarded)

            # further mock out our mocked function so things work as they should
            called_method.__name__ = forwarded
            called_method.__qualname__ = forwarded
            called_method.__annotations__ = {}

            method = getattr(self.plugin_settings, deprecated)
            self.assertTrue(callable(method))
            method(["some_raw_key"])

            called_method.assert_called_once_with(
                ["plugins", self.plugin_key, "some_raw_key"],
                defaults={"plugins": {"test_plugin": self.defaults}},
                preprocessors={"plugins": {"test_plugin": self.get_preprocessors}},
            )

            self.assertEqual(1, len(w))
            self.assertTrue(issubclass(w[-1].category, DeprecationWarning))
            self.assertTrue(
                f"{deprecated} has been renamed to {current}" in str(w[-1].message)
            )

    @data(
        (
            "set",
            (
                [
                    "some_raw_key",
                ],
                "some_value",
            ),
            {},
            "set",
        ),
        (
            "set",
            (
                [
                    "some_raw_key",
                ],
                "some_value",
            ),
            {"force": True},
            "set",
        ),
        (
            "set_int",
            (
                [
                    "some_int_key",
                ],
                23,
            ),
            {},
            "setInt",
        ),
        (
            "set_int",
            (
                [
                    "some_int_key",
                ],
                23,
            ),
            {"force": True},
            "setInt",
        ),
        (
            "set_float",
            (
                [
                    "some_float_key",
                ],
                2.3,
            ),
            {},
            "setFloat",
        ),
        (
            "set_float",
            (
                [
                    "some_float_key",
                ],
                2.3,
            ),
            {"force": True},
            "setFloat",
        ),
        (
            "set_boolean",
            (
                [
                    "some_boolean_key",
                ],
                True,
            ),
            {},
            "setBoolean",
        ),
        (
            "set_boolean",
            (
                [
                    "some_boolean_key",
                ],
                True,
            ),
            {"force": True},
            "setBoolean",
        ),
    )
    @unpack
    def test_forwarded_setter(self, setter, setter_args, setter_kwargs, forwarded):
        method_under_test = getattr(self.plugin_settings, setter)
        self.assertTrue(callable(method_under_test))

        method_under_test(*setter_args, **setter_kwargs)

        forwarded_method = getattr(self.settings, forwarded)
        forwarded_args = (["plugins", self.plugin_key] + setter_args[0], setter_args[1])
        forwarded_kwargs = setter_kwargs
        forwarded_kwargs.update(
            {
                "defaults": {"plugins": {"test_plugin": self.defaults}},
                "preprocessors": {"plugins": {"test_plugin": self.set_preprocessors}},
            }
        )
        forwarded_method.assert_called_once_with(*forwarded_args, **forwarded_kwargs)

    @data(
        (
            "global_set",
            (
                [
                    "some_raw_key",
                ],
                "some_value",
            ),
            {},
            "set",
        ),
        (
            "global_set",
            (
                [
                    "some_raw_key",
                ],
                "some_value",
            ),
            {"force": True},
            "set",
        ),
        (
            "global_set_int",
            (
                [
                    "some_int_key",
                ],
                23,
            ),
            {},
            "setInt",
        ),
        (
            "global_set_int",
            (
                [
                    "some_int_key",
                ],
                23,
            ),
            {"force": True},
            "setInt",
        ),
        (
            "global_set_float",
            (
                [
                    "some_float_key",
                ],
                2.3,
            ),
            {},
            "setFloat",
        ),
        (
            "global_set_float",
            (
                [
                    "some_float_key",
                ],
                2.3,
            ),
            {"force": True},
            "setFloat",
        ),
        (
            "global_set_boolean",
            (
                [
                    "some_boolean_key",
                ],
                True,
            ),
            {},
            "setBoolean",
        ),
        (
            "global_set_boolean",
            (
                [
                    "some_boolean_key",
                ],
                True,
            ),
            {"force": True},
            "setBoolean",
        ),
    )
    @unpack
    def test_global_setter(self, setter, setter_args, setter_kwargs, forwarded):
        method_under_test = getattr(self.plugin_settings, setter)
        self.assertTrue(callable(method_under_test))

        method_under_test(*setter_args, **setter_kwargs)

        forwarded_method = getattr(self.settings, forwarded)
        forwarded_method.assert_called_once_with(*setter_args, **setter_kwargs)

    @data(
        ("setInt", "set_int", "setInt", 1),
        ("setFloat", "set_float", "setFloat", 2.5),
        ("setBoolean", "set_boolean", "setBoolean", True),
    )
    @unpack
    def test_deprecated_forwarded_setter(self, deprecated, current, forwarded, value):
        with warnings.catch_warnings(record=True) as w:
            called_method = getattr(self.settings, forwarded)

            # further mock out our mocked function so things work as they should
            called_method.__name__ = forwarded
            called_method.__qualname__ = forwarded
            called_method.__annotations__ = {}

            method = getattr(self.plugin_settings, deprecated)
            self.assertTrue(callable(method))
            method(["some_raw_key"], value)

            called_method.assert_called_once_with(
                ["plugins", self.plugin_key, "some_raw_key"],
                value,
                defaults={"plugins": {"test_plugin": self.defaults}},
                preprocessors={"plugins": {"test_plugin": self.set_preprocessors}},
            )

            self.assertEqual(1, len(w))
            self.assertTrue(issubclass(w[-1].category, DeprecationWarning))
            self.assertTrue(
                f"{deprecated} has been renamed to {current}" in str(w[-1].message)
            )

    def test_global_get_basefolder(self):
        self.plugin_settings.global_get_basefolder("some_folder")
        self.settings.getBaseFolder.assert_called_once_with("some_folder")

    def test_logfile_path(self):
        import os

        self.settings.getBaseFolder.return_value = "/some/folder"

        path = self.plugin_settings.get_plugin_logfile_path()

        self.settings.getBaseFolder.assert_called_once_with("logs")
        self.assertEqual(
            f"/some/folder/plugin_{self.plugin_key}.log",
            path.replace(os.sep, "/"),
        )

    def test_logfile_path_with_postfix(self):
        import os

        self.settings.getBaseFolder.return_value = "/some/folder"

        path = self.plugin_settings.get_plugin_logfile_path(postfix="mypostfix")

        self.settings.getBaseFolder.assert_called_once_with("logs")
        self.assertEqual(
            f"/some/folder/plugin_{self.plugin_key}_mypostfix.log",
            path.replace(os.sep, "/"),
        )

    def test_unhandled_method(self):
        try:
            self.plugin_settings.some_method("some_parameter")
        except AttributeError as e:
            self.assertTrue("Mock object has no attribute 'some_method'" in str(e))
