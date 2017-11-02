# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Marc Hannappel <salandora@gmail.com>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import os

from octoprint.settings import settings
from octoprint.util import atomic_write
from octoprint.access.permissions import Permissions


class GroupManager(object):
	def __init__(self):
		self._logger = logging.getLogger(__name__)
		self._groups = dict()
		self._default_groups()

		import yaml
		from yaml.dumper import SafeDumper
		from yaml.loader import SafeLoader

		yaml.add_representer(Group, self.yaml_representer, Dumper=SafeDumper)
		yaml.add_constructor(u'!group', self.yaml_constructor, Loader=SafeLoader)

	@property
	def groups(self):
		return list(self._groups.values())

	@property
	def admins_group(self):
		return self.find_group("Admins")

	@property
	def guests_group(self):
		return self.find_group("Guests")

	def _default_groups(self):
		from octoprint.access.permissions import Permissions

		# We need to make sure that we are not trying to save the default groups here
		self.add_group("Admins", "Admin group", permissions=[Permissions.ADMIN], default=False, specialGroup=True, save=False)
		if settings().get(["server", "firstRun"]):
			self.add_group("Users", "User group", permissions=Permissions.USER_ARRAY)

		self.add_group("Guests", "Guest group", permissions=[], default=False, specialGroup=True, save=False)

	def yaml_representer(self, dumper, data):
		return dumper.represent_scalar(u'!group', data.get_name())

	def yaml_constructor(self, loader, node):
		name = loader.construct_scalar(node)
		return self.find_group(name)

	def change_group_permissions(self, groupname, permissions):
		pass

	def change_group_default(self, groupname, default):
		pass

	def change_group_description(self, groupname, description):
		pass

	def add_group(self, name, description, permissions, default, specialGroup, save=True):
		pass

	def remove_group(self, name):
		pass

	def remove_permissions_from_groups(self, permission):
		pass

	def find_group(self, name=None):
		return self._groups.get(name, None)

	def get_group_from(self, group):
		return group if isinstance(group, Group) \
			else self.find_group(group["name"]) if isinstance(group, dict) \
			else self.find_group(group)


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
		if os.path.exists(self._groupfile) and os.path.isfile(self._groupfile):
			with open(self._groupfile, "r") as f:
				import yaml
				data = yaml.safe_load(f)
				from octoprint.server import permissionManager
				for name in data.keys():
					attributes = data[name]
					permissions = [],
					description = ""
					specialGroup = False
					default = False
					if "permissions" in attributes:
						permissions = attributes["permissions"]
					if "description" in attributes:
						description = attributes["description"]
					if "specialGroup" in attributes:
						specialGroup = attributes["specialGroup"]
					if "default" in attributes:
						default = attributes["default"]

					self._groups[name] = Group(name, description=description, permissionslist=permissions, default=default, specialGroup=specialGroup)

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

		if groupname in self._groups.keys() and not overwrite:
			raise GroupAlreadyExists(groupname)

		self._groups[groupname] = Group(groupname, description=description, permissionslist=permissions, default=default, specialGroup=specialGroup)
		if save:
			self._dirty = True
			self._save()

	def change_group_permissions(self, groupname, permissions):
		"""Changes the permissions of a group"""
		if groupname not in self._groups.keys():
			raise UnknownGroup(groupname)

		group = self._groups[groupname]
		if not group.is_changable():
			raise GroupCantBeChanged(groupname)

		from octoprint.server import permissionManager
		tmp_permissions = []
		for p in permissions:
			permission = permissionManager.get_permission_from(p)
			if permission is not None:
				tmp_permissions.append(permission.get_name())

		removedPermissions = list(set(group._permissions) - set(tmp_permissions))
		addedPermissions = list(set(tmp_permissions) - set(group._permissions))

		if len(removedPermissions) > 0:
			group.remove_permissions_from_group(removedPermissions)
			self._dirty = True
		if len(addedPermissions) > 0:
			group.add_permissions_to_group(addedPermissions)
			self._dirty = True

		if self._dirty:
			self._save()

	def add_permissions_to_group(self, groupname, permissions):
		"""Adds a list of permissions to a group"""
		if groupname not in self._groups.keys():
			raise UnknownGroup(groupname)

		if not self._groups[groupname].isChangable():
			raise GroupCantBeChanged(groupname)

		if self._groups[groupname].add_permissions_to_group(permissions):
			self._dirty = True
			self._save()

	def remove_permissions_from_group(self, groupname, permissions):
		"""Removes a list of permissions from a group"""
		if groupname not in self._groups.keys():
			raise UnknownGroup(groupname)

		if not self._groups[groupname].is_changable():
			raise GroupCantBeChanged(groupname)

		if self._groups[groupname].remove_permissions_from_group(permissions):
			self._dirty = True
			self._save()

	def change_group_default(self, groupname, default):
		"""Changes the default flag of a Group"""
		if groupname not in self._groups.keys():
			raise UnknownGroup(groupname)

		if default == self._groups[groupname].get_default():
			return

		if not self._groups[groupname].is_changable():
			raise GroupCantBeChanged(groupname)

		self._groups[groupname].change_default(default)
		self._dirty = True
		self._save()

	def change_group_description(self, groupname, description):
		"""Changes the description of a group"""
		if groupname not in self._groups.keys():
			raise UnknownGroup(groupname)

		if description == self._groups[groupname].get_description():
			return

		self._groups[groupname].change_description(description)
		self._dirty = True
		self._save()

	def remove_group(self, groupname):
		"""Removes a Group by name"""
		if groupname not in self._groups.keys():
			raise UnknownGroup(groupname)

		group = self._groups[groupname]
		if not group.is_removeable():
			raise GroupUnremovable(groupname)

		# Make sure the group gets deleted from all user objects
		from octoprint.server import userManager
		if userManager.enabled:
			userManager.remove_groups_from_users([group.get_name()])

		del self._groups[groupname]
		self._dirty = True
		self._save()

	def remove_permissions_from_groups(self, permissions):
		"""Removes a OctoPrintPermission from every group"""
		for group in self._groups.values():
			try:
				self._dirty |= group.remove_permissions_from_group(permissions)
			except GroupCantBeChanged:
				pass

		if self._dirty:
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


