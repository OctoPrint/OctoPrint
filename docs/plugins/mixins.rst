.. _sec-plugins-mixins:

Mixins
======

.. contents::
   :local:

.. _sec-plugins-mixins-general:

General Concepts
----------------

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

   :ref:`The Plugin Tutorial <sec-plugins-gettingstarted>`
       Tutorial on how to write a simple OctoPrint module utilizing mixins for various types of extension.

.. _sec-plugins-mixins-ordering:

Execution Order
---------------

Some mixin types, such as :class:`~octoprint.plugin.StartupPlugin`, :class:`~octoprint.plugin.ShutdownPlugin` and
:class:`~octoprint.plugin.UiPlugin`, support influencing the execution order for various execution contexts by also
implementing the :class:`~octoprint.plugin.core.SortablePlugin` mixin.

If a method is to be called on a plugin implementation for which a sorting context is defined (see the mixin
documentation for information on this), OctoPrint's plugin subsystem will ensure that the order in which the implementation
calls are done is as follows:

  * Plugins with a return value that is not ``None`` for :meth:`~octoprint.plugin.core.SortablePlugin.get_sorting_key`
    for the provided sorting context will be ordered among each other first. If the returned order number is equal for
    two or more implementations, the plugin's identifier will be the next sorting criteria.
  * After that follow plugins which returned ``None`` (the default). They are sorted by their identifier.

Example: Consider three plugin implementations implementing the :class:`~octoprint.plugin.StartupPlugin` mixin, called
``plugin_a``, ``plugin_b`` and ``plugin_c``. ``plugin_a`` doesn't override :meth:`~octoprint.plugin.core.SortablePlugin.get_sorting_key`.
``plugin_b`` and ``plugin_c`` both return ``1`` for the sorting context ``StartupPlugin.on_startup``, ``None`` otherwise:

.. code-block:: python
   :linenos:
   :caption: plugin_a.py

   import octoprint.plugin

   class PluginA(octoprint.plugin.StartupPlugin):

       def on_startup(self, *args, **kwargs):
           self._logger.info("PluginA starting up")

       def on_after_startup(self, *args, **kwargs):
           self._logger.info("PluginA started up")

   __plugin_implementation__ = PluginA()

.. code-block:: python
   :linenos:
   :caption: plugin_b.py

   import octoprint.plugin

   class PluginB(octoprint.plugin.StartupPlugin):

       def get_sorting_key(context):
           if context == "StartupPlugin.on_startup":
               return 1
           return None

       def on_startup(self, *args, **kwargs):
           self._logger.info("PluginB starting up")

       def on_after_startup(self, *args, **kwargs):
           self._logger.info("PluginB started up")

   __plugin_implementation__ = PluginB()

.. code-block:: python
   :linenos:
   :caption: plugin_c.py

   import octoprint.plugin

   class PluginC(octoprint.plugin.StartupPlugin):

       def get_sorting_key(context):
           if context == "StartupPlugin.on_startup":
               return 1
           return None

       def on_startup(self, *args, **kwargs):
           self._logger.info("PluginC starting up")

       def on_after_startup(self, *args, **kwargs):
           self._logger.info("PluginC started up")


   __plugin_implementation__ = PluginC()

OctoPrint will detect that ``plugin_b`` and ``plugin_c`` define a order number, and since it's identical for both (``1``)
will order both plugins based on their plugin identifier. ``plugin_a`` doesn't define a sort key and hence will be
put after the other two. The execution order of the ``on_startup`` method will hence be ``plugin_b``, ``plugin_c``, ``plugin_a``.

Now, the execution order of the ``on_after_startup`` method will be determined based on another sorting context,
``StartupPlugin.on_after_startup`` for which all of the plugins return ``None``. Hence, the execution order of the
``on_after_startup`` method will be purely ordered by plugin identifier, ``plugin_a``, ``plugin_b``, ``plugin_c``.

.. _sec-plugins-mixins-injectedproperties:

Injected Properties
-------------------

OctoPrint's plugin subsystem will inject a bunch of properties into each :ref:`mixin implementation <sec-plugins-mixins>`.
An overview of these properties follows.

``self._identifier``
  The plugin's identifier.
``self._plugin_name``
  The plugin's name, as taken from either the ``__plugin_name__`` control property or the package info.
``self._plugin_version``
  The plugin's version, as taken from either the ``__plugin_version__`` control property or the package info.
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
``self._user_manager``
  OctoPrint's user manager, an instance of :class:`octoprint.users.UserManager`.

.. seealso::

   :class:`~octoprint.plugin.core.Plugin` and :class:`~octoprint.plugin.types.OctoPrintPlugin`
       Class documentation also containing the properties shared among all mixing implementations.

.. _sec-plugins-mixins-available:

Available plugin mixins
-----------------------

The following plugin mixins are currently available:

.. contents::
   :local:

Please note that all plugin mixins inherit from :class:`~octoprint.plugin.core.Plugin` and
:class:`~octoprint.plugin.types.OctoPrintPlugin`,  which also provide attributes of interest to plugin developers.

.. _sec-plugins-mixins-startupplugin:

StartupPlugin
~~~~~~~~~~~~~

.. autoclass:: octoprint.plugin.StartupPlugin
   :members:
   :show-inheritance:

.. _sec-plugins-mixins-shutdownplugin:

ShutdownPlugin
~~~~~~~~~~~~~~

.. autoclass:: octoprint.plugin.ShutdownPlugin
   :members:
   :show-inheritance:

.. _sec-plugins-mixins-settingsplugin:

SettingsPlugin
~~~~~~~~~~~~~~

.. autoclass:: octoprint.plugin.SettingsPlugin
   :members:
   :show-inheritance:

.. _sec-plugins-mixins-assetplugin:

AssetPlugin
~~~~~~~~~~~

.. autoclass:: octoprint.plugin.AssetPlugin
   :members:
   :show-inheritance:

.. _sec-plugins-mixins-templateplugin:

TemplatePlugin
~~~~~~~~~~~~~~

.. autoclass:: octoprint.plugin.TemplatePlugin
   :members:
   :show-inheritance:

.. _sec-plugins-mixins-wizardplugin:

WizardPlugin
~~~~~~~~~~~~

.. autoclass:: octoprint.plugin.WizardPlugin
   :members:
   :show-inheritance:

.. _sec-plugins-mixins-uiplugin:

UiPlugin
~~~~~~~~

.. autoclass:: octoprint.plugin.UiPlugin
   :members:
   :show-inheritance:

.. _sec-plugins-mixins-simpleapiplugin:

SimpleApiPlugin
~~~~~~~~~~~~~~~

.. autoclass:: octoprint.plugin.SimpleApiPlugin
   :members:
   :show-inheritance:

.. _sec-plugins-mixins-blueprintplugin:

BlueprintPlugin
~~~~~~~~~~~~~~~

.. autoclass:: octoprint.plugin.BlueprintPlugin
   :members:
   :show-inheritance:

.. _sec-plugins-mixins-eventhandlerplugin:

EventHandlerPlugin
~~~~~~~~~~~~~~~~~~

.. autoclass:: octoprint.plugin.EventHandlerPlugin
   :members:
   :show-inheritance:

.. _sec-plugins-mixins-progressplugin:

ProgressPlugin
~~~~~~~~~~~~~~

.. autoclass:: octoprint.plugin.ProgressPlugin
   :members:
   :show-inheritance:

.. _sec-plugins-mixins-slicerplugin:

SlicerPlugin
~~~~~~~~~~~~

.. autoclass:: octoprint.plugin.SlicerPlugin
   :members:
   :show-inheritance:

