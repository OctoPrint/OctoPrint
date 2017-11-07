# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask_login import UserMixin, AnonymousUserMixin
from flask_principal import Identity
from werkzeug.local import LocalProxy
import hashlib
import os
import yaml
import uuid
import wrapt

import logging
from builtins import range, bytes

from octoprint.settings import settings
from octoprint.util import atomic_write, to_str, deprecated
from octoprint.access.permissions import Permissions


class UserManager(object):
	def __init__(self):
		self._logger = logging.getLogger(__name__)
		self._session_users_by_session = dict()
		self._sessionids_by_userid = dict()
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

	def login_user(self, user):
		self._cleanup_sessions()

		if user is None:
			return

		if isinstance(user, LocalProxy):
			user = user._get_current_object()

		if not isinstance(user, User):
			return None

		if not isinstance(user, SessionUser):
			user = SessionUser(user)

		self._session_users_by_session[user.session] = user

		userid = user.get_id()
		if not userid in self._sessionids_by_userid:
			self._sessionids_by_userid[userid] = set()

		self._sessionids_by_userid[userid].add(user.session)

		self._logger.debug("Logged in user: %r" % user)

		return user

	def logout_user(self, user):
		if user is None:
			return

		if isinstance(user, LocalProxy):
			user = user._get_current_object()

		if not isinstance(user, SessionUser):
			return

		userid = user.get_id()
		sessionid = user.session

		if userid in self._sessionids_by_userid:
			try:
				self._sessionids_by_userid[userid].remove(sessionid)
			except KeyError:
				pass

		if sessionid in self._session_users_by_session:
			del self._session_users_by_session[sessionid]

		self._logger.debug("Logged out user: %r" % user)

	def _cleanup_sessions(self):
		import time
		for session, user in self._session_users_by_session.items():
			if not isinstance(user, SessionUser):
				continue
			if user.created + (24 * 60 * 60) < time.time():
				self.logout_user(user)

	@staticmethod
	def create_password_hash(password, salt=None):
		if not salt:
			salt = settings().get(["accessControl", "salt"])
			if salt is None:
				import string
				from random import choice
				chars = string.ascii_lowercase + string.ascii_uppercase + string.digits
				salt = "".join(choice(chars) for _ in range(32))
				settings().set(["accessControl", "salt"], salt)
				settings().save()

		return hashlib.sha512(to_str(password, encoding="utf-8", errors="replace") + to_str(salt)).hexdigest()

	def check_password(self, username, password):
		user = self.find_user(username)
		if not user:
			return False

		hash = UserManager.create_password_hash(password)
		if user.check_password(hash):
			# new hash matches, correct password
			return True
		else:
			# new hash doesn't match, but maybe the old one does, so check that!
			oldHash = UserManager.create_password_hash(password, salt="mvBUTvwzBzD3yPwvnJ4E4tXNf3CGJvvW")
			if user.check_password(oldHash):
				# old hash matches, we migrate the stored password hash to the new one and return True since it's the correct password
				self.change_user_password(username, password)
				return True
			else:
				# old hash doesn't match either, wrong password
				return False

	def add_user(self, username, password, active, permissions, groups, overwrite=False):
		pass

	def change_user_activation(self, username, active):
		pass

	def change_user_permissions(self, username, permissions):
		pass

	def add_permissions_to_user(self, username, permissions):
		pass

	def remove_permissions_from_user(self, username, permissions):
		pass

	def change_user_groups(self, username, groups):
		pass

	def add_groups_to_user(self, username, groups):
		pass

	def remove_groups_from_user(self, username, groups):
		pass

	def remove_group_from_all_users(self, group):
		pass

	def change_user_password(self, username, password):
		pass

	def get_user_setting(self, username, key):
		return None

	def get_all_user_settings(self, username):
		return dict()

	def change_user_setting(self, username, key, value):
		pass

	def change_user_settings(self, username, new_settings):
		pass

	def remove_user(self, username):
		if username in self._sessionids_by_userid:
			sessions = self._sessionids_by_userid[username]
			for session in sessions:
				if session in self._session_users_by_session:
					del self._session_users_by_session[session]
			del self._sessionids_by_userid[username]

	def find_user(self, userid=None, session=None):
		if session is not None and session in self._session_users_by_session:
			user = self._session_users_by_session[session]
			if userid is None or userid == user.get_id():
				return user

		return None

	def get_all_users(self):
		return []

	def has_been_customized(self):
		return False

	#~~ Deprecated methods follow

	# TODO: Remove deprecated methods in OctoPrint 1.5.0

	@staticmethod
	def createPasswordHash(*args, **kwargs):
		"""
		.. deprecated: 1.4.0

		   Replaced by :func:`~UserManager.create_password_hash`
		"""
		# we can't use the deprecated decorator here since this method is static
		import warnings
		warnings.warn("createPasswordHash has been renamed to create_password_hash", DeprecationWarning, stacklevel=2)
		return UserManager.create_password_hash(*args, **kwargs)

	checkPassword        = deprecated("checkPassword has been renamed to check_password",
	                                  includedoc="Replaced by :func:`check_password`",
	                                  since="1.4.0")(check_password)
	addUser              = deprecated("addUser has been renamed to add_user",
	                                  includedoc="Replaced by :func:`add_user`",
	                                  since="1.4.0")(add_user)
	changeUserActivation = deprecated("changeUserActivation has been renamed to change_user_activation",
	                                  includedoc="Replaced by :func:`change_user_activation`",
	                                  since="1.4.0")(change_user_activation)
	changeUserRoles      = deprecated("changeUserRoles has been renamed to change_user_permissions",
	                                  includedoc="Replaced by :func:`change_user_permissions`",
	                                  since="1.4.0")(change_user_permissions)
	addRolesToUser       = deprecated("addRolesToUser has been renamed to add_permissions_to_user",
	                                  includedoc="Replaced by :func:`add_permissions_to_user`",
	                                  since="1.4.0")(add_permissions_to_user)
	removeRolesFromUser  = deprecated("removeRolesFromUser has been renamed to remove_permissions_from_user",
	                                  includedoc="Replaced by :func:`remove_permissions_from_user`",
	                                  since="1.4.0")(remove_permissions_from_user)
	changeUserPassword   = deprecated("changeUserPassword has been renamed to change_user_password",
	                                  includedoc="Replaced by :func:`change_user_password`",
	                                  since="1.4.0")(change_user_password)
	getUserSetting       = deprecated("getUserSetting has been renamed to get_user_setting",
	                                  includedoc="Replaced by :func:`get_user_setting`",
	                                  since="1.4.0")(get_user_setting)
	getAllUserSettings   = deprecated("getAllUserSettings has been renamed to get_all_user_settings",
	                                  includedoc="Replaced by :func:`get_all_user_settings`",
	                                  since="1.4.0")(get_all_user_settings)
	changeUserSetting    = deprecated("changeUserSetting has been renamed to change_user_setting",
	                                  includedoc="Replaced by :func:`change_user_setting`",
	                                  since="1.4.0")(change_user_setting)
	changeUserSettings   = deprecated("changeUserSettings has been renamed to change_user_settings",
	                                  includedoc="Replaced by :func:`change_user_settings`",
	                                  since="1.4.0")(change_user_settings)
	removeUser           = deprecated("removeUser has been renamed to remove_user",
	                                  includedoc="Replaced by :func:`remove_user`",
	                                  since="1.4.0")(remove_user)
	findUser             = deprecated("findUser has been renamed to find_user",
	                                  includedoc="Replaced by :func:`find_user`",
	                                  since="1.4.0")(find_user)
	getAllUsers          = deprecated("getAllUsers has been renamed to get_all_users",
	                                  includedoc="Replaced by :func:`get_all_users`",
	                                  since="1.4.0")(get_all_users)
	hasBeenCustomized    = deprecated("hasBeenCustomized has been renamed to has_been_customized",
	                                  includedoc="Replaced by :func:`has_been_customized`",
	                                  since="1.4.0")(has_been_customized)

