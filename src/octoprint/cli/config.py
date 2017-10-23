# coding=utf-8
from __future__ import absolute_import, division, print_function

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import click
import logging

from octoprint import init_settings, FatalStartupError
from octoprint.cli import pass_octoprint_ctx, standard_options, bulk_options, get_ctx_obj_option

import yaml
import json
import pprint

def _to_settings_path(path):
	if not isinstance(path, (list, tuple)):
		path = filter(lambda x: x, map(lambda x: x.strip(), path.split(".")))
	return path

def _set_helper(settings, path, value, data_type=None):
	path = _to_settings_path(path)

	method = settings.set
	if data_type is not None:
		name = None
		if data_type == bool:
			name = "setBoolean"
		elif data_type == float:
			name = "setFloat"
		elif data_type == int:
			name = "setInt"

		if name is not None:
			method = getattr(settings, name)

	method(path, value)
	settings.save()

#~~ "octoprint config" commands

@click.group()
def config_commands():
	pass

@config_commands.group(name="config")
@click.pass_context
def config(ctx):
	"""Basic config manipulation."""
	logging.basicConfig(level=logging.DEBUG if get_ctx_obj_option(ctx, "verbosity", 0) > 0 else logging.WARN)
	try:
		ctx.obj.settings = init_settings(get_ctx_obj_option(ctx, "basedir", None), get_ctx_obj_option(ctx, "configfile", None))
	except FatalStartupError as e:
		click.echo(e.message, err=True)
		click.echo("There was a fatal error initializing the client.", err=True)
		ctx.exit(-1)


@config.command(name="set")
@standard_options(hidden=True)
@click.argument("path", type=click.STRING)
@click.argument("value", type=click.STRING)
@click.option("--bool", "as_bool", is_flag=True,
              help="Interpret value as bool")
@click.option("--float", "as_float", is_flag=True,
              help="Interpret value as float")
@click.option("--int", "as_int", is_flag=True,
              help="Interpret value as int")
@click.option("--json", "as_json", is_flag=True,
              help="Parse value from json")
@pass_octoprint_ctx
@click.pass_context
def set_command(ctx, path, value, as_bool, as_float, as_int, as_json):
	"""Sets a config path to the provided value."""
	if as_json:
		try:
			value = json.loads(value)
		except Exception as e:
			click.echo(e.message, err=True)
			ctx.exit(-1)

	data_type = None
	if as_bool:
		data_type = bool
	elif as_float:
		data_type = float
	elif as_int:
		data_type = int

	_set_helper(ctx.obj.settings, path, value, data_type=data_type)


@config.command(name="remove")
@standard_options(hidden=True)
@click.argument("path", type=click.STRING)
@click.pass_context
def remove_command(ctx, path):
	"""Removes a config path."""
	_set_helper(ctx.obj.settings, path, None)


@config.command(name="append_value")
@standard_options(hidden=True)
@click.argument("path", type=click.STRING)
@click.argument("value", type=click.STRING)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def append_value_command(ctx, path, value, as_json=False):
	"""Appends value to list behind config path."""
	path = _to_settings_path(path)

	if as_json:
		try:
			value = json.loads(value)
		except Exception as e:
			click.echo(e.message, err=True)
			ctx.exit(-1)

	current = ctx.obj.settings.get(path)
	if current is None:
		current = []
	if not isinstance(current, list):
		click.echo("Cannot append to non-list value at given path", err=True)
		ctx.exit(-1)

	current.append(value)
	_set_helper(ctx.obj.settings, path, current)


@config.command(name="insert_value")
@standard_options(hidden=True)
@click.argument("path", type=click.STRING)
@click.argument("index", type=click.INT)
@click.argument("value", type=click.STRING)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def insert_value_command(ctx, path, index, value, as_json=False):
	"""Inserts value at index of list behind config key."""
	path = _to_settings_path(path)

	if as_json:
		try:
			value = json.loads(value)
		except Exception as e:
			click.echo(e.message, err=True)
			ctx.exit(-1)

	current = ctx.obj.settings.get(path)
	if current is None:
		current = []
	if not isinstance(current, list):
		click.echo("Cannot insert into non-list value at given path", err=True)
		ctx.exit(-1)

	current.insert(index, value)
	_set_helper(ctx.obj.settings, path, current)


@config.command(name="remove_value")
@standard_options(hidden=True)
@click.argument("path", type=click.STRING)
@click.argument("value", type=click.STRING)
@click.option("--json", "as_json", is_flag=True)
@pass_octoprint_ctx
@click.pass_context
def remove_value_command(ctx, path, value, as_json=False):
	"""Removes value from list at config path."""
	path = _to_settings_path(path)

	if as_json:
		try:
			value = json.loads(value)
		except Exception as e:
			click.echo(e.message, err=True)
			ctx.exit(-1)

	current = ctx.obj.settings.get(path)
	if current is None:
		current = []
	if not isinstance(current, list):
		click.echo("Cannot remove value from non-list value at given path", err=True)
		ctx.exit(-1)

	if not value in current:
		click.echo("Value is not contained in list at given path")
		ctx.exit()

	current.remove(value)
	_set_helper(ctx.obj.settings, path, current)


@config.command(name="get")
@click.argument("path", type=click.STRING)
@click.option("--json", "as_json", is_flag=True,
              help="Output value formatted as JSON")
@click.option("--yaml", "as_yaml", is_flag=True,
              help="Output value formatted as YAML")
@click.option("--raw", "as_raw", is_flag=True,
              help="Output value as raw string representation")
@standard_options(hidden=True)
@click.pass_context
def get_command(ctx, path, as_json=False, as_yaml=False, as_raw=False):
	"""Retrieves value from config path."""
	path = _to_settings_path(path)
	value = ctx.obj.settings.get(path, merged=True)

	if as_json:
		output = json.dumps(value)
	elif as_yaml:
		output = yaml.safe_dump(value, default_flow_style=False, indent="    ", allow_unicode=True)
	elif as_raw:
		output = value
	else:
		output = pprint.pformat(value)

	click.echo(output)
