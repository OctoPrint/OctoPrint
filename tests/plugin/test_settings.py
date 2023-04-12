__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


from unittest import mock

import pytest

import octoprint.plugin
import octoprint.settings

plugin_key = "test_plugin"
defaults = {
    "some_raw_key": "some_raw_value",
    "some_int_key": 1,
    "some_float_key": 2.5,
    "some_boolean_key": True,
    "preprocessed": {"get": "PreProcessed", "set": "PreProcessed"},
}
get_preprocessors = {"preprocessed": {"get": lambda x: x.upper()}}
set_preprocessors = {"preprocessed": {"set": lambda x: x.lower()}}


@pytest.fixture()
def settings():
    yield mock.create_autospec(octoprint.settings.Settings)


@pytest.fixture()
def plugin_settings(settings):
    yield octoprint.plugin.PluginSettings(
        settings,
        plugin_key,
        defaults=defaults,
        get_preprocessors=get_preprocessors,
        set_preprocessors=set_preprocessors,
    )


@pytest.mark.parametrize(
    "getter, getter_args, getter_kwargs, forwarded",
    [
        ("get", (["some_raw_key"],), {}, "get"),
        ("get", (["some_raw_key"],), {"merged": True}, "get"),
        ("get", (["some_raw_key"],), {"asdict": True}, "get"),
        ("get", (["some_raw_key"],), {"merged": True, "asdict": True}, "get"),
        ("get_int", (["some_int_key,"],), {}, "getInt"),
        ("get_float", (["some_float_key"],), {}, "getFloat"),
        ("get_boolean", (["some_boolean_key"],), {}, "getBoolean"),
    ],
)
def test_forwarded_getter(
    plugin_settings, settings, getter, getter_args, getter_kwargs, forwarded
):
    method_under_test = getattr(plugin_settings, getter)
    assert callable(method_under_test)

    method_under_test(*getter_args, **getter_kwargs)

    forwarded_method = getattr(settings, forwarded)
    forwarded_args = (["plugins", plugin_key] + getter_args[0],)
    forwarded_kwargs = getter_kwargs
    forwarded_kwargs.update(
        {
            "defaults": {"plugins": {"test_plugin": defaults}},
            "preprocessors": {"plugins": {"test_plugin": get_preprocessors}},
        }
    )
    forwarded_method.assert_called_once_with(*forwarded_args, **forwarded_kwargs)


@pytest.mark.parametrize(
    "getter, getter_args, getter_kwargs, forwarded",
    [
        ("global_get", (["some_raw_key"],), {}, "get"),
        ("global_get", (["some_raw_key"],), {"merged": True}, "get"),
        ("global_get", (["some_raw_key"],), {"asdict": True}, "get"),
        ("global_get", (["some_raw_key"],), {"merged": True, "asdict": True}, "get"),
        ("global_get_int", (["some_int_key"],), {}, "getInt"),
        ("global_get_float", (["some_float_key"],), {}, "getFloat"),
        ("global_get_boolean", (["some_boolean_key"],), {}, "getBoolean"),
    ],
)
def test_global_getter(
    plugin_settings, settings, getter, getter_args, getter_kwargs, forwarded
):
    method_under_test = getattr(plugin_settings, getter)
    assert callable(method_under_test)

    method_under_test(*getter_args, **getter_kwargs)

    forwarded_method = getattr(settings, forwarded)
    forwarded_method.assert_called_once_with(*getter_args, **getter_kwargs)


@pytest.mark.parametrize(
    "deprecated, current, forwarded",
    [
        ("getInt", "get_int", "getInt"),
        ("getFloat", "get_float", "getFloat"),
        ("getBoolean", "get_boolean", "getBoolean"),
    ],
)
def test_deprecated_forwarded_getter(
    plugin_settings, settings, deprecated, current, forwarded
):
    called_method = getattr(settings, forwarded)

    # further mock out our mocked function so things work as they should
    called_method.__name__ = forwarded
    called_method.__qualname__ = forwarded
    called_method.__annotations__ = {}

    method = getattr(plugin_settings, deprecated)
    assert callable(method)

    with pytest.warns(
        DeprecationWarning, match=f"{deprecated} has been renamed to {current}"
    ):
        method(["some_raw_key"])

    called_method.assert_called_once_with(
        ["plugins", plugin_key, "some_raw_key"],
        defaults={"plugins": {"test_plugin": defaults}},
        preprocessors={"plugins": {"test_plugin": get_preprocessors}},
    )