##~~ FilebasedUserManager, takes available users from users.yaml file

class FilebasedUserManager(UserManager):
	def __init__(self):
		UserManager.__init__(self)

		userfile = settings().get(["accessControl", "userfile"])
		if userfile is None:
			userfile = os.path.join(settings().getBaseFolder("base"), "users.yaml")
		self._userfile = userfile
		self._users = {}
		self._dirty = False

		self._customized = None
		self._load()

	def _load(self):
		if os.path.exists(self._userfile) and os.path.isfile(self._userfile):
			self._customized = True
			with open(self._userfile, "r") as f:
				data = yaml.safe_load(f)
				for name in data.keys():
					attributes = data[name]
					permissions = []
					if "permissions" in attributes:
						permissions = attributes["permissions"]

					groups = []
					if "groups" in attributes:
						groups = attributes["groups"]

					# migrate from roles to permissions
					if "roles" in attributes and not "permissions" in attributes:
						self._logger.info("Migrating user {} to new granular permission system".format(name))

						from octoprint.server import groupManager
						groups.extend(self._migrate_roles_to_groups(attributes["roles"]))
						self._dirty = True

					apikey = None
					if "apikey" in attributes:
						apikey = attributes["apikey"]
					settings = dict()
					if "settings" in attributes:
						settings = attributes["settings"]

					self._users[name] = User(username=name,
					                         passwordHash=attributes["password"],
					                         active=attributes["active"],
					                         permissions=permissions,
					                         groups=groups,
					                         apikey=apikey,
					                         settings=settings)
					for sessionid in self._sessionids_by_userid.get(name, set()):
						if sessionid in self._session_users_by_session:
							self._session_users_by_session[sessionid].update_user(self._users[name])

			if self._dirty:
				self._save()

		else:
			self._customized = False

	def _save(self, force=False):
		if not self._dirty and not force:
			return

		data = {}
		for name in self._users.keys():
			user = self._users[name]

			if not user or not isinstance(user, User):
				continue

			data[name] = {
				"password": user._passwordHash,
				"active": user._active,
				"groups": user._groups,
				"permissions": user._permissions,
				"apikey": user._apikey,
				"settings": user._settings,

				# TODO: deprecated, remove in 1.5.0
				"roles": user._roles
			}

		with atomic_write(self._userfile, "wb", permissions=0o600, max_permissions=0o666) as f:
			yaml.safe_dump(data, f, default_flow_style=False, indent="    ", allow_unicode=True)
			self._dirty = False
		self._load()

	@staticmethod
	def _migrate_roles_to_groups(roles):
		from octoprint.server import groupManager

		# If admin is inside the roles, just return admin group
		if "admin" in roles:
			return [groupManager.admins_group]
		else:
			# Because the Original system only contained of admin and user we can simply check for a user group,
			# create it and return it
			if groupManager.find_group("Users") is None:
				groupManager.add_group("Users", "User group", permissions=Permissions.USER_ARRAY, default=False)

			return [groupManager.find_group("Users")]

	def add_user(self, username, password, active=False, permissions=None, groups=None, apikey=None, overwrite=False):
		if not permissions:
			permissions = []

		if not groups:
			groups = []

		if username in self._users.keys() and not overwrite:
			raise UserAlreadyExists(username)

		self._users[username] = User(username, UserManager.create_password_hash(password), active, permissions, groups, apikey=apikey)
		self._dirty = True
		self._save()

	def change_user_activation(self, username, active):
		if username not in self._users.keys():
			raise UnknownUser(username)

		if self._users[username].is_active != active:
			self._users[username]._active = active
			self._dirty = True
			self._save()

	def change_user_permissions(self, username, permissions):
		if username not in self._users.keys():
			raise UnknownUser(username)

		user = self._users[username]

		removed_permissions = list(set(user._permissions) - set(permissions))
		added_permissions = list(set(permissions) - set(user._permissions))

		if len(removed_permissions) > 0:
			user.remove_permissions_from_user(removed_permissions)
			self._dirty = True

		if len(added_permissions) > 0:
			user.add_permissions_to_user(added_permissions)
			self._dirty = True

		if self._dirty:
			self._save()

	def add_permissions_to_user(self, username, permissions):
		if username not in self._users.keys():
			raise UnknownUser(username)

		if self._users[username].add_permissions_to_user(permissions):
			self._dirty = True
			self._save()

	def remove_permissions_from_user(self, username, permissions):
		if username not in self._users.keys():
			raise UnknownUser(username)

		if self._users[username].remove_permissions_from_user(permissions):
			self._dirty = True
			self._save()

	def remove_permissions_from_users(self, permissions):
		for user in self._users.keys():
			self._dirty |= user.remove_permissions_from_user(permissions)

		if self._dirty:
			self._save()

	def change_user_groups(self, username, groups):
		if username not in self._users.keys():
			raise UnknownUser(username)

		user = self._users[username]

		removed_groups = list(set(user._groups) - set(groups))
		added_groups = list(set(groups) - set(user._groups))

		if len(removed_groups) > 0:
			user.remove_groups_from_user(removed_groups)
			self._dirty = True

		if len(added_groups) > 0:
			user.add_groups_to_user(added_groups)
			self._dirty = True

		if self._dirty:
			self._save()

	def add_groups_to_user(self, username, groups):
		if username not in self._users.keys():
			raise UnknownUser(username)

		if self._users[username].add_groups_to_user(groups):
			self._dirty = True
			self._save()

	def remove_groups_from_user(self, username, groups):
		if username not in self._users.keys():
			raise UnknownUser(username)

		if self._users[username].remove_groups_from_user(groups):
			self._dirty = True
			self._save()

	def remove_groups_from_users(self, groups):
		for username in self._users.keys():
			self._dirty |= self._users[username].remove_groups_from_user(groups)

		if self._dirty:
			self._save()

	def change_user_password(self, username, password):
		if not username in self._users.keys():
			raise UnknownUser(username)

		passwordHash = UserManager.create_password_hash(password)
		user = self._users[username]
		if user._passwordHash != passwordHash:
			user._passwordHash = passwordHash
			self._dirty = True
			self._save()

	def change_user_setting(self, username, key, value):
		if not username in self._users.keys():
			raise UnknownUser(username)

		user = self._users[username]
		old_value = user.get_setting(key)
		if not old_value or old_value != value:
			user.set_setting(key, value)
			self._dirty = self._dirty or old_value != value
			self._save()

	def change_user_settings(self, username, new_settings):
		if not username in self._users:
			raise UnknownUser(username)

		user = self._users[username]
		for key, value in new_settings.items():
			old_value = user.get_setting(key)
			user.set_setting(key, value)
			self._dirty = self._dirty or old_value != value
		self._save()

	def get_all_user_settings(self, username):
		if not username in self._users.keys():
			raise UnknownUser(username)

		user = self._users[username]
		return user.get_all_settings()

	def get_user_setting(self, username, key):
		if not username in self._users.keys():
			raise UnknownUser(username)

		user = self._users[username]
		return user.get_setting(key)

	def generate_api_key(self, username):
		if not username in self._users.keys():
			raise UnknownUser(username)

		user = self._users[username]
		user._apikey = ''.join('%02X' % z for z in bytes(uuid.uuid4().bytes))
		self._dirty = True
		self._save()
		return user._apikey

	def delete_api_key(self, username):
		if not username in self._users.keys():
			raise UnknownUser(username)

		user = self._users[username]
		user._apikey = None
		self._dirty = True
		self._save()

	def remove_user(self, username):
		UserManager.remove_user(self, username)

		if not username in self._users.keys():
			raise UnknownUser(username)

		del self._users[username]
		self._dirty = True
		self._save()

	def find_user(self, userid=None, apikey=None, session=None):
		user = UserManager.find_user(self, userid=userid, session=session)

		if user is not None:
			return user

		if userid is not None:
			if userid not in self._users.keys():
				return None
			return self._users[userid]

		elif apikey is not None:
			for user in self._users.values():
				if apikey == user._apikey:
					return user
			return None

		else:
			return None

	def get_all_users(self):
		return map(lambda x: x.as_dict(), self._users.values())

	def has_been_customized(self):
		return self._customized

	# ~~ Deprecated methods follow

	# TODO: Remove deprecated methods in OctoPrint 1.5.0

	generateApiKey = deprecated("generateApiKey has been renamed to generate_api_key",
	                            includedoc="Replaced by :func:`generate_api_key`",
	                            since="1.4.0")(generate_api_key)
	deleteApiKey   = deprecated("deleteApiKey has been renamed to delete_api_key",
	                            includedoc="Replaced by :func:`delete_api_key`",
	                            since="1.4.0")(delete_api_key)

