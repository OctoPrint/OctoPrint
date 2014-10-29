# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


from .core import Plugin


class StartupPlugin(Plugin):
	"""
	The ``StartupPlugin`` allows hooking into the startup of OctoPrint. It can be used to start up additional services
	on or just after the startup of the server.
	"""

	def on_startup(self, host, port):
		"""
		Called just before the server is actually launched. Plugins get supplied with the ``host`` and ``port`` the server
		will listen on. Note that the ``host`` may be ``0.0.0.0`` if it will listen on all interfaces, so you can't just
		blindly use this for constructing publicly reachable URLs. Also note that when this method is called, the server
		is not actually up yet and none of your plugin's APIs or blueprints will be reachable yet. If you need to be
		externally reachable, use ``on_after_startup`` instead or additionally.

		:param host: the host the server will listen on, may be ``0.0.0.0``
		:param port: the port the server will listen on
		"""

		pass

	def on_after_startup(self):
		"""
		Called just after launch of the server, so when the listen loop is actually running already.
		"""

		pass


class ShutdownPlugin(Plugin):
	"""
	The ``ShutdownPlugin`` allows hooking into the shutdown of OctoPrint. It's usually used in conjunction with the
	``StartupPlugin`` mixin, to cleanly shut down additional services again that where started by the ``StartupPlugin``
	part of the plugin.
	"""

	def on_shutdown(self):
		"""
		Called upon the imminent shutdown of OctoPrint.
		"""
		pass


class AssetPlugin(Plugin):
	"""
	The ``AssetPlugin`` mixin allows plugins to define additional static assets such as Javascript or CSS files to
	be automatically embedded into the pages delivered by the server to be used within the client sided part of
	the plugin.

	A typical usage of the ``AssetPlugin`` functionality is to embed a custom view model to be used on the settings page
	of a ``SettingsPlugin``.
	"""

	def get_asset_folder(self):
		"""
		Defines the folder where the plugin stores its static assets as defined in ``get_assets``. Usually an
		implementation such as

		.. code-block:: python

		   def get_asset_folder(self):
		       import os
		       return os.path.join(os.path.dirname(os.path.realpath(__file__)), "static")

		should be sufficient here. This way, assets can be put into a sub folder ``static`` in the plugin directory.

		:return: the absolute path to the folder where the plugin stores its static assets
		"""
		return None

	def get_assets(self):
		"""
		Defines the static assets the plugin offers. The following asset types are recognized and automatically
		imported at the appropriate places to be available:

		js
		   Javascript files, such as additional view models
		css
		   CSS files with additional styles, will be embedded into delivered pages when not running in LESS mode.
		less
		   LESS files with additional styles, will be embedded into delivered pages when running in LESS mode.

		The expected format to be returned is a dictionary mapping one or more of these keys to a list of files of that
		type, the files being represented as relative paths from the asset folder as defined via ``get_asset_folder``.
		Example:

		.. code-block:: python

		   def get_assets(self):
		       return dict(
		           js=['js/my_file.js', 'js/my_other_file.js'],
		           css=['css/my_styles.css'],
		           less=['less/my_styles.less']
		        )

		The assets will be made available by OctoPrint under the URL ``/plugin_assets/<plugin name>/<path>``, with
		``plugin_name`` being the plugin's name and ``path`` being the path as defined in the asset dictionary.

		:return: a dictionary describing the static assets to publish for the plugin
		"""
		return []


class TemplatePlugin(Plugin):
	def get_template_vars(self):
		return dict()

	def get_template_folder(self):
		return None


class SimpleApiPlugin(Plugin):
	def get_api_commands(self):
		return None

	def on_api_command(self, command, data):
		return None

	def on_api_get(self, request):
		return None


class BlueprintPlugin(Plugin):
	"""
	The ``BlueprintPlugin`` mixin allows plugins to define their own full fledged endpoints for whatever purpose,
	be it a more sophisticated API than what is possible via the ``SimpleApiPlugin`` or a custom web frontend.

	The mechanism at work here is `Flask's <http://flask.pocoo.org/>`_ own `Blueprint mechanism <http://flask.pocoo.org/docs/0.10/blueprints/>`_.

	Your plugin should define a blueprint like this:

	.. code-block:: python

	   template_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), "templates")
	   blueprint = flask.Blueprint("plugin.myplugin", __name__, template_folder=template_folder)

	Use your blueprint just like any other Flask blueprint for defining your own endpoints, e.g.

	.. code-block:: python

	   @blueprint.route("/echo", methods=["GET"])
	   def myEcho():
	       if not "text" in flask.request.values:
	           return flask.make_response("Expected a text to echo back.", 400)
	       return flask.request.values["text"]

	Your blueprint will be published by OctoPrint under the URL ``/plugin/<pluginname>/``, so the above example
	would be reachable under ``/plugin/myplugin/echo`` (given that you named your plugin "myplugin"). You'll be able
	to create URLs via ``url_for`` under the prefix that you've chosen when constructing your blueprint, ``plugin.myplugin``
	in the above example:

	.. code-block:: python

	   flask.url_for("plugin.myplugin.echo") # will return "/plugin/myplugin/echo"

	OctoPrint Blueprint plugins should always follow the naming scheme ``plugin.<plugin name>`` here
	to avoid conflicts.
	"""

	def get_blueprint(self):
		"""
		Retrieves the blueprint as defined by your plugin.

		:return: the blueprint ready to be registered with Flask
		"""

		return None


class SettingsPlugin(Plugin):
	def on_settings_load(self):
		return None

	def on_settings_save(self, data):
		pass


class EventHandlerPlugin(Plugin):
	def on_event(self, event, payload):
		pass


class SlicerPlugin(Plugin):
	def is_slicer_configured(self):
		return False

	def get_slicer_properties(self):
		return dict(
			type=None,
			name=None,
			same_device=True,
			progress_report=False
		)

	def get_slicer_profile_options(self):
		return None

	def get_slicer_profile(self, path):
		return None

	def get_slicer_default_profile(self):
		return None

	def save_slicer_profile(self, path, profile, allow_overwrite=True, overrides=None):
		pass

	def do_slice(self, model_path, machinecode_path=None, profile_path=None, on_progress=None, on_progress_args=None, on_progress_kwargs=None):
		pass

	def cancel_slicing(self, machinecode_path):
		pass


