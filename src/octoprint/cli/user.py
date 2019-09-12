# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2019 The OctoPrint Project - Released under terms of the AGPLv3 License"


import click
import logging

from octoprint import init_settings
from octoprint.cli import get_ctx_obj_option
from octoprint.users import FilebasedUserManager, UnknownUser, UserAlreadyExists
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


@user.command(name="list")
@click.pass_context
def list_users_command(ctx):
	"""Lists user information"""
	users = ctx.obj.user_manager.getAllUsers()
	_print_list(users)


@user.command(name="add")
@click.argument("username", type=click.STRING, required=True)
@click.password_option("--password", "password", help="Password for user")
@click.option("--admin", "is_admin", type=click.BOOL, is_flag=True, default=False,
			  help="Sets admin role on user")
@click.pass_context
def add_user_command(ctx, username, password, is_admin):
	"""Add a new user."""
	try:
		ctx.obj.user_manager.addUser(username,
		                             password,
		                             roles=(("user", "admin") if is_admin else ("user",)),
		                             active=True)

		user = ctx.obj.user_manager.findUser(username)
		if user:
			click.echo("User created:")
			click.echo("\t{}".format(_user_to_line(user.asDict())))
	except UserAlreadyExists:
		click.echo("A user with the name {} does already exist!".format(username), err=True)


@user.command(name="remove")
@click.argument("username", type=click.STRING)
@click.pass_context
def remove_user_command(ctx, username):
	"""Remove an existing user."""
	confirm = click.prompt("This is will irreversibly destroy the user account! Enter 'yes' to confirm",
	                       type=click.STRING)

	if confirm.lower() == "yes":
		ctx.obj.user_manager.removeUser(username)
		click.echo("User {} removed.".format(username))
	else:
		click.echo("User {} not removed.".format(username))


@user.command(name="password")
@click.argument("username", type=click.STRING)
@click.password_option("--password", "password", help="New password for user")
@click.pass_context
def change_password_command(ctx, username, password):
	"""Change an existing user's password."""
	try:
		ctx.obj.user_manager.changeUserPassword(username, password)
		click.echo("Password changed for user {}.".format(username))
	except UnknownUser:
		click.echo("User {} does not exist!".format(username), err=True)


@user.command(name="activate")
@click.argument("username", type=click.STRING)
@click.pass_context
def activate_command(ctx, username):
	"""Activate a user account."""
	try:
		ctx.obj.user_manager.changeUserActivation(username, True)
		click.echo("User {} activated.".format(username))

		user = ctx.obj.user_manager.findUser(username)
		if user:
			click.echo("User created:")
			click.echo("\t{}".format(_user_to_line(user.asDict())))
	except UnknownUser:
		click.echo("User {} does not exist!".format(username), err=True)


@user.command(name="deactivate")
@click.argument("username", type=click.STRING)
@click.pass_context
def deactivate_command(ctx, username):
	"""Activate a user account."""
	try:
		ctx.obj.user_manager.changeUserActivation(username, False)
		click.echo("User {} activated.".format(username))

		user = ctx.obj.user_manager.findUser(username)
		if user:
			click.echo("User created:")
			click.echo("\t{}".format(_user_to_line(user.asDict())))
	except UnknownUser:
		click.echo("User {} does not exist!".format(username), err=True)


def _print_list(users):
	click.echo("{} users registered in the system:".format(len(users)))
	for user in sorted(users, key=lambda x: x.get("name")):
		click.echo("\t{}".format(_user_to_line(user)))


def _user_to_line(user):
	return "{} (active: {}, admin: {})".format(user.get("name"),
	                                           "yes" if user.get("active", False) else "no",
	                                           "yes" if user.get("admin", False) else "no")
