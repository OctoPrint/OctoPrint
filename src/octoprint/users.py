__author__ = "Marc Hannappel <salandora@gmail.com>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

# Wrapper to the new access.users location

import warnings

from octoprint.access.users import *  # noqa: F401, F403 ## possibly used by other modules
from octoprint.access.users import User, deprecated

warnings.warn(
    "octoprint.users is deprecated, use octoprint.access.users instead",
    DeprecationWarning,
    stacklevel=2,
)

AccessUser = User


class User(AccessUser):
    @deprecated(
        "octoprint.users.User is deprecated, please use octoprint.access.users.User instead"
    )
    def __init__(self, username, passwordHash, active, roles, apikey=None, settings=None):
        from octoprint.server import groupManager

        if "admin" in roles:
            groups = [groupManager.admin_group]
        elif "user" in roles:
            groups = [groupManager.user_group]
        else:
            groups = [groupManager.guest_group]

        AccessUser(
            username=username,
            passwordHash=passwordHash,
            active=active,
            permissions=None,
            groups=groups,
            apikey=apikey,
            settings=settings,
        )