##~~ Exceptions

class UserAlreadyExists(Exception):
	def __init__(self, username):
		Exception.__init__(self, "User %s already exists" % username)


class UnknownUser(Exception):
	def __init__(self, username):
		Exception.__init__(self, "Unknown user: %s" % username)


class UnknownRole(Exception):
	def _init_(self, role):
		Exception.__init__(self, "Unknown role: %s" % role)

##~~ Refactoring helpers

class MethodReplacedByBooleanProperty(object):

	def __init__(self, name, message, getter):
		self._name = name
		self._message = message
		self._getter = getter

	@property
	def _attr(self):
		return self._getter()

	def __call__(self):
		from warnings import warn
		warn(DeprecationWarning(self._message.format(name=self._name)), stacklevel=2)
		return self._attr

	def __eq__(self, other):
		return self._attr == other

	def __ne__(self, other):
		return self._attr != other

	def __bool__(self):
		# Python 3
		return self._attr

	def __nonzero__(self):
		# Python 2
		return self._attr

	def __hash__(self):
		return hash(self._attr)

	def __repr__(self):
		return "MethodReplacedByProperty({}, {}, {})".format(self._name, self._message, self._getter)

	def __str__(self):
		return str(self._attr)


# TODO: Remove compatibility layer in OctoPrint 1.5.0
class FlaskLoginMethodReplacedByBooleanProperty(MethodReplacedByBooleanProperty):

	def __init__(self, name, getter):
		message = "{name} is now a property in Flask-Login versions >= 0.3.0, which OctoPrint now uses. " + \
		          "Use {name} instead of {name}(). This compatibility layer will be removed in OctoPrint 1.5.0."
		MethodReplacedByBooleanProperty.__init__(self, name, message, getter)


# TODO: Remove compatibility layer in OctoPrint 1.5.0
class OctoPrintUserMethodReplacedByBooleanProperty(MethodReplacedByBooleanProperty):

	def __init__(self, name, getter):
		message = "{name} is now a property for consistency reasons with Flask-Login versions >= 0.3.0, which " + \
		          "OctoPrint now uses. Use {name} instead of {name}(). This compatibility layer will be removed " + \
		          "in OctoPrint 1.5.0."
		MethodReplacedByBooleanProperty.__init__(self, name, message, getter)

##~~ User object

class User(UserMixin):
	def __init__(self, username, passwordHash, active, permissions=[], groups=[], apikey=None, settings=None):
		self._username = username
		self._passwordHash = passwordHash
		self._active = active
		self._apikey = apikey

		from octoprint.server import permissionManager, groupManager
		self._permissions = []
		for p in permissions:
			permission = permissionManager.get_permission_from(p)
			if permission is not None:
				self._permissions.append(permission.get_name())

		self._groups = []
		for g in groups:
			group = groupManager.get_group_from(g)
			if group is not None:
				self._groups.append(group.get_name())

		if settings is None:
			settings = dict()

		self._settings = settings

	def as_dict(self):
		from octoprint.access.permissions import OctoPrintPermission
		return {
			"name": self._username,
			"active": bool(self.is_active),
			"permissions": self._permissions,
			"groups": self._groups,
			"needs": OctoPrintPermission.convert_needs_to_dict(self.needs),
			"apikey": self._apikey,
			"settings": self._settings,

			# TODO: deprecated, remove in 1.5.0
			"admin": self.has_permission(Permissions.ADMIN),
			"user": not self.is_anonymous,
			"roles": self._roles
		}

	def check_password(self, passwordHash):
		return self._passwordHash == passwordHash

	def get_id(self):
		return self.get_name()

	def get_name(self):
		return self._username

	@property
	def is_anonymous(self):
		return FlaskLoginMethodReplacedByBooleanProperty("is_anonymous", lambda: False)

	@property
	def is_authenticated(self):
		return FlaskLoginMethodReplacedByBooleanProperty("is_authenticated", lambda: True)

	@property
	def is_active(self):
		return FlaskLoginMethodReplacedByBooleanProperty("is_active", lambda: self._active)

	def get_all_settings(self):
		return self._settings

	def get_setting(self, key):
		if not isinstance(key, (tuple, list)):
			path = [key]
		else:
			path = key

		return self._get_setting(path)

	def add_permissions_to_user(self, permissions):
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

	def remove_permissions_from_user(self, permissions):
		# Make sure the permissions variable is of type list
		if not isinstance(permissions, list):
			permissions = [permissions]

		dirty = False
		from octoprint.access.permissions import OctoPrintPermission
		for permission in permissions:
			# If someone gives a OctoPrintPermission object, we convert it into the identifier name,
			# because all permissions are stored as identifiers inside the group
			if isinstance(permission, OctoPrintPermission):
				permission = permission.get_name()

			# We don't check if the permission exists, because it could have been removed
			# from the permission manager already
			if permission in self._permissions:
				self._permissions.remove(permission)
				dirty = True

		return dirty

	def add_groups_to_user(self, groups):
		# Make sure the groups variable is of type list
		if not isinstance(groups, list):
			groups = [groups]

		dirty = False
		from octoprint.server import groupManager
		for group in groups:
			# We check if the group is registered in the group manager,
			# if not we are not going to add it to the users groups list
			tmp_group = groupManager.get_group_from(group)
			if tmp_group is not None and tmp_group not in self.groups:
				self._groups.append(tmp_group.get_name())
				dirty = True

		return dirty

	def remove_groups_from_user(self, groups):
		# Make sure the groups variable is of type list
		if not isinstance(groups, list):
			groups = [groups]

		dirty = False
		from octoprint.access.groups import Group
		for group in groups:
			# If someone gives a OctoPrintPermission object, we convert it into the identifier name,
			# because all permissions are stored as identifiers inside the group
			if isinstance(group, Group):
				group = group.get_name()

			# We don't check if the group exists, because it could have been removed
			# from the group manager already
			if group in self._groups:
				self._groups.remove(group)
				dirty = True

		return dirty

	@property
	def permissions(self):
		if self._permissions is None:
			return []

		from octoprint.server import permissionManager
		if Permissions.ADMIN.get_name() in self._permissions:
			return permissionManager.permissions

		return filter(lambda p: p is not None,
					map(lambda x: permissionManager.find_permission(x), self._permissions))

	@property
	def groups(self):
		if self._groups is None:
			return []

		from octoprint.server import groupManager
		return filter(lambda p: p is not None,
					map(lambda x: groupManager.find_group(x), self._groups))

	@property
	def needs(self):
		needs = set()
		permissions = self.permissions
		for group in self.groups:
			if group is not None:
				permissions += group.permissions

		for permission in permissions:
			if permission is not None:
				needs = needs.union(permission.needs)

		return needs

	def has_permission(self, permission):
		from octoprint.server import groupManager
		if Permissions.ADMIN.get_name() in self._permissions or (groupManager is not None and groupManager.admins_group.get_name() in self._groups):
			return True

		return permission.needs.issubset(self.needs)

	def set_setting(self, key, value):
		if not isinstance(key, (tuple, list)):
			path = [key]
		else:
			path = key
		return self._set_setting(path, value)

	def _get_setting(self, path):
		s = self._settings
		for p in path:
			if isinstance(s, dict) and p in s:
				s = s[p]
			else:
				return None
		return s

	def _set_setting(self, path, value):
		s = self._settings
		for p in path[:-1]:
			if p not in s:
				s[p] = dict()

			if not isinstance(s[p], dict):
				s[p] = dict()

			s = s[p]

		key = path[-1]
		s[key] = value
		return True

	def __repr__(self):
		return "User(id=%s,name=%s,active=%r,user=True,admin=%r,permissions=%s,groups=%s)" % (self.get_id(), self.get_name(), bool(self.is_active), self.has_permission(Permissions.ADMIN), self._permissions, self._groups)

	# ~~ Deprecated methods & properties follow

	# TODO: Remove deprecated methods & properties in OctoPrint 1.5.0

	asDict = deprecated("asDict has been renamed to as_dict",
	                    includedoc="Replaced by :func:`as_dict`",
	                    since="1.4.0")(as_dict)

	@property
	@deprecated("is_user is deprecated, please use has_permissions", since="1.4.0")
	def is_user(self):
		return OctoPrintUserMethodReplacedByBooleanProperty("is_user", lambda: not self.is_anonymous)

	@property
	@deprecated("is_admin is deprecated, please use has_permissions", since="1.4.0")
	def is_admin(self):
		return OctoPrintUserMethodReplacedByBooleanProperty("is_admin", lambda: self.has_permission(Permissions.ADMIN))

	@property
	@deprecated("roles is deprecated, please use has_permission", since="1.4.0")
	def roles(self):
		return self._roles

	@property
	def _roles(self):
		"""Helper for the deprecated self.roles and serializing to yaml"""
		if self.has_permission(Permissions.ADMIN):
			return ["user", "admin"]
		elif not self.is_anonymous:
			return ["user"]
		else:
			return []


