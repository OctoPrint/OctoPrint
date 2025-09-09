__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2024 The OctoPrint Project - Released under terms of the AGPLv3 License"

import flask
from flask_babel import gettext

import octoprint.access.permissions
import octoprint.plugin
import octoprint.settings
from octoprint.access.groups import ADMIN_GROUP
from octoprint.util import RepeatedTimer

from .checks import OK_RESULT


class HealthCheckPlugin(
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.SimpleApiPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.SettingsPlugin,
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._checks = {}
        self._background_check_timer = None

    def initialize(self):
        self._initialize_checks()

        check_interval = self._settings.get(["check_interval"])
        if check_interval > 0:
            self._background_check_timer = RepeatedTimer(
                check_interval * 60, self._background_check, run_first=True
            )
            self._background_check_timer.start()

    def _initialize_checks(self):
        from .checks.filesystem_storage import FilesystemStorageCheck
        from .checks.global_api_key import GlobalApiKeyCheck
        from .checks.octoprint_freshness import OctoPrintFreshnessCheck
        from .checks.python_eol import PythonEolHealthCheck

        for clz in (
            OctoPrintFreshnessCheck,
            PythonEolHealthCheck,
            FilesystemStorageCheck,
            GlobalApiKeyCheck,
        ):
            if clz.key in self.disabled_checks:
                continue
            self._checks[clz.key] = clz(self._settings_for_check(clz.key))

        hooks = self._plugin_manager.get_hooks(
            "octoprint.plugin.health_check.get_additional_checks"
        )
        for name, hook in hooks.items():
            try:
                checks = hook()
                for clz in checks:
                    if clz.key in self.disabled_checks:
                        continue
                    self._checks[clz.key] = clz(self._settings_for_check(clz.key))
            except Exception:
                self._logger.exception(
                    f"Error while fetching additional health checks from {name}",
                    extra={"plugin": name},
                )

    @property
    def disabled_checks(self):
        return self._settings.get(["disabled"])

    def check_all(self, force=False):
        result = {}
        for check in self._checks.values():
            if check.key in self.disabled_checks:
                continue

            try:
                result[check.key] = check.perform_check(force=force)
                if result[check.key] is None:
                    result[check.key] = OK_RESULT
            except Exception:
                self._logger.exception(
                    f"Exception while running health check {check.key}"
                )

        return result

    def _background_check(self, force=False):
        from .checks import Result

        result = self.check_all(force=force)

        issues = {k: v for k, v in result.items() if v.result == Result.ISSUE.value}
        warnings = {k: v for k, v in result.items() if v.result == Result.WARNING.value}
        if issues or warnings:
            issue_text = (
                (
                    "  Issues:\n"
                    + "\n".join([f"  - {k}: {v.context!r}" for k, v in issues.items()])
                    + "\n"
                )
                if issues
                else ""
            )
            warning_text = (
                (
                    "  Warnings:\n"
                    + "\n".join([f"  - {k}: {v.context!r}" for k, v in warnings.items()])
                )
                if warnings
                else ""
            )
            self._logger.warning(
                f"Health check detected problems!\n{issue_text}{warning_text}"
            )

    def _settings_for_check(self, key):
        return self._settings.get(["checks", key], asdict=True, merged=True)

    ##~~ Additional permissions hook

    def get_additional_permissions(self):
        return [
            {
                "key": "CHECK",
                "name": "Perform healthchecks",
                "description": gettext(
                    "Allows to perform health checks and view their results"
                ),
                "roles": ["check"],
                "default_groups": [ADMIN_GROUP],
            },
        ]

    ##~~ Custom events hook

    def register_custom_events(self, *args, **kwargs):
        return ["update_healthcheck"]

    ##~~ Additional bundle files hook

    def get_additional_bundle_files(self, *args, **kwargs):
        def output():
            import json

            from .checks import Result

            result = self.check_all()

            output = "Health Check Report\n\n"
            for k, v in result.items():
                output += f"- {k}: {v.result}\n"
                if v.result != Result.OK.value and v.context:
                    output += "  Context:\n"
                    output += "\n".join(
                        ["  " + x for x in json.dumps(v.context, indent=2).split("\n")]
                    )
                    output += "\n"
                output += "\n"

            return output

        return {
            "plugin_health_check_report.log": output,
        }

    ##~~ SettingsPlugin

    def get_settings_defaults(self):
        return {
            "checks": {
                "python_eol": {
                    "url": "https://get.octoprint.org/python-eol",
                    "ttl": 24 * 60 * 60,
                    "fallback": {
                        "3.7": {"date": "2023-06-27", "last_octoprint": "1.11.*"},
                        "3.8": {"date": "2024-10-07", "last_octoprint": "1.11.*"},
                    },
                },
                "filesystem_storage": {"issue_threshold": 95, "warning_threshold": 85},
            },
            "disabled": [],
            "check_interval": 60,
        }

    def on_settings_save(self, data):
        result = super().on_settings_save(data)

        for check in self._checks.values():
            check.update_settings(self._settings_for_check(check.key))

        return result

    ##~~ SimpleApiPlugin

    def on_api_get(self, request):
        if not octoprint.access.permissions.Permissions.PLUGIN_HEALTH_CHECK_CHECK.can():
            flask.abort(403)

        result = self.check_all(
            force=request.values.get("refresh") in octoprint.settings.valid_boolean_trues
        )

        health = {}
        for k, v in result.items():
            health[k] = v.model_dump()
            health[k]["hash"] = v.hash
        return flask.jsonify(health=health)

    def is_api_protected(self):
        return True

    ##~~ TemplatePlugin

    def get_template_configs(self):
        return [
            {
                "type": "navbar",
                "template": "health_check_navbar.jinja2",
                "styles": ["display: none"],
                "data_bind": "visible: loginState.hasPermission(access.permissions.PLUGIN_HEALTH_CHECK_CHECK)",
            },
        ]


__plugin_name__ = "Healthcheck Plugin"
__plugin_author__ = "Gina Häußge"
__plugin_description__ = "Checks your OctoPrint"
__plugin_disabling_discouraged__ = gettext(
    "Without this plugin you might miss problematic issues with your "
    "OctoPrint installation."
)
__plugin_license__ = "AGPLv3"
__plugin_pythoncompat__ = ">=3.9,<4"
__plugin_implementation__ = HealthCheckPlugin()

__plugin_hooks__ = {
    "octoprint.access.permissions": __plugin_implementation__.get_additional_permissions,
    "octoprint.events.register_custom_events": __plugin_implementation__.register_custom_events,
    "octoprint.systeminfo.additional_bundle_files": __plugin_implementation__.get_additional_bundle_files,
}
