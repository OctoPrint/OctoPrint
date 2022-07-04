__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask import jsonify

from octoprint.access.permissions import Permissions
from octoprint.server.api import api
from octoprint.server.util.flask import no_firstrun_access
from octoprint.webcams import get_all_webcams, webcams_to_dict


@api.route("/webcams", methods=["GET"])
@no_firstrun_access
@Permissions.WEBCAM.require(403)
def getWebcams():
    return jsonify(webcams_to_dict(get_all_webcams()))
