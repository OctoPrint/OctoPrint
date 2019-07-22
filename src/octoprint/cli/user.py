# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2019 The OctoPrint Project - Released under terms of the AGPLv3 License"


import click
import logging

from octoprint import init_settings
from octoprint.cli import get_ctx_obj_option
from octoprint.users import FilebasedUserManager, UnknownUser
from octoprint.util import get_class

click.disable_unicode_literals_warning = True

#~~ "octoprint user" commands


@click.group()
def user_commands():
	pass


@user_commands.group(name="user")
@click.pass_context
def user(ctx):
	"""
	User management.

	Note that this currently only supports managing user accounts stored in the configured user manager, not any
	user managers added through plugins and the "octoprint.users.factory" hook.
	"""
	try:
		logging.basicConfig(level=logging.DEBUG if get_ctx_obj_option(ctx, "verbosity", 0) > 0 else logging.WARN)
		settings = init_settings(get_ctx_obj_option(ctx, "basedir", None), get_ctx_obj_option(ctx, "configfile", None))

		name = settings.get(["accessControl", "userManager"])
		try:
			clazz = get_class(name)
			manager = clazz(settings=settings)
		except Exception:
			click.echo("Could not instantiate user manager {}, falling back to FilebasedUserManager!".format(name), err=True)
			manager = FilebasedUserManager(settings=settings)
		finally:
			manager.enabled = settings.getBoolean(["accessControl", "enabled"])

		ctx.obj.user_manager = manager

	except Exception:
		click.echo("Could not instantiate user manager", err=True)
		return


@user.command(name="add")
@click.argument("username", type=click.STRING, required=True)
@click.password_option("--password", "password", help="Password for user")
@click.option("--admin", "is_admin", type=click.BOOL, default=False,
			  help="Sets admin role on user")
@click.pass_context
def add_user_command(ctx, username, password, is_admin):
	"""Add a new user"""
	ctx.obj.user_manager.addUser(username,
	                             password,
	                             roles=("admin" if is_admin else "user"),
	                             active=True)


@user.command(name="remove")
@click.argument("username", type=click.STRING)
@click.pass_context
def remove_user_command(ctx, username):
	"""Remove a user"""
	confirm = click.prompt("This is will irreversibly destroy the user account! Enter 'yes' to confirm",
	                       type=click.STRING)

	if confirm.lower() == "yes":
		ctx.obj.user_manager.removeUser(username)
	else:
		click.echo("User not removed")


@user.command(name="password")
@click.argument("username", type=click.STRING)
@click.password_option("--password", "password", help="New password for user")
@click.pass_context
def change_password_command(ctx, username, password):
	"""Changes an existing user's password"""
	try:
		ctx.obj.user_manager.changeUserPassword(username, password)
	except UnknownUser:
		click.echo("This user does not exist!", err=True)

