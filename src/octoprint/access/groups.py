# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__author__ = "Marc Hannappel <salandora@gmail.com>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

import io
import logging
import os
from functools import partial

import yaml

from past.builtins import basestring

from octoprint.settings import settings
from octoprint.util import atomic_write
from octoprint.access import ADMIN_GROUP, USER_GROUP, GUEST_GROUP, READONLY_GROUP
from octoprint.access.permissions import Permissions, OctoPrintPermission
from octoprint.vendor.flask_principal import Need, Permission


GroupNeed = partial(Need, 'group')
GroupNeed.__doc__ = """A need with the method preset to `"group"`."""


class GroupPermission(Permission):
	def __init__(self, key):
		need = GroupNeed(key)
		super(GroupPermission, self).__init__(need)


class GroupManager(object):
	@classmethod
	def default_permissions_for_group(cls, group):
		result = []
		for permission in Permissions.all():
			if group in permission.default_groups:
				result.append(permission)
		return result

	def __init__(self):
		self._logger = logging.getLogger(__name__)
		self._group_change_listeners = []

		self._default_groups = []
		self._init_defaults()

	@property
	def groups(self):
		return []

	@property
	def admin_group(self):
		return self.find_group(ADMIN_GROUP)

	@property
	def user_group(self):
		return self.find_group(USER_GROUP)

	@property
	def guest_group(self):
		return self.find_group(GUEST_GROUP)

	def _init_defaults(self):
		self._default_groups = {
			ADMIN_GROUP: dict(name="Admins",
			                  description="Administrators",
			                  permissions=self.default_permissions_for_group(ADMIN_GROUP),
			                  subgroups=[],
			                  changeable=False,
			                  removable=False,
			                  default=False,
			                  toggleable=True),
			USER_GROUP: dict(name="Operator",
			                 description="Group to gain operator access",
			                 permissions=self.default_permissions_for_group(USER_GROUP),
			                 subgroups=[],
			                 changeable=True,
			                 default=True,
			                 removable=False,
			                 toggleable=True),
			GUEST_GROUP: dict(name="Guests",
			                  description="Anyone who is not currently logged in",
			                  permissions=self.default_permissions_for_group(GUEST_GROUP),
			                  subgroups=[],
			                  changeable=True,
			                  default=False,
			                  removable=False,
			                  toggleable=False),
			READONLY_GROUP: dict(name="Read-only Access",
			                     description="Group to gain read-only access",
			                     permissions=self.default_permissions_for_group(READONLY_GROUP),
			                     subgroups=[],
			                     changeable=False,
			                     removable=False,
			                     default=False,
			                     toggleable=True)
		}

		for key, g in self._default_groups.items():
			self.add_group(key, g["name"], g["description"],
			               g["permissions"], g["subgroups"],
			               changeable=g.get("changeable", True),
			               removable=g.get("removable", True),
			               default=g.get("default", False),
			               toggleable=g.get("toggleable", True),
			               save=False)


	def register_listener(self, listener):
		self._group_change_listeners.append(listener)

	def unregister_listener(self, listener):
		self._group_change_listeners.remove(listener)

	def add_group(self, key, name, description, permissions, subgroups,
	              default=False, removable=True, changeable=True, toggleable=True, save=True, notify=True):
		pass

	def update_group(self, key, description=None, permissions=None, subgroups=None, default=None, save=True, notify=True):
		pass

	def remove_group(self, key, save=True, notify=True):
		pass

	def find_group(self, key):
		return None

	def _to_permissions(self, *permissions):
		return list(filter(lambda x: x is not None,
		                   [Permissions.find(permission) for permission in permissions]))

	def _from_permissions(self, *permissions):
		return [permission.key for permission in permissions]

	def _from_groups(self, *groups):
		return [group.key for group in groups]

	def _to_groups(self, *groups):
		return list(filter(lambda x: x is not None,
		                   [self._to_group(g) for g in groups]))

	def _to_group(self, group):
		# noinspection PyCompatibility
		if isinstance(group, Group):
			return group
		elif isinstance(group, basestring):
			return self.find_group(group)
		elif isinstance(group, dict):
			return self.find_group(group.get("key"))
		else:
			return None

	def _notify_listeners(self, action, group, *args, **kwargs):
		method = "on_group_{}".format(action)
		for listener in self._group_change_listeners:
			try:
				getattr(listener, method)(group, *args, **kwargs)
			except Exception:
				self._logger.exception("Error notifying listener {!r} via {}".format(listener, method))

