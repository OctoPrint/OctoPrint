.. _sec-plugins-controlproperties:

Control Properties
==================

As already mentioned earlier, plugins are Python packages which provide certain pieces of metadata to tell OctoPrint's
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

