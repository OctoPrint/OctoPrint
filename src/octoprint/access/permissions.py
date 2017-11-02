# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Marc Hannappel <salandora@gmail.com>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"


from flask import g, abort
from flask_babel import gettext
from flask_principal import Permission, PermissionDenied, RoleNeed
from functools import wraps
from collections import OrderedDict
import logging


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

		Permission.__init__(self, *needs)

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
		p = OctoPrintPermission(self._name, self._description, *self.needs.union(other.needs))
		p.excludes.update(self.excludes.union(other.excludes))
		return p

	def difference(self, other):
		"""Create a new OctoPrintPermission consisting of requirements in this
		permission and not in the other.
		"""

		p = OctoPrintPermission(self._name, self._description, *self.needs.difference(other.needs))
		p.excludes.update(self.excludes.difference(other.excludes))
		return p

	def __repr__(self):
		needs = []
		for need in sorted(self.needs):
			if need.method == 'role':
				needs.append("RoleNeed('{0}')".format(need.value))

		return '{0}("{1}", "{2}", {3})'.format(self.__class__.__name__, self.get_name(), self.get_description(), ', '.join(needs))


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
		permission = Permissions.__getattr__(self.key)
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
		permission = Permissions.__getattr__(self.key)
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


class PermissionManager(object):
	def __init__(self):
		self._permissions = OrderedDict()
		self._combined_permissions = OrderedDict()

		self.logger = logging.getLogger(__name__)

		import yaml
		from yaml.dumper import SafeDumper
		from yaml.loader import SafeLoader

		yaml.add_representer(OctoPrintPermission, self.yaml_representer, Dumper=SafeDumper)
		yaml.add_constructor(u'!octoprintpermission', self.yaml_constructor, Loader=SafeLoader)

	@property
	def permissions(self):
		"""Returns a list of all registered permissions"""
		return self._permissions.values()

	@property
	def combined_permissions(self):
		"""Returns a list of all registered combined permissions"""
		return self._combined_permissions.values()

	def yaml_representer(self, dumper, data):
		return dumper.represent_scalar(u'!octoprintpermission', data.get_name())

	def yaml_constructor(self, loader, node):
		name = loader.construct_scalar(node)
		return self.find_permission(name)

	def add_permission(self, permission):
		"""Registers a OctoPrintPermission object inside the permission manager class"""
		if permission.get_name() in self._permissions:
			raise PermissionAlreadyExists(permission.get_name())

		self._permissions[permission.get_name()] = permission
		return permission

	def remove_permission(self, permission):
		"""Removes a OctoPrintPermission object from the permission manager class"""
		if permission is None:
			self.logger.exception("Attribute permission is None")
			return

		permission_name = permission.get_name() if isinstance(permission, OctoPrintPermission) else permission
		if permission_name not in self._permissions.keys():
			raise UnknownPermission(permission_name)

		from octoprint.server import groupManager, userManager
		groupManager.remove_permissions_from_groups([permission_name])
		userManager.remove_permissions_from_users([permission_name])

		try:
			del self._permissions[permission_name]
		except KeyError as e:
			self.logger.exception("Tried to remove a permission (%s) that is already gone" % permission_name)
			pass

	def find_permission(self, name):
		"""Searches a registered OctoPrintPermission by name, returns either the permission object or None"""
		return self._permissions.get(name, None)

	def get_permission_from(self, permission):
		"""This function accepts either a OctoPrintPermission object, a return value of asDict, or a name
		to search for a registered OctoPrintPermission in the permission manager class"""
		return self.find_permission(permission.get_name()) if isinstance(permission, OctoPrintPermission) \
			else self.find_permission(permission["name"]) if isinstance(permission, dict) \
			else self.find_permission(permission)

	def add_combined_permission(self, permission):
		"""Registers a combined OctoPrintPermission object inside the permission manager class"""
		if permission.get_name() in self._combined_permissions:
			raise PermissionAlreadyExists(permission.get_name())

		self._combined_permissions[permission.get_name()] = permission
		return permission

	def remove_combined_permission(self, permission):
		"""Removes a combined OctoPrintPermission object from the permission manager class"""
		if permission is None:
			self.logger.exception("Attribute permission is None")
			return

		permission_name = permission.get_name() if isinstance(permission, OctoPrintPermission) else permission
		if permission_name not in self._combined_permissions.keys():
			raise UnknownPermission(permission_name)

		try:
			del self._combined_permissions[permission_name]
		except KeyError as e:
			self.logger.exception("Tried to remove a combined permission (%s) that is already gone" % permission_name)
			pass

	def find_combined_permission(self, name):
		"""Searches a registered OctoPrintPermission by name, returns either the permission object or None"""
		return self._combined_permissions.get(name, None)

	def get_combined_permission_from(self, permission):
		"""This function accepts either a OctoPrintPermission object, a return value of asDict, or a name
		to search for a registered OctoPrintPermission in the permission manager class"""
		return self.find_combined_permission(permission.get_name()) if isinstance(permission, OctoPrintPermission) \
			else self.find_combined_permission(permission["name"]) if isinstance(permission, dict) \
			else self.find_combined_permission(permission)

