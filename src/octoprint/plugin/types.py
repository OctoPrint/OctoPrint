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

	   The included template must be called ``<pluginname>_navbar.jinja2`` (e.g. ``myplugin_navbar.jinja2``) unless
	   overridden by the configuration supplied through ``get_template_config``.

	   The template will be already wrapped into the necessary structure, plugins just need to supply the pure content. The
	   wrapper structure will have all additional classes and styles applied as specified via the configuration supplied
	   through ``get_template_config``.

	Sidebar
	   The left side bar containing Connection, State and Files sections can be enriched with additional sections. Note
	   that with the current implementations, plugins will always be located *beneath* the existing sections.

	   The included template must be called ``<pluginname>_sidebar.jinja2`` (e.g. ``myplugin_sidebar.jinja2``) unless
	   overridden by the configuration supplied through ``get_template_config``.

	   The template will be already wrapped into the necessary structure, plugins just need to supply the pure content. The
	   wrapper divs for both the whole box as well as the content pane will have all additional classes and styles applied
	   as specified via the configuration supplied through ``get_template_config``.

	Tabs
	   The available tabs of the main part of the interface may be extended with additional tabs originating from within
	   plugins. Note that with the current implementation, plugins will always be located *to the right* of the existing
	   tabs.

	   The included template must be called ``<pluginname>_tab.jinja2`` (e.g. ``myplugin_tab.jinja2``) unless
	   overridden by the configuration supplied through ``get_template_config``.

	   The template will be already wrapped into the necessary structure, plugins just need to supply the pure content. The
	   wrapper div and the link in the navigation will have the additional classes and styles applied as specified via the
	   configuration supplied through ``get_template_config``.

	Settings
	   Plugins may inject a dialog into the existing settings view. Note that with the current implementations, plugins
	   will always be listed beneath the "Plugins" header in the settings link list, ordered alphabetically after
	   their displayed name.

	   The included template must be called ``<pluginname>_settings.jinja2`` (e.g. ``myplugin_settings.jinja2``) unless
	   overridden by the configuration supplied through ``get_template_config``.

	   The template will be already wrapped into the necessary structure, plugins just need to supply the pure content. The
	   wrapper div and the link in the navigation will have the additional classes and styles applied as defined via the
	   supplied configuration supplied through ``get_template_config``.

	Generic
	   Plugins may also inject arbitrary templates into the page of the web interface itself, e.g. in order to
	   add overlays or dialogs to be called from within the plugin's javascript code.

	.. figure:: ../images/template-plugin-types-main.png
	   :align: center
	   :alt: Template injection types in the main part of the interface

	   Template injection types in the main part of the interface

	.. figure:: ../images/template-plugin-types-settings.png
	   :align: center
	   :alt: Template injection types in the settings

	   Template injection types in the settings

	You can find an example for a simple plugin which injects navbar, sidebar, tab and settings content into the interface in
	`the "helloworld" plugin in OctoPrint's collection of plugin examples <https://github.com/OctoPrint/Plugin-Examples/tree/master/helloworld>`_.
	"""

	def get_template_configs(self):
		"""
		Allows configuration of injected navbar, sidebar, tab and settings templates. Should be a list containing one
		configuration object per template to inject. Each configuration object is represented by a dictionary with a mandatory key
		``type`` encoding the template type the configuration is targeting. Possible values here are ``navbar``, ``sidebar``,
		``tab``, ``settings`` and ``generic``.

		Further keys to be included in the dictionary depend on the type:

		``navbar`` type
		   .. figure:: ../images/template-plugin-type-navbar.png
		      :align: center
		      :alt: Structure of navbar plugins

		   Configures a navbar component to inject. The following keys are supported:

		   .. list-table::
		      :widths: 5 95

		      * - template
		        - Name of the template to inject, defaults to ``<pluginname>_navbar.jinja2``.
		      * - suffix
		        - Suffix to attach to the element ID of the injected template, will be ``_<index>`` if not provided and not
		          the first template of the type, with ``index`` counting from 1 and increasing for each template of the same
		          type.
		      * - custom_bindings
		        - A boolean value indicating whether the default view model should be bound to the navbar entry (``false``)
		          or if a custom binding will be used by the plugin (``true``, default).
		      * - data_bind
		        - Additional knockout data bindings to apply to the navbar entry, can be used to add further behaviour to
		          the container based on internal state if necessary.
		      * - classes
		        - Additional classes to apply to the navbar entry, as a list of individual classes
		          (e.g. ``classes=["myclass", "myotherclass"]``) which will be joined into the correct format by the template engine.
		      * - styles
		        - Additional CSS styles to apply to the navbar entry, as a list of individual declarations
		          (e.g. ``styles=["color: red", "display: block"]``) which will be joined into the correct format by the template
		          engine.

		``sidebar`` type
		   .. figure:: ../images/template-plugin-type-sidebar.png
		      :align: center
		      :alt: Structure of sidebar plugins

		   Configures a sidebar component to inject. The following keys are supported:

		   .. list-table::
		      :widths: 5 95

		      * - name
		        - The name of the sidebar entry, if not set the name of the plugin will be used.
		      * - icon
		        - Icon to use for the sidebar header, should be the name of a Font Awesome icon without the leading ``icon-`` part.
		      * - template
		        - Name of the template to inject, defaults to ``<pluginname>_sidebar.jinja2``.
		      * - template_header
		        - Additional template to include in the head section of the sidebar item. For an example of this, see the additional
		          options included in the "Files" section.
		      * - suffix
		        - Suffix to attach to the element ID of the injected template, will be ``_<index>`` if not provided and not
		          the first template of the type, with ``index`` counting from 1 and increasing for each template of the same
		          type.
		      * - custom_bindings
		        - A boolean value indicating whether the default view model should be bound to the sidebar container (``false``)
		          or if a custom binding will be used by the plugin (``true``, default).
		      * - data_bind
		        - Additional knockout data bindings to apply to the template container, can be used to add further behaviour to
		          the container based on internal state if necessary.
		      * - classes
		        - Additional classes to apply to both the wrapper around the sidebar box as well as the content pane itself, as a
		          list of individual classes (e.g. ``classes=["myclass", "myotherclass"]``) which will be joined into the correct
		          format by the template engine.
		      * - classes_wrapper
		        - Like ``classes`` but only applied to the whole wrapper around the sidebar box.
		      * - classes_content
		        - Like ``classes`` but only applied to the content pane itself.
		      * - styles
		        - Additional CSS styles to apply to both the wrapper around the sidebar box as well as the content pane itself,
		          as a list of individual declarations (e.g. ``styles=["color: red", "display: block"]``) which will be joined
		          into the correct format by the template engine.
		      * - styles_wrapper
		        - Like ``styles`` but only applied to the whole wrapper around the sidebar box.
		      * - styles_content
		        - Like ``styles`` but only applied to the content pane itself

		``tab`` type
		   .. figure:: ../images/template-plugin-type-tab.png
		      :align: center
		      :alt: Structure of tab plugins

		   Configures a tab component to inject. The value must be a dictionary, supported values are the following:

		   .. list-table::
		      :widths: 5 95

		      * - name
		        - The name under which to include the tab, if not set the name of the plugin will be used.
		      * - template
		        - Name of the template to inject, defaults to ``<pluginname>_tab.jinja2``.
		      * - suffix
		        - Suffix to attach to the element ID of the injected template, will be ``_<index>`` if not provided and not
		          the first template of the type, with ``index`` counting from 1 and increasing for each template of the same
		          type.
		      * - custom_bindings
		        - A boolean value indicating whether the default view model should be bound to the tab pane and link
		          in the navigation (``false``) or if a custom binding will be used by the plugin (``true``, default).
		      * - data_bind
		        - Additional knockout data bindings to apply to the template container, can be used to add further behaviour to
		          the container based on internal state if necessary.
		      * - classes
		        - Additional classes to apply to both the wrapper around the sidebar box as well as the content pane itself, as a
		          list of individual classes (e.g. ``classes=["myclass", "myotherclass"]``) which will be joined into the correct
		          format by the template engine.
		      * - classes_link
		        - Like ``classes`` but only applied to the link in the navigation.
		      * - classes_content
		        - Like ``classes`` but only applied to the content pane itself.
		      * - styles
		        - Additional CSS styles to apply to both the wrapper around the sidebar box as well as the content pane itself,
		          as a list of individual declarations (e.g. ``styles=["color: red", "display: block"]``) which will be joined
		          into the correct format by the template engine.
		      * - styles_link
		        - Like ``styles`` but only applied to the link in the navigation.
		      * - styles_content
		        - Like ``styles`` but only applied to the content pane itself.

		``settings`` type
		   .. figure:: ../images/template-plugin-type-settings.png
		      :align: center
		      :alt: Structure of settings plugins

		   Configures a settings component to inject. The value must be a dictionary, supported values are the following:

		   .. list-table::
		      :widths: 5 95

		      * - name
		        - The name under which to include the settings pane, if not set the name of the plugin will be used.
		      * - template
		        - Name of the template to inject, defaults to ``<pluginname>_settings.jinja2``.
		      * - suffix
		        - Suffix to attach to the element ID of the injected template, will be ``_<index>`` if not provided and not
		          the first template of the type, with ``index`` counting from 1 and increasing for each template of the same
		          type.
		      * - custom_bindings
		        - A boolean value indicating whether the default settings view model should be bound to the settings pane and link
		          in the navigation (``false``) or if a custom binding will be used by the plugin (``true``, default).
		      * - data_bind
		        - Additional knockout data bindings to apply to the template container, can be used to add further behaviour to
		          the container based on internal state if necessary.
		      * - classes
		        - Additional classes to apply to both the wrapper around the navigation link as well as the content pane itself, as a
		          list of individual classes (e.g. ``classes=["myclass", "myotherclass"]``) which will be joined into the correct
		          format by the template engine.
		      * - classes_link
		        - Like ``classes`` but only applied to the link in the navigation.
		      * - classes_content
		        - Like ``classes`` but only applied to the content pane itself.
		      * - styles
		        - Additional CSS styles to apply to both the wrapper around the navigation link as well as the content pane itself,
		          as a list of individual declarations (e.g. ``styles=["color: red", "display: block"]``) which will be joined
		          into the correct format by the template engine.
		      * - styles_link
		        - Like ``styles`` but only applied to the link in the navigation.
		      * - styles_content
		        - Like ``styles`` but only applied to the content pane itself

		``generic`` type
		   Configures a generic template to inject. The following keys are supported:

		   .. list-table::
		      :widths: 5 95

		      * - template
		        - Name of the template to inject, defaults to ``<pluginname>.jinja2``.

		.. note::

		   As already outlined above, each template type has a default template name (i.e. the default navbar template
		   of a plugin is called ``<pluginname>_navbar.jinja2``), which may be overridden using the template configuration.
		   If a plugin needs to include more than one template of a given type, it needs to provide an entry for each of
		   those, since the implicit default template will only be included automatically if no other templates of that
		   type are defined.

		:return: a list containing the configuration options for the plugin's injected templates
		"""
		return []

	def get_template_vars(self):
		"""
		Defines additional template variables to include into the template renderer.

		:return: a dictionary containing any additional template variables to include in the renderer
		"""
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

