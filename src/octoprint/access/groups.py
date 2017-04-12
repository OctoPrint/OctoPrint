# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Marc Hannappel <salandora@gmail.com>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import os

import yaml
from yaml.dumper import SafeDumper
from yaml.loader import SafeLoader

from octoprint.settings import settings
from octoprint.util import atomic_write
from octoprint.access.permissions import Permissions

class GroupManager(object):
	def __init__(self):
		self._logger = logging.getLogger(__name__)
		self._groups = dict()
		self._default_groups()
		self._enabled = True

	@property
	def enabled(self):
		return self._enabled

	@enabled.setter
	def enabled(self, value):
		self._enabled = value

	@property
	def groups(self):
		return list(self._groups.values())

	@property
	def admins_group(self):
		return self.find_group("Admins")

	@property
	def guests_group(self):
		return self.find_group("Guests")

	def enable(self):
		self._enabled = True

	def disable(self):
		self._enabled = False

	def _default_groups(self):
		from octoprint.access.permissions import Permissions

		# We need to make sure that we are not trying to save the default groups here
		self.add_group("Admins", "Admin group", permissions=[Permissions.ADMIN], default=False, specialGroup=True, save=False)
		self.add_group("Guests", "Guest group", permissions=[], default=False, specialGroup=True, save=False)

	def change_group_germissions(self, groupname, permissions):
		pass

	def change_group_default(self, groupname, default):
		pass

	def change_group_description(self, groupname, description):
		pass

	def add_group(self, name, description, permissions, specialGroup, save=True):
		pass

	def remove_group(self, name):
		pass

	def find_group(self, name=None):
		if name is not None:
			if name not in self._groups.keys():
				return None
			return self._groups[name]
		else:
			return None

	def get_group_from(cls, group):
		from octoprint.server import groupManager
		return group if isinstance(group, Group) \
			else groupManager.find_group(group["name"]) if isinstance(group, dict) \
			else groupManager.find_group(group)


class FilebasedGroupManager(GroupManager):
	def __init__(self):
		GroupManager.__init__(self)

		groupfile = settings().get(["accessControl", "groupfile"])
		if groupfile is None:
			groupfile = os.path.join(settings().getBaseFolder("base"), "groups.yaml")
		self._groupfile = groupfile
		self._dirty = False

		self._load()

	def _load(self):
		import yaml
		if os.path.exists(self._groupfile) and os.path.isfile(self._groupfile):
			with open(self._groupfile, "r") as f:
				data = yaml.safe_load(f)
				for name in data.keys():
					attributes = data[name]
					description = ""
					specialGroup = False
					default = False
					if "description" in attributes:
						description = attributes["description"]
					if "specialGroup" in attributes:
						specialGroup = attributes["specialGroup"]
					if "default" in attributes:
						default = attributes["default"]

					self._groups[name] = Group(name, description=description, permissionslist=attributes["permissions"], default=default, specialGroup=specialGroup)

	def _save(self, force=False):
		if self._groupfile is None or not self._dirty and not force:
			return

		data = dict()
		for name in self._groups.keys():
			group = self._groups[name]
			data[name] = dict(
				description=group._description,
				permissions=group._permissions,
				default=group._default,
				specialGroup=group._specialGroup
			)

		with atomic_write(self._groupfile, "wb", permissions=0o600, max_permissions=0o666) as f:
			import yaml
			yaml.safe_dump(data, f, default_flow_style=False, indent="    ", allow_unicode=True)
			self._dirty = False
		self._load()

	def add_group(self, groupname, description="", permissions=None, default=False, specialGroup=False, overwrite=False, save=True):
		if not permissions:
			permissions = []

		from octoprint.server import permissionManager
		opermissions = []
		for p in permissions:
			opermissions.append(permissionManager.get_permission_from(p))

		if groupname in self._groups.keys() and not overwrite:
			raise GroupAlreadyExists(groupname)

		self._groups[groupname] = Group(groupname, description=description, permissionslist=opermissions, default=default, specialGroup=specialGroup)
		if save:
			self._dirty = True
			self._save()

	def change_group_germissions(self, groupname, permissions):
		if not groupname in self._groups.keys():
			raise UnknownGroup(groupname)

		from octoprint.server import permissionManager
		opermissions = []
		for p in permissions:
			opermissions.append(permissionManager.get_permission_from(p))

		group = self._groups[groupname]

		removedPermissions = set(group._permissions) - set(opermissions)
		addedPermissions = set(opermissions) - set(group._permissions)

		if len(removedPermissions) == 0 and len(addedPermissions) == 0:
			return

		if not self._groups[groupname].isChangable():
			raise GroupCantbeChanged(groupname)

		self.remove_permissions_from_group(groupname, removedPermissions)
		self.add_permissions_to_group(groupname, addedPermissions)

	def add_permissions_to_group(self, groupname, permissions):
		if groupname not in self._groups.keys():
			raise UnknownGroup(groupname)

		if not self._groups[groupname].isChangable():
			raise GroupCantbeChanged(groupname)

		from octoprint.server import permissionManager
		opermissions = []
		for p in permissions:
			opermissions.append(permissionManager.get_permission_from(p))

		if self._groups[groupname].add_permissions_to_group(opermissions):
			self._dirty = True
			self._save()

	def remove_permissions_from_group(self, groupname, permissions):
		if groupname not in self._groups.keys():
			raise UnknownGroup(groupname)

		if not self._groups[groupname].isChangable():
			raise GroupCantbeChanged(groupname)

		from octoprint.server import permissionManager
		opermissions = []
		for p in permissions:
			opermissions.append(permissionManager.get_permission_from(p))

		if self._groups[groupname].remove_permissions_from_group(opermissions):
			self._dirty = True
			self._save()

	def change_group_default(self, groupname, default):
		if not groupname in self._groups.keys():
			raise UnknownGroup(groupname)

		if default == self._groups[groupname].get_default():
			return

		if not self._groups[groupname].isChangable():
			raise GroupCantbeChanged(groupname)

		self._groups[groupname].change_default(default)
		self._dirty = True
		self._save()

	def change_group_description(self, groupname, description):
		if not groupname in self._groups.keys():
			raise UnknownGroup(groupname)

		if description == self._groups[groupname].get_description():
			return

		self._groups[groupname].change_description(description)
		self._dirty = True
		self._save()

	def remove_group(self, groupname):
		if not groupname in self._groups.keys():
			raise UnknownGroup(groupname)

		if not self._groups[groupname].isRemoveable():
			raise GroupUnremovable(groupname)

		del self._groups[groupname]
		self._dirty = True
		self._save()


