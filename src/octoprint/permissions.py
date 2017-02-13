# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Marc Hannappel <salandora@gmail.com>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask.ext.principal import Permission, RoleNeed
from flask.json import JSONEncoder
from .util import variable_deprecated

class OctoPermissionEncoder(JSONEncoder):
	def default(self, obj):
		if isinstance(obj, OctoPermission):
			return Permissions.permissions_to_list([obj])

		return JSONEncoder.default(self, obj)


all_permissions = []
class OctoPermission(Permission):
	def __init__(self, name, description, *needs):
		self._name = name
		self._description = description
		all_permissions.append(self)

		super(OctoPermission, self).__init__(*needs)

	def asDict(self):
		return dict(
				name=self.get_name(),
				description=self.get_description(),
				needs=Permissions.permissions_to_need_list([self])
		)

	def get_name(self):
		return self._name

	def get_description(self):
		return self._description

	def get_js_need_list(self):
		'''
		Returns a list of all needs to use within the javascript context
		e.g.:
		[
			{method:'role', value:'settings'},
			{method:'role', value:'system'},
		]
		:return: returns a jsonified list of all needs
		'''
		needs = "["
		for need in self.needs:
			needs += "{method:'" + need.method.strip() + "', value:'" + need.value.strip() + "'},"

		needs += "]"
		return needs

	def reverse(self):
		"""
		Returns reverse of current state (needs->excludes, excludes->needs)
		"""

		p = OctoPermission(self._name, self._description)
		all_permissions.remove(p)

		p.needs.update(self.excludes)
		p.excludes.update(self.needs)
		return p

	def union(self, other):
		"""Create a new permission with the requirements of the union of this
		and other.

		:param other: The other permission
		"""
		p = OctoPermission(self._name, self._description, *self.needs.union(other.needs))
		all_permissions.remove(p)

		p.excludes.update(self.excludes.union(other.excludes))
		return p

	def difference(self, other):
		"""Create a new permission consisting of requirements in this
		permission and not in the other.
		"""

		p = OctoPermission(self._name, self._description, *self.needs.difference(other.needs))
		all_permissions.remove(p)

		p.excludes.update(self.excludes.difference(other.excludes))
		return p

	def __repr__(self):
		return '{0} name={1}'.format(self.__class__.__name__, self.get_name())

class Permissions(object):
	# Special permission
	admin = OctoPermission("Admin", "Admin is allowed to do everything", RoleNeed("admin"))

	################################################################################
	# Deprecated should be removed with the user_permission variable in a future version
	user = variable_deprecated("user_permission has been deprecated and will be removed in the future", since="now")(
			OctoPermission("User", "User is allowed to do basic stuff", RoleNeed("user")))
	################################################################################

	status = OctoPermission("Status",
	                        "Allows to gather Statusinformations like, Connection, Printstate, Temperaturegraph",
	                        RoleNeed("status"))
	connection = OctoPermission("Connection", "Allows to connect and disconnect to a printer", RoleNeed("connection"))
	webcam = OctoPermission("Webcam", "Allows to watch the webcam stream", RoleNeed("webcam"))
	system = OctoPermission("System", "Allows to run system commands, e.g. shutdown, reboot, restart octoprint",
	                        RoleNeed("system"))
	upload = OctoPermission("Upload", "Allows users to upload new gcode files", RoleNeed("upload"))
	download = OctoPermission("Download",
	                          "Allows users to download gcode files, the gCodeViewer is affected by this too.",
	                          RoleNeed("download"))
	delete = OctoPermission("Delete", "Allows users to delete files in their folder", RoleNeed("delete_file"))
	select = OctoPermission("Selecting", "Allows to select a file", RoleNeed("select"))
	printing = OctoPermission("Printing", "Allows to start a print job, inherits the select permission",
	                          RoleNeed("print"))
	terminal = OctoPermission("Terminal", "Allows to watch the Terminaltab, without the ability to send any commands",
	                          RoleNeed("terminal"))
	control = OctoPermission("Control",
	                         "Allows to manually control the printer by using the controltab or sending gcodes through the terminal, this implies the terminal permission",
	                         RoleNeed("control"))
	slice = OctoPermission("Slicen", "Allows to slice stl files into gcode files", RoleNeed("slice"))
	timelapse = OctoPermission("Timelapse", "Allows to download timelapse videos", RoleNeed("timelapse"))
	timelapse_admin = OctoPermission("Timelapse Admin",
	                                 "Allows to change the timelapse settings, remove timelapses, implies timelapse",
	                                 RoleNeed("timelapse_admin"))
	settings = OctoPermission("Settings", "Allows to open and change Settings", RoleNeed("settings"))
	logs = OctoPermission("Logs", "Allows to download and remove logs", RoleNeed("logs"))

	file_permission = Permission(*upload.needs.union(download.needs).union(delete.needs).union(select.needs).union(printing.needs).union(slice.needs))

	@classmethod
	def getPermissionFrom(cls, permission):
		return permission if isinstance(permission, OctoPermission) \
			else cls.permission_by_name(permission["name"]) if isinstance(permission, dict) \
			else cls.permission_by_name(permission)

	@classmethod
	def permission_by_name(cls, name):
		for p in all_permissions:
			if p.get_name() == name:
				return p

		return None

	@classmethod
	def permissions_to_need_list(cls, permissions):
		needs = dict()
		for permission in permissions:
			for need in permission.needs:
				if need.method not in needs:
					needs[need.method] = []

				if need.value not in needs[need.method]:
					needs[need.method].append(need.value)

		return needs
