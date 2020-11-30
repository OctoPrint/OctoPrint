# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__author__ = "Marc Hannappel <salandora@gmail.com>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

from collections import OrderedDict, defaultdict
from functools import wraps

from flask import abort, g
from flask_babel import gettext
from future.utils import with_metaclass

# noinspection PyCompatibility
from past.builtins import basestring

from octoprint.access import ADMIN_GROUP, READONLY_GROUP, USER_GROUP
from octoprint.vendor.flask_principal import Need, Permission, PermissionDenied, RoleNeed


class OctoPrintPermission(Permission):
    @classmethod
    def convert_needs_to_dict(cls, needs):
        ret_needs = defaultdict(list)
        for need in needs:
            if need.value not in ret_needs[need.method]:
                ret_needs[need.method].append(need.value)
        return ret_needs

    @classmethod
    def convert_to_needs(cls, needs):
        result = []
        for need in needs:
            # noinspection PyCompatibility
            if isinstance(need, Need):
                result.append(need)
            elif isinstance(need, Permission):
                result += need.needs
            elif isinstance(need, basestring):
                result.append(RoleNeed(need))
        return result

    def __init__(self, name, description, *needs, **kwargs):
        self._name = name
        self._description = description
        self._dangerous = kwargs.pop("dangerous", False)
        self._default_groups = kwargs.pop("default_groups", [])

        self._key = None

        Permission.__init__(self, *self.convert_to_needs(needs))

    def as_dict(self):
        return {
            "key": self.key,
            "name": self.get_name(),
            "dangerous": self._dangerous,
            "default_groups": self._default_groups,
            "description": self.get_description(),
            "needs": self.convert_needs_to_dict(self.needs),
        }

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, value):
        self._key = value

    @property
    def dangerous(self):
        return self._dangerous

    @property
    def default_groups(self):
        return self._default_groups

    def get_name(self):
        return self._name

    def get_description(self):
        return self._description

    def allows(self, identity):
        """Whether the identity can access this permission.
        Overridden from Permission.allows to make sure the Identity provides ALL
        required needs instead of ANY required need.

        :param identity: The identity
        """
        if self.needs and len(self.needs.intersection(identity.provides)) != len(
            self.needs
        ):
            return False

        if self.excludes and self.excludes.intersection(identity.provides):
            return False

        return True

    def union(self, other):
        """Create a new OctoPrintPermission with the requirements of the union of this
        and other.

        :param other: The other permission
        """
        p = self.__class__(self._name, self._description, *self.needs.union(other.needs))
        p.excludes.update(self.excludes.union(other.excludes))
        return p

    def difference(self, other):
        """Create a new OctoPrintPermission consisting of requirements in this
        permission and not in the other.
        """

        p = self.__class__(
            self._name, self._description, *self.needs.difference(other.needs)
        )
        p.excludes.update(self.excludes.difference(other.excludes))
        return p

    def __repr__(self):
        return "{}({!r}, {!r}, {})".format(
            self.__class__.__name__,
            self.get_name(),
            self.get_description(),
            ", ".join(map(repr, self.needs)),
        )

    def __hash__(self):
        return self.get_name().__hash__()

    def __eq__(self, other):
        return (
            isinstance(other, OctoPrintPermission) and other.get_name() == self.get_name()
        )


class PluginOctoPrintPermission(OctoPrintPermission):
    def __init__(self, *args, **kwargs):
        self.plugin = kwargs.pop("plugin", None)
        OctoPrintPermission.__init__(self, *args, **kwargs)

    def as_dict(self):
        result = OctoPrintPermission.as_dict(self)
        result["plugin"] = self.plugin
        return result


