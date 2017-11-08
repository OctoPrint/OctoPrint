# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Marc Hannappel <salandora@gmail.com>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"


from flask import g, abort
from flask_babel import gettext
from flask_principal import Permission, PermissionDenied, RoleNeed, Need
from functools import wraps

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

	def __init__(self, name, description, *needs):
		self._name = name
		self._description = description

		Permission.__init__(self, *map(lambda x: RoleNeed(x) if not isinstance(x, Need) else x, needs))

	def as_dict(self):
		return dict(
			name=self.get_name(),
			description=self.get_description(),
			needs=self.convert_needs_to_dict(self.needs)
		)

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

		return '{0}("{1}", "{2}", {3})'.format(self.__class__.__name__, self.get_name(), self.get_description(), ', '.join(needs))


class CombinedOctoPrintPermission(OctoPrintPermission):

	def as_dict(self):
		result = OctoPrintPermission.as_dict(self)
		result["combined"] = True
		return result

	@classmethod
	def from_permissions(cls, name, *permissions, **kwargs):
		if len(permissions) == 0:
			return None

		description = kwargs.get("description", "")

		permission = CombinedOctoPrintPermission(name, description, *permissions[0].needs)
		for p in permissions[1:]:
			permission = permission.union(p)

		return permission


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
	plugin_permissions = dict()

	def __setattr__(cls, key, value):
		if key.startswith("PLUGIN_"):
			if key in cls.plugin_permissions:
				raise PermissionAlreadyExists(key)
			cls.plugin_permissions[key] = value

	def __getattr__(cls, key):
		if key.startswith("PLUGIN_"):
			permission = cls.plugin_permissions.get(key, None)
			if permission is None:
				return PluginPermissionDecorator(key)
			return permission

		return None


class Permissions(object):
	__metaclass__ = PermissionsMetaClass

	# Special permission
	ADMIN = OctoPrintPermission("Admin", gettext("Admin is allowed to do everything"), RoleNeed("admin"))

	STATUS = OctoPrintPermission("Status",
	                        gettext("Allows to gather Statusinformations like, Connection, Printstate, Temperaturegraph"),
	                             RoleNeed("status"))
	CONNECTION = OctoPrintPermission("Connection", gettext("Allows to connect and disconnect to a printer"), RoleNeed("connection"))
	WEBCAM = OctoPrintPermission("Webcam", gettext("Allows to watch the webcam stream"), RoleNeed("webcam"))
	SYSTEM = OctoPrintPermission("System", gettext("Allows to run system commands, e.g. shutdown, reboot, restart octoprint"),
	                             RoleNeed("system"))
	UPLOAD = OctoPrintPermission("Upload", gettext("Allows users to upload new gcode files"), RoleNeed("upload"))
	DOWNLOAD = OctoPrintPermission("Download",
	                          gettext("Allows users to download gcode files, the gCodeViewer is affected by this too."),
	                               RoleNeed("download"))
	DELETE = OctoPrintPermission("Delete", gettext("Allows users to delete files in their folder"), RoleNeed("delete_file"))
	SELECT = OctoPrintPermission("Select", gettext("Allows to select a file"), RoleNeed("select"))
	PRINT = OctoPrintPermission("Print", gettext("Allows to start a print job, inherits the select permission"),
	                               RoleNeed("print"))
	TERMINAL = OctoPrintPermission("Terminal", gettext("Allows to watch the Terminaltab, without the ability to send any commands"),
	                               RoleNeed("terminal"))
	CONTROL = OctoPrintPermission("Control",
	                         gettext("Allows to manually control the printer by using the controltab or sending gcodes through the terminal, this implies the terminal permission"),
	                              RoleNeed("control"))
	SLICE = OctoPrintPermission("Slice", gettext("Allows to slice stl files into gcode files"), RoleNeed("slice"))
	TIMELAPSE = OctoPrintPermission("Timelapse", gettext("Allows to download timelapse videos"), RoleNeed("timelapse"))
	TIMELAPSE_ADMIN = OctoPrintPermission("Timelapse Admin",
	                                 gettext("Allows to change the timelapse settings, remove timelapses, implies timelapse"),
	                                      RoleNeed("timelapse_admin"))
	SETTINGS = OctoPrintPermission("Settings", gettext("Allows to open and change Settings"), RoleNeed("settings"))
	LOGS = OctoPrintPermission("Logs", gettext("Allows to download and remove logs"), RoleNeed("logs"))

	CONTROL_ACCESS = CombinedOctoPrintPermission.from_permissions("Control Access", CONTROL, WEBCAM)
	CONNECTION_ACCESS = CombinedOctoPrintPermission.from_permissions("Connection Access", CONNECTION, STATUS)
	FILES_ACCESS = CombinedOctoPrintPermission.from_permissions("Files Access", UPLOAD, DOWNLOAD, DELETE, SELECT, PRINT, SLICE)
	PRINTERPROFILES_ACCESS = CombinedOctoPrintPermission.from_permissions("Printerprofiles Access", CONNECTION, SETTINGS)
	TIMELAPSE_ACCESS = CombinedOctoPrintPermission.from_permissions("Timelapse Access", TIMELAPSE, TIMELAPSE_ADMIN)

	@classmethod
	def all(cls):
		return [getattr(Permissions, name) for name in Permissions.__dict__
		        if not name.startswith("__") and isinstance(getattr(Permissions, name), OctoPrintPermission)] \
		       + cls.__metaclass__.plugin_permissions.values()

	@classmethod
	def filter(cls, cb):
		return filter(cb, cls.all())

	@classmethod
	def regular(cls):
		return cls.filter(lambda x: not isinstance(x, CombinedOctoPrintPermission))

	@classmethod
	def combined(cls):
		return cls.filter(lambda x: isinstance(x, CombinedOctoPrintPermission))

	@classmethod
	def find(cls, p, filter=None):
		name = None
		if isinstance(p, OctoPrintPermission):
			name = p.get_name()
		elif isinstance(p, dict):
			name = p.get("name")
		elif isinstance(p, basestring):
			name = p

		if name is None:
			return None

		return cls.match(lambda p: p.get_name() == name, filter=filter)

	@classmethod
	def match(cls, match, filter=None):
		if callable(filter):
			permissions = cls.filter(filter)
		else:
			permissions = cls.all()

		for permission in permissions:
			if match(permission):
				return permission

		return None


class PermissionAlreadyExists(Exception):
	def __init__(self, permission):
		Exception.__init__(self, "Permission %s already exists" % permission)


class UnknownPermission(Exception):
	def __init__(self, permissionname):
		Exception.__init__(self, "Unknown permission: %s" % permissionname)
