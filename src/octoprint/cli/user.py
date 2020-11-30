# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2019 The OctoPrint Project - Released under terms of the AGPLv3 License"


import logging

import click

from octoprint import init_settings
from octoprint.access.groups import FilebasedGroupManager
from octoprint.access.users import (
    CorruptUserStorage,
    FilebasedUserManager,
    UnknownUser,
    UserAlreadyExists,
)
from octoprint.cli import get_ctx_obj_option
from octoprint.util import get_class, sv

click.disable_unicode_literals_warning = True

# ~~ "octoprint user" commands


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
        logging.basicConfig(
            level=logging.DEBUG
            if get_ctx_obj_option(ctx, "verbosity", 0) > 0
            else logging.WARN
        )
        settings = init_settings(
            get_ctx_obj_option(ctx, "basedir", None),
            get_ctx_obj_option(ctx, "configfile", None),
        )

        group_manager_name = settings.get(["accessControl", "groupManager"])
        try:
            clazz = get_class(group_manager_name)
            group_manager = clazz()
        except AttributeError:
            click.echo(
                "Could not instantiate group manager {}, "
                "falling back to FilebasedGroupManager!".format(group_manager_name),
                err=True,
            )
            group_manager = FilebasedGroupManager()

        ctx.obj.group_manager = group_manager

        name = settings.get(["accessControl", "userManager"])
        try:
            clazz = get_class(name)
            user_manager = clazz(group_manager=group_manager, settings=settings)
        except CorruptUserStorage:
            raise
        except Exception:
            click.echo(
                "Could not instantiate user manager {}, falling back to FilebasedUserManager!".format(
                    name
                ),
                err=True,
            )
            user_manager = FilebasedUserManager(group_manager, settings=settings)

        ctx.obj.user_manager = user_manager

    except Exception:
        click.echo("Could not instantiate user manager", err=True)
        ctx.exit(-1)


@user.command(name="list")
@click.pass_context
def list_users_command(ctx):
    """Lists user information"""
    users = ctx.obj.user_manager.get_all_users()
    _print_list(users)


@user.command(name="add")
@click.argument("username", type=click.STRING, required=True)
@click.password_option("--password", "password", help="Password for the user")
@click.option("-g", "--group", "groups", multiple=True, help="Groups to set on the user")
@click.option(
    "-p",
    "--permission",
    "permissions",
    multiple=True,
    help="Individual permissions to set on the user",
)
@click.option(
    "--admin",
    "is_admin",
    type=click.BOOL,
    is_flag=True,
    default=False,
    help="Adds user to admin group",
)
@click.pass_context
def add_user_command(ctx, username, password, groups, permissions, is_admin):
    """Add a new user."""
    if not groups:
        groups = []

    if is_admin:
        groups.append(ctx.obj.group_manager.admin_group)

    try:
        ctx.obj.user_manager.add_user(
            username, password, groups=groups, permissions=permissions, active=True
        )

        user = ctx.obj.user_manager.find_user(username)
        if user:
            click.echo("User created:")
            click.echo("\t{}".format(_user_to_line(user.as_dict())))
    except UserAlreadyExists:
        click.echo(
            "A user with the name {} does already exist!".format(username), err=True
        )


@user.command(name="remove")
@click.argument("username", type=click.STRING)
@click.pass_context
def remove_user_command(ctx, username):
    """Remove an existing user."""
    confirm = click.prompt(
        "This is will irreversibly destroy the user account! Enter 'yes' to confirm",
        type=click.STRING,
    )

    if confirm.lower() == "yes":
        ctx.obj.user_manager.remove_user(username)
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
        ctx.obj.user_manager.change_user_password(username, password)
        click.echo("Password changed for user {}.".format(username))
    except UnknownUser:
        click.echo("User {} does not exist!".format(username), err=True)


@user.command(name="activate")
@click.argument("username", type=click.STRING)
@click.pass_context
def activate_command(ctx, username):
    """Activate a user account."""
    try:
        ctx.obj.user_manager.change_user_activation(username, True)
        click.echo("User {} activated.".format(username))

        user = ctx.obj.user_manager.find_user(username)
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
        ctx.obj.user_manager.change_user_activation(username, False)
        click.echo("User {} activated.".format(username))

        user = ctx.obj.user_manager.find_user(username)
        if user:
            click.echo("User created:")
            click.echo("\t{}".format(_user_to_line(user.asDict())))
    except UnknownUser:
        click.echo("User {} does not exist!".format(username), err=True)


def _print_list(users):
    click.echo("{} users registered in the system:".format(len(users)))
    for user in sorted(
        map(lambda x: x.as_dict(), users), key=lambda x: sv(x.get("name"))
    ):
        click.echo("\t{}".format(_user_to_line(user)))


def _user_to_line(user):
    return (
        "{name}"
        "\n\t\tactive: {active}"
        "\n\t\tgroups: {groups}"
        "\n\t\tpermissions: {permissions}".format(
            name=user.get("name"),
            active=user.get("active", "False"),
            groups=", ".join(user.get("groups", [])),
            permissions=", ".join(user.get("permissions", [])),
        )
    )