class PluginIdentityContext(object):
    """Identity context for not initialized Permissions

    Needed to support @Permissions.PLUGIN_X_Y.require()

    Will search the permission when needed
    """

    def __init__(self, key, http_exception=None):
        self.key = key
        self.http_exception = http_exception
        """The permission of this principal
        """

    @property
    def identity(self):
        """The identity of this principal"""
        return g.identity

    def can(self):
        """Whether the identity has access to the permission"""
        permission = getattr(Permissions, self.key)
        if permission is None or isinstance(permission, PluginPermissionDecorator):
            raise UnknownPermission(self.key)

        return permission.can()

    def __call__(self, f):
        @wraps(f)
        def _decorated(*args, **kw):
            with self:
                rv = f(*args, **kw)
            return rv

        return _decorated

    def __enter__(self):
        permission = getattr(Permissions, self.key)
        if permission is None or isinstance(permission, PluginPermissionDecorator):
            raise UnknownPermission(self.key)

        # check the permission here
        if not permission.can():
            if self.http_exception:
                abort(self.http_exception, permission)
            raise PermissionDenied(permission)

    def __exit__(self, *args):
        return False


class PluginPermissionDecorator(Permission):
    """Decorator Class for not initialized Permissions

    Needed to support @Permissions.PLUGIN_X_Y.require()
    """

    def __init__(self, key):
        self.key = key

    def require(self, http_exception=None):
        return PluginIdentityContext(self.key, http_exception)


class PermissionsMetaClass(type):
    permissions = OrderedDict()

    def __new__(mcs, name, bases, args):
        cls = type.__new__(mcs, name, bases, args)

        for key, value in args.items():
            if isinstance(value, OctoPrintPermission):
                value.key = key
                mcs.permissions[key] = value
                delattr(cls, key)

        return cls

    def __setattr__(cls, key, value):
        if isinstance(value, OctoPrintPermission):
            if key in cls.permissions:
                raise PermissionAlreadyExists(key)
            value.key = key
            cls.permissions[key] = value

    def __getattr__(cls, key):
        permission = cls.permissions.get(key)

        if key.startswith("PLUGIN_") and permission is None:
            return PluginPermissionDecorator(key)

        return permission

    def all(cls):
        return list(cls.permissions.values())

    def filter(cls, cb):
        return list(filter(cb, cls.all()))

    def find(cls, p, filter=None):
        key = None
        if isinstance(p, OctoPrintPermission):
            key = p.key
        elif isinstance(p, dict):
            key = p.get("key")
        elif isinstance(p, basestring):
            key = p

        if key is None:
            return None

        return cls.match(lambda p: p.key == key, filter=filter)

    def match(cls, match, filter=None):
        if callable(filter):
            permissions = cls.filter(filter)
        else:
            permissions = cls.all()

        for permission in permissions:
            if match(permission):
                return permission

        return None