class GroupCantBeChanged(Exception):
	def __init__(self, groupname):
		Exception.__init__(self, "Group can't be changed: %s" % groupname)


class Group(object):
	def __init__(self, name, description="", permissionslist=None, default=False, specialGroup=False):
		self._name = name
		self._description = description
		self._default = default
		self._specialGroup = specialGroup

		from octoprint.server import permissionManager
		self._permissions = []
		for p in permissionslist:
			permission = permissionManager.get_permission_from(p)
			if permission is not None:
				self._permissions.append(permission.get_name())

	def as_dict(self):
		from octoprint.access.permissions import OctoPrintPermission
		return dict(
			name=self.get_name(),
			description=self.get_description(),
			permissions=self._permissions,
			needs=OctoPrintPermission.convert_needs_to_dict(self.needs),
			defaultOn=self.get_default()
		)

	def get_name(self):
		return self._name

	def get_description(self):
		return self._description

	def get_default(self):
		return self._default

	def is_changable(self):
		from octoprint.server import groupManager
		return self is not groupManager.admins_group

	def is_removeable(self):
		return not self._specialGroup

	def add_permissions_to_group(self, permissions):
		"""Adds a list of permissions to a group"""
		if not self.is_changable():
			raise GroupCantBeChanged(self.get_name())

		# Make sure the permissions variable is of type list
		if not isinstance(permissions, list):
			permissions = [permissions]

		dirty = False
		from octoprint.server import permissionManager
		for permission in permissions:
			# We check if the permission is registered in the permission manager,
			# if not we are not going to add it to the groups permission list
			tmp_permission = permissionManager.get_permission_from(permission)
			if tmp_permission is not None and tmp_permission not in self.permissions:
				self._permissions.append(tmp_permission.get_name())
				dirty = True

		return dirty

	def remove_permissions_from_group(self, permissions):
		"""Removes a list of permissions from a group"""
		if not self.is_changable():
			raise GroupCantBeChanged(self.get_name())

		# Make sure the permissions variable is of type list
		if not isinstance(permissions, list):
			permissions = [permissions]

		dirty = False
		from octoprint.access.permissions import OctoPrintPermission
		for permission in permissions:
			# If someone gives a OctoPrintPermission object, we convert it into the identifier name,
			# because all permissions are stored as identifiers inside the group
			if isinstance(permissions, OctoPrintPermission):
				permission = permission.get_name()

			# We don't check if the permission exists, because it could have been removed
			# from the permission manager already
			if permission in self._permissions:
				self._permissions.remove(permission)
				dirty = True

		return dirty

	def change_default(self, default):
		"""Changes the default flag of a Group"""
		if not self.is_changable():
			raise GroupCantBeChanged(self.get_name())

		self._default = default

	def change_description(self, description):
		"""Changes the description of a group"""
		self._description = description

	@property
	def permissions(self):
		from octoprint.server import permissionManager
		if Permissions.ADMIN.get_name() in self._permissions:
			return list(permissionManager.permissions)

		return filter(lambda p: p is not None,
					map(lambda x: permissionManager.find_permission(x), self._permissions))

	@property
	def needs(self):
		needs = set()
		for p in self.permissions:
			needs = needs.union(p.needs)

		return needs

	def has_permission(self, permission):
		if Permissions.ADMIN.get_name() in self._permissions:
			return True

		return permission.needs.issubset(self.needs)

	def __repr__(self):
		return '{0}(name="{1}", description="{2}", permissionslist={3}, default={4}, specialGroup={5})'.format(self.__class__.__name__, self.get_name(), self.get_description(), self._permissions, bool(self.get_default()), bool(self._specialGroup))

