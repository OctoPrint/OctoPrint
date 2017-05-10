# coding=utf-8
"""
Unit tests for octoprint.users.User
"""
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

import shutil
import tempfile
import contextlib

import unittest
import ddt

import octoprint.server
from octoprint import settings
from octoprint.util import dict_merge
from octoprint.access import permissions, users
from octoprint.access.permissions import PermissionManager, OctoPrintPermission
from octoprint.access.groups import FilebasedGroupManager

default_settings = dict(key="value", sub=dict(subkey="subvalue"))
admin_permissions = map(lambda a: getattr(permissions.Permissions, a), filter(lambda a: isinstance(getattr(permissions.Permissions, a), OctoPrintPermission), dir(permissions.Permissions)))
admin_needs_dict = OctoPrintPermission.convert_needs_to_dict(set().union(*map(lambda p: p.needs, admin_permissions)))

@ddt.ddt
class UserTestCase(unittest.TestCase):
	def setUp(self):
		try:
			with self.mocked_basedir():
				settings.settings(init=True)

			octoprint.server.permissionManager = PermissionManager()
			permissions.Permissions.initialize()
			octoprint.server.groupManager = FilebasedGroupManager()
		except Exception as e:
			pass

		self.maxDiff = None

		self.user = users.User("user", "passwordHash", True, permissions=[permissions.Permissions.STATUS], apikey="apikey_user", settings=default_settings)
		self.user_multi_permission = users.User("userMultiPermission", "passwordHash", True, permissions=[permissions.Permissions.STATUS, permissions.Permissions.DOWNLOAD, permissions.Permissions.CONNECTION], apikey="apikey_user", settings=default_settings)
		self.user_permission_group = users.User("userPermissionGroup", "passwordHash", True, permissions=[permissions.Permissions.DOWNLOAD], groups=[octoprint.server.groupManager.guests_group], apikey="apikey_user", settings=default_settings)
		self.admin_permission = users.User("adminPermission", "passwordHash", True, permissions=[permissions.Permissions.ADMIN], apikey="apikey_admin", settings=default_settings)
		self.admin_group = users.User("adminGroup", "passwordHash", True, permissions=[], groups=[octoprint.server.groupManager.admins_group], apikey="apikey_admin", settings=default_settings)
		self.inactive = users.User("inactive", "passwordHash", False, apikey="apikey_inactive", settings=default_settings)

	# It's possible to use the convert method here, because this method get's tested in the permission tests,
	# this makes the testing a bit easier especially if for some reason one day the permission needs get adjusted
	@ddt.unpack
	@ddt.data(("user", dict(name="user",
			              active=True,
			              permissions=[permissions.Permissions.STATUS],
			              groups=[],
			              needs=OctoPrintPermission.convert_needs_to_dict(permissions.Permissions.STATUS.needs),
			              admin=False,
			              user=True,
			              apikey="apikey_user",
			              settings=default_settings)),
	          ("user_multi_permission", dict(name="userMultiPermission",
	                        active=True,
	                        permissions=[permissions.Permissions.CONNECTION, permissions.Permissions.DOWNLOAD, permissions.Permissions.STATUS],
	                        groups=[],
	                        needs=OctoPrintPermission.convert_needs_to_dict(permissions.Permissions.STATUS.needs
	                                                                        .union(permissions.Permissions.DOWNLOAD.needs)
	                                                                        .union(permissions.Permissions.CONNECTION.needs)),
	                        admin=False,
	                        user=True,
	                        apikey="apikey_user",
	                        settings=default_settings)),
			("admin_permission", dict(name="adminPermission",
			                          active=True,
			                          permissions=[permissions.Permissions.ADMIN],
			                          groups=[],
			                          needs=admin_needs_dict,
			                          admin=True,
			                          user=True,
			                          apikey="apikey_admin",
			                          settings=default_settings)),
			("inactive", dict(name="inactive",
		                      active=False,
		                      permissions=[],
		                      groups=[],
		                      needs=dict(),
		                      admin=False,
		                      user=True,
		                      apikey="apikey_inactive",
		                      settings=default_settings))
			)
	def test_user_permission_as_dict(self, uservar, expected):
		user = getattr(self, uservar)

		# we need to sort the needs, permissions and groups
		# these values could be in any order so we need to sort them to have a defined order for the assertEqual
		asDict = self.sort_attributes(user.asDict())
		expected = self.sort_attributes(expected)

		self.assertDictEqual(expected, asDict)

	def test_group_permission_as_dict(self):
		data_groups = [
			("user_permission_group", dict(name="userPermissionGroup",
			                     active=True,
			                     permissions=[permissions.Permissions.DOWNLOAD],
			                     groups=[octoprint.server.groupManager.guests_group],
			                     needs=dict(role=["download"]),
			                     admin=False,
			                     user=True,
			                     apikey="apikey_user",
			                     settings=default_settings)),
			("admin_group", dict(name="adminGroup",
			                     active=True,
			                     permissions=[],
			                     groups=[octoprint.server.groupManager.admins_group],
			                     needs=admin_needs_dict,
			                     admin=True,
			                     user=True,
			                     apikey="apikey_admin",
			                     settings=default_settings)),
		]

		for uservar, expected in data_groups:
			user = getattr(self, uservar)

			# we need to sort the needs
			asDict = self.sort_attributes(user.asDict())
			expected = self.sort_attributes(expected)

			self.assertDictEqual(expected, asDict)

	@ddt.data(
			("user", dict(add=[permissions.Permissions.DOWNLOAD],
						  _permissions=[permissions.Permissions.DOWNLOAD, permissions.Permissions.STATUS],
			              permissions=[permissions.Permissions.DOWNLOAD, permissions.Permissions.STATUS]),
			         dict(remove=[permissions.Permissions.STATUS],
			              _permissions=[permissions.Permissions.DOWNLOAD],
			              permissions=[permissions.Permissions.DOWNLOAD])),
			("admin_permission", dict(add=[permissions.Permissions.DOWNLOAD],
			                          _permissions=[permissions.Permissions.ADMIN],
			                          permissions=admin_permissions
			                     ),
			                     dict(remove=[permissions.Permissions.ADMIN],
			                          _permissions=[],
			                          permissions=[])),
	)
	@ddt.unpack
	def test_change_permission(self, uservar, add_expected, remove_expected):
		user = getattr(self, uservar)

		user.add_permissions_to_user(add_expected['add'])
		self.assertEqual(sorted(user._permissions, key=lambda p: p.get_name()), sorted(add_expected['_permissions'], key=lambda p: p.get_name()))
		self.assertEqual(sorted(user.permissions, key=lambda p: p.get_name()), sorted(add_expected['permissions'], key=lambda p: p.get_name()))

		user.remove_permissions_from_user(remove_expected['remove'])
		self.assertEqual(sorted(user._permissions, key=lambda p: p.get_name()), sorted(remove_expected['_permissions'], key=lambda p: p.get_name()))
		self.assertEqual(sorted(user.permissions, key=lambda p: p.get_name()), sorted(remove_expected['permissions'], key=lambda p: p.get_name()))

	def test_change_group(self):
		pass

	@ddt.data(
		("key", "value"),
		(["sub", "subkey"], "subvalue"),
		("doesntexist", None)
	)
	@ddt.unpack
	def test_get_setting(self, key, expected):
		value = self.user.get_setting(key)
		self.assertEqual(expected, value)

	@ddt.data(
		("otherkey", "othervalue", dict(otherkey="othervalue"), True),
		(["sub", "othersubkey"], "othersubvalue", dict(sub=dict(othersubkey="othersubvalue")), True),
		("booleankey", True, dict(booleankey=True), True),
		(["newsub", "newsubkey"], "newsubvalue", dict(newsub=dict(newsubkey="newsubvalue")), True),
		# ["sub", "subkey"] is already existing and gets overwritten
		(["sub", "subkey", "subsubkey"], "42", dict(sub=dict(subkey=dict(subsubkey="42"))), True),
		(["sub"], "overwrite", dict(sub="overwrite"), True)
	)
	@ddt.unpack
	def test_set_setting_string(self, key, value, update, expected_returnvalue):
		returnvalue = self.user.set_setting(key, value)

		expected = dict_merge(default_settings, update)

		self.assertDictEqual(expected, self.user.get_all_settings())
		self.assertEqual(expected_returnvalue, returnvalue)

	def test_check_password(self):
		self.assertTrue(self.user.check_password("passwordHash"))
		self.assertFalse(self.user.check_password("notThePasswordHash"))

	def test_repr(self):
		test_data = [
			("user", "User(id=user,name=user,active=True,user=True,admin=False,permissions=%s,groups=[])" % ([permissions.Permissions.STATUS])),
			# we can add the groups here by reference because their repr will be tested in the test_groups.py so it is unnecessary to do this here again
			("user_multi_permission", "User(id=userMultiPermission,name=userMultiPermission,active=True,user=True,admin=False,permissions=%s,groups=[])" % ([permissions.Permissions.CONNECTION, permissions.Permissions.DOWNLOAD, permissions.Permissions.STATUS])),
			("user_permission_group", "User(id=userPermissionGroup,name=userPermissionGroup,active=True,user=True,admin=False,permissions=%s,groups=%s)" % ([permissions.Permissions.DOWNLOAD], [octoprint.server.groupManager.guests_group])),
			("admin_permission", "User(id=adminPermission,name=adminPermission,active=True,user=True,admin=True,permissions=%s,groups=[])" % ([permissions.Permissions.ADMIN])),
			("admin_group", "User(id=adminGroup,name=adminGroup,active=True,user=True,admin=True,permissions=[],groups=%s)" % ([octoprint.server.groupManager.admins_group])),
			("inactive", "User(id=inactive,name=inactive,active=False,user=True,admin=False,permissions=[],groups=[])")
		]

		for uservar, output in test_data:
			self.assertEqual(output, repr(getattr(self, uservar)))

	##~~ helpers

	def sort_attributes(self, obj):
		obj['permissions'] = sorted(obj['permissions'])
		obj['groups'] = sorted(obj['groups'])

		for k in obj['needs']:
			obj['needs'][k] = sorted(obj['needs'][k])

		return obj

	@contextlib.contextmanager
	def mocked_basedir(self):
		orig_default_basedir = octoprint.settings._default_basedir
		directory = None

		try:
			directory = tempfile.mkdtemp("octoprint-settings-test")
			octoprint.settings._default_basedir = lambda *args, **kwargs: directory
			yield directory
		finally:
			octoprint.settings._default_basedir = orig_default_basedir
			if directory is not None:
				try:
					shutil.rmtree(directory)
				except:
					self.fail("Could not remove temporary basedir")