class GroupChangeListener(object):

	def on_group_added(self, group):
		pass

	def on_group_removed(self, group):
		pass

	def on_group_permissions_changed(self, group, added=None, removed=None):
		pass

	def on_group_subgroups_changed(self, group, added=None, removed=None):
		pass


class FilebasedGroupManager(GroupManager):
	FILE_VERSION = 2

	def __init__(self, path=None):
		if path is None:
			path = settings().get(["accessControl", "groupfile"])
			if path is None:
				path = os.path.join(settings().getBaseFolder("base"), "groups.yaml")

		self._groupfile = path
		self._groups = dict()
		self._dirty = False

		GroupManager.__init__(self)

		self._load()

	def _load(self):
		if os.path.exists(self._groupfile) and os.path.isfile(self._groupfile):
			try:
				with io.open(self._groupfile, 'rt', encoding='utf-8') as f:
					data = yaml.safe_load(f)

				if not "groups" in data:
					groups = data
					data = dict(groups=groups)

				file_version = data.get("_version", 1)
				if file_version < self.FILE_VERSION:
					# make sure we migrate the file on disk after loading
					self._logger.info("Detected file version {} on group "
					                  "storage, migrating to version {}".format(file_version, self.FILE_VERSION))
					self._dirty = True

				groups = data.get("groups", dict())
				tracked_permissions = data.get("tracked", list())

				for key, attributes in groups.items():
					if key in self._default_groups:
						# group is a default group
						if not self._default_groups[key].get("changeable", True):
							# group may not be changed -> bail
							continue

						name = self._default_groups[key].get("name", "")
						description = self._default_groups[key].get("description", "")
						removable = self._default_groups[key].get("removable", True)
						changeable = self._default_groups[key].get("changeable", True)
						toggleable = self._default_groups[key].get("toggleable", True)

						if file_version == 1:
							# 1.4.0/file version 1 has a bug that resets default to True for users group on modification
							set_default = self._default_groups[key].get("default", False)
						else:
							set_default = attributes.get("default", False)
					else:
						name = attributes.get("name", "")
						description = attributes.get("description", "")
						removable = True
						changeable = True
						toggleable = True
						set_default = attributes.get("default", False)

					permissions = self._to_permissions(*attributes.get("permissions", []))
					default_permissions = self.default_permissions_for_group(key)
					for permission in default_permissions:
						if not permission.key in tracked_permissions and not permission in permissions:
							permissions.append(permission)

					subgroups = attributes.get("subgroups", [])

					group = Group(key, name,
					              description=description,
					              permissions=permissions,
					              subgroups=subgroups,
					              default=set_default,
					              removable=removable,
					              changeable=changeable,
					              toggleable=toggleable)
					self._groups[key] = group

				for group in self._groups.values():
					group._subgroups = self._to_groups(*group._subgroups)

				if self._dirty:
					self._save()

			except Exception:
				self._logger.exception("Error while loading groups from file {}".format(self._groupfile))

	def _save(self, force=False):
		if self._groupfile is None or not self._dirty and not force:
			return

		groups = dict()
		for key in self._groups.keys():
			group = self._groups[key]
			groups[key] = dict(
				permissions=self._from_permissions(*group._permissions),
				subgroups=self._from_groups(*group._subgroups),
				default=group._default
			)
			if not key in self._default_groups:
				groups[key]["name"] = group.get_name()
				groups[key]["description"] = group.get_description()

		data = dict(_version=self.FILE_VERSION,
		            groups=groups,
		            tracked=[x.key for x in Permissions.all()])

		with atomic_write(self._groupfile, mode='wt', permissions=0o600, max_permissions=0o666) as f:
			import yaml
			yaml.safe_dump(data, f, default_flow_style=False, indent=4, allow_unicode=True)
			self._dirty = False
		self._load()

	@property
	def groups(self):
		return list(self._groups.values())

	@property
	def default_groups(self):
		return [group for group in self._groups.values() if group.is_default()]

	def find_group(self, key):
		if key is None:
			return None
		return self._groups.get(key)

	def add_group(self, key, name, description, permissions, subgroups, default=False, removable=True,
	              changeable=True, toggleable=True, overwrite=False, notify=True, save=True):
		if key in self._groups and not overwrite:
			raise GroupAlreadyExists(key)

		if not permissions:
			permissions = []

		permissions = self._to_permissions(*permissions)
		assert(all(map(lambda p: isinstance(p, OctoPrintPermission), permissions)))

		subgroups = self._to_groups(*subgroups)
		assert(all(map(lambda g: isinstance(g, Group), subgroups)))

		group = Group(key, name,
		              description=description,
		              permissions=permissions,
		              subgroups=subgroups,
		              default=default,
		              changeable=changeable,
		              removable=removable,
		              toggleable=toggleable)
		self._groups[key] = group

		if save:
			self._dirty = True
			self._save()

		if notify:
			self._notify_listeners("added", group)

	def remove_group(self, key, save=True, notify=True):
		"""Removes a Group by key"""
		group = self._to_group(key)
		if group is None:
			raise UnknownGroup(key)

		if not group.is_removable():
			raise GroupUnremovable(key)

		del self._groups[key]
		self._dirty = True

		if save:
			self._save()

		if notify:
			self._notify_listeners("removed", group)

	def update_group(self, key, description=None, permissions=None, subgroups=None, default=None, save=True, notify=True):
		group = self._to_group(key)
		if group is None:
			raise UnknownGroup(key)

		if not group.is_changeable():
			raise GroupCantBeChanged(key)

		if description is not None and description != group.get_description():
			group.change_description(description)
			self._dirty = True

		notifications = []

		if permissions is not None:
			permissions = self._to_permissions(*permissions)
			assert (all(map(lambda p: isinstance(p, OctoPrintPermission), permissions)))

			removed_permissions = list(set(group._permissions) - set(permissions))
			added_permissions = list(set(permissions) - set(group._permissions))

			if removed_permissions:
				self._dirty |= group.remove_permissions_from_group(removed_permissions)
			if added_permissions:
				self._dirty |= group.add_permissions_to_group(added_permissions)

			notifications.append((("permissions_changed", group),
			                      dict(added=added_permissions, removed=removed_permissions)))

		if subgroups is not None:
			subgroups = self._to_groups(*subgroups)
			assert(all(map(lambda g: isinstance(g, Group), subgroups)))

			removed_subgroups = list(set(group._subgroups) - set(subgroups))
			added_subgroups = list(set(subgroups) - set(group._subgroups))

			if removed_subgroups:
				self._dirty = group.remove_subgroups_from_group(removed_subgroups)
			if added_subgroups:
				self._dirty = group.add_subgroups_to_group(added_subgroups)

			notifications.append((("subgroups_changed", group),
			                      dict(added=added_subgroups, removed=removed_subgroups)))

		if default is not None:
			group.change_default(default)
			self._dirty = True

		if self._dirty:
			if save:
				self._save()

			if notify:
				for args, kwargs in notifications:
					self._notify_listeners(*args, **kwargs)


