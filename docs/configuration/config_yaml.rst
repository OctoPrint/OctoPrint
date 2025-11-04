.. _sec-configuration-config_yaml:

config.yaml
===========

If not specified via the command line, the main configuration file ``config.yaml`` for OctoPrint is expected in its
settings folder, which unless defined differently via the command line is located at ``~/.octoprint`` on Linux, at
``%APPDATA%/OctoPrint`` on Windows and at ``~/Library/Application Support/OctoPrint`` on macOS. If the file is not there,
you can just create it - it will only get created by OctoPrint once you save settings that deviate from the default
settings.

Note that many of these settings are available from the "Settings" menu in OctoPrint itself.
They can also be configured via :ref:`config command line interface <sec-configuration-cli>`.

.. _sec-configuration-config_yaml-accesscontrol:

Access Control
--------------

Defaults
........

.. pydantic-example:: octoprint.schema.config.access_control.AccessControlConfig
   :key: accessControl

Data model
..........

.. pydantic-table:: octoprint.schema.config.access_control.AccessControlConfig

.. _sec-configuration-config_yaml-api:

API
---

Settings for the REST API.

Defaults
........

.. pydantic-example:: octoprint.schema.config.api.ApiConfig
   :key: api

Data model
..........

.. pydantic-table:: octoprint.schema.config.api.ApiConfig

.. _sec-configuration-config_yaml-appearance:

Appearance
----------

Use the following settings to tweak OctoPrint's appearance a bit to better distinguish multiple instances/printers
appearance or to modify the order and presence of the various UI components.

Defaults
........

.. pydantic-example:: octoprint.schema.config.appearance.AppearanceConfig
   :key: appearance

Data model
..........

.. pydantic-table:: octoprint.schema.config.appearance.AppearanceConfig

Notes
.....

.. note::

   By modifying the ``components`` > ``order`` lists you may reorder OctoPrint's UI components as you like. You can also
   inject Plugins at another than their default location in their respective container by adding the entry
   ``plugin_<plugin identifier>`` where you want them to appear.

   Example: If you want the tab of the :ref:`Hello World Plugin <sec-plugins-gettingstarted>` to appear as the first tab
   in OctoPrint, you'd need to redefine ``components`` > ``order`` > ``tab`` by including something like this in your
   ``config.yaml``:

   .. code-block:: yaml

      appearance:
        components:
          order:
            tab:
            - plugin_helloworld

   OctoPrint will then display the tabs in the order ``plugin_helloworld``, ``temperature``, ``control``, ``plugin_gcodeviewer``,
   ``terminal``, ``timelapse`` plus any other plugins.


.. _sec-configuration-config_yaml-controls:

Controls
--------

``controls`` is a list, with each entry in the list being a dictionary describing either a control or a container.

Defaults
........

.. code-block:: yaml

   controls: []


Data Model
..........

Controls

.. pydantic-table:: octoprint.schema.config.controls.CustomControl

   octoprint.schema.config.controls.CustomControlInput = Input

Containers

.. pydantic-table:: octoprint.schema.config.controls.CustomControlContainer

   octoprint.schema.config.controls.CustomControl = Control
   octoprint.schema.config.controls.CustomControlContainer = Container

Inputs

.. pydantic-table:: octoprint.schema.config.controls.CustomControlInput

   octoprint.schema.config.controls.CustomControlSlider = CustomControlSlider

Sliders

.. pydantic-table:: octoprint.schema.config.controls.CustomControlSlider

Example
.......

.. code-block:: yaml

   controls:
     - name: Fan
       layout: horizontal
       children:
         - name: Enable Fan
           type: parametric_command
           command: M106 S%(speed)s
           input:
             - name: Speed (0-255)
               parameter: speed
               default: 255
         - name: Disable Fan
           type: command
           command: M107

.. _sec-configuration-config_yaml-devel:

Development settings
--------------------

The following settings are only relevant to you if you want to do OctoPrint development.

Defaults
........

.. pydantic-example:: octoprint.schema.config.devel.DevelConfig
   :key: devel

Data model
..........

.. pydantic-table:: octoprint.schema.config.devel.DevelConfig

.. _sec-configuration-config_yaml-estimation:

Estimation
----------

Defaults
........

.. pydantic-example:: octoprint.schema.config.estimation.EstimationConfig
   :key: estimation

Data model
..........

.. pydantic-table:: octoprint.schema.config.estimation.EstimationConfig

.. _sec-configuration-config_yaml-events:

Events
------

Use the following settings to add shell/gcode commands to be executed on certain :ref:`events <sec-events>`.

Defaults
........

.. pydantic-example:: octoprint.schema.config.events.EventsConfig
   :key: event

Data model
..........

.. pydantic-table:: octoprint.schema.config.events.EventsConfig

   octoprint.schema.config.events.EventSubscription = EventSubscription

