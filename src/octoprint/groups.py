# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Marc Hannappel <salandora@gmail.com>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import os

from octoprint.settings import settings
from octoprint.util import atomic_write

from octoprint.permissions import all_permissions, Permissions

import yaml
from yaml.dumper import SafeDumper
from yaml.loader import SafeLoader


def group_yaml_representer(dumper, data):
	return dumper.represent_scalar(u'!group', repr(data))


def group_yaml_constructor(loader, node):
	value = loader.construct_scalar(node)
	name = value[value.find('name=') + 5:]
	from octoprint.server import groupManager
	return groupManager.findGroup(name)


class GroupManager(object):
	def __init__(self):
		self._logger = logging.getLogger(__name__)
		self._enabled = True

	@property
	def enabled(self):
		return self._enabled

	@enabled.setter
	def enabled(self, value):
		self._enabled = value

	def enable(self):
		self._enabled = True

	def disable(self):
		self._enabled = False

	def addGroup(self, name, permissions, specialGroup):
		pass

	def removeGroup(self, name):
		pass

	def findGroup(self, name):
		pass

	def getAllGroups(self):
		return []


class FilebasedGroupManager(GroupManager):
	def __init__(self):
		GroupManager.__init__(self)

		groupfile = settings().get(["accessControl", "groupfile"])
		if groupfile is None:
			groupfile = os.path.join(settings().getBaseFolder("base"), "groups.yaml")
		self._groupfile = groupfile
		self._groups = dict()
		self._dirty = False

		self._load()

	def _load(self):
		if os.path.exists(self._groupfile) and os.path.isfile(self._groupfile):
			with open(self._groupfile, "r") as f:
				data = yaml.safe_load(f)
				for name in data.keys():
					attributes = data[name]
					specialGroup = False
					if "specialGroup" in attributes:
						specialGroup = attributes["specialGroup"]

					self._groups[name] = Group(name, attributes["permissions"], specialGroup)

	def _save(self, force=False):
		if not self._dirty and not force:
			return

		data = dict()
		for name in self._groups.keys():
			group = self._groups[name]
			data[name] = dict(
				permissions=group._permissions,
				specialGroup=group._specialGroup
			)

		with atomic_write(self._groupfile, "wb", permissions=0o600, max_permissions=0o666) as f:
			yaml.safe_dump(data, f, default_flow_style=False, indent="    ", allow_unicode=True)
			self._dirty = False
		self._load()

	def addGroup(self, groupname, permissions=None, overwrite=False, specialGroup=False):
		if not permissions:
			permissions = []

		opermissions = []
		for p in permissions:
			opermissions.append(Permissions.getPermissionFrom(p))

		if groupname in self._groups.keys() and not overwrite:
			raise GroupAlreadyExists(groupname)

		self._groups[groupname] = Group(groupname, opermissions, specialGroup)
		self._dirty = True
		self._save()

	def changeGroupPermissions(self, groupname, permissions):
		if not groupname in self._groups.keys():
			raise UnknownGroup(groupname)

		if not self._groups[groupname].isChangable():
			raise GroupCantbeChagned(groupname)

		opermissions = []
		for p in permissions:
			opermissions.append(Permissions.getPermissionFrom(p))

		group = self._groups[groupname]

		removedPermissions = set(group._permissions) - set(opermissions)
		self.removePermissionsFromGroup(groupname, removedPermissions)

		addedPermissions = set(opermissions) - set(group._permissions)
		self.addPermissionsToGroup(groupname, addedPermissions)

	def addPermissionsToGroup(self, groupname, permissions):
		if groupname not in self._groups.keys():
			raise UnknownGroup(groupname)

		if not self._groups[groupname].isChangable():
			raise GroupCantbeChagned(groupname)

		opermissions = []
		for p in permissions:
			opermissions.append(Permissions.getPermissionFrom(p))

		if self._groups[groupname].add_permissions_to_group(opermissions):
			self._dirty = True
			self._save()

	def removePermissionsFromGroup(self, groupname, permissions):
		if groupname not in self._groups.keys():
			raise UnknownGroup(groupname)

		if not self._groups[groupname].isChangable():
			raise GroupCantbeChagned(groupname)

		opermissions = []
		for p in permissions:
			opermissions.append(Permissions.getPermissionFrom(p))

		if self._groups[groupname].remove_permissions_from_group(opermissions):
			self._dirty = True
			self._save()

	def removeGroup(self, groupname):
		if not groupname in self._groups.keys():
			raise UnknownGroup(groupname)

		if not self._groups[groupname].isRemoveable():
			raise GroupUnremovable(groupname)

		del self._groups[groupname]
		self._dirty = True
		self._save()

	def findGroup(self, groupid=None):
		if groupid is not None:
			if groupid not in self._groups.keys():
				return None
			return self._groups[groupid]

		else:
			return None

	def getAllGroups(self):
		return map(lambda x: x.asDict(), self._groups.values())


