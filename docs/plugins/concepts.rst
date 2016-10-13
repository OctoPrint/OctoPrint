.. _sec-plugin-concepts:

Concepts
========

.. contents::
   :local:

OctoPrint's plugins are `Python Packages <https://docs.python.org/2/tutorial/modules.html#packages>`_ which in their
top-level module define a bunch of :ref:`control properties <sec-plugin-concepts-controlproperties>` defining
metadata (like name, version etc of the plugin) as well as information on how to initialize the plugin and into what
parts of the system the plugin will actually plug in to perform its job.

There are three types of ways a plugin might attach itself to the system, through so called
:ref:`mixin <sec-plugin-concepts-mixins>` implementations, by attaching itself to specified
:ref:`hook <sec-plugin-concepts-hooks>` or by offering :ref:`helper <sec-plugin-concepts-helpers>` functionality to be
used by other plugins.

Plugin mixin implementations will get a bunch of :ref:`properties injected <sec-plugins-concepts-injectedproperties>`
by OctoPrint plugin system to help them work.

.. _sec-plugin-concepts-controlproperties:

Control Properties
------------------

As already mentioned above, plugins are Python packages which provide certain pieces of metadata to tell OctoPrint's
plugin subsystem about themselves. These are simple package attributes defined in the top most package file, e.g.:

.. code-block:: python

   import octoprint.plugin

   # ...

   __plugin_name__ = "My Plugin"
   def __plugin_load__():
       # whatever you need to do to load your plugin, if anything at all
       pass

The following properties are recognized:

``__plugin_name__``
  Name of your plugin, optional, overrides the name specified in ``setup.py`` if provided. If neither this property nor
  a name from ``setup.py`` is available to the plugin subsystem, the plugin's identifier (= package name) will be
  used instead.
``__plugin_version__``
  Version of your plugin, optional, overrides the version specified in ``setup.py`` if provided.
``__plugin_description__``
  Description of your plugin, optional, overrides the description specified in ``setup.py`` if provided.
``__plugin_author__``
  Author of your plugin, optional, overrides the author specified in ``setup.py`` if provided.
``__plugin_url__``
  URL of the webpage of your plugin, e.g. the Github repository, optional, overrides the URL specified in ``setup.py`` if
  provided.
``__plugin_license__``
  License of your plugin, optional, overrides the license specified in ``setup.py`` if provided.
``__plugin_implementation__``
  Instance of an implementation of one or more :ref:`plugin mixins <sec-plugins-mixins>`.
``__plugin_hooks__``
  Handlers for one or more of the various :ref:`plugin hooks <sec-plugins-hooks>`.
``__plugin_check__``
  Method called upon discovery of the plugin by the plugin subsystem, should return ``True`` if the
  plugin can be instantiated later on, ``False`` if there are reasons why not, e.g. if dependencies
  are missing.
``__plugin_load__``
  Method called upon loading of the plugin by the plugin subsystem, can be used to instantiate
  plugin implementations, connecting them to hooks etc.
``__plugin_unload__``
  Method called upon unloading of the plugin by the plugin subsystem, can be used to do any final clean ups.
``__plugin_enable__``
  Method called upon enabling of the plugin by the plugin subsystem. Also see :func:`~octoprint.plugin.core.Plugin.on_plugin_enabled``.
``__plugin_disable__``
  Method called upon disabling of the plugin by the plugin subsystem. Also see :func:`~octoprint.plugin.core.Plugin.on_plugin_disabled``.

.. _sec-plugin-concepts-mixins:

Mixins
------

Plugin mixins are the heart of OctoPrint's plugin system. They are :ref:`special base classes <sec-plugins-mixins>`
which are to be subclassed and extended to add functionality to OctoPrint. Plugins declare their instances that
implement one or multiple mixins using the ``__plugin_implementation__`` control property. OctoPrint's plugin core
collects those from the plugins and offers methods to access them based on the mixin type, which get used at multiple
locations within OctoPrint.

Using mixins always follows the pattern of retrieving the matching implementations from the plugin subsystem, then
calling the specific mixin's methods as defined and necessary.

The following snippet taken from OctoPrint's code for example shows how all :class:`~octoprint.plugin.AssetPlugin`
implementations are collected and then all assets they return via their ``get_assets`` methods are retrieved and
merged into one big asset map (differing between javascripts and stylesheets of various types) for use during
rendition of the UI.

.. code-block:: python
   :linenos:

   asset_plugins = pluginManager.get_implementations(octoprint.plugin.AssetPlugin)
   for name, implementation in asset_plugins.items():
       all_assets = implementation.get_assets()

       if "js" in all_assets:
           for asset in all_assets["js"]:
               assets["js"].append(url_for('plugin_assets', name=name, filename=asset))

       if preferred_stylesheet in all_assets:
           for asset in all_assets[preferred_stylesheet]:
               assets["stylesheets"].append((preferred_stylesheet, url_for('plugin_assets', name=name, filename=asset)))
       else:
           for stylesheet in supported_stylesheets:
               if not stylesheet in all_assets:
                   continue

               for asset in all_assets[stylesheet]:
                   assets["stylesheets"].append((stylesheet, url_for('plugin_assets', name=name, filename=asset)))
               break

.. seealso::

   :ref:`Available Mixins <sec-plugins-mixins>`
       An overview of all mixin types available for extending OctoPrint.

   :ref:`The Getting Started Guide <sec-plugins-gettingstarted>`
       Tutorial on how to write a simple OctoPrint module utilizing mixins for various types of extension.

.. _sec-plugin-concepts-hooks:

Hooks
-----

Hooks are the smaller siblings of mixins, allowing to extend functionality or data processing where a custom mixin type
would be too much overhead. Where mixins are based on classes, hooks are based on methods. Like with the mixin
implementations, plugins inform OctoPrint about hook handlers using a control property, ``__plugin_hooks__``.

Each hook defines a contract detailing the call parameters for the hook handler method and the expected return type.
OctoPrint will call the hook with the define parameters and process the result depending on the hook.

An example for a hook within OctoPrint is ``octoprint.comm.protocol.scripts``, which allows adding additional
lines to OctoPrint's :ref:`GCODE scripts <sec-features-gcode_scripts>`, either as ``prefix`` (before the existing lines)
or as ``postfix`` (after the existing lines).

.. code-block:: python
   :linenos:

   self._gcode_hooks = self._pluginManager.get_hooks("octoprint.comm.protocol.scripts")

   # ...

   for hook in self._gcodescript_hooks:
       try:
           retval = self._gcodescript_hooks[hook](self, "gcode", scriptName)
       except:
           self._logger.exception("Error while processing gcodescript hook %s" % hook)
       else:
           if retval is None:
               continue
           if not isinstance(retval, (list, tuple)) or not len(retval) == 2:
               continue

           def to_list(data):
               if isinstance(data, str):
                   data = map(str.strip, data.split("\n"))
               elif isinstance(data, unicode):
                   data = map(unicode.strip, data.split("\n"))

               if isinstance(data, (list, tuple)):
                   return list(data)
               else:
                   return None

           prefix, suffix = map(to_list, retval)
           if prefix:
               scriptLines = list(prefix) + scriptLines
           if suffix:
               scriptLines += list(suffix)

As you can see, the hook's method signature is defined to take the current ``self`` (as in, the current comm layer instance),
the general type of script for which to look for additions ("gcode") and the script name for which to look (e.g.
``beforePrintStarted`` for the GCODE script executed before the beginning of a print job). The hook is expected to
return a 2-tuple of prefix and postfix if has something for either of those, otherwise ``None``. OctoPrint will then take
care to add prefix and suffix as necessary after a small round of preprocessing.

.. note::

   At the moment there exists no way to determine the execution order of various hook handlers within OctoPrint,
   or to prevent the execution of further handlers down the chain.

   This is planned for the very near future though.

Plugins can easily add their own hooks too. For example, the `Software Update Plugin <https://github.com/OctoPrint/OctoPrint-SoftwareUpdate>`_
declares a custom hook "octoprint.plugin.softwareupdate.check_config" which other plugins can add handlers for in order
to register themselves with the Software Update Plugin by returning their own update check configuration.

If you want your hook handler to be an instance method of a mixin implementation of your plugin (for example since you
need access to instance variables handed to your implementation via mixin invocations), you can get this work
by using a small trick. Instead of defining it directly via ``__plugin_hooks__`` utilize the ``__plugin_load__``
property instead, manually instantiate your implementation instance and then add its hook handler method to the
``__plugin_hooks__`` property and itself to the ``__plugin_implementation__`` property. See the following example.

.. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/custom_action_command.py
   :linenos:
   :tab-width: 4
   :caption: `custom_action_command.py <https://github.com/OctoPrint/Plugin-Examples/blob/master/custom_action_command.py>`_
   :name: sec-plugin-concepts-hooks-example

.. seealso::

   :ref:`Available Hooks <sec-plugins-hooks>`
       An overview of all hooks defined in OctoPrint itself.


.. _sec-plugin-concepts-helpers:

Helpers
-------

Helpers are methods that plugin can exposed to other plugins in order to make common functionality available on the
system. They are registered with the OctoPrint plugin system through the use of the control property ``__plugin_helpers__``.

An example for providing a couple of helper functions to the system can be found in the
`Discovery Plugin <https://github.com/foosel/OctoPrint/wiki/Plugin:-Discovery>`_,
which provides it's SSDP browsing and Zeroconf browsing and publishing functions as helper methods.

.. code-block:: python
   :linenos:
   :emphasize-lines: 11-20
   :caption: Excerpt from the Discovery Plugin showing the declaration of its exported helpers.
   :name: sec-plugin-concepts-helpers-example-export

   def __plugin_load__():
       if not pybonjour:
           # no pybonjour available, we can't use that
           logging.getLogger("octoprint.plugins." + __name__).info("pybonjour is not installed, Zeroconf Discovery won't be available")

       plugin = DiscoveryPlugin()

       global __plugin_implementation__
       __plugin_implementation__ = plugin

       global __plugin_helpers__
       __plugin_helpers__ = dict(
           ssdp_browse=plugin.ssdp_browse
       )
       if pybonjour:
           __plugin_helpers__.update(dict(
               zeroconf_browse=plugin.zeroconf_browse,
               zeroconf_register=plugin.zeroconf_register,
               zeroconf_unregister=plugin.zeroconf_unregister
           ))

An example of how to use helpers can be found in the `Growl Plugin <https://github.com/OctoPrint/OctoPrint-Growl>`_.
Using :meth:`~octoprint.plugin.code.PluginManager.get_helpers` plugins can retrieve exported helper methods and call
them as (hopefully) documented.

.. code-block:: python
   :linenos:
   :emphasize-lines: 6-8,20
   :caption: Excerpt from the Growl Plugin showing utilization of the helpers published by the Discovery Plugin.
   :name: sec-plugin-concepts-helpers-example-usage

   def on_after_startup(self):
       host = self._settings.get(["hostname"])
       port = self._settings.getInt(["port"])
       password = self._settings.get(["password"])

       helpers = self._plugin_manager.get_helpers("discovery", "zeroconf_browse")
       if helpers and "zeroconf_browse" in helpers:
           self.zeroconf_browse = helpers["zeroconf_browse"]

       self.growl, _ = self._register_growl(host, port, password=password)

   # ...

   def on_api_get(self, request):
       if not self.zeroconf_browse:
           return flask.jsonify(dict(
               browsing_enabled=False
           ))

       browse_results = self.zeroconf_browse("_gntp._tcp", block=True)
       growl_instances = [dict(name=v["name"], host=v["host"], port=v["port"]) for v in browse_results]

       return flask.jsonify(dict(
           browsing_enabled=True,
           growl_instances=growl_instances
       ))

.. _sec-plugins-concepts-injectedproperties:

Injected Properties
-------------------

OctoPrint's plugin subsystem will inject a bunch of properties into each :ref:`mixin implementation <sec-plugin-concepts-mixins>`.
An overview of these properties follows.

``self._identifier``
  The plugin's identifier.
``self._plugin_name``
  The plugin's name, as taken from either the ``__plugin_name__`` control property or the package info.
``self._plugin_version``
  The plugin's version, as taken from either the ``__plugin_version__`` control property or the package info.
``self._plugin_info``
  The :class:`octoprint.plugin.core.PluginInfo` object associated with the plugin.
``self._basefolder``
  The plugin's base folder where it's installed. Can be used to refer to files relative to the plugin's installation
  location, e.g. included scripts, templates or assets.
``self._datafolder``
  The plugin's additional data folder path. Can be used to store additional files needed for the plugin's operation (cache,
  data files etc). Plugins should not access this property directly but instead utilize :func:`~octoprint.plugin.types.OctoPrintPlugin.get_plugin_data_folder`
  which will make sure the path actually does exist and if not create it before returning it.
``self._logger``
  A `python logger instance <https://docs.python.org/2/library/logging.html>`_ logging to the log target
  ``octoprint.plugin.<plugin identifier>``.
``self._settings``
  The plugin's personalized settings manager, injected only into plugins that include the :class:`~octoprint.plugin.SettingsPlugin` mixin.
  An instance of :class:`octoprint.plugin.PluginSettings`.
``self._plugin_manager``
  OctoPrint's plugin manager object, an instance of :class:`octoprint.plugin.core.PluginManager`.
``self._printer_profile_manager``
  OctoPrint's printer profile manager, an instance of :class:`octoprint.printer.profile.PrinterProfileManager`.
``self._event_bus``
  OctoPrint's event bus, an instance of :class:`octoprint.events.EventManager`.
``self._analysis_queue``
  OctoPrint's analysis queue for analyzing GCODEs or other files, an instance of :class:`octoprint.filemanager.analysis.AnalysisQueue`.
``self._slicing_manager``
  OctoPrint's slicing manager, an instance of :class:`octoprint.slicing.SlicingManager`.
``self._file_manager``
  OctoPrint's file manager, an instance of :class:`octoprint.filemanager.FileManager`.
``self._printer``
  OctoPrint's printer management object, an instance of :class:`octoprint.printer.PrinterInterface`.
``self._app_session_manager``
  OctoPrint's application session manager, an instance of :class:`octoprint.server.util.flask.AppSessionManager`.

.. seealso::

   :class:`~octoprint.plugin.core.Plugin` and :class:`~octoprint.plugin.types.OctoPrintPlugin`
       Class documentation also containing the properties shared among all mixing implementations.

   :ref:`Available Mixins <sec-plugins-mixins>`
       Some mixin types trigger the injection of additional properties.

.. _sec-plugins-concept-lifecycle:

Lifecycle
---------

.. image:: ../images/plugins_lifecycle.png
   :align: center
   :alt: The lifecycle of OctoPrint plugins.
