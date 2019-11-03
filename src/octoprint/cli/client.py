# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

import click
click.disable_unicode_literals_warning = True

import io
import json

import octoprint_client

from octoprint.cli import get_ctx_obj_option, bulk_options
from octoprint import init_settings, FatalStartupError

from past.builtins import unicode

class JsonStringParamType(click.ParamType):
	name = "json"

	def convert(self, value, param, ctx):
		try:
			return json.loads(value)
		except Exception:
			self.fail("%s is not a valid json string" % value, param, ctx)


def create_client(settings=None, apikey=None, host=None, port=None, httpuser=None, httppass=None, https=False, prefix=None):
	assert(host is not None or settings is not None)
	assert(port is not None or settings is not None)
	assert(apikey is not None or settings is not None)

	if not host:
		host = settings.get(["server", "host"])
		host = host if host != "0.0.0.0" else "127.0.0.1"
	if not port:
		port = settings.getInt(["server", "port"])

	if not apikey:
		apikey = settings.get(["api", "key"])

	baseurl = octoprint_client.build_base_url(https=https,
	                                          httpuser=httpuser,
	                                          httppass=httppass,
	                                          host=host,
	                                          port=port,
	                                          prefix=prefix)

	return octoprint_client.Client(baseurl, apikey)


client_options = bulk_options([
	click.option("--apikey", "-a", type=click.STRING),
	click.option("--host", "-h", type=click.STRING),
	click.option("--port", "-p", type=click.INT),
	click.option("--httpuser", type=click.STRING),
	click.option("--httppass", type=click.STRING),
	click.option("--https", is_flag=True),
	click.option("--prefix", type=click.STRING)
])
"""Common options to configure an API client."""


@click.group()
def client_commands():
	pass


@client_commands.group("client", context_settings=dict(ignore_unknown_options=True))
@client_options
@click.pass_context
def client(ctx, apikey, host, port, httpuser, httppass, https, prefix):
	"""Basic API client."""
	try:
		settings = None
		if not host or not port or not apikey:
			settings = init_settings(get_ctx_obj_option(ctx, "basedir", None), get_ctx_obj_option(ctx, "configfile", None))

		ctx.obj.client = create_client(settings=settings,
		                               apikey=apikey,
		                               host=host,
		                               port=port,
		                               httpuser=httpuser,
		                               httppass=httppass,
		                               https=https,
		                               prefix=prefix)

	except FatalStartupError as e:
		click.echo(e.message, err=True)
		click.echo("There was a fatal error initializing the client.", err=True)
		ctx.exit(-1)


def log_response(response, status_code=True, body=True, headers=False):
	if status_code:
		click.echo("Status Code: {}".format(response.status_code))
	if headers:
		for header, value in response.headers.items():
			click.echo("{}: {}".format(header, value))
		click.echo()
	if body:
		click.echo(response.text)


@client.command("get")
@click.argument("path")
@click.option("--timeout", type=float, default=None)
@click.pass_context
def get(ctx, path, timeout):
	"""Performs a GET request against the specified server path."""
	r = ctx.obj.client.get(path, timeout=timeout)
	log_response(r)


@client.command("post_json")
@click.argument("path")
@click.argument("data", type=JsonStringParamType())
@click.option("--timeout", type=float, default=None)
@click.pass_context
def post_json(ctx, path, data, timeout):
	"""POSTs JSON data to the specified server path."""
	r = ctx.obj.client.post_json(path, data, timeout=timeout)
	log_response(r)


@client.command("patch_json")
@click.argument("path")
@click.argument("data", type=JsonStringParamType())
@click.option("--timeout", type=float, default=None, help="Request timeout in seconds")
@click.pass_context
def patch_json(ctx, path, data, timeout):
	"""PATCHes JSON data to the specified server path."""
	r = ctx.obj.client.patch(path, data, encoding="json", timeout=timeout)
	log_response(r)


@client.command("post_from_file")
@click.argument("path")
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False, resolve_path=True))
@click.option("--json", is_flag=True)
@click.option("--yaml", is_flag=True)
@click.option("--timeout", type=float, default=None, help="Request timeout in seconds")
@click.pass_context
def post_from_file(ctx, path, file_path, json_flag, yaml_flag, timeout):
	"""POSTs JSON data to the specified server path, taking the data from the specified file."""
	if json_flag or yaml_flag:
		if json_flag:
			with io.open(file_path, 'rt') as fp:
				data = json.load(fp)
		else:
			import yaml
			with io.open(file_path, 'rt') as fp:
				data = yaml.safe_load(fp)

		r = ctx.obj.client.post_json(path, data, timeout=timeout)
	else:
		with io.open(file_path, 'rb') as fp:
			data = fp.read()

		r = ctx.obj.client.post(path, data, timeout=timeout)

	log_response(r)


@client.command("command")
@click.argument("path")
@click.argument("command")
@click.option("--str", "-s", "str_params", multiple=True, nargs=2, type=click.Tuple([unicode, unicode]))
@click.option("--int", "-i", "int_params", multiple=True, nargs=2, type=click.Tuple([unicode, int]))
@click.option("--float", "-f", "float_params", multiple=True, nargs=2, type=click.Tuple([unicode, float]))
@click.option("--bool", "-b", "bool_params", multiple=True, nargs=2, type=click.Tuple([unicode, bool]))
@click.option("--timeout", type=float, default=None, help="Request timeout in seconds")
@click.pass_context
def command(ctx, path, command, str_params, int_params, float_params, bool_params, timeout):
	"""Sends a JSON command to the specified server path."""
	data = dict()
	params = str_params + int_params + float_params + bool_params
	for param in params:
		data[param[0]] = param[1]
	r = ctx.obj.client.post_command(path, command, additional=data, timeout=timeout)
	log_response(r, body=False)


@client.command("upload")
@click.argument("path")
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False, resolve_path=True))
@click.option("--parameter", "-P", "params", multiple=True, nargs=2, type=click.Tuple([unicode, unicode]))
@click.option("--file-name", type=click.STRING)
@click.option("--content-type", type=click.STRING)
@click.option("--timeout", type=float, default=None, help="Request timeout in seconds")
@click.pass_context
def upload(ctx, path, file_path, params, file_name, content_type, timeout):
	"""Uploads the specified file to the specified server path."""
	data = dict()
	for param in params:
		data[param[0]] = param[1]

	r = ctx.obj.client.upload(path, file_path,
	                          additional=data, file_name=file_name, content_type=content_type, timeout=timeout)
	log_response(r)


@client.command("delete")
@click.argument("path")
@click.option("--timeout", type=float, default=None, help="Request timeout in seconds")
@click.pass_context
def delete(ctx, path, timeout):
	"""Sends a DELETE request to the specified server path."""
	r = ctx.obj.client.delete(path, timeout=timeout)
	log_response(r)


@client.command("listen")
@click.pass_context
def listen(ctx):
	def on_connect(ws):
		click.echo(">>> Connected!")

	def on_close(ws):
		click.echo(">>> Connection closed!")

	def on_error(ws, error):
		click.echo("!!! Error: {}".format(error))

	def on_heartbeat(ws):
		click.echo("<3")

	def on_message(ws, message_type, message_payload):
		click.echo("Message: {}, Payload: {}".format(message_type, json.dumps(message_payload)))

	socket = ctx.obj.client.create_socket(on_connect=on_connect,
	                                      on_close=on_close,
	                                      on_error=on_error,
	                                      on_heartbeat=on_heartbeat,
	                                      on_message=on_message)

	click.echo(">>> Waiting for client to exit")
	try:
		socket.wait()
	finally:
		click.echo(">>> Goodbye...")
