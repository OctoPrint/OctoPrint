# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Marc Hannappel <salandora@gmail.com>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"


from flask import g, abort
from flask_babel import gettext
from flask_principal import Permission, PermissionDenied, RoleNeed, Need

from functools import wraps
from collections import OrderedDict

from past.builtins import basestring


class OctoPrintPermission(Permission):
	@classmethod
	def convert_needs_to_dict(cls, needs):
		ret_needs = dict()
		for need in needs:
			if need.method not in ret_needs:
				ret_needs[need.method] = []

			if need.value not in ret_needs[need.method]:
				ret_needs[need.method].append(need.value)

		return ret_needs

	def __init__(self, name, description, *needs, **kwargs):
		self._name = name
		self._description = description
		self._dangerous = kwargs.pop("dangerous", False) == True

		self._key = None

		Permission.__init__(self, *[RoleNeed(x) if not isinstance(x, Need) else x for x in needs])

	def as_dict(self):
		return dict(
			key=self.key,
			name=self.get_name(),
			dangerous=self._dangerous,
			description=self.get_description(),
			needs=self.convert_needs_to_dict(self.needs)
		)

	@property
	def key(self):
		return self._key

	@key.setter
	def key(self, value):
		self._key = value

	def get_name(self):
		return self._name

	def get_description(self):
		return self._description

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

		p = self.__class__(self._name, self._description, *self.needs.difference(other.needs))
		p.excludes.update(self.excludes.difference(other.excludes))
		return p

	def __repr__(self):
		needs = []
		for need in sorted(self.needs):
			if need.method == 'role':
				needs.append("RoleNeed('{0}')".format(need.value))

		return '{}("{}", "{}", {})'.format(self.__class__.__name__, self.get_name(), self.get_description(), ', '.join(needs))

	def __hash__(self):
		return self.get_name().__hash__()

	def __eq__(self, other):
		return isinstance(other, OctoPrintPermission) and other.get_name() == self.get_name()


class PluginOctoPrintPermission(OctoPrintPermission):

	def __init__(self, *args, **kwargs):
		self.plugin = kwargs.pop("plugin", None)
		OctoPrintPermission.__init__(self, *args, **kwargs)

	def as_dict(self):
		result = OctoPrintPermission.as_dict(self)
		result["plugin"] = self.plugin
		return result


class CombinedOctoPrintPermission(OctoPrintPermission):

	def as_dict(self):
		result = OctoPrintPermission.as_dict(self)
		result["combined"] = True
		return result

	@classmethod
	def from_permissions(cls, name, *permissions, **kwargs):
		if len(permissions) == 0:
			return None

		description = kwargs.pop("description", "")

		permission = cls(name, description, *permissions[0].needs, **kwargs)
		for p in permissions[1:]:
			permission = permission.union(p)

		return permission


class CombinedPluginOctoPrintPermission(CombinedOctoPrintPermission):

	def __init__(self, *args, **kwargs):
		self.plugin = kwargs.pop("plugin", None)
		CombinedOctoPrintPermission.__init__(self, *args, **kwargs)

	def as_dict(self):
		result = CombinedOctoPrintPermission.as_dict(self)
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
		"""The identity of this principal
		"""
		return g.identity

	def can(self):
		"""Whether the identity has access to the permission
		"""
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
		return cls.permissions.values()

	def filter(cls, cb):
		return filter(cb, cls.all())

	def regular(cls):
		return cls.filter(lambda x: not isinstance(x, CombinedOctoPrintPermission))

	def combined(cls):
		return cls.filter(lambda x: isinstance(x, CombinedOctoPrintPermission))

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


