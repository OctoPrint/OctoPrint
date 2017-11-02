# coding=utf-8
"""
Unit tests for octoprint.access
"""
from __future__ import absolute_import, division, print_function

import unittest
import ddt

import shutil
import tempfile

import octoprint.server
from octoprint.util import dict_merge
from octoprint.access.permissions import Permissions, PermissionManager, OctoPrintPermission, RoleNeed
from octoprint.access.groups import FilebasedGroupManager, Group
from octoprint.access.users import FilebasedUserManager, User, SessionUser

class TestPermissions(object):
	# Needs to be a Reference to the Permissions.ADMIN, because the admins_group is hard coded using the Permissions.ADMIN permission
	ADMIN = Permissions.ADMIN

	TEST1 = OctoPrintPermission("Test 1", "Test permission 1", RoleNeed("p1"))
	TEST2 = OctoPrintPermission("Test 2", "Test permission 2", RoleNeed("p2"))

	@classmethod
	def initialize(cls):
		octoprint.server.permissionManager.add_permission(cls.ADMIN)

		octoprint.server.permissionManager.add_permission(cls.TEST1)
		octoprint.server.permissionManager.add_permission(cls.TEST2)


default_settings = dict(key="value", sub=dict(subkey="subvalue"))
admin_permissions = map(lambda a: getattr(TestPermissions, a), filter(lambda a: isinstance(getattr(TestPermissions, a), OctoPrintPermission), dir(TestPermissions)))
admin_needs_dict = OctoPrintPermission.convert_needs_to_dict(set().union(*map(lambda p: p.needs, admin_permissions)))


ORIG_DEFAULT_BASEDIR = None
DIRECTORY = None


def setUpModule():
	global ORIG_DEFAULT_BASEDIR
	global DIRECTORY

	ORIG_DEFAULT_BASEDIR = octoprint.settings._default_basedir

	try:
		DIRECTORY = tempfile.mkdtemp("octoprint-settings-access-test")

		octoprint.settings._default_basedir = lambda *args, **kwargs: DIRECTORY
		octoprint.settings.settings(init=True)

		octoprint.server.permissionManager = PermissionManager()
		TestPermissions.initialize()

		octoprint.server.groupManager = FilebasedGroupManager()
		octoprint.server.userManager = FilebasedUserManager()

	except Exception:
		pass


def tearDownModule():
	octoprint.settings._default_basedir = ORIG_DEFAULT_BASEDIR
	if DIRECTORY is not None:
		shutil.rmtree(DIRECTORY)


@ddt.ddt
class PermissionTestCase(unittest.TestCase):
	def setUp(self):
		self.permission = OctoPrintPermission("Permission", "My Permission", RoleNeed("permission"))
		self.permission_multi_need = OctoPrintPermission("PermissionMultiNeed", "My multi need Permission", RoleNeed("permission1"), RoleNeed("permission2"), RoleNeed("permission3"))

	@ddt.data(
			("permission",
			 "OctoPrintPermission(\"Permission\", \"My Permission\", RoleNeed('permission'))"),
			("permission_multi_need",
			 "OctoPrintPermission(\"PermissionMultiNeed\", \"My multi need Permission\", RoleNeed('permission1'), RoleNeed('permission2'), RoleNeed('permission3'))"),
	)
	@ddt.unpack
	def test_repr(self, uservar, expected):
		self.assertEqual(expected, repr(getattr(self, uservar)))

@ddt.ddt
class GroupTestCase(unittest.TestCase):
	def setUp(self):
		self.group = Group("Group", "description", [TestPermissions.TEST1], False, False)
		self.admins_group = Group("AdminsGroup", "description", [TestPermissions.ADMIN], False, True)
		self.multi_permission_group = Group("MultiPermissionGroup", "description",
		                                    [TestPermissions.TEST1, TestPermissions.TEST2], False, False)

	@ddt.data(
			("group",
			 "Group(name=\"Group\", description=\"description\", permissionslist=['Test 1'], default=False, specialGroup=False)"),
			("admins_group",
			 "Group(name=\"AdminsGroup\", description=\"description\", permissionslist=['Admin'], default=False, specialGroup=True)"),
			("multi_permission_group",
			 "Group(name=\"MultiPermissionGroup\", description=\"description\", permissionslist=['Test 1', 'Test 2'], default=False, specialGroup=False)"),
	)
	@ddt.unpack
	def test_repr(self, uservar, expected):
		self.assertEqual(expected, repr(getattr(self, uservar)))

