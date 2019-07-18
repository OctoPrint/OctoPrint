# coding=utf-8
from __future__ import absolute_import, division, print_function

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2019 The OctoPrint Project - Released under terms of the AGPLv3 License"


import click
import logging

from octoprint import init_settings
from octoprint.cli import get_ctx_obj_option
from octoprint.users import FilebasedUserManager, UnknownUser

#~~ "octoprint user" commands


@click.group()
def user_commands():
	pass


@user_commands.group(name="user")
@click.pass_context
def user(ctx):
	"""User account management"""
	try:
		logging.basicConfig(level=logging.DEBUG if get_ctx_obj_option(ctx, "verbosity", 0) > 0 else logging.WARN)
		settingz = init_settings(get_ctx_obj_option(ctx, "basedir", None), get_ctx_obj_option(ctx, "configfile", None))
		ctx.obj.users = FilebasedUserManager(settingz=settingz)
	except Exception:
		click.echo("Could not instantiate user manager")
		return


@user.command(name="add_user")
@click.argument("username", type=click.STRING, required=True)
@click.password_option("--password", "password", help="Password for user")
@click.option("--is-admin", "is_admin", type=click.BOOL, default=False,
			  help="Sets user role as admin")
@click.pass_context
def add_user_command(ctx, username, password, is_admin):
	"""Adds new user account"""
	ctx.obj.users.addUser(
		username,
		password,
		roles=("admin" if is_admin else "user"),
		active=True
	)


@user.command(name="remove_user")
@click.argument("username", type=click.STRING)
@click.pass_context
def remove_user_command(ctx, username):
	"""Removes user account"""
	confirm = click.prompt(
		"This is will irreversibly destroy the user account! Enter 'yes' to confirm",
		type=click.STRING)

	if confirm == 'yes':
		ctx.obj.users.removeUser(username)
	else:
		click.echo("User NOT removed")


@user.command(name="change_password")
@click.argument("username", type=click.STRING)
@click.password_option("--password", "password", help="New password for user")
@click.pass_context
def change_password_command(ctx, username, password):
	"""Changes an existing user password"""
	try:
		ctx.obj.users.changeUserPassword(username, password)
	except UnknownUser:
		click.echo("User does not exist!")