class Permissions(with_metaclass(PermissionsMetaClass)):

    # Special permission
    ADMIN = OctoPrintPermission(
        "Admin",
        gettext("Admin is allowed to do everything"),
        RoleNeed("admin"),
        dangerous=True,
        default_groups=[ADMIN_GROUP],
    )

    STATUS = OctoPrintPermission(
        "Status",
        gettext(
            "Allows to gather basic status information, e.g. job progress, "
            "printer state, temperatures, ... Mandatory for the default UI "
            "to work"
        ),
        RoleNeed("status"),
        default_groups=[USER_GROUP, READONLY_GROUP],
    )

    CONNECTION = OctoPrintPermission(
        "Connection",
        gettext("Allows to connect to and disconnect from a printer"),
        RoleNeed("connection"),
        default_groups=[USER_GROUP],
    )

    WEBCAM = OctoPrintPermission(
        "Webcam",
        gettext("Allows to watch the webcam stream"),
        RoleNeed("webcam"),
        default_groups=[USER_GROUP, READONLY_GROUP],
    )

    SYSTEM = OctoPrintPermission(
        "System",
        gettext(
            "Allows to run system commands, e.g. restart OctoPrint, "
            "shutdown or reboot the system, and to retrieve system and usage information"
        ),
        RoleNeed("system"),
        dangerous=True,
    )

    FILES_LIST = OctoPrintPermission(
        "File List",
        gettext(
            "Allows to retrieve a list of all uploaded files and folders, including"
            "their metadata (e.g. date, file size, analysis results, ...)"
        ),
        RoleNeed("files_list"),
        default_groups=[USER_GROUP, READONLY_GROUP],
    )
    FILES_UPLOAD = OctoPrintPermission(
        "File Upload",
        gettext(
            "Allows users to upload new files, create new folders and copy existing ones. If "
            "the File Delete permission is also set, File Upload also allows "
            "moving files and folders."
        ),
        RoleNeed("files_upload"),
        default_groups=[USER_GROUP],
    )
    FILES_DOWNLOAD = OctoPrintPermission(
        "File Download",
        gettext(
            "Allows users to download files. The GCODE viewer is "
            "affected by this as well."
        ),
        RoleNeed("files_download"),
        default_groups=[USER_GROUP, READONLY_GROUP],
    )
    FILES_DELETE = OctoPrintPermission(
        "File Delete",
        gettext(
            "Allows users to delete files and folders. If the File Upload permission is "
            "also set, File Delete also allows moving files and folders."
        ),
        RoleNeed("files_delete"),
        default_groups=[USER_GROUP],
    )
    FILES_SELECT = OctoPrintPermission(
        "File Select",
        gettext("Allows to select a file for printing"),
        RoleNeed("files_select"),
        default_groups=[USER_GROUP],
    )

    PRINT = OctoPrintPermission(
        "Print",
        gettext("Allows to start, pause and cancel a print job"),
        RoleNeed("print"),
        default_groups=[USER_GROUP],
    )

    GCODE_VIEWER = OctoPrintPermission(
        "GCODE viewer",
        gettext(
            'Allows access to the GCODE viewer if the "File Download"'
            "permission is also set."
        ),
        RoleNeed("gcodeviewer"),
        default_groups=[USER_GROUP, READONLY_GROUP],
    )

    MONITOR_TERMINAL = OctoPrintPermission(
        "Terminal",
        gettext(
            "Allows to watch the terminal tab but not to send commands "
            "to the printer from it"
        ),
        RoleNeed("monitor_terminal"),
        default_groups=[USER_GROUP, READONLY_GROUP],
    )

    CONTROL = OctoPrintPermission(
        "Control",
        gettext(
            "Allows to control of the printer by using the temperature controls,"
            "the control tab or sending commands through the terminal."
        ),
        RoleNeed("control"),
        default_groups=[USER_GROUP],
    )

    SLICE = OctoPrintPermission(
        "Slice",
        gettext("Allows to slice files"),
        RoleNeed("slice"),
        default_groups=[USER_GROUP],
    )

    TIMELAPSE_LIST = OctoPrintPermission(
        "Timelapse List",
        gettext("Allows to list timelapse videos"),
        RoleNeed("timelapse_list"),
        default_groups=[USER_GROUP, READONLY_GROUP],
    )
    TIMELAPSE_DOWNLOAD = OctoPrintPermission(
        "Timelapse Download",
        gettext("Allows to download timelapse videos"),
        RoleNeed("timelapse_download"),
        default_groups=[USER_GROUP, READONLY_GROUP],
    )
    TIMELAPSE_DELETE = OctoPrintPermission(
        "Timelapse Delete",
        gettext("Allows to delete timelapse videos and unrendered timelapses"),
        RoleNeed("timelapse_delete"),
        default_groups=[USER_GROUP],
    )
    TIMELAPSE_ADMIN = OctoPrintPermission(
        "Timelapse Admin",
        gettext(
            "Allows to change the timelapse settings and delete or "
            'render unrendered timelapses. Includes the "Timelapse List",'
            '"Timelapse Delete" and "Timelapse Download" permissions'
        ),
        RoleNeed("timelapse_admin"),
        TIMELAPSE_LIST,
        TIMELAPSE_DOWNLOAD,
        default_groups=[USER_GROUP],
    )

    SETTINGS_READ = OctoPrintPermission(
        "Settings Access",
        gettext(
            "Allows to read non sensitive settings. Mandatory for the "
            "default UI to work."
        ),
        RoleNeed("settings_read"),
        default_groups=[USER_GROUP, READONLY_GROUP],
    )
    SETTINGS = OctoPrintPermission(
        "Settings Admin",
        gettext("Allows to manage settings and also to read sensitive settings"),
        RoleNeed("settings"),
        dangerous=True,
    )


class PermissionAlreadyExists(Exception):
    def __init__(self, permission):
        Exception.__init__(self, "Permission %s already exists" % permission)


class UnknownPermission(Exception):
    def __init__(self, permissionname):
        Exception.__init__(self, "Unknown permission: %s" % permissionname)
