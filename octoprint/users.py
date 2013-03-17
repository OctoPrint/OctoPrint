# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

from flask.ext.login import UserMixin
import hashlib
import os
import yaml

from octoprint.settings import settings

class UserManager:
	valid_roles=["user", "admin"]

	@staticmethod
	def createPasswordHash(password):
		return hashlib.sha512(password + "mvBUTvwzBzD3yPwvnJ4E4tXNf3CGJvvW").hexdigest()

	def addUser(self, username, password):
		pass

	def addRoleToUser(self, username, role):
		pass

	def removeRoleFromUser(self, username, role):
		pass

	def updateUser(self, username, password):
		pass

	def removeUser(self, username):
		pass

	def findUser(self, username=None):
		return None

##~~ FilebasedUserManager, takes available users from users.yaml file

class FilebasedUserManager(UserManager):
	def __init__(self, userfile=None):
		UserManager.__init__(self)

		if userfile is None:
			userfile = os.path.join(settings().settings_dir, "users.yaml")
		self._userfile = userfile
		self._users = None
		self._dirty = False

		self._load()

	def _load(self):
		self._users = {}
		if os.path.exists(self._userfile) and os.path.isfile(self._userfile):
			with open(self._userfile, "r") as f:
				data = yaml.safe_load(f)
				for name in data.keys():
					attributes = data[name]
					self._users[name] = User(name, attributes.password, attributes.active, attributes.roles)

	def _save(self, force=False):
		if not self._dirty and not force:
			return

		data = {}
		for name in self._users.keys():
			user = self._users[name]
			data[name] = {
				"password": user.passwordHash,
				"active": user.active,
				"roles": user.roles
			}

		with open(self._userfile, "wb") as f:
			yaml.safe_dump(data, f, default_flow_style=False, indent="    ", allow_unicode=True)
			self._dirty = False
		self._load()

	def addUser(self, username, password):
		if username in self._users.keys():
			raise UserAlreadyExists(username)

		self._users[username] = User(username, UserManager.createPasswordHash(password), False, ["user"])
		self._dirty = True
		self._save()

	def addRoleToUser(self, username, role):
		if not username in self._users.keys():
			raise UnknownUser(username)

		user = self._users[username]
		if not role in user.roles:
			user.roles.append(role)
			self._dirty = True
			self._save()

	def removeRoleFromUser(self, username, role):
		if not username in self._users.keys():
			raise UnknownUser(username)

		user = self._users[username]
		if role in user.roles:
			user.roles.remove(role)
			self._dirty = True
			self._save()

	def updateUser(self, username, password):
		if not username in self._users.keys():
			raise UnknownUser(username)

		passwordHash = UserManager.createPasswordHash(password)
		user = self._users[username]
		if user.passwordHash != passwordHash:
			user.passwordHash = passwordHash
			self._dirty = True
			self._save()

	def removeUser(self, username):
		if not username in self._users.keys():
			raise UnknownUser(username)

		del self._users[username]
		self._dirty = True
		self._save()

	def findUser(self, username=None):
		if username is None:
			return None

		if username not in self._users.keys():
			return None

		return self._users[username]

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

##~~ User object

class User(UserMixin):
	def __init__(self, username, passwordHash, active, roles):
		self.username = username
		self.passwordHash = passwordHash
		self.active = active
		self.roles = roles

	def get_id(self):
		return self.username

	def is_active(self):
		return self.active