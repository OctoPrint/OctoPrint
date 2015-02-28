# coding=utf-8
"""
This module bundles all of OctoPrint's supported plugin implementation types as well as their common parent
class, :class:`OctoPrintPlugin`.

Please note that the plugin implementation types are documented in the section
:ref:`Available plugin mixins <sec-plugins-mixins>`.

.. autoclass: OctoPrintPlugin

"""

from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


from .core import Plugin


class OctoPrintPlugin(Plugin):
	"""
	.. attribute:: _plugin_manager

	.. attribute:: _printer_profile_manager

	.. attribute:: _event_bus

	.. attribute:: _analysis_queue

	.. attribute:: _slicing_manager

	.. attribute:: _file_manager

	.. attribute:: _printer

	.. attribute:: _app_session_manager
	"""

	pass


class StartupPlugin(OctoPrintPlugin):
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
		externally reachable, use :func:`on_after_startup` instead or additionally.

		:param string host: the host the server will listen on, may be ``0.0.0.0``
		:param int port:    the port the server will listen on
		"""

		pass

	def on_after_startup(self):
		"""
		Called just after launch of the server, so when the listen loop is actually running already.
		"""

		pass


class ShutdownPlugin(OctoPrintPlugin):
	"""
	The ``ShutdownPlugin`` allows hooking into the shutdown of OctoPrint. It's usually used in conjunction with the
	:class:`StartupPlugin` mixin, to cleanly shut down additional services again that where started by the :class:`StartupPlugin`
	part of the plugin.
	"""

	def on_shutdown(self):
		"""
		Called upon the imminent shutdown of OctoPrint.
		"""
		pass


class AssetPlugin(OctoPrintPlugin):
	"""
	The ``AssetPlugin`` mixin allows plugins to define additional static assets such as Javascript or CSS files to
	be automatically embedded into the pages delivered by the server to be used within the client sided part of
	the plugin.

	A typical usage of the ``AssetPlugin`` functionality is to embed a custom view model to be used by templates injected
	through a :class:`TemplatePlugin`.
	"""

	def get_asset_folder(self):
		"""
		Defines the folder where the plugin stores its static assets as defined in :func:`get_assets`. Override this if
		your plugin stores its assets at some other place than the ``static`` sub folder in the plugin base directory.

		:return string: the absolute path to the folder where the plugin stores its static assets
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
		type, the files being represented as relative paths from the asset folder as defined via :func:`get_asset_folder`.
		Example:

		.. code-block:: python

		   def get_assets(self):
		       return dict(
		           js=['js/my_file.js', 'js/my_other_file.js'],
		           css=['css/my_styles.css'],
		           less=['less/my_styles.less']
		        )

		The assets will be made available by OctoPrint under the URL ``/plugin_assets/<plugin identifier>/<path>``, with
		``plugin identifier`` being the plugin's identifier and ``path`` being the path as defined in the asset dictionary.

		:return dict: a dictionary describing the static assets to publish for the plugin
		"""
		return dict()


class TemplatePlugin(OctoPrintPlugin):
	"""
	Using the ``TemplatePlugin`` mixin plugins may inject their own components into the OctoPrint web interface.

	Currently OctoPrint supports the following types of injections:

	Navbar
	   The right part of the navigation bar located at the top of the UI can be enriched with additional links. Note that
	   with the current implementation, plugins will always be located *to the left* of the existing links.

	   The included template must be called ``<pluginname>_navbar.jinja2`` (e.g. ``myplugin_navbar.jinja2``) unless
	   overridden by the configuration supplied through :func:`get_template_configs`.

	   The template will be already wrapped into the necessary structure, plugins just need to supply the pure content. The
	   wrapper structure will have all additional classes and styles applied as specified via the configuration supplied
	   through :func:`get_template_configs`.

	Sidebar
	   The left side bar containing Connection, State and Files sections can be enriched with additional sections. Note
	   that with the current implementations, plugins will always be located *beneath* the existing sections.

	   The included template must be called ``<pluginname>_sidebar.jinja2`` (e.g. ``myplugin_sidebar.jinja2``) unless
	   overridden by the configuration supplied through :func:`get_template_configs`.

	   The template will be already wrapped into the necessary structure, plugins just need to supply the pure content. The
	   wrapper divs for both the whole box as well as the content pane will have all additional classes and styles applied
	   as specified via the configuration supplied through :func:`get_template_configs`.

	Tabs
	   The available tabs of the main part of the interface may be extended with additional tabs originating from within
	   plugins. Note that with the current implementation, plugins will always be located *to the right* of the existing
	   tabs.

	   The included template must be called ``<pluginname>_tab.jinja2`` (e.g. ``myplugin_tab.jinja2``) unless
	   overridden by the configuration supplied through :func:`get_template_configs`.

	   The template will be already wrapped into the necessary structure, plugins just need to supply the pure content. The
	   wrapper div and the link in the navigation will have the additional classes and styles applied as specified via the
	   configuration supplied through :func:`get_template_configs`.

	Settings
	   Plugins may inject a dialog into the existing settings view. Note that with the current implementations, plugins
	   will always be listed beneath the "Plugins" header in the settings link list, ordered alphabetically after
	   their displayed name.

	   The included template must be called ``<pluginname>_settings.jinja2`` (e.g. ``myplugin_settings.jinja2``) unless
	   overridden by the configuration supplied through :func:`get_template_configs`.

	   The template will be already wrapped into the necessary structure, plugins just need to supply the pure content. The
	   wrapper div and the link in the navigation will have the additional classes and styles applied as defined via the
	   supplied configuration supplied through :func:`get_template_configs`.

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
		      * - div
		        - Id for the div containing the component. If not provided, defaults to ``plugin_<pluginname>`` plus
		          the suffix if provided or required.
		      * - replaces
		        - Id of navbar component this one replaces, might be either one of the core components or a component
		          provided by another plugin. See :ref:`this section <sec-plugins-templates>` for more on replacing template components.
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
		      * - div
		        - Id for the div containing the component. If not provided, defaults to ``plugin_<pluginname>`` plus
		          the suffix if provided or required.
		      * - replaces
		        - Id of sidebar component this one replaces, might be either one of the core components or a component
		          provided by another plugin. See :ref:`this section <sec-plugins-templates>` for more on replacing template components.
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
		      * - div
		        - Id for the div containing the component. If not provided, defaults to ``plugin_<pluginname>`` plus
		          the suffix if provided or required.
		      * - replaces
		        - Id of tab component this one replaces, might be either one of the core components or a component
		          provided by another plugin. See :ref:`this section <sec-plugins-templates>` for more on replacing template components.
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
		      * - div
		        - Id for the div containing the component. If not provided, defaults to ``plugin_<pluginname>`` plus
		          the suffix if provided or required.
		      * - replaces
		        - Id of settings component this one replaces, might be either one of the core components or a component
		          provided by another plugin. See :ref:`this section <sec-plugins-templates>` for more on replacing template components.
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

		:return list: a list containing the configuration options for the plugin's injected templates
		"""
		return []

	def get_template_vars(self):
		"""
		Defines additional template variables to include into the template renderer. Variable names will be prefixed
		with ``plugin_<plugin identifier>_``.

		:return dict: a dictionary containing any additional template variables to include in the renderer
		"""
		return dict()

	def get_template_folder(self):
		"""
		Defines the folder where the plugin stores its templates. Override this if your plugin stores its templates at
		some other place than the ``templates`` sub folder in the plugin base directory.

		:return string: the absolute path to the folder where the plugin stores its jinja2 templates
		"""
		import os
		return os.path.join(self._basefolder, "templates")


class SimpleApiPlugin(OctoPrintPlugin):
	"""
	Utilizing the ``SimpleApiPlugin`` mixin plugins may implement a simple API based around one GET resource and one
	resource accepting JSON commands POSTed to it. This is the easy alternative for plugin's which don't need the
	full power of a `Flask Blueprint <http://flask.pocoo.org/docs/0.10/blueprints/>`_ that the :class:`BlueprintPlugin`
	mixin offers.

	Use this mixin if all you need to do is return some kind of dynamic data to your plugin from the backend
	and/or want to react to simple commands which boil down to a type of command and a couple of flat parameters
	supplied with it.

	The simple API constructed by OctoPrint for you will be made available under ``/api/plugin/<plugin identifier>/``.
	OctoPrint will do some preliminary request validation for your defined commands, making sure the request body is in
	the correct format (content type must be JSON) and contains all obligatory parameters for your command.

	Let's take a look at a small example for such a simple API and how you would go about calling it.

	Take this example of a plugin registered under plugin identifier ``mysimpleapiplugin``:

	.. code-block:: python
	   :linenos:

	   import octoprint.plugin

	   import flask

	   class MySimpleApiPlugin(octoprint.plugin.SimpleApiPlugin):
	       def get_api_commands(self):
	           return dict(
	               command1=[],
	               command2=["some_parameter"]
	           )

	       def on_api_command(self, command, data):
	           import flask
	           if command == "command1":
	               parameter = "unset"
	               if "parameter" in data:
	                   parameter = "set"
	               self._logger.info("command1 called, parameter is {parameter}".format(**locals()))
	           elif command == "command2":
	               self._logger.info("command2 called, some_parameter is {some_parameter}".format(**data))

	       def on_api_get(self, request):
	           return flask.jsonify(foo="bar")

	   __plugin_implementations__ = [MySimpleApiPlugin()]


	Our plugin defines two commands, ``command1`` with no mandatory parameters and ``command2`` with one
	mandatory parameter ``some_parameter``.

	``command1`` can also accept an optional parameter ``parameter``, and will log whether
	that parameter was set or unset. ``command2`` will log the content of the mandatory ``some_parameter`` parameter.

	A valid POST request for ``command2`` sent to ``/api/plugin/mysimpleapiplugin`` would look like this:

	.. sourcecode:: http

	   POST /api/plugin/mysimpleapiplugin HTTP/1.1
	   Host: example.com
	   Content-Type: application/json
	   X-Api-Key: abcdef...

	   {
	     "command": "command2",
	     "some_parameter": "some_value",
	     "some_optional_parameter": 2342
	   }

	which would produce a response like this:

	.. sourcecode:: http

	   HTTP/1.1 204 No Content

	and print something like this line to ``octoprint.log``::

	   2015-02-12 17:40:21,140 - octoprint.plugins.mysimpleapiplugin - INFO - command2 called, some_parameter is some_value

	A GET request on our plugin's simple API resource will only return a JSON document like this:

	.. sourcecode:: http

	   HTTP/1.1 200 Ok
	   Content-Type: application/json

	   {
	     "foo": "bar"
	   }
	"""

	def get_api_commands(self):
		"""
		Return a dictionary here with the keys representing the accepted commands and the values being lists of
		mandatory parameter names.
		"""
		return None

	def on_api_command(self, command, data):
		"""
		Called by OctoPrint upon a POST request to ``/api/plugin/<plugin identifier>``. ``command`` will contain one of
		the commands as specified via :func:`get_api_commands`, ``data`` will contain the full request body parsed
		from JSON into a Python dictionary. Note that this will also contain the ``command`` attribute itself. For the
		example given above, for the ``command2`` request the ``data`` received by the plugin would be equal to
		``dict(command="command2", some_parameter="some_value")``.

		If your plugin returns nothing here, OctoPrint will return an empty response with return code ``204 No content``
		for you. You may also return regular responses as you would return from any Flask view here though, e.g.
		``return flask.jsonify(result="some json result")`` or ``return flask.make_response("Not found", 404)``.

		:param string command: the command with which the resource was called
		:param dict data:      the full request body of the POST request parsed from JSON into a Python dictionary
		:return: ``None`` in which case OctoPrint will generate a ``204 No content`` response with empty body, or optionally
		         a proper Flask response.
		"""
		return None

	def on_api_get(self, request):
		"""
		Called by OctoPrint upon a GET request to ``/api/plugin/<plugin identifier>``. ``request`` will contain the
		received `Flask request object <http://flask.pocoo.org/docs/0.9/api/#flask.Request>`_ which you may evaluate
		for additional arguments supplied with the request.

		If your plugin returns nothing here, OctoPrint will return an empty response with return code ``204 No content``
		for you. You may also return regular responses as you would return from any Flask view here though, e.g.
		``return flask.jsonify(result="some json result")`` or ``return flask.make_response("Not found", 404)``.

		:param request: the Flask request object
		:return: ``None`` in which case OctoPrint will generate a ``204 No content`` response with empty body, or optionally
		         a proper Flask response.
		"""
		return None


class BlueprintPlugin(OctoPrintPlugin):
	"""
	The ``BlueprintPlugin`` mixin allows plugins to define their own full fledged endpoints for whatever purpose,
	be it a more sophisticated API than what is possible via the :class:`SimpleApiPlugin` or a custom web frontend.

	The mechanism at work here is `Flask's <http://flask.pocoo.org/>`_ own `Blueprint mechanism <http://flask.pocoo.org/docs/0.10/blueprints/>`_.

	The mixin automatically creates a blueprint for you that will be registered under ``/plugin/<plugin identifier>/``.
	All you need to do is decorate all of your view functions with the :func:`route` decorator,
	which behaves exactly the same like Flask's regular ``route`` decorators. Example:

	.. code-block:: python
	   :linenos:

	   import octoprint.plugin
	   import flask

	   class MyBlueprintPlugin(octoprint.plugin.BlueprintPlugin):
	       @octoprint.plugin.BlueprintPlugin.route("/echo", methods=["GET"])
	       def myEcho(self):
	           if not "text" in flask.request.values:
	               return flask.make_response("Expected a text to echo back.", 400)
	           return flask.request.values["text"]

	   __plugin_implementations__ = [MyPlugin()]

	Your blueprint will be published by OctoPrint under the base URL ``/plugin/<plugin identifier>/``, so the above
	example of a plugin with the identifier "myblueprintplugin" would be reachable under
	``/plugin/myblueprintplugin/echo``.

	Just like with regular blueprints you'll be able to create URLs via ``url_for``, just use the prefix
	``plugin.<plugin identifier>``, e.g.:

	.. code-block:: python

	   flask.url_for("plugin.myblueprintplugin.echo") # will return "/plugin/myblueprintplugin/echo"

	"""

	@staticmethod
	def route(rule, **options):
		"""
		A decorator to mark view methods in your BlueprintPlugin subclass. Works just the same as Flask's
		own ``route`` decorator available on blueprints.

		See `the documentation for flask.Blueprint.route <http://flask.pocoo.org/docs/0.10/api/#flask.Blueprint.route>`_
		and `the documentation for flask.Flask.route <http://flask.pocoo.org/docs/0.10/api/#flask.Flask.route>`_ for more
		information.
		"""

		from collections import defaultdict
		def decorator(f):
			# We attach the decorator parameters directly to the function object, because that's the only place
			# we can access right now.
			# This neat little trick was adapter from the Flask-Classy project: https://pythonhosted.org/Flask-Classy/
			if not hasattr(f, "_blueprint_rules") or f._blueprint_rules is None:
				f._blueprint_rules = defaultdict(list)
			f._blueprint_rules[f.__name__].append((rule, options))
			return f
		return decorator

	def get_blueprint(self):
		"""
		Creates and returns the blueprint for your plugin. Override this if you want to define and handle your blueprint yourself.

		This method will only be called once during server initialization.

		:return: the blueprint ready to be registered with Flask
		"""

		import flask
		kwargs = self.get_blueprint_kwargs()
		blueprint = flask.Blueprint("plugin." + self._identifier, self._identifier, **kwargs)
		for member in [member for member in dir(self) if not member.startswith("_")]:
			f = getattr(self, member)
			if hasattr(f, "_blueprint_rules") and member in f._blueprint_rules:
				for blueprint_rule in f._blueprint_rules[member]:
					rule, options = blueprint_rule
					blueprint.add_url_rule(rule, options.pop("endpoint", f.__name__), view_func=f, **options)
		return blueprint

	def get_blueprint_kwargs(self):
		"""
		Override this if you want your blueprint constructed with additional options such as ``static_folder``,
		``template_folder``, etc.

		Defaults to the blueprint's ``static_folder`` and ``template_folder`` to be set to the plugin's basefolder
		plus ``/static`` or respectively ``/templates``.
		"""
		import os
		return dict(
			static_folder=os.path.join(self._basefolder, "static"),
			template_folder=os.path.join(self._basefolder, "templates")
		)

	def is_blueprint_protected(self):
		"""
		Whether a valid API key is needed to access the blueprint (the default) or not.
		"""

		return True


class SettingsPlugin(OctoPrintPlugin):
	"""
	Including the ``SettingsPlugin`` mixin allows plugins to store and retrieve their own settings within OctoPrint's
	configuration.

	Plugins including the mixing will get injected an additional property ``self._settings`` which is an instance of
	:class:`PluginSettingsManager` already properly initialized for use by the plugin. In order for the manager to
	know about the available settings structure and default values upon initialization, implementing plugins will need
	to provide a dictionary with the plugin's default settings through overriding the method :func:`get_settings_defaults`.
	The defined structure will then be available to access through the settings manager available as ``self._settings``.

	If your plugin needs to react to the change of specific configuration values on the fly, e.g. to adjust the log level
	of a logger when the user changes a corresponding flag via the settings dialog, you can override the
	:func:`on_settings_save` method and wrap the call to the implementation from the parent class with retrieval of the
	old and the new value and react accordingly.

	Example:

	.. code-block:: python

	   import octoprint.plugin

	   class MySettingsPlugin(octoprint.plugin.SettingsPlugin, octoprint.plugin.StartupPlugin):
	       def get_settings_defaults(self):
	           return dict(
	               some_setting="foo",
	               some_value=23,
	               sub=dict(
	                   some_flag=True
	               )
	           )

	       def on_settings_save(self, data):
	           old_flag = self._settings.getBoolean(["sub", "some_flag"])

	           super(MySettingsPlugin, self).on_settings_save(data)

	           new_flag = self._settings.getBoolean(["sub", "some_flag"])
	           if old_flag != new_flag:
	               self._logger.info("sub.some_flag changed from {old_flag} to {new_flag}".format(**locals()))

	       def on_after_startup(self):
	           some_setting = self._settings.get(["some_setting"])
	           some_value = self._settings.getInt(["some_value"])
	           some_flag = self._settings.getBoolean(["sub", "some_flag"])
	           self._logger.info("some_setting = {some_setting}, some_value = {some_value}, sub.some_flag = {some_flag}".format(**locals())

	   __plugin_implementations__ = [MySettingsPlugin()]

	Of course, you are always free to completely override both :func:`on_settings_load` and :func:`on_settings_save` if the
	default implementations do not fit your requirements.

	.. attribute:: _settings

	   The :class:`~octoprint.plugin.PluginSettings` instance to use for accessing the plugin's settings. Injected by
	   the plugin core system upon initialization of the implementation.
	"""

	def on_settings_load(self):
		"""
		Loads the settings for the plugin, called by the Settings API view in order to retrieve all settings from
		all plugins. Override this if you want to inject additional settings properties that are not stored within
		OctoPrint's configuration.

		.. note::

		   The default implementation will return your plugin's settings as is, so just in the structure and in the types
		   that are currently stored in OctoPrint's configuration.

		   If you need more granular control here, e.g. over the used data types, you'll need to override this method
		   and iterate yourself over all your settings, using the proper retriever methods on the settings manager
		   to retrieve the data in the correct format.

		:return: the current settings of the plugin, as a dictionary
		"""
		return self._settings.get([], asdict=True, merged=True)

	def on_settings_save(self, data):
		"""
		Saves the settings for the plugin, called by the Settings API view in order to persist all settings
		from all plugins. Override this if you need to directly react to settings changes or want to extract
		additional settings properties that are not stored within OctoPrint's configuration.

		.. note::

		   The default implementation will persist your plugin's settings as is, so just in the structure and in the
		   types that were received by the Settings API view.

		   If you need more granular control here, e.g. over the used data types, you'll need to override this method
		   and iterate yourself over all your settings, retrieving them (if set) from the supplied received ``data``
		   and using the proper setter methods on the settings manager to persist the data in the correct format.

		:param dict data: the settings dictionary to be saved for the plugin
		"""
		import octoprint.util

		current = self._settings.get([], asdict=True, merged=True)
		data = octoprint.util.dict_merge(current, data)
		self._settings.set([], data)

	def get_settings_defaults(self):
		"""
		Retrieves the plugin's default settings with which the plugin's settings manager will be initialized.

		Override this in your plugin's implementation and return a dictionary defining your settings data structure
		with included default values.
		"""
		return dict()


class EventHandlerPlugin(OctoPrintPlugin):
	"""
	The ``EventHandlerPlugin`` mixin allows OctoPrint plugins to react to any of :ref:`OctoPrint's events <sec-events>`.
	OctoPrint will call the :func:`on_event` method for any event fired on its internal event bus, supplying the
	event type and the associated payload. Please note that until your plugin returns from that method, further event
	processing within OctoPrint will block - the event queue itself is run asynchronously from the rest of OctoPrint,
	but the processing of the events within the queue itself happens consecutively.

	This mixin is especially interesting for plugins which want to react on things like print jobs finishing, timelapse
	videos rendering etc.
	"""

	def on_event(self, event, payload):
		"""
		Called by OctoPrint upon processing of a fired event on the platform.

		:param string event: the type of event that got fired, see :ref:`the list of events <sec-events-available_events>`
		                     for possible values
		:param dict payload: the payload as provided with the event
		"""
		pass


class SlicerPlugin(OctoPrintPlugin):
	"""
	Via the ``SlicerPlugin`` mixin plugins can add support for slicing engines to be used by OctoPrint.

	"""

	def is_slicer_configured(self):
		"""
		Unless the return value of this method is ``True``, OctoPrint will not register the slicer within the slicing
		sub system upon startup. Plugins may use this to do some start up checks to verify that e.g. the path to
		a slicing binary as set and the binary is executable, or credentials of a cloud slicing platform are properly
		entered etc.
		"""
		return False

	def get_slicer_properties(self):
		"""
		Plugins should override this method to return a ``dict`` containing a bunch of meta data about the implemented slicer.

		The expected keys in the returned ``dict`` have the following meaning:

		type
		    The type identifier to use for the slicer. This should be a short unique lower case string which will be
		    used to store slicer profiles under or refer to the slicer programmatically or from the API.
		name
		    The human readable name of the slicer. This will be displayed to the user during slicer selection.
		same_device
		    ``True`` if the slicer runs on the same device as OctoPrint, ``False`` otherwise. Slicers running on the same
		    device will TODO
		progress_report
		    ``True`` if the slicer can report back slicing progress to OctoPrint ``False`` otherwise.
		"""
		return dict(
			type=None,
			name=None,
			same_device=True,
			progress_report=False
		)

	def get_slicer_default_profile(self):
		"""
		Should return a :class:`SlicingProfile` containing the default slicing profile to use with this slicer if
		no other profile has been selected.
		"""
		return None

	def get_slicer_profile(self, path):
		"""
		Should return a :class:`SlicingProfile` parsed from the slicing profile stored at the indicated ``path``.

		:param string path: the path from which to read the slicing profile
		"""
		return None

	def save_slicer_profile(self, path, profile, allow_overwrite=True, overrides=None):
		"""
		Should save the provided :class:`SlicingProfile` to the indicated ``path``, after applying any supplied
		``overrides``. If a profile is already saved under the indicated path and ``allow_overwrite`` is set to
		``False`` (defaults to ``True``), an ``IOError`` should be raised.

		:param string path: the path to which to save the profile
		:param SlicingProfile profile: the profile to save
		:param bool allow_overwrite: whether to allow to overwrite an existing profile at the indicated path (``True``, default)
		    or not (``False``) - if a profile already exists on the path and this is ``False``
		    and :class:`IOError` should be raised
		:param dict overrides: profile overrides to apply to the ``profile`` before saving it
		"""
		pass

	def do_slice(self, model_path, printer_profile, machinecode_path=None, profile_path=None, position=None, on_progress=None, on_progress_args=None, on_progress_kwargs=None):
		"""
		Called by OctoPrint to slice ``model_path`` for the indicated ``printer_profile``. If the ``machinecode_path`` is ``None``,
		slicer implementations should generate it from the provided model_path.

		If provided, the ``profile_path`` is guaranteed by OctoPrint to be a serialized slicing profile created through the slicing
		plugin's own :func:`save_slicer_profile` method.

		If provided, ``position`` will be a ``dict`` containing and ``x`` and a ``y`` key, indicating the position
		the center of the model on the print bed should have in the final sliced machine code. If not provided, slicer
		implementations should place the model in the center of the print bed.

		``on_progress`` will be a callback which expects an additional keyword argument ``_progress`` with the current
		slicing progress which - if progress reporting is supported - the slicing plugin should call like the following:

		.. code-block:: python

		   if on_progress is not None:
		       if on_progress_args is None:
		           on_progress_args = ()
		       if on_progress_kwargs is None:
		           on_progress_kwargs = dict()

		       on_progress_kwargs["_progress"] = your_plugins_slicing_progress
		       on_progress(*on_progress_args, **on_progress_kwargs)

		Please note that both ``on_progress_args`` and ``on_progress_kwargs`` as supplied by OctoPrint might be ``None``,
		so always make sure to initialize those values to sane defaults like depicted above before invoking the callback.
		"""
		pass

	def cancel_slicing(self, machinecode_path):
		"""
		Cancels the slicing to the indicated file
		"""
		pass


class ProgressPlugin(OctoPrintPlugin):
	"""
	Via the ``ProgressPlugin`` mixing plugins can let themselves be called upon progress in print jobs or slicing jobs,
	limited to minimally 1% steps.
	"""

	def on_print_progress(self, storage, path, progress):
		"""
		Called by OctoPrint on minimally 1% increments during a running print job.

		:param string location: Location of the file
		:param string path:     Path of the file
		:param int progress:    Current progress as a value between 0 and 100
		"""
		pass

	def on_slicing_progress(self, slicer, source_location, source_path, destination_location, destination_path, progress):
		"""
		Called by OctoPrint on minimally 1% increments during a running slicing job.

		:param string slicer:               Key of the slicer reporting the progress
		:param string source_location:      Location of the source file
		:param string source_path:          Path of the source file
		:param string destination_location: Location the destination file
		:param string destination_path:     Path of the destination file
		:param int progress:                Current progress as a value between 0 and 100
		"""
		pass


class AppPlugin(OctoPrintPlugin):
	def get_additional_apps(self):
		return []