class GroupAlreadyExists(Exception):
	def __init__(self, groupname):
		Exception.__init__(self, "Group %s already exists" % groupname)


class UnknownGroup(Exception):
	def __init__(self, groupname):
		Exception.__init__(self, "Unknown group: %s" % groupname)


class GroupUnremovable(Exception):
	def __init__(self, groupname):
		Exception.__init__(self, "Group can't be removed: %s" % groupname)


class GroupCantbeChanged(Exception):
	def __init__(self, groupname):
		Exception.__init__(self, "Group can't be changed: %s" % groupname)


class Group(object):
	def __init__(self, name, description="", permissionslist=[], default=False, specialGroup=False):
		self._name = name
		self._description = description
		self._permissions = permissionslist if permissionslist is not None else []
		self._default = default
		self._specialGroup = specialGroup

	def asDict(self):
		permissions = self.permissions if not self.hasPermission(Permissions.ADMIN) else [Permissions.ADMIN]

		return {
			"name": self.get_name(),
			"description": self.get_description(),
			"permissions": permissions,
			"defaultOn": self.get_default()
		}

	def get_id(self):
		return self.get_name()

	def get_name(self):
		return self._name

	def get_description(self):
		return self._description

	def get_default(self):
		return self._default

	def isChangable(self):
		from octoprint.server import groupManager
		return self is not groupManager.admins_group

	def isRemoveable(self):
		return not self._specialGroup

	def add_permissions_to_group(self, permissions):
		if not self.isChangable():
			raise GroupCantbeChanged(self.get_name())

		dirty = False
		from octoprint.access.permissions import OctoPrintPermission
		for permission in permissions:
			if isinstance(permission, OctoPrintPermission) and permission not in self.permissions:
				self._permissions.append(permission)
				dirty = True

		return dirty

	def remove_permissions_from_group(self, permissions):
		if not self.isChangable():
			raise GroupCantbeChanged(self.get_name())

		dirty = False
		from octoprint.access.permissions import OctoPrintPermission
		for permission in permissions:
			if isinstance(permission, OctoPrintPermission) and permission in self._permissions:
				self._permissions.remove(permission)
				dirty = True

		return dirty

	def change_default(self, default):
		if not self.isChangable():
			raise GroupCantbeChanged(self.get_name())

		self._default = default

	def change_description(self, description):
		self._description = description

	@property
	def permissions(self):
		if Permissions.ADMIN in self._permissions:
			from octoprint.server import permissionManager
			return permissionManager.permissions

		return list(self._permissions)

	@property
	def needs(self):
		needs = set()
		for permission in self.permissions:
			needs = needs.union(permission.needs)

		return needs

	def hasPermission(self, permission):
		if Permissions.ADMIN in self._permissions:
			return True

		return permission.needs.issubset(self.needs)

	def __repr__(self):
		return '{0}(name={1}, description={2}, default={3})'.format(self.__class__.__name__, self.get_name(), self.get_description(), self.get_default())


def group_yaml_representer(dumper, data):
	return dumper.represent_scalar(u'!group', repr(data))

def group_yaml_constructor(loader, node):
	value = loader.construct_scalar(node)
	name = value[value.find('name=') + 5:]
	from octoprint.server import groupManager
	return groupManager.find_group(name)

yaml.add_representer(Group, group_yaml_representer, Dumper=SafeDumper)
yaml.add_constructor(u'!group', group_yaml_constructor, Loader=SafeLoader)
