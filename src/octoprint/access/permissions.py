# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Marc Hannappel <salandora@gmail.com>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask_principal import Permission, RoleNeed

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

	def asDict(self):
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
		return '{0}(name="{1}", description="{2}", needs={3})'.format(self.__class__.__name__, self.get_name(), self.get_description(), self.needs)

class PermissionManager(object):
	def __init__(self):
		self._permissions = []

		import yaml
		from yaml.dumper import SafeDumper
		from yaml.loader import SafeLoader

		yaml.add_representer(OctoPrintPermission, self.yaml_representer, Dumper=SafeDumper)
		yaml.add_constructor(u'!octoprintpermission', self.yaml_constructor, Loader=SafeLoader)

	@property
	def permissions(self):
		return list(self._permissions)

	def yaml_representer(self, dumper, data):
		return dumper.represent_scalar(u'!octoprintpermission', data.get_name())

	def yaml_constructor(self, loader, node):
		name = loader.construct_scalar(node)
		return self.find_permission(name)

	def add_permission(self, permission):
		self._permissions.append(permission)
		return permission

	def remove_permission(self, permission):
		self._permissions.remove(permission)

		from octoprint.server import groupManager, userManager
		groupManager.remove_permissions_from_groups([permission])
		userManager.remove_permissions_from_users([permission])

	def find_permission(self, name):
		for p in self._permissions:
			if p.get_name() == name:
				return p

		return None

	def get_permission_from(self, permission):
		return permission if isinstance(permission, OctoPrintPermission) \
			else self.find_permission(permission["name"]) if isinstance(permission, dict) \
			else self.find_permission(permission)


class Permissions(object):
	# Special permission
	ADMIN = OctoPrintPermission("Admin", "Admin is allowed to do everything", RoleNeed("admin"))

	STATUS = OctoPrintPermission("Status",
	                        "Allows to gather Statusinformations like, Connection, Printstate, Temperaturegraph",
	                             RoleNeed("status"))
	CONNECTION = OctoPrintPermission("Connection", "Allows to connect and disconnect to a printer", RoleNeed("connection"))
	WEBCAM = OctoPrintPermission("Webcam", "Allows to watch the webcam stream", RoleNeed("webcam"))
	SYSTEM = OctoPrintPermission("System", "Allows to run system commands, e.g. shutdown, reboot, restart octoprint",
	                             RoleNeed("system"))
	UPLOAD = OctoPrintPermission("Upload", "Allows users to upload new gcode files", RoleNeed("upload"))
	DOWNLOAD = OctoPrintPermission("Download",
	                          "Allows users to download gcode files, the gCodeViewer is affected by this too.",
	                               RoleNeed("download"))
	DELETE = OctoPrintPermission("Delete", "Allows users to delete files in their folder", RoleNeed("delete_file"))
	SELECT = OctoPrintPermission("Select", "Allows to select a file", RoleNeed("select"))
	PRINT = OctoPrintPermission("Print", "Allows to start a print job, inherits the select permission",
	                               RoleNeed("print"))
	TERMINAL = OctoPrintPermission("Terminal", "Allows to watch the Terminaltab, without the ability to send any commands",
	                               RoleNeed("terminal"))
	CONTROL = OctoPrintPermission("Control",
	                         "Allows to manually control the printer by using the controltab or sending gcodes through the terminal, this implies the terminal permission",
	                              RoleNeed("control"))
	SLICE = OctoPrintPermission("Slice", "Allows to slice stl files into gcode files", RoleNeed("slice"))
	TIMELAPSE = OctoPrintPermission("Timelapse", "Allows to download timelapse videos", RoleNeed("timelapse"))
	TIMELAPSE_ADMIN = OctoPrintPermission("Timelapse Admin",
	                                 "Allows to change the timelapse settings, remove timelapses, implies timelapse",
	                                      RoleNeed("timelapse_admin"))
	SETTINGS = OctoPrintPermission("Settings", "Allows to open and change Settings", RoleNeed("settings"))
	LOGS = OctoPrintPermission("Logs", "Allows to download and remove logs", RoleNeed("logs"))

	################################################################################
	# Deprecated only for migration
	USER_ARRAY = [STATUS, CONNECTION, WEBCAM, UPLOAD, DOWNLOAD, DELETE, SELECT, PRINT, TERMINAL, CONTROL, SLICE, TIMELAPSE, TIMELAPSE_ADMIN]
	#from operator import or_
	#USER = variable_deprecated("This variable is only for migration and is deprecated already, don't use it!", since="now")(OctoPrintPermission("User", "Migrated User permission class, deprecated", *reduce(or_, map(lambda p: p.needs, USER_ARRAY))))
	################################################################################

	FILE_PERMISSION = Permission(*UPLOAD.needs.union(DOWNLOAD.needs).union(DELETE.needs).union(SELECT.needs).union(PRINT.needs).union(SLICE.needs))

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
