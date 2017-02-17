# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Marc Hannappel <salandora@gmail.com>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask_principal import Permission, RoleNeed
from octoprint.util import variable_deprecated

all_permissions = []


class OctoPrintPermission(Permission):
	def __init__(self, name, description, *needs):
		self._name = name
		self._description = description
		all_permissions.append(self)

		super(OctoPrintPermission, self).__init__(*needs)

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

	def reverse(self):
		"""
		Returns reverse of current state (needs->excludes, excludes->needs)
		"""

		p = OctoPrintPermission(self._name, self._description)
		all_permissions.remove(p)

		p.needs.update(self.excludes)
		p.excludes.update(self.needs)
		return p

	def union(self, other):
		"""Create a new permission with the requirements of the union of this
		and other.

		:param other: The other permission
		"""
		p = OctoPrintPermission(self._name, self._description, *self.needs.union(other.needs))
		all_permissions.remove(p)

		p.excludes.update(self.excludes.union(other.excludes))
		return p

	def difference(self, other):
		"""Create a new permission consisting of requirements in this
		permission and not in the other.
		"""

		p = OctoPrintPermission(self._name, self._description, *self.needs.difference(other.needs))
		all_permissions.remove(p)

		p.excludes.update(self.excludes.difference(other.excludes))
		return p

	def __repr__(self):
		return '{0} name={1}'.format(self.__class__.__name__, self.get_name())


class Permissions(object):
	# Special permission
	admin = OctoPrintPermission("Admin", "Admin is allowed to do everything", RoleNeed("admin"))

	################################################################################
	# Deprecated should be removed with the user_permission variable in a future version
	user = variable_deprecated("user_permission has been deprecated and will be removed in the future", since="now")(
			OctoPrintPermission("User", "User is allowed to do basic stuff", RoleNeed("user")))
	################################################################################

	status = OctoPrintPermission("Status",
	                        "Allows to gather Statusinformations like, Connection, Printstate, Temperaturegraph",
	                             RoleNeed("status"))
	connection = OctoPrintPermission("Connection", "Allows to connect and disconnect to a printer", RoleNeed("connection"))
	webcam = OctoPrintPermission("Webcam", "Allows to watch the webcam stream", RoleNeed("webcam"))
	system = OctoPrintPermission("System", "Allows to run system commands, e.g. shutdown, reboot, restart octoprint",
	                             RoleNeed("system"))
	upload = OctoPrintPermission("Upload", "Allows users to upload new gcode files", RoleNeed("upload"))
	download = OctoPrintPermission("Download",
	                          "Allows users to download gcode files, the gCodeViewer is affected by this too.",
	                               RoleNeed("download"))
	delete = OctoPrintPermission("Delete", "Allows users to delete files in their folder", RoleNeed("delete_file"))
	select = OctoPrintPermission("Selecting", "Allows to select a file", RoleNeed("select"))
	printing = OctoPrintPermission("Printing", "Allows to start a print job, inherits the select permission",
	                               RoleNeed("print"))
	terminal = OctoPrintPermission("Terminal", "Allows to watch the Terminaltab, without the ability to send any commands",
	                               RoleNeed("terminal"))
	control = OctoPrintPermission("Control",
	                         "Allows to manually control the printer by using the controltab or sending gcodes through the terminal, this implies the terminal permission",
	                              RoleNeed("control"))
	slice = OctoPrintPermission("Slicen", "Allows to slice stl files into gcode files", RoleNeed("slice"))
	timelapse = OctoPrintPermission("Timelapse", "Allows to download timelapse videos", RoleNeed("timelapse"))
	timelapse_admin = OctoPrintPermission("Timelapse Admin",
	                                 "Allows to change the timelapse settings, remove timelapses, implies timelapse",
	                                      RoleNeed("timelapse_admin"))
	settings = OctoPrintPermission("Settings", "Allows to open and change Settings", RoleNeed("settings"))
	logs = OctoPrintPermission("Logs", "Allows to download and remove logs", RoleNeed("logs"))

	file_permission = Permission(*upload.needs.union(download.needs).union(delete.needs).union(select.needs).union(printing.needs).union(slice.needs))

	@classmethod
	def getPermissionFrom(cls, permission):
		return permission if isinstance(permission, OctoPrintPermission) \
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
