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
		Defines the folder where the plugin stores its static assets as defined in ``get_assets``. Override this if
		your plugin stores its assets at some other place than the ``static`` sub folder in the plugin base directory.

		:return: the absolute path to the folder where the plugin stores its static assets
		"""
		import os
		return os.path.join(self._basefolder, "static")

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
		return dict()


class TemplatePlugin(Plugin):
	"""
	Using the ``TemplatePlugin`` mixin plugins may inject their own components into the OctoPrint web interface.

	Currently OctoPrint supports the following types of injections:

	Navbar
	   The right part of the navigation bar located at the top of the UI can be enriched with additional links. Note that
	   with the current implementation, plugins will always be located *to the left* of the existing links.
	Sidebar
	   The left side bar containing Connection, State and Files sections can be enriched with additional sections. Note
	   that with the current implementations, plugins will always be located *beneath* the existing sections.
	Tabs
	   The available tabs of the main part of the interface may be extended with additional tabs originating from within
	   plugins. Note that with the current implementation, plugins will always be located *to the right* of the existing
	   tabs.
	Settings
	   Plugins may inject a dialog into the existing settings view. Note that with the current implementations, plugins
	   will always be listed beneath the "Plugins" header in the settings link list, ordered alphabetically after
	   their displayed name.

	.. figure:: ../images/template-plugin-types-main.png
	   :align: center
	   :alt: Template injection types in the main part of the interface

	   Template injection types in the main part of the interface

	.. figure:: ../images/template-plugin-types-settings.png
	   :align: center
	   :alt: Template injection types in the settings

	   Template injection types in the settings

	Which components a plugin supplies is controlled by a number of special template variables returned by the overridden
	``get_template_vars`` method. The following special keys are supported:

	_settings
	   Configures the settings component to inject. The value must be a dictionary, supported values are the following:

	   name
	      The name under which to include the settings pane, will be visible in the navigation tree on the left of the
	      settings dialog
	   custom_bindings
	      A boolean value indicating whether the default settings view model should be bound to the settings pane (``false``, default)
	      or if a custom binding will be used by the plugin (``true``)
	   data_bind
	      Additional knockout data bindings to apply to the template container, can be used to add further behaviour to
	      the container based on internal state if necessary. Note that if you include this and set ``custom_bindings``
	      to ``True``, you need to also supply ``allowBindings: true`` as part of your custom data binding, otherwise
	      it won't work.

	   The included settings dialog template file must be called ``<plugin name>_settings.jinja2`` (e.g. ``myplugin_settings.jinja2``).
	   The template will be already included in the necessary wrapper divs, you just need to supply the pure content.
	_tab
	   Configures the tab component to inject. The value must be a dictionary, supported values are the following:

	   name
	      The name under which to include the tab, will be visible in the list of tabs on the top of the main view
	   data_bind
	      Additional knockout data bindings to apply to the template container, can be used to add further behaviour to
	      the container based on internal state if necessary. Note that if you include this and set ``custom_bindings``
	      to ``True``, you need to also supply ``allowBindings: true`` as part of your custom data binding, otherwise
	      it won't work.

	   The template included into the tab pane section must be called ``<plugin name>_tab.jinja2`` (e.g. ``myplugin_tab.jinja2``).
	   The template will be already included in the necessary wrapper divs, you just need to supply the pure content.
	_sidebar
	   Configures the sidebar component to inject. The value must be a dictionary, supported values are the following:

	   name
	      The name of the sidebar entry
	   icon
	      Icon to use for the sidebar header, should be the name of a Font Awesome icon without the leading ``icon-`` part
	   header_addon
	      Additional template to include in the head section of the sidebar item. For an example of this, see the additional
	      options included in the "Files" section
	   data_bind
	      Additional knockout data bindings to apply to the template container, can be used to add further behaviour to
	      the container based on internal state if necessary. Note that if you include this and set ``custom_bindings``
	      to ``True``, you need to also supply ``allowBindings: true`` as part of your custom data binding, otherwise
	      it won't work.

	   The template included into the sidebar section must be called ``<plugin name>_sidebar.jinja2`` (e.g. ``myplugin_sidebar.jinja2``).
	   The template will be already included in the necessary wrapper divs, you just need to supply the pure content.
	_navbar
	   Configures the navbar component to inject. The value must be an empty dictionary.

	   The template included into the sidebar section must be called ``<plugin name>_navbar.jinja2``

	The following is an example for a simple plugin which injects all four types of templates into the interfaces:

	``helloworld/__init__.py``

	.. code-block:: python

	   import octoprint.plugin

	   class HelloWorldPlugin(octoprint.plugin.TemplatePlugin, octoprint.plugin.AssetPlugin):
	       def get_template_vars(self):
	           return dict(
	               _settings=dict(name="Hello World"),
	               _tab=dict(name="Hello World", custom_bindings=True, data_bind="allowBindings: true, visible: self.loginState.isUser()"),
	               _sidebar=dict(name="Hello World", icon="gear"),
	               _navbar=dict()
	           )

	       def get_assets(self):
	           return dict(
	               js=["js/helloworld.js"]
	           )

	   __plugin_name__ = "Hello World"
	   __plugin_version__ = "1.0"
	   __plugin_implementations__ = [HelloWorldPlugin()]

	``helloworld/templates/helloworld_settings.jinja2``

	.. code-block:: html+jinja

	   <h1>Hello World!</h1>

	   This is a custom settings pane.

	``helloworld/templates/helloworld_tab.jinja2``

	.. code-block:: html+jinja

	   <h1>Hello World!</h1>

	   This is a custom tab.

	``helloworld/templates/helloworld_sidebar.jinja2``

	.. code-block:: html+jinja

	   Hello World! This is a custom side bar.

	``helloworld/templates/helloworld_navbar.jinja2``

	.. code-block:: html+jinja

	   <li>
	     <a class="pull-right" href="http://www.example.com"><i class="icon-gear"></i> {{ _('Hello World!') }}</a>
	   </li>

	"""

	def get_template_vars(self):
		return dict()

	def get_template_folder(self):
		"""
		Defines the folder where the plugin stores its templates. Override this if your plugin stores its templates at
		some other place than the ``templates`` sub folder in the plugin base directory.

		:return: the absolute path to the folder where the plugin stores its jinja2 templates
		"""
		import os
		return os.path.join(self._basefolder, "templates")


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

	def is_blueprint_protected(self):
		"""
		Whether the blueprint is supposed to be protected by API key (the default) or not.
		"""

		return True


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

	def do_slice(self, model_path, printer_profile, machinecode_path=None, profile_path=None, on_progress=None, on_progress_args=None, on_progress_kwargs=None):
		pass

	def cancel_slicing(self, machinecode_path):
		pass


class ProgressPlugin(Plugin):
	"""
	Via the ``ProgressPlugin`` mixing plugins can let themselves be called upon progress in print jobs or slicing jobs,
	limited to minimally 1% steps.
	"""

	def on_print_progress(self, storage, path, progress):
		"""
		Called by OctoPrint on minimally 1% increments during a running print job.

		:param location string: Location of the file
		:param path string:     Path of the file
		:param progress int:    Current progress as a value between 0 and 100
		"""
		pass

	def on_slicing_progress(self, slicer, source_location, source_path, destination_location, destination_path, progress):
		"""
		Called by OctoPrint on minimally 1% increments during a running slicing job.

		:param slicer string:               Key of the slicer reporting the progress
		:param source_location string:      Location of the source file
		:param source_path string:          Path of the source file
		:param destination_location string: Location the destination file
		:param destination_path string:     Path of the destination file
		:param progress int:                Current progress as a value between 0 and 100
		"""
		pass


class AppPlugin(Plugin):
	def get_additional_apps(self):
		return []

