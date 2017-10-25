.. _sec-plugins-injectedproperties:

Injected Properties
===================

OctoPrint's plugin subsystem will inject a bunch of properties into each :ref:`mixin implementation <sec-plugins-mixins>`.
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
``self._user_manager``
  OctoPrint's user manager, an instance of :class:`octoprint.users.UserManager`.
``self._connectivity_checker``
  OctoPrint's connectivity checker, an instance of :class:`octoprint.util.ConnectivityChecker`.

.. seealso::

   :class:`~octoprint.plugin.core.Plugin` and :class:`~octoprint.plugin.types.OctoPrintPlugin`
       Class documentation also containing the properties shared among all mixing implementations.

   :ref:`Available Mixins <sec-plugins-mixins-available>`
       Some mixin types trigger the injection of additional properties.