class GroupAlreadyExists(Exception):
	def __init__(self, key):
		Exception.__init__(self, "Group %s already exists" % key)


class UnknownGroup(Exception):
	def __init__(self, key):
		Exception.__init__(self, "Unknown group: %s" % key)


class GroupUnremovable(Exception):
	def __init__(self, key):
		Exception.__init__(self, "Group can't be removed: %s" % key)


class GroupCantBeChanged(Exception):
	def __init__(self, key):
		Exception.__init__(self, "Group can't be changed: %s" % key)


class Group(object):
	def __init__(self, key, name, description="", permissions=None, subgroups=None, default=False, removable=True, changeable=True, toggleable=True):
		self._key = key
		self._name = name
		self._description = description
		self._permissions = permissions
		self._subgroups = subgroups
		self._default = default
		self._removable = removable
		self._changeable = changeable
		self._toggleable = toggleable

	def as_dict(self):
		from octoprint.access.permissions import OctoPrintPermission
		return dict(
			key=self.key,
			name=self.get_name(),
			description=self._description,
			permissions=list(map(lambda p: p.key, self._permissions)),
			subgroups=list(map(lambda g: g.key, self._subgroups)),
			needs=OctoPrintPermission.convert_needs_to_dict(self.needs),
			default=self._default,
			removable=self._removable,
			changeable=self._changeable,
			toggleable=self._toggleable
		)

	@property
	def key(self):
		return self._key

	def get_name(self):
		return self._name

	def get_description(self):
		return self._description

	def is_default(self):
		return self._default

	def is_changeable(self):
		return self._changeable

	def is_removable(self):
		return self._removable

	def is_toggleable(self):
		return self._toggleable

	def add_permissions_to_group(self, permissions):
		"""Adds a list of permissions to a group"""
		if not self.is_changeable():
			raise GroupCantBeChanged(self.key)

		# Make sure the permissions variable is of type list
		if not isinstance(permissions, list):
			permissions = [permissions]

		assert(all(map(lambda p: isinstance(p, OctoPrintPermission), permissions)))

		dirty = False
		for permission in permissions:
			if permissions not in self.permissions:
				self._permissions.append(permission)
				dirty = True

		return dirty

	def remove_permissions_from_group(self, permissions):
		"""Removes a list of permissions from a group"""
		if not self.is_changeable():
			raise GroupCantBeChanged(self.key)

		# Make sure the permissions variable is of type list
		if not isinstance(permissions, list):
			permissions = [permissions]

		assert(all(map(lambda p: isinstance(p, OctoPrintPermission), permissions)))

		dirty = False
		for permission in permissions:
			if permission in self._permissions:
				self._permissions.remove(permission)
				dirty = True

		return dirty

	def add_subgroups_to_group(self, subgroups):
		"""Adds a list of subgroups to a group"""
		if not self.is_changeable():
			raise GroupCantBeChanged(self.key)

		# Make sure the subgroups variable is of type list
		if not isinstance(subgroups, list):
			subgroups = [subgroups]

		assert(all(map(lambda g: isinstance(g, Group), subgroups)))

		dirty = False
		for group in subgroups:
			if group.is_toggleable() and group not in self._subgroups:
				self._subgroups.append(group)
				dirty = True

		return dirty

	def remove_subgroups_from_group(self, subgroups):
		"""Removes a list of subgroups from a group"""
		"""Adds a list of subgroups to a group"""
		if not self.is_changeable():
			raise GroupCantBeChanged(self.key)

		# Make sure the subgroups variable is of type list
		if not isinstance(subgroups, list):
			subgroups = [subgroups]

		assert (all(map(lambda g: isinstance(g, Group), subgroups)))

		dirty = False
		for group in subgroups:
			if group.is_toggleable() and group in self._subgroups:
				self._subgroups.remove(group)
				dirty = True

		return dirty

	def change_default(self, default):
		"""Changes the default flag of a Group"""
		if not self.is_changeable():
			raise GroupCantBeChanged(self.key)

		self._default = default

	def change_description(self, description):
		"""Changes the description of a group"""
		self._description = description

	@property
	def permissions(self):
		if Permissions.ADMIN in self._permissions:
			return Permissions.all()

		return list(filter(lambda p: p is not None, self._permissions))

	@property
	def subgroups(self):
		return filter(lambda g: g is not None, self._subgroups)

	@property
	def needs(self):
		needs = set()
		needs.add(GroupNeed(self.key))
		for p in self.permissions:
			needs = needs.union(p.needs)
		for g in self.subgroups:
			needs = needs.union(g.needs)

		return needs

	def has_permission(self, permission):
		if Permissions.ADMIN.get_name() in self._permissions:
			return True

		return permission.needs.issubset(self.needs)

	def __repr__(self):
		return '{}("{}", "{}", description="{}", permissions={!r}, ' \
		       'default={}, removable={}, changeable={})'.format(self.__class__.__name__,
                                                                 self._key,
		                                                         self._name,
		                                                         self._description,
		                                                         self._permissions,
		                                                         bool(self._default),
		                                                         bool(self._removable),
		                                                         bool(self._changeable))

	def __hash__(self):
		return self.key.__hash__()

	def __eq__(self, other):
		return isinstance(other, Group) and other.key == self.key
