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

.. _sec-plugins-controlproperties-plugin_name:

``__plugin_name__``
  Name of your plugin, optional, overrides the name specified in ``setup.py`` if provided. If neither this property nor
  a name from ``setup.py`` is available to the plugin subsystem, the plugin's identifier (= package name) will be
  used instead.

.. _sec-plugins-controlproperties-plugin_version:

``__plugin_version__``
  Version of your plugin, optional, overrides the version specified in ``setup.py`` if provided.

.. _sec-plugins-controlproperties-plugin_description:

``__plugin_description__``
  Description of your plugin, optional, overrides the description specified in ``setup.py`` if provided.

.. _sec-plugins-controlproperties-plugin_author:

``__plugin_author__``
  Author of your plugin, optional, overrides the author specified in ``setup.py`` if provided.

.. _sec-plugins-controlproperties-plugin_url:

``__plugin_url__``
  URL of the webpage of your plugin, e.g. the Github repository, optional, overrides the URL specified in ``setup.py`` if
  provided.

.. _sec-plugins-controlproperties-plugin_license:

``__plugin_license__``
  License of your plugin, optional, overrides the license specified in ``setup.py`` if provided.

.. _sec-plugins-controlproperties-plugin_implementation:

``__plugin_implementation__``
  Instance of an implementation of one or more :ref:`plugin mixins <sec-plugins-mixins>`. E.g.

  .. code-block:: python

     __plugin_implementation__ = MyPlugin()


.. _sec-plugins-controlproperties-plugin_hooks:

``__plugin_hooks__``
  Handlers for one or more of the various :ref:`plugin hooks <sec-plugins-hooks>`. E.g.

  .. code-block:: python

     def handle_gcode_sent(comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
         if gcode in ("M106", "M107"):
             import logging
             logging.getLogger(__name__).info("We just sent a fan command to the printer!")

     __plugin_hooks__ = {
         "octoprint.comm.protocol.gcode.sent": handle_gcode_sent
     }


.. _sec-plugins-controlproperties-plugin_check:

``__plugin_check__``
  Method called upon discovery of the plugin by the plugin subsystem, should return ``True`` if the
  plugin can be instantiated later on, ``False`` if there are reasons why not, e.g. if dependencies
  are missing. An example:

  .. code-block:: python

     def __plugin_check__():
         # Make sure we only run our plugin if some_dependency is available
         try:
             import some_dependency
         except ImportError:
             return False

         return True

.. _sec-plugins-controlproperties-plugin_load:

``__plugin_load__``
  Method called upon loading of the plugin by the plugin subsystem, can be used to instantiate
  plugin implementations, connecting them to hooks etc. An example:

  .. code-block:: python

     def __plugin_load__():
         global __plugin_implementation__
         __plugin_implementation__ = MyPlugin()

         global __plugin_hooks__
         __plugin_hooks__ = {
             "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
         }


.. _sec-plugins-controlproperties-plugin_unload:

``__plugin_unload__``
  Method called upon unloading of the plugin by the plugin subsystem, can be used to do any final clean ups.

.. _sec-plugins-controlproperties-plugin_enable:

``__plugin_enable__``
  Method called upon enabling of the plugin by the plugin subsystem. Also see :func:`~octoprint.plugin.core.Plugin.on_plugin_enabled`.

.. _sec-plugins-controlproperties-plugin_disable:

``__plugin_disable__``
  Method called upon disabling of the plugin by the plugin subsystem. Also see :func:`~octoprint.plugin.core.Plugin.on_plugin_disabled`.

.. _sec-plugins-controlproperties-plugin_settings_overlay:

``__plugin_settings_overlay__``
  An optional ``dict`` providing an overlay over the application's default settings. Plugins can use that to modify the
  **default** settings of OctoPrint and its plugins that apply when there's no different configuration present in ``config.yaml``. Note that ``config.yaml``
  has the final say - it is not possible to override what is in there through an overlay. Plugin authors should use this
  sparingly - it's supposed to be utilized when creating specific customization of the core application that necessitate
  changes in things like e.g. standard naming, UI ordering or API endpoints. Example:

  .. code-block:: python

     __plugin_settings_overlay__ = dict(api=dict(enabled=False),
                                        server=dict(host="127.0.0.1",
                                                    port=5001))