class AnonymousUser(AnonymousUserMixin, User):
	def __init__(self):
		from octoprint.server import groupManager
		User.__init__(self, "guest", "", True, [], [groupManager.guests_group])

	@property
	def is_anonymous(self):
		return FlaskLoginMethodReplacedByBooleanProperty("is_anonymous", lambda: True)

	@property
	def is_authenticated(self):
		return FlaskLoginMethodReplacedByBooleanProperty("is_authenticated", lambda: False)

	@property
	def is_active(self):
		return FlaskLoginMethodReplacedByBooleanProperty("is_active", lambda: False)

	def check_password(self, passwordHash):
		return True


class SessionUser(wrapt.ObjectProxy):
	def __init__(self, user):
		wrapt.ObjectProxy.__init__(self, user)

		import string
		import random
		import time
		chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
		self._self_session = "".join(random.choice(chars) for _ in range(10))
		self._self_created = time.time()

	@property
	def session(self):
		return self._self_session

	@property
	def created(self):
		return self._self_created

	@deprecated("SessionUser.get_session() has been deprecated, use SessionUser.session instead", since="1.3.5")
	def get_session(self):
		return self.session

	def update_user(self, user):
		self.__wrapped__ = user

	def __repr__(self):
		return "SessionUser({!r},session={},created={})".format(self.__wrapped__, self.session, self.created)

##~~ DummyUser object to use when accessControl is disabled

class DummyUser(User):
	def __init__(self):
		from octoprint.server import groupManager
		User.__init__(self, "dummy", "", True, [], [groupManager.admins_group])

	def check_password(self, passwordHash):
		return True


class DummyIdentity(Identity):
	def __init__(self):
		Identity.__init__(self, "dummy")


def dummy_identity_loader():
	return DummyIdentity()


##~~ Apiuser object to use when global api key is used to access the API
class ApiUser(User):
	def __init__(self):
		from octoprint.server import groupManager
		User.__init__(self, "_api", "", True, [], [groupManager.admins_group])
