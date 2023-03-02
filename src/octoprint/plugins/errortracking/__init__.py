__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2019 The OctoPrint Project - Released under terms of the AGPLv3 License"

import errno
import logging

import requests.exceptions
import serial
import tornado.websocket
from flask import jsonify
from flask_babel import gettext

import octoprint.plugin
from octoprint.util import get_fully_qualified_classname as fqcn  # noqa: F401
from octoprint.util.version import (
    get_octoprint_version_string,
    is_released_octoprint_version,
)

SENTRY_URL_SERVER = (
    "https://9c242ccf183444eaacd046d86d8b0ea2@o118517.ingest.sentry.io/1373987"
)
SENTRY_URL_COREUI = (
    "https://4d9844043596415faa606ff722174b90@o118517.ingest.sentry.io/1374096"
)

SETTINGS_DEFAULTS = {
    "enabled": False,
    "enabled_unreleased": False,
    "unique_id": None,
    "url_server": SENTRY_URL_SERVER,
    "url_coreui": SENTRY_URL_COREUI,
}

IGNORED_EXCEPTIONS = [
    # serial exceptions in octoprint.util.comm
    (
        serial.SerialException,
        lambda exc, logger, plugin, cb: logger == "octoprint.util.comm",
    ),
    # KeyboardInterrupts
    KeyboardInterrupt,
    # IOErrors of any kind due to a full file system
    (
        IOError,
        lambda exc, logger, plugin, cb: exc.errorgetattr(exc, "errno")  # noqa: B009
        and exc.errno in (getattr(errno, "ENOSPC"),),  # noqa: B009
    ),
    # RequestExceptions of any kind
    requests.exceptions.RequestException,
    # Tornado WebSocketErrors of any kind
    tornado.websocket.WebSocketError,
    # Anything triggered by or in third party plugin Astroprint
    (
        Exception,
        lambda exc, logger, plugin, cb: logger.startswith("octoprint.plugins.astroprint")
        or plugin == "astroprint"
        or cb.startswith("octoprint_astroprint."),
    ),
]

try:
    # noinspection PyUnresolvedReferences
    from octoprint.plugins.backup import InsufficientSpace

    # if the backup plugin is enabled, ignore InsufficientSpace errors from it as well
    IGNORED_EXCEPTIONS.append(InsufficientSpace)

    del InsufficientSpace
except ImportError:
    pass


class ErrorTrackingPlugin(
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.SimpleApiPlugin,
):
    def get_template_configs(self):
        return [
            {
                "type": "settings",
                "name": gettext("Error Tracking"),
                "template": "errortracking_settings.jinja2",
                "custom_bindings": False,
            },
            {"type": "generic", "template": "errortracking_javascripts.jinja2"},
        ]

    def get_template_vars(self):
        enabled = self._settings.get_boolean(["enabled"])
        enabled_unreleased = self._settings.get_boolean(["enabled_unreleased"])

        return {
            "enabled": _is_enabled(enabled, enabled_unreleased),
            "unique_id": self._settings.get(["unique_id"]),
            "url_coreui": self._settings.get(["url_coreui"]),
        }

    def get_assets(self):
        return {"js": ["js/sentry.min.js", "js/errortracking.js"]}

    def get_settings_defaults(self):
        return SETTINGS_DEFAULTS

    def on_settings_save(self, data):
        old_enabled = _is_enabled(
            self._settings.get_boolean(["enabled"]),
            self._settings.get_boolean(["enabled_unreleased"]),
        )

        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

        enabled = _is_enabled(
            self._settings.get_boolean(["enabled"]),
            self._settings.get_boolean(["enabled_unreleased"]),
        )

        if old_enabled != enabled:
            _enable_errortracking()

    def on_api_get(self, request):
        return jsonify(**self.get_template_vars())


_enabled = False


def _enable_errortracking():
    # this is a bit hackish, but we want to enable error tracking as early in the platform lifecycle as possible
    # and hence can't wait until our implementation is initialized and injected with settings

    from octoprint.settings import settings

    global _enabled

    if _enabled:
        return

    version = get_octoprint_version_string()

    s = settings()
    plugin_defaults = {"plugins": {"errortracking": SETTINGS_DEFAULTS}}

    enabled = s.getBoolean(
        ["plugins", "errortracking", "enabled"], defaults=plugin_defaults
    )
    enabled_unreleased = s.getBoolean(
        ["plugins", "errortracking", "enabled_unreleased"], defaults=plugin_defaults
    )
    url_server = s.get(
        ["plugins", "errortracking", "url_server"], defaults=plugin_defaults
    )
    unique_id = s.get(["plugins", "errortracking", "unique_id"], defaults=plugin_defaults)
    if unique_id is None:
        import uuid

        unique_id = str(uuid.uuid4())
        s.set(
            ["plugins", "errortracking", "unique_id"],
            unique_id,
            defaults=plugin_defaults,
        )
        s.save()

    if _is_enabled(enabled, enabled_unreleased):
        import sentry_sdk

        from octoprint.plugin import plugin_manager

        def _before_send(event, hint):
            if "exc_info" not in hint:
                # we only want exceptions
                return None

            handled = True
            logger = event.get("logger", "")
            plugin = event.get("extra", {}).get("plugin", None)
            callback = event.get("extra", {}).get("callback", None)

            for ignore in IGNORED_EXCEPTIONS:
                if isinstance(ignore, tuple):
                    ignored_exc, matcher = ignore
                else:
                    ignored_exc = ignore
                    matcher = lambda *args: True

                exc = hint["exc_info"][1]
                if isinstance(exc, ignored_exc) and matcher(
                    exc, logger, plugin, callback
                ):
                    # exception ignored for logger, plugin and/or callback
                    return None

                elif isinstance(ignore, type):
                    if isinstance(hint["exc_info"][1], ignore):
                        # exception ignored
                        return None

            if event.get("exception") and event["exception"].get("values"):
                handled = not any(
                    map(
                        lambda x: x.get("mechanism")
                        and not x["mechanism"].get("handled", True),
                        event["exception"]["values"],
                    )
                )

            if handled:
                # error is handled, restrict further based on logger
                if logger != "" and not (
                    logger.startswith("octoprint.") or logger.startswith("tornado.")
                ):
                    # we only want errors logged by loggers octoprint.* or tornado.*
                    return None

                if logger.startswith("octoprint.plugins."):
                    plugin_id = logger.split(".")[2]
                    plugin_info = plugin_manager().get_plugin_info(plugin_id)
                    if plugin_info is None or not plugin_info.bundled:
                        # we only want our active bundled plugins
                        return None

                if plugin is not None:
                    plugin_info = plugin_manager().get_plugin_info(plugin)
                    if plugin_info is None or not plugin_info.bundled:
                        # we only want our active bundled plugins
                        return None

            return event

        sentry_sdk.init(url_server, release=version, before_send=_before_send)

        with sentry_sdk.configure_scope() as scope:
            scope.user = {"id": unique_id}

        logging.getLogger("octoprint.plugins.errortracking").info(
            "Initialized error tracking"
        )
        _enabled = True


def _is_enabled(enabled, enabled_unreleased):
    return enabled and (enabled_unreleased or is_released_octoprint_version())


def __plugin_enable__():
    _enable_errortracking()


__plugin_name__ = "Error Tracking"
__plugin_author__ = "Gina Häußge"
__plugin_license__ = "AGPLv3"
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_implementation__ = ErrorTrackingPlugin()
