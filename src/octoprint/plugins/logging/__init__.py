# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = ""
__license__ = ''
__copyright__ = ""


import octoprint.plugin
from octoprint.settings import settings

from octoprint.server import NO_CONTENT, admin_permission
from octoprint.server.util.flask import redirect_to_tornado, restricted_access

from flask import request, jsonify, url_for, make_response
from werkzeug.utils import secure_filename


import os
try:
    from os import scandir
except ImportError:
    from scandir import scandir

class LoggingPlugin(octoprint.plugin.AssetPlugin,
                    octoprint.plugin.SettingsPlugin,
                    octoprint.plugin.TemplatePlugin,
                    octoprint.plugin.BlueprintPlugin,
                    octoprint.plugin.SimpleApiPlugin):


    @octoprint.plugin.BlueprintPlugin.route("/logs", methods=["GET"])
    @restricted_access
    @admin_permission.require(403)
    def getLogFiles(self):
        import psutil
        usage = psutil.disk_usage(settings().getBaseFolder("logs"))

        files = self._getLogFiles()

        return jsonify(files=files, free=usage.free, total=usage.total)


    @octoprint.plugin.BlueprintPlugin.route("/logs/<path:filename>", methods=["GET"])
    @restricted_access
    @admin_permission.require(403)
    def downloadLog(self, filename):
        return redirect_to_tornado(request, url_for("index") + "downloads/logs/" + filename)


    @octoprint.plugin.BlueprintPlugin.route("/logs/<path:filename>", methods=["DELETE"])
    @restricted_access
    @admin_permission.require(403)
    def deleteLog(self, filename):
        secure = os.path.join(settings().getBaseFolder("logs"), secure_filename(filename))
        if not os.path.exists(secure):
            return make_response("File not found: %s" % filename, 404)

        os.remove(secure)

        return NO_CONTENT


    def _getLogFiles(self):
        files = []
        basedir = settings().getBaseFolder("logs")
        for entry in scandir(basedir):
            files.append({
                "name": entry.name,
                "date": int(entry.stat().st_mtime),
                "size": entry.stat().st_size,
                "refs": {
                    "resource": url_for(".downloadLog", filename=entry.name, _external=True),
                    "download": url_for("index", _external=True) + "downloads/logs/" + entry.name
                }
            })

        return files

    def _get_available_loggers(self):
        return self._logger.manager.loggerDict.keys()

    def _get_logging_config(self):
        #config_from_file example data: {'loggers': {'octoprint.printer': {'level': 'DEBUG'}, 'octoprint.plugins.psucontrol': {'level': 'INFO'}, 'octoprint.printer.PrinterCallback': {'level': 'DEBUG'}, 'octoprint.printer.standard': {'level': 'DEBUG'}}}
        logging_file = os.path.join(self._settings.getBaseFolder("base"), "logging.yaml")

        config_from_file = {}
        if os.path.exists(logging_file) and os.path.isfile(logging_file):
            import yaml
            with open(logging_file, "r") as f:
                config_from_file = yaml.safe_load(f)

        if config_from_file is not None and isinstance(config_from_file, dict):
            return config_from_file
        else:
            return dict()

    def get_api_commands(self):
        return dict(
            getAvailableLoggers=[],
            getLoggingConfig=[]
        )

    def on_api_command(self, command, data):
        if not admin_permission.can():
            return make_response("Insufficient rights", 403)
        if command  == 'getAvailableLoggers':
            return jsonify(self._get_available_loggers())
        elif command == 'getLoggingConfig':
            return jsonify(self._get_logging_config())

    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=True)
        ]
        
    def get_assets(self):
        return dict(js=["js/logging.js"])

__plugin_name__ = "Logging"
__plugin_author__ = ""
__plugin_description__ = "Provides access to OctoPrint logging."
__plugin_license__ = ""
#__plugin_implementation__ = LoggingPlugin()


# Required for regular plugin
def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = LoggingPlugin()