The individual event subscriptions have to be defined like this:

.. pydantic-table:: octoprint.schema.config.events.EventSubscription

Notes
.....

.. note::

   For debugging purposes, you can also add an additional property ``debug`` to your event subscription definitions
   that if set to true will make the event handler print a log line with your subscription's command after performing
   all placeholder replacements. Example:

   .. code-block:: yaml

      events:
        subscriptions:
        - event: Startup
          command: "logger 'OctoPrint started up'"
          type: system
          debug: true

   This will be logged in OctoPrint's logfile as

   .. code-block:: none

      Executing System Command: logger 'OctoPrint started up'

Example
.......

.. code-block:: yaml

   events:
   subscriptions:
     # example event consumer that prints a message to the system log if the printer is disconnected
     - event: Disconnected
       command: "logger 'Printer got disconnected'"
       type: system

     # example event consumer that queries printer information from the firmware, prints a "Connected"
     # message to the LCD and homes the print head upon established printer connection, disabled though
     - event: Connected
       command: M115,M117 printer connected!,G28
       type: gcode
       enabled: False

.. _sec-configuration-config_yaml-feature:

Feature
-------

Use the following settings to enable or disable OctoPrint features.

Defaults
........

.. pydantic-example:: octoprint.schema.config.feature.FeatureConfig
   :key: feature

Data model
..........

.. pydantic-table:: octoprint.schema.config.feature.FeatureConfig

.. _sec-configuration-config_yaml-folder:

Folder
------

Use the following settings to set custom paths for folders used by OctoPrint.

Defaults
........

.. pydantic-example:: octoprint.schema.config.folder.FolderConfig
   :key: folder

Data model
..........

.. pydantic-table:: octoprint.schema.config.folder.FolderConfig

.. _sec-configuration-config_yaml-gcodeanalysis:

GCODE Analysis
--------------

Settings pertaining to the server side GCODE analysis implementation.

.. pydantic-example:: octoprint.schema.config.gcode_analysis.GcodeAnalysisConfig
   :key: gcode_analysis

.. pydantic-table:: octoprint.schema.config.gcode_analysis.GcodeAnalysisConfig

.. _sec-configuration-config_yaml-plugins:

Plugin settings
---------------

The ``plugins`` section is where plugins can store their specific settings. It is also where the installed but disabled
plugins are tracked.

.. pydantic-example:: octoprint.schema.config.plugins.PluginsConfig
   :key: plugins

.. pydantic-table:: octoprint.schema.config.plugins.PluginsConfig

Additionally to the fields listed here, ``plugins`` will contain further keys for each plugin that is storing settings itself. The keys will be the plugin's identifier.

Example
.......

.. code-block:: yaml

   plugins:
   _disabled:
     - some_plugin
   _forcedCompatible:
     - some_other_plugin
   _sortingOrder:
     yet_another_plugin:
       octoprint.plugin.ordertest.callback: 1
       StartupPlugin.on_startup: 10
   virtual_printer:
     _config_version: 1
     enabled: true

.. _sec-configuration-config_yaml-printerparameters:

Printer Parameters
------------------

Defaults
........

.. pydantic-example:: octoprint.schema.config.printer_parameters.PrinterParametersConfig
   :key: printerParameters

Data model
..........

.. pydantic-table:: octoprint.schema.config.printer_parameters.PrinterParametersConfig


.. _sec-configuration-config_yaml-printerprofiles:

Printer Profiles
----------------

Defaults settings for printer profiles.

Defaults
........

.. pydantic-example:: octoprint.schema.config.printer_profiles.PrinterProfilesConfig
   :key: printerProfiles

Data model
..........

.. pydantic-table:: octoprint.schema.config.printer_profiles.PrinterProfilesConfig

.. _sec-configuration-config_yaml-scripts:

Scripts
-------

Default scripts and snippets. You'd usually not edit the ``config.yaml`` file to adjust those but instead create the
corresponding files in ``~/.octoprint/scripts/``. See :ref:`GCODE Script <sec-features-gcode_scripts>`.

Defaults
........

.. pydantic-example:: octoprint.schema.config.scripts.ScriptsConfig
   :key: scripts

Data model
..........

.. pydantic-table:: octoprint.schema.config.scripts.ScriptsConfig

.. _sec-configuration-config_yaml-serial:

Serial
------

The serial settings have been moved into the bundled "Serial Connector" plugin.

.. _sec-configuration-config_yaml-server:

Server
------

Use the following settings to configure the server.

Defaults
........

.. pydantic-example:: octoprint.schema.config.server.ServerConfig
   :key: server

Data model
..........

.. pydantic-table:: octoprint.schema.config.server.ServerConfig

   octoprint.schema.config.server.PythonEolEntry = PythonEolEntry

