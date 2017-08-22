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
                    octoprint.plugin.BlueprintPlugin):


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

    # AssetPlugin

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