@ddt.ddt
class PermissionManagerTestCase(unittest.TestCase):
	def setUp(self):
		import os
		self.plugin_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), "_plugins")

		plugin_folders = [self.plugin_folder]
		plugin_types = []
		plugin_entry_points = None
		octoprint.server.pluginManager = octoprint.plugin.core.PluginManager(plugin_folders,
		                                                          plugin_types,
		                                                          plugin_entry_points,
		                                                          plugin_disabled_list=[],
		                                                          logging_prefix="logging_prefix.")
		octoprint.server.pluginManager.reload_plugins(startup=True, initialize_implementations=False)
		octoprint.server.pluginManager.initialize_implementations()

	def test_add_remove_permission(self):
		FANCY_NEW_PERMISSION = OctoPrintPermission("Fancy new Permission", "My fancy new permission", RoleNeed("fancy"))

		octoprint.server.permissionManager.add_permission(FANCY_NEW_PERMISSION)
		self.assertTrue(FANCY_NEW_PERMISSION in octoprint.server.permissionManager.permissions)

		octoprint.server.permissionManager.remove_permission(FANCY_NEW_PERMISSION)
		self.assertTrue(FANCY_NEW_PERMISSION not in octoprint.server.permissionManager.permissions)

	def test_add_permission_by_plugin(self):
		server = octoprint.server.Server()
		server._setup_plugin_permissions([])

		data_groups = [
			dict(
					name="Plugin_permissions_plugin_fancy permission",
					description="My Fancy new Permission",
					needs=OctoPrintPermission.convert_needs_to_dict({RoleNeed("plugin_permissions_plugin_fancy")})
				),
			dict(
					name="Plugin_permissions_plugin_fancy permission with two roles",
					description="My Fancy new Permission with two roles",
					needs=OctoPrintPermission.convert_needs_to_dict(
							{RoleNeed("plugin_permissions_plugin_fancy1"), RoleNeed("plugin_permissions_plugin_fancy2")})
				)
		]

		for expected in data_groups:
			permission = octoprint.server.permissionManager.find_permission(expected["name"])

			self.assertDictEqual(permission.as_dict(), expected)

	def test_remove_permission(self):
		octoprint.server.permissionManager.remove_permission("Plugin_permissions_plugin_fancy permission")

		from octoprint.access.permissions import Permissions
		octoprint.server.permissionManager.remove_permission(Permissions.PLUGIN_PERMISSIONS_PLUGIN_FANCY_PERMISSION_WITH_TWO_ROLES)

class GroupManagerTestCase(unittest.TestCase):
	def test_add_remove_group(self):
		octoprint.server.groupManager.add_group("Fancy Group", "My fancy new group", permissions=[TestPermissions.TEST1], save=False)
		self.assertTrue(octoprint.server.groupManager.find_group("Fancy Group") is not None)

		octoprint.server.groupManager.remove_group("Fancy Group")
		self.assertTrue(octoprint.server.groupManager.find_group("Fancy Group") is None)