def unionPermissions(name, *args):
	if len(args) == 0:
		return None

	permission = OctoPrintPermission(name, "", *args[0].needs)
	for p in args[1:]:
		permission = permission.union(p)

	return permission

class Permissions:
	class PluginPermissionMetaclass(type):
		plugin_permissions = OrderedDict()

		@classmethod
		def __setattr__(cls, key, value):
			if key.startswith("PLUGIN"):
				if cls.plugin_permissions.get(key, None) is not None:
					raise PermissionAlreadyExists(key)

				cls.plugin_permissions[key] = value

		def __getattr__(cls, key):
			if key.startswith("PLUGIN"):
				permission = cls.plugin_permissions.get(key, None)

				if permission is None:
					return PluginPermissionDecorator(key)

				return permission

			return None

	__metaclass__ = PluginPermissionMetaclass


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

	CONTROL_ACCESS = unionPermissions("Control Access", CONTROL, WEBCAM)
	CONNECTION_ACCESS = unionPermissions("Connection Access", CONNECTION, STATUS)
	FILES_ACCESS = unionPermissions("Files Access", UPLOAD, DOWNLOAD, DELETE, SELECT, PRINT, SLICE)
	PRINTERPROFILES_ACCESS = unionPermissions("Printerprofiles Access", CONNECTION, SETTINGS)
	TIMELAPSE_ACCESS = unionPermissions("Timelapse Access", TIMELAPSE, TIMELAPSE_ADMIN)


	##############################################################
	## This will be used to define permissions for normal users ##
	USER_ARRAY = [STATUS, CONNECTION, WEBCAM, UPLOAD, DOWNLOAD, DELETE, SELECT, PRINT, TERMINAL, CONTROL, SLICE, TIMELAPSE, TIMELAPSE_ADMIN]

	@classmethod
	def initialize(cls):
		from octoprint.server import permissionManager as pm

		pm.add_permission(cls.ADMIN)
		pm.add_permission(cls.STATUS)
		pm.add_permission(cls.CONNECTION)
		pm.add_permission(cls.WEBCAM)
		pm.add_permission(cls.SYSTEM)

		pm.add_permission(cls.UPLOAD)
		pm.add_permission(cls.DOWNLOAD)
		pm.add_permission(cls.DELETE)
		pm.add_permission(cls.SELECT)
		pm.add_permission(cls.PRINT)

		pm.add_permission(cls.TERMINAL)
		pm.add_permission(cls.CONTROL)
		pm.add_permission(cls.SLICE)
		pm.add_permission(cls.TIMELAPSE)
		pm.add_permission(cls.TIMELAPSE_ADMIN)

		pm.add_permission(cls.SETTINGS)
		pm.add_permission(cls.LOGS)

		pm.add_combined_permission(cls.CONTROL_ACCESS)
		pm.add_combined_permission(cls.CONNECTION_ACCESS)
		pm.add_combined_permission(cls.FILES_ACCESS)
		pm.add_combined_permission(cls.PRINTERPROFILES_ACCESS)
		pm.add_combined_permission(cls.TIMELAPSE_ACCESS)

	@classmethod
	def __setattr__(cls, key, value):
		if key.startswith("PLUGIN"):
			cls.__metaclass__.__setattr__(key, value)


class PermissionAlreadyExists(Exception):
	def __init__(self, permission):
		Exception.__init__(self, "Permission %s already exists" % permission)


class UnknownPermission(Exception):
	def __init__(self, permissionname):
		Exception.__init__(self, "Unknown permission: %s" % permissionname)
