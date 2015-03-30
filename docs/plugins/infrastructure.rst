.. _sec-plugins-infrastructure:

Plugin Infrastructure
=====================

.. _sec-plugins-infrastructure-controlproperties:

Control Properties
------------------

``__plugin_name__``
  Name of your plugin, optional, overrides the name specified in ``setup.py`` if provided.
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
  Instance of an implementation of one or more :ref:`plugin mixins <sec-plugins-mixins>`
``__plugin_hooks__``
  Handlers for one or more of the various :ref:`plugin hooks <sec-plugins-hooks>`
``__plugin_check__``
  Method called upon discovery of the plugin by the plugin subsystem, should return ``True`` if the
  plugin can be instantiated later on, ``False`` if there are reasons why not, e.g. if dependencies
  are missing.
``__plugin_init__``
  Method called upon initializing of the plugin by the plugin subsystem, can be used to instantiate
  plugin implementations, connecting them to hooks etc.

.. _sec-plugins-infrastructure-injections:

Injected Properties
-------------------

``self._identifier``
  The plugin's identifier.
``self._plugin_name``
  The plugin's name, as taken from either the ``__plugin_name__`` control property or the package info.
``self._plugin_version``
  The plugin's version, as taken from either the ``__plugin_version__`` control property or the package info.
``self._basefolder``
  The plugin's base folder where it's installed. Can be used to refer to files relative to the plugin's installation
  location, e.g. included scripts, templates or assets.
``self._logger``
  A `python logger instance <https://docs.python.org/2/library/logging.html>`_ logging to the log target
  ``octoprint.plugin.<plugin identifier>``.
``self._settings``
  The plugin's personalized settings manager, injected only into plugins that include the :class:`SettingsPlugin` mixin.
``self._plugin_manager``
  OctoPrint's plugin manager.
``self._printer_profile_manager``
  OctoPrint's printer profile manager.
``self._event_bus``
  OctoPrint's event bus.
``self._analysis_queue``
  OctoPrint's analysis queue for analyzing GCODEs or other files.
``self._slicing_manager``
  OctoPrint's slicing manager.
``self._file_manager``
  OctoPrint's file manager.
``self._printer``
  OctoPrint's printer management object.
``self._app_session_manager``
  OctoPrint's application session manager.
