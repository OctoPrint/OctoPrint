# coding=utf-8
from __future__ import absolute_import, division, print_function

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

import click
import json

import octoprint_client

from octoprint.cli import get_ctx_obj_option
from octoprint import init_settings, FatalStartupError


class JsonStringParamType(click.ParamType):
	name = "json"

	def convert(self, value, param, ctx):
		try:
			return json.loads(value)
		except:
			self.fail("%s is not a valid json string" % value, param, ctx)


@click.group()
def client_commands():
	pass


@client_commands.group("client", context_settings=dict(ignore_unknown_options=True))
@click.option("--host", "-h", type=click.STRING)
@click.option("--port", "-p", type=click.INT)
@click.option("--httpuser", type=click.STRING)
@click.option("--httppass", type=click.STRING)
@click.option("--https", is_flag=True)
@click.option("--prefix", type=click.STRING)
@click.pass_context
def client(ctx, host, port, httpuser, httppass, https, prefix):
	"""Basic API client."""
	try:
		ctx.obj.settings = init_settings(get_ctx_obj_option(ctx, "basedir", None), get_ctx_obj_option(ctx, "configfile", None))
		octoprint_client.init_client(ctx.obj.settings, https=https, httpuser=httpuser, httppass=httppass, host=host, port=port, prefix=prefix)
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
def get(path):
	"""Performs a GET request against the specified server path."""
	r = octoprint_client.get(path)
	log_response(r)


@client.command("post_json")
@click.argument("path")
@click.argument("data", type=JsonStringParamType())
def post_json(path, data):
	"""POSTs JSON data to the specified server path."""
	r = octoprint_client.post_json(path, data)
	log_response(r)


@client.command("patch_json")
@click.argument("path")
@click.argument("data", type=JsonStringParamType())
def patch_json(path, data):
	"""PATCHes JSON data to the specified server path."""
	r = octoprint_client.patch(path, data, encoding="json")
	log_response(r)


@client.command("post_from_file")
@click.argument("path")
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False, resolve_path=True))
@click.option("--json", is_flag=True)
@click.option("--yaml", is_flag=True)
def post_from_file(path, file_path, json_flag, yaml_flag):
	"""POSTs JSON data to the specified server path."""
	if json_flag or yaml_flag:
		if json_flag:
			with open(file_path, "rb") as fp:
				data = json.load(fp)
		else:
			import yaml
			with open(file_path, "rb") as fp:
				data = yaml.safe_load(fp)

		r = octoprint_client.post_json(path, data)
	else:
		with open(file_path, "rb") as fp:
			data = fp.read()

		r = octoprint_client.post(path, data)

	log_response(r)


@client.command("command")
@click.argument("path")
@click.argument("command")
@click.option("--str", "-s", "str_params", multiple=True, nargs=2, type=click.Tuple([unicode, unicode]))
@click.option("--int", "-i", "int_params", multiple=True, nargs=2, type=click.Tuple([unicode, int]))
@click.option("--float", "-f", "float_params", multiple=True, nargs=2, type=click.Tuple([unicode, float]))
@click.option("--bool", "-b", "bool_params", multiple=True, nargs=2, type=click.Tuple([unicode, bool]))
def command(path, command, str_params, int_params, float_params, bool_params):
	"""Sends a JSON command to the specified server path."""
	data = dict()
	params = str_params + int_params + float_params + bool_params
	for param in params:
		data[param[0]] = param[1]
	r = octoprint_client.post_command(path, command, additional=data)
	log_response(r, body=False)


@client.command("upload")
@click.argument("path")
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False, resolve_path=True))
@click.option("--parameter", "-P", "params", multiple=True, nargs=2, type=click.Tuple([unicode, unicode]))
@click.option("--file-name", type=click.STRING)
@click.option("--content-type", type=click.STRING)
def upload(path, file_path, params, file_name, content_type):
	"""Uploads the specified file to the specified server path."""
	data = dict()
	for param in params:
		data[param[0]] = param[1]

	r = octoprint_client.upload(path, file_path, additional=data, file_name=file_name, content_type=content_type)
	log_response(r)


@client.command("delete")
@click.argument("path")
def delete(path):
	"""Sends a DELETE request to the specified server path."""
	r = octoprint_client.delete(path)
	log_response(r)


@client.command("listen")
def listen():
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

	socket = octoprint_client.connect_socket(on_connect=on_connect,
	                                         on_close=on_close,
	                                         on_error=on_error,
	                                         on_heartbeat=on_heartbeat,
	                                         on_message=on_message)

	click.echo(">>> Waiting for client to exit")
	try:
		socket.wait()
	finally:
		click.echo(">>> Goodbye...")
