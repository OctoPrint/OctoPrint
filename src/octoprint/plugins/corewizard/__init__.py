__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask_babel import gettext

import octoprint.plugin

from .subwizards import Subwizards


class CoreWizardPlugin(
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.WizardPlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.BlueprintPlugin,
    Subwizards,
):

    # ~~ TemplatePlugin API

    def get_template_configs(self):
        required = self._get_subwizard_attrs("_is_", "_wizard_required")
        names = self._get_subwizard_attrs("_get_", "_wizard_name")
        additional = self._get_subwizard_attrs(
            "_get_", "_additional_wizard_template_data"
        )

        firstrunonly = self._get_subwizard_attrs("_is_", "_wizard_firstrunonly")
        firstrun = self._settings.global_get(["server", "firstRun"])

        if not firstrun:
            required = {
                key: value
                for key, value in required.items()
                if not firstrunonly.get(key, lambda: False)()
            }

        result = list()
        for key, method in required.items():
            if not callable(method):
                continue

            if not method():
                continue

            if key not in names:
                continue

            name = names[key]()
            if not name:
                continue

            config = {
                "type": "wizard",
                "name": name,
                "template": f"corewizard_{key}_wizard.jinja2",
                "div": f"wizard_plugin_corewizard_{key}",
                "suffix": f"_{key}",
            }
            if key in additional:
                additional_result = additional[key]()
                if additional_result:
                    config.update(additional_result)
            result.append(config)

        return result

    # ~~ AssetPlugin API

    def get_assets(self):
        if self.is_wizard_required():
            return {"js": ["js/corewizard.js"], "css": ["css/corewizard.css"]}
        else:
            return {}

    # ~~ WizardPlugin API

    def is_wizard_required(self):
        required = self._get_subwizard_attrs("_is_", "_wizard_required")
        firstrunonly = self._get_subwizard_attrs("_is_", "_wizard_firstrunonly")
        firstrun = self._settings.global_get(["server", "firstRun"])

        if not firstrun:
            required = {
                key: value
                for key, value in required.items()
                if not firstrunonly.get(key, lambda: False)()
            }
        any_required = any(map(lambda m: m(), required.values()))

        return any_required

    def get_wizard_details(self):
        result = {}

        def add_result(key, method):
            result[key] = method()

        self._get_subwizard_attrs("_get_", "_wizard_details", add_result)

        return result

    def get_wizard_version(self):
        return 4

    # ~~ helpers

    def _get_subwizard_attrs(self, start, end, callback=None):
        result = {}

        for item in dir(self):
            if not item.startswith(start) or not item.endswith(end):
                continue

            key = item[len(start) : -len(end)]
            if not key:
                continue

            attr = getattr(self, item)
            if callable(callback):
                callback(key, attr)
            result[key] = attr

        return result


__plugin_name__ = "Core Wizard"
__plugin_author__ = "Gina Häußge"
__plugin_description__ = "Provides wizard dialogs for core components and functionality"
__plugin_disabling_discouraged__ = gettext(
    "Without this plugin OctoPrint will no longer be able to perform "
    "setup steps that might be required after an update."
)
__plugin_license__ = "AGPLv3"
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_implementation__ = CoreWizardPlugin()