class GroupAlreadyExists(Exception):
	def __init__(self, groupname):
		Exception.__init__(self, "Group %s already exists" % groupname)


class UnknownGroup(Exception):
	def __init__(self, groupname):
		Exception.__init__(self, "Unknown group: %s" % groupname)


class GroupUnremovable(Exception):
	def __init__(self, groupname):
		Exception.__init__(self, "Group can't be removed: %s" % groupname)


class GroupCantbeChagned(Exception):
	def __init__(self, groupname):
		Exception.__init__(self, "Group can't be changed: %s" % groupname)


class Group(object):
	def __init__(self, name, permissionslist=[], specialGroup=False):
		self._name = name
		self._permissions = permissionslist
		self._specialGroup = specialGroup

	def asDict(self):
		permissions = self.permissions if not self.hasPermission(Permissions.admin) else [Permissions.admin]
		permissionDict = map(lambda p: p.asDict(), permissions)

		return {
			"name": self.get_name(),
			"permissions": permissionDict
		}

	def get_id(self):
		return self.get_name()

	def get_name(self):
		return self._name

	def isChangable(self):
		return self is not Groups.admins

	def isRemoveable(self):
		return not self._specialGroup

	def add_permissions_to_group(self, permissions):
		if not self.isChangable():
			raise GroupCantbeChagned(self.get_name())

		dirty = False
		from octoprint.permissions import OctoPermission
		for permission in permissions:
			if isinstance(permission, OctoPermission) and permission not in self.permissions:
				self._permissions.append(permission)
				dirty = True

		return dirty

	def remove_permissions_from_group(self, permissions):
		if not self.isChangable():
			raise GroupCantbeChagned(self.get_name())

		dirty = False
		from octoprint.permissions import OctoPermission
		for permission in permissions:
			if isinstance(permission, OctoPermission) and permission in self._permissions:
				self._permissions.remove(permission)
				dirty = True

		return dirty

	@property
	def permissions(self):
		if Permissions.admin in self._permissions:
			return all_permissions

		return list(self._permissions)

	@property
	def needs(self):
		needs = set()
		for permission in self.permissions:
			needs = needs.union(permission.needs)

		return needs

	def hasPermission(self, permission):
		if Permissions.admin in self._permissions:
			return True

		return permission.needs.issubset(self.needs)

	def __repr__(self):
		return '{0} name={1}'.format(self.__class__.__name__, self.get_name())


class Groups(object):
	admins = None
	guests = None

	@classmethod
	def initialize(cls):
		global admins
		global guests

		admins = cls.getOrCreateGroup("Admins", [Permissions.admin])
		guests = cls.getOrCreateGroup("Guests", [])

	@classmethod
	def getGroupFrom(cls, group):
		from octoprint.server import groupManager
		return group if isinstance(group, Group) \
			else groupManager.findGroup(group["name"]) if isinstance(group, dict) \
			else groupManager.findGroup(group)

	@classmethod
	def getOrCreateGroup(cls, groupname, permissionslist, overwrite=False, specialGroup=True):
		from octoprint.server import groupManager
		return groupManager.findGroup(groupname) if groupManager.findGroup(groupname) is not None \
			else groupManager.addGroup(groupname, permissionslist, overwrite, specialGroup)

yaml.add_representer(Group, group_yaml_representer, Dumper=SafeDumper)
yaml.add_constructor(u'!group', group_yaml_constructor, Loader=SafeLoader)