@pytest.mark.parametrize(
    "setter, setter_args, setter_kwargs, forwarded",
    [
        (
            "set",
            (
                ["some_raw_key"],
                "some_value",
            ),
            {},
            "set",
        ),
        (
            "set",
            (
                ["some_raw_key"],
                "some_value",
            ),
            {"force": True},
            "set",
        ),
        (
            "set_int",
            (
                ["some_int_key"],
                23,
            ),
            {},
            "setInt",
        ),
        (
            "set_int",
            (
                ["some_int_key"],
                23,
            ),
            {"force": True},
            "setInt",
        ),
        (
            "set_float",
            (
                ["some_float_key"],
                2.3,
            ),
            {},
            "setFloat",
        ),
        (
            "set_float",
            (
                ["some_float_key"],
                2.3,
            ),
            {"force": True},
            "setFloat",
        ),
        (
            "set_boolean",
            (
                ["some_boolean_key"],
                True,
            ),
            {},
            "setBoolean",
        ),
        (
            "set_boolean",
            (
                ["some_boolean_key"],
                True,
            ),
            {"force": True},
            "setBoolean",
        ),
    ],
)
def test_forwarded_setter(
    plugin_settings, settings, setter, setter_args, setter_kwargs, forwarded
):
    method_under_test = getattr(plugin_settings, setter)
    assert callable(method_under_test)

    method_under_test(*setter_args, **setter_kwargs)

    forwarded_method = getattr(settings, forwarded)
    forwarded_args = (["plugins", plugin_key] + setter_args[0], setter_args[1])
    forwarded_kwargs = setter_kwargs
    forwarded_kwargs.update(
        {
            "defaults": {"plugins": {"test_plugin": defaults}},
            "preprocessors": {"plugins": {"test_plugin": set_preprocessors}},
        }
    )
    forwarded_method.assert_called_once_with(*forwarded_args, **forwarded_kwargs)


@pytest.mark.parametrize(
    "setter, setter_args, setter_kwargs, forwarded",
    [
        (
            "global_set",
            (
                ["some_raw_key"],
                "some_value",
            ),
            {},
            "set",
        ),
        (
            "global_set",
            (
                ["some_raw_key"],
                "some_value",
            ),
            {"force": True},
            "set",
        ),
        (
            "global_set_int",
            (
                ["some_int_key"],
                23,
            ),
            {},
            "setInt",
        ),
        (
            "global_set_int",
            (
                ["some_int_key"],
                23,
            ),
            {"force": True},
            "setInt",
        ),
        (
            "global_set_float",
            (
                ["some_float_key"],
                2.3,
            ),
            {},
            "setFloat",
        ),
        (
            "global_set_float",
            (
                ["some_float_key"],
                2.3,
            ),
            {"force": True},
            "setFloat",
        ),
        (
            "global_set_boolean",
            (
                ["some_boolean_key"],
                True,
            ),
            {},
            "setBoolean",
        ),
        (
            "global_set_boolean",
            (
                ["some_boolean_key"],
                True,
            ),
            {"force": True},
            "setBoolean",
        ),
    ],
)
def test_global_setter(
    plugin_settings, settings, setter, setter_args, setter_kwargs, forwarded
):
    method_under_test = getattr(plugin_settings, setter)
    assert callable(method_under_test)

    method_under_test(*setter_args, **setter_kwargs)

    forwarded_method = getattr(settings, forwarded)
    forwarded_method.assert_called_once_with(*setter_args, **setter_kwargs)


@pytest.mark.parametrize(
    "deprecated, current, forwarded, value",
    [
        ("setInt", "set_int", "setInt", 1),
        ("setFloat", "set_float", "setFloat", 2.5),
        ("setBoolean", "set_boolean", "setBoolean", True),
    ],
)
def test_deprecated_forwarded_setter(
    plugin_settings, settings, deprecated, current, forwarded, value
):
    called_method = getattr(settings, forwarded)

    # further mock out our mocked function so things work as they should
    called_method.__name__ = forwarded
    called_method.__qualname__ = forwarded
    called_method.__annotations__ = {}

    method = getattr(plugin_settings, deprecated)
    assert callable(method)

    with pytest.warns(
        DeprecationWarning, match=f"{deprecated} has been renamed to {current}"
    ):
        method(["some_raw_key"], value)

    called_method.assert_called_once_with(
        ["plugins", plugin_key, "some_raw_key"],
        value,
        defaults={"plugins": {"test_plugin": defaults}},
        preprocessors={"plugins": {"test_plugin": set_preprocessors}},
    )


def test_global_get_basefolder(plugin_settings, settings):
    plugin_settings.global_get_basefolder("some_folder")
    settings.getBaseFolder.assert_called_once_with("some_folder")


def test_logfile_path(plugin_settings, settings):
    import os

    settings.getBaseFolder.return_value = "/some/folder"

    path = plugin_settings.get_plugin_logfile_path()

    settings.getBaseFolder.assert_called_once_with("logs")
    assert f"/some/folder/plugin_{plugin_key}.log" == path.replace(os.sep, "/")


def test_logfile_path_with_postfix(plugin_settings, settings):
    import os

    settings.getBaseFolder.return_value = "/some/folder"

    path = plugin_settings.get_plugin_logfile_path(postfix="mypostfix")

    settings.getBaseFolder.assert_called_once_with("logs")
    assert f"/some/folder/plugin_{plugin_key}_mypostfix.log" == path.replace(os.sep, "/")


def test_unhandled_method(plugin_settings):
    with pytest.raises(
        AttributeError, match="Mock object has no attribute 'some_method'"
    ):
        plugin_settings.some_method("some_parameter")