class Permissions(object):
	__metaclass__ = PermissionsMetaClass

	# Special permission
	ADMIN                  = OctoPrintPermission("Admin",
	                                             gettext("Admin is allowed to do everything"),
	                                             RoleNeed("admin"),
	                                             dangerous=True)

	STATUS                 = OctoPrintPermission("Status",
	                                             gettext("Allows to gather status information, e.g. job progress, "
	                                                     "printer state, temperatures, ..."),
	                                             RoleNeed("status"))
	CONNECTION             = OctoPrintPermission("Connection",
	                                             gettext("Allows to connect to and disconnect and from a printer"),
	                                             RoleNeed("connection"))
	WEBCAM                 = OctoPrintPermission("Webcam",
	                                             gettext("Allows to watch the webcam stream"),
	                                             RoleNeed("webcam"))
	SYSTEM                 = OctoPrintPermission("System",
	                                             gettext("Allows to run system commands, e.g. restart OctoPrint, "
	                                                     "shutdown or reboot the system"),
	                                             RoleNeed("system"))
	UPLOAD                 = OctoPrintPermission("Upload",
	                                             gettext("Allows users to upload new files"),
	                                             RoleNeed("upload"))
	DOWNLOAD               = OctoPrintPermission("Download",
	                                             gettext("Allows users to download files. The GCODE viewer is "
	                                                     "affected by this as well."),
	                                             RoleNeed("download"))
	GCODE_VIEWER           = OctoPrintPermission("GCODE viewer",
	                                             gettext("Allowed access to the GCODE viewer. Includes the \"Download\""
	                                                     "permission."),
	                                             RoleNeed("gcodeviewer"), RoleNeed("download"))
	DELETE                 = OctoPrintPermission("Delete",
	                                             gettext("Allows users to delete files"),
	                                             RoleNeed("delete_file"))
	SELECT                 = OctoPrintPermission("Select",
	                                             gettext("Allows to select a file for printing"),
	                                             RoleNeed("select"))
	PRINT                  = OctoPrintPermission("Print",
	                                             gettext("Allows to start a print job. Includes the \"Select\" "
	                                                     "permission"),
	                                             RoleNeed("print"), RoleNeed("select"))
	TERMINAL               = OctoPrintPermission("Terminal",
	                                             gettext("Allows to watch the terminal tab but not to send commands "
	                                                     "to the printer from it"),
	                                             RoleNeed("terminal"))
	CONTROL                = OctoPrintPermission("Control",
	                                             gettext("Allows to control of the printer by using the control tab or "
	                                                     "sending commands through the terminal. Includes the "
	                                                     "\"Terminal\" permission"),
	                                             RoleNeed("control"), RoleNeed("terminal"))
	SLICE                  = OctoPrintPermission("Slice",
	                                             gettext("Allows to slice files"),
	                                             RoleNeed("slice"))
	TIMELAPSE              = OctoPrintPermission("Timelapse",
	                                             gettext("Allows to download timelapse videos"),
	                                             RoleNeed("timelapse"))
	TIMELAPSE_ADMIN        = OctoPrintPermission("Timelapse Admin",
	                                             gettext("Allows to change the timelapse settings, remove timelapses,"
	                                                     "render unrendered timelapses. Includes the \"Timelapse\""
	                                                     "permission"),
	                                             RoleNeed("timelapse_admin"), RoleNeed("timelapse"))
	SETTINGS               = OctoPrintPermission("Settings",
	                                             gettext("Allows to manage settings"),
	                                             RoleNeed("settings"))
	LOGS                   = OctoPrintPermission("Logs",
	                                             gettext("Allows to download and remove logs"),
	                                             RoleNeed("logs"))

	CONTROL_ACCESS         = CombinedOctoPrintPermission.from_permissions("Control Access",
	                                                                      CONTROL, WEBCAM)
	CONNECTION_ACCESS      = CombinedOctoPrintPermission.from_permissions("Connection Access",
	                                                                      CONNECTION, STATUS)
	FILES_ACCESS           = CombinedOctoPrintPermission.from_permissions("Files Access",
	                                                                      UPLOAD, DOWNLOAD, DELETE, SELECT, PRINT,
	                                                                      SLICE)
	PRINTERPROFILES_ACCESS = CombinedOctoPrintPermission.from_permissions("Printerprofiles Access",
	                                                                      CONNECTION, SETTINGS)
	TIMELAPSE_ACCESS       = CombinedOctoPrintPermission.from_permissions("Timelapse Access",
	                                                                      TIMELAPSE, TIMELAPSE_ADMIN)


class PermissionAlreadyExists(Exception):
	def __init__(self, permission):
		Exception.__init__(self, "Permission %s already exists" % permission)


class UnknownPermission(Exception):
	def __init__(self, permissionname):
		Exception.__init__(self, "Unknown permission: %s" % permissionname)