@ddt.ddt
class UserTestCase(unittest.TestCase):
	def setUp(self):
		self.maxDiff = None

		self.user = User("user", "passwordHash", True, permissions=[TestPermissions.TEST1], apikey="apikey_user", settings=default_settings)
		self.user_multi_permission = User("userMultiPermission", "passwordHash", True, permissions=sorted([TestPermissions.TEST1, TestPermissions.TEST2]), apikey="apikey_user", settings=default_settings)
		self.user_permission_group = User("userPermissionGroup", "passwordHash", True,
		                                        permissions=[TestPermissions.TEST1],
		                                        groups=[octoprint.server.groupManager.guests_group],
		                                        apikey="apikey_user", settings=default_settings)
		self.admin_permission = User("adminPermission", "passwordHash", True,
		                                   permissions=[TestPermissions.ADMIN], apikey="apikey_admin",
		                                   settings=default_settings)
		self.admin_group = User("adminGroup", "passwordHash", True, permissions=[],
		                              groups=[octoprint.server.groupManager.admins_group], apikey="apikey_admin",
		                              settings=default_settings)
		self.inactive = User("inactive", "passwordHash", False, apikey="apikey_inactive",
		                           settings=default_settings)

	# It's possible to use the convert method here, because this method get's tested in the permission tests,
	# this makes the testing a bit easier especially if for some reason one day the permission needs get adjusted
	@ddt.unpack
	@ddt.data(("user", dict(name="user",
	                        active=True,
	                        permissions=["Test 1"],
	                        groups=[],
	                        needs=OctoPrintPermission.convert_needs_to_dict(TestPermissions.TEST1.needs),
	                        admin=False,
	                        user=True,
	                        apikey="apikey_user",
	                        settings=default_settings)),
	          ("user_multi_permission", dict(name="userMultiPermission",
	                                         active=True,
	                                         permissions=["Test 1",
	                                                      "Test 2"],
	                                         groups=[],
	                                         needs=OctoPrintPermission.convert_needs_to_dict(
			                                         TestPermissions.TEST1.needs
			                                         .union(TestPermissions.TEST2.needs)),
	                                         admin=False,
	                                         user=True,
	                                         apikey="apikey_user",
	                                         settings=default_settings)),
	          ("admin_permission", dict(name="adminPermission",
	                                    active=True,
	                                    permissions=["Admin"],
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
		asDict = sort_attributes(user.as_dict())
		expected = sort_attributes(expected)

		self.assertDictEqual(expected, asDict)

	def test_group_permission_as_dict(self):
		data_groups = [
			("user_permission_group", dict(name="userPermissionGroup",
			                               active=True,
			                               permissions=["Test 1"],
			                               groups=["Guests"],
			                               needs=dict(role=["p1"]),
			                               admin=False,
			                               user=True,
			                               apikey="apikey_user",
			                               settings=default_settings)),
			("admin_group", dict(name="adminGroup",
			                     active=True,
			                     permissions=[],
			                     groups=["Admins"],
			                     needs=admin_needs_dict,
			                     admin=True,
			                     user=True,
			                     apikey="apikey_admin",
			                     settings=default_settings)),
		]

		for uservar, expected in data_groups:
			user = getattr(self, uservar)

			# we need to sort the needs
			asDict = sort_attributes(user.as_dict())
			expected = sort_attributes(expected)

			self.assertDictEqual(expected, asDict)

	@ddt.data(
			("user", dict(add=[TestPermissions.TEST2],
			              _permissions=["Test 1", "Test 2"],
			              permissions=[TestPermissions.TEST1, TestPermissions.TEST2]),
					 dict(remove=[TestPermissions.TEST2],
					      _permissions=["Test 1"],
					      permissions=[TestPermissions.TEST1])),
			("admin_permission", dict(add=["Test1"],
			                          _permissions=["Admin"],
			                          permissions=admin_permissions
			                          ),
			                        dict(remove=["Admin"],
			                            _permissions=[],
			                            permissions=[])),
	)
	@ddt.unpack
	def test_change_permission(self, uservar, add_expected, remove_expected):
		user = getattr(self, uservar)

		user.add_permissions_to_user(add_expected['add'])
		self.assertEqual(sorted(user._permissions),
		                 sorted(add_expected['_permissions']))
		self.assertEqual(sorted(user.permissions, key=lambda p: p.get_name()),
		                 sorted(add_expected['permissions'], key=lambda p: p.get_name()))

		user.remove_permissions_from_user(remove_expected['remove'])
		self.assertEqual(sorted(user._permissions),
		                 sorted(remove_expected['_permissions']))
		self.assertEqual(sorted(user.permissions, key=lambda p: p.get_name()),
		                 sorted(remove_expected['permissions'], key=lambda p: p.get_name()))

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
			("user", "User(id=user,name=user,active=True,user=True,admin=False,permissions=['Test 1'],groups=[])"),
			# we can add the groups here by reference because their repr will be tested in the test_groups.py so it is unnecessary to do this here again
			("user_multi_permission",
			 "User(id=userMultiPermission,name=userMultiPermission,active=True,user=True,admin=False,permissions=['Test 1', 'Test 2'],groups=[])"),
			("user_permission_group",
			 "User(id=userPermissionGroup,name=userPermissionGroup,active=True,user=True,admin=False,permissions=['Test 1'],groups=['Guests'])"),
			("admin_permission",
			 "User(id=adminPermission,name=adminPermission,active=True,user=True,admin=True,permissions=['Admin'],groups=[])"),
			("admin_group",
			 "User(id=adminGroup,name=adminGroup,active=True,user=True,admin=True,permissions=[],groups=['Admins'])"),
			("inactive",
			 "User(id=inactive,name=inactive,active=False,user=True,admin=False,permissions=[],groups=[])")
		]

		for uservar, output in test_data:
			self.assertEqual(output, repr(getattr(self, uservar)))

class SessionUserTestCase(unittest.TestCase):
	def setUp(self):
		self.user = User("username", "passwordHash", True,
		                 permissions=[TestPermissions.TEST1],
		                 apikey="apikey",
		                 settings=dict(key="value"))

	def test_two_sessions(self):
		session1 = SessionUser(self.user)
		session2 = SessionUser(self.user)

		# session should be different, wrapped object should be identical
		self.assertNotEqual(session1.session, session2.session)
		self.assertEqual(session1.__wrapped__, session2.__wrapped__)
		self.assertEqual(session1.get_name(), session2.get_name())

	def test_settings_change_propagates(self):
		session1 = SessionUser(self.user)
		session2 = SessionUser(self.user)

		# change should propagate from User to SessionUser
		self.user.set_setting("otherkey", "othervalue")
		self.assertDictEqual(dict(key="value", otherkey="othervalue"), session1.get_all_settings())

		# change should propagate from SessionUser to SessionUser
		session2.set_setting("otherkey", "yetanothervalue")
		self.assertDictEqual(dict(key="value", otherkey="yetanothervalue"), session1.get_all_settings())

	def test_repr(self):
		user = SessionUser(self.user)
		expected = "SessionUser({!r},session={},created={})".format(self.user, user.session, user.created)
		self.assertEqual(expected, repr(user))

	def test_isinstance(self):
		session = SessionUser(self.user)

		# needs to be detected as User instance
		self.assertTrue(isinstance(session, User))

		# also needs to be detected as SessionUser instance
		self.assertTrue(isinstance(session, SessionUser))

		# but wrapped user should NOT be detected as SessionUser instance of course
		self.assertFalse(isinstance(self.user, SessionUser))

#~~ Helpers

def sort_attributes(obj):
	obj['permissions'] = sorted(obj['permissions'])
	obj['groups'] = sorted(obj['groups'])

	for k in obj['needs']:
		obj['needs'][k] = sorted(obj['needs'][k])

	return obj