Python EOL Check fallback data

.. pydantic-table:: octoprint.schema.config.server.PythonEolEntry

Notes
.....

.. note::

   If you want to run OctoPrint behind a reverse proxy such as HAProxy or Nginx and use a different base URL than the
   server root ``/`` you have two options to achieve this. One approach is using the configuration settings ``baseUrl`` and
   ``scheme`` mentioned above in which OctoPrint will only work under the configured base URL.

   The second and better approach is to make your proxy send a couple of custom headers with each forwarded requests:

   * ``X-Script-Name``: should contain your custom baseUrl (absolute server path), e.g. ``/octoprint``
   * ``X-Scheme``: should contain your custom URL scheme to use (if different from ``http``), e.g. ``https``

   If you use these headers OctoPrint will work both via the reverse proxy as well as when called directly. Take a look
   `into OctoPrint's wiki <https://community.octoprint.org/t/reverse-proxy-configuration-examples/1107>`_ for some
   examples on how to configure this.

.. note::

   If you want to embed OctoPrint in a frame, you'll need to set ``allowFraming`` to ``true`` or your browser will
   prevent this.

   In future browser builds you will also have to make sure you frame is on the same domain as OctoPrint or that
   OctoPrint is served via https through a reverse proxy and has set ``cookies.secure`` to ``true`` or your browser
   will refuse to persist cookies and logging in will not work.

   See also `Cookies default to SameSite=Lax <https://www.chromestatus.com/feature/5088147346030592>`_ and
   `Reject insecure SameSite=None cookies  <https://www.chromestatus.com/feature/5633521622188032>`_ as well as
   `this ticket <https://github.com/OctoPrint/OctoPrint/issues/3482>`_ on why OctoPrint cannot
   solve this on its own/ship with https that doesn't cause scary warnings in your browser.

.. _sec-configuration-config_yaml-slicing:

Slicing
-------

Settings for the built-in slicing support.

Defaults
........

.. pydantic-example:: octoprint.schema.config.slicing.SlicingConfig
   :key: slicing

Data model
..........

.. pydantic-table:: octoprint.schema.config.slicing.SlicingConfig

.. _sec-configuration-config_yaml-system:

System
------

Use the following settings to add custom system commands to the "System" dropdown within OctoPrint's top bar.

Defaults
........

.. pydantic-example:: octoprint.schema.config.system.SystemConfig
   :key: system

Data model
..........

.. pydantic-table:: octoprint.schema.config.system.SystemConfig

   octoprint.schema.config.system.ActionConfig = Action

Actions consist of a ``name`` shown to the user, an ``action`` identifier used by the code and the actual
``command`` including any argument needed for its execution.
By default OctoPrint blocks until the command has returned so that the exit code can be used to show a success
or failure message; use the flag ``async: true`` for commands that don't return.

Optionally you can add a confirmation message to display before actually executing the command (should be set to 
False if a confirmation dialog is not desired).

.. pydantic-table:: octoprint.schema.config.system.ActionConfig

Example
.......

The following example defines a command for shutting down the system under Linux. It assumes that the user under which
OctoPrint is running is allowed to do this without password entry:

.. code-block:: yaml

   system:
     actions:
     - name: Shutdown
       action: shutdown
       command: sudo shutdown -h now
       confirm: You are about to shutdown the system.

You can also add a divider by setting action to divider like this:

.. code-block:: yaml

   system:
     actions:
     - action: divider


.. _sec-configuration-config_yaml-temperature:

Temperature
-----------

Use the following settings to configure temperature profiles which will be displayed in the temperature tab.

Defaults
........

.. pydantic-example:: octoprint.schema.config.temperature.TemperatureConfig
   :key: temperature

Data model
..........

.. pydantic-table:: octoprint.schema.config.temperature.TemperatureConfig

   octoprint.schema.config.temperature.TemperatureProfile = Profile

The individual temperature profiles are defined like this:

.. pydantic-table:: octoprint.schema.config.temperature.TemperatureProfile

.. _sec-configuration-config_yaml-terminalfilters:

Terminal Filters
----------------

Use the following settings to define a set of terminal filters to display in the terminal tab for filtering certain
lines from the display terminal log.

Defaults
........

.. pydantic-example:: octoprint.schema.config.DEFAULT_TERMINAL_FILTERS
   :key: terminalFilters

Data model
..........

Each filter entry in the list is a dictionary with the following keys:

.. pydantic-table:: octoprint.schema.config.TerminalFilterEntry

.. _sec-configuration-config_yaml-webcam:

Webcam
------

Use the following settings to configure webcam support:

.. pydantic-example:: octoprint.schema.config.webcam.WebcamConfig
   :key: webcam

.. pydantic-table:: octoprint.schema.config.webcam.WebcamConfig
