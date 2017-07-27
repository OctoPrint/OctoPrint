.. _sec-configuration-config_yaml:

config.yaml
===========

If not specified via the command line, the main configuration file ``config.yaml`` for OctoPrint is expected in its
settings folder, which unless defined differently via the command line is located at ``~/.octoprint`` on Linux, at
``%APPDATA%/OctoPrint`` on Windows and at ``~/Library/Application Support/OctoPrint`` on MacOS. If the file is not there,
you can just create it - it will only get created by OctoPrint once you save settings that deviate from the default
settings.

Note that many of these settings are available from the "Settings" menu in OctoPrint itself.

.. contents::

.. _sec-configuration-config_yaml-accesscontrol:

Access Control
--------------

Use the following settings to enable access control:

.. code-block:: yaml

   accessControl:
     # whether to enable access control or not. Defaults to true
     enabled: true

     # The user manager implementation to use for accessing user information. Currently only a filebased
     # user manager is implemented which stores configured accounts in a YAML file (Default: users.yaml
     # in the default configuration folder, see below)
     userManager: octoprint.users.FilebasedUserManager

     # The YAML user file to use. If left out defaults to users.yaml in the default configuration folder.
     userFile: /path/to/users.yaml

     # If set to true, will automatically log on clients originating from any of the networks defined in
     # "localNetworks" as the user defined in "autologinAs". Defaults to false.
     autologinLocal: true

     # The name of the user to automatically log on clients originating from "localNetworks" as. Must
     # be the name of one of your configured users.
     autologinAs: someUser

     # A list of networks or IPs for which an automatic logon as the user defined in "autologinAs" will
     # take place. If available OctoPrint will evaluate the "X-Forwarded-For" HTTP header for determining
     # the client's IP address (see https://code.google.com/p/haproxy-docs/wiki/forwardfor on how to
     # configure the sending of this header in HAProxy). Defaults to 127.0.0.0/8 (so basically anything
     # originating from localhost).
     localNetworks:
     - 127.0.0.0/8
     - 192.168.1.0/24

.. _sec-configuration-config_yaml-api:

API
---

Settings for the REST API:

.. code-block:: yaml

   api:
     # Whether to enable the API
     enabled: True

     # Current API key needed for accessing the API
     key: ...

     # Whether to allow cross origin access to the API or not
     allowCrossOrigin: false

     # Additional app api keys, see REST API > Apps in the docs
     apps:
       "some.app.identifier:some_version":
         pubkey: <RSA pubkey>
         enabled: true

.. _sec-configuration-config_yaml-appearance:

Appearance
----------

Use the following settings to tweak OctoPrint's appearance a bit to better distinguish multiple instances/printers
appearance or to modify the order and presence of the various UI components:

.. code-block:: yaml

   appearance:
     # Use this to give your printer a name. It will be displayed in the title bar
     # (as "<Name> [OctoPrint]") and in the navigation bar (as "OctoPrint: <Name>")
     name: My Printer

     # Use this to color the navigation bar. Supported colors are red, orange,
     # yellow, green, blue, violet and default.
     color: default

     # Makes the color of the navigation bar "transparent". In case your printer uses
     # acrylic for its frame ;)
     colorTransparent: false

     # Configures the order and availability of the UI components
     components:

       # Defines the order of the components within their respective containers.
       #
       # If overridden by the user the resulting order for display will be calculated as
       # follows:
       #
       # - first all components as defined by the user
       # - then all enabled core components as define in the default order (see below)
       #
       # Components not contained within the default order (e.g. from plugins) will be either
       # prepended or appended to that result, depending on component type.
       #
       # Note that a component is not included in the order as defined by the user will still
       # be put into the container, according to the default order. To fully disable a
       # component, you'll need to add it to the container's disabled list further below.
       order:

         # order of navbar items
         navbar:
         - settings
         - systemmenu
         - login

         # order of sidebar items
         sidebar:
         - connection
         - state
         - files

         # order of tab items
         tab:
         - temperature
         - control
         - gcodeviewer
         - terminal
         - timelapse

         # order of settings, if settings plugins are registered gets extended internally by
         # section_plugins and all settings plugins
         settings
         - section_printer
         - serial
         - printerprofiles
         - temperatures
         - terminalfilters
         - gcodescripts
         - section_features
         - features
         - webcam
         - accesscontrol
         - api
         - section_octoprint
         - folders
         - appearance
         - logs

         # order of user settings
         usersettings:
         - access
         - interface

         # order of generic templates
         generic: []

       # Disabled components per container. If a component is included here it will not
       # be included in OctoPrint's UI at all. Note that this might mean that critical
       # functionality will not be available if no replacement is registered.
       disabled:
         navbar: []
         sidebar: []
         tab: []
         settings: []
         usersettings: []
         generic: []

     # Default language of OctoPrint. If left unset OctoPrint will try to match up available
     # languages with the user's browser settings.
     defaultLanguage: null

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

   OctoPrint will then turn this into the order ``plugin_helloworld``, ``temperature``, ``control``, ``gcodeviewer``,
   ``terminal``, ``timelapse`` plus any other plugins.


.. _sec-configuration-config_yaml-controls:

Controls
--------

Use the ``controls`` section to add :ref:`custom controls <sec-features-custom_controls>` to the "Controls" tab within
OctoPrint.

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

The following settings are only relevant to you if you want to do OctoPrint development:

.. code-block:: yaml

   # Settings only relevant for development
   devel:
     # Settings for OctoPrint's internal caching
     cache:
       # Whether to enable caching. Defaults to true. Setting it to false will cause the UI to always
       # be fully rerendered on request to / on the server.
       enabled: true

       # Whether to enable the preemptive cache
       preemptive: true

     # Settings for stylesheet preference. OctoPrint will prefer to use the stylesheet type
     # specified here. Usually (on a production install) that will be the compiled css (default).
     # Developers may specify less here too.
     stylesheet: css

     # Settings for OctoPrint's web asset merging and minifying
     webassets:
       # If set to true, OctoPrint will merge all JS, all CSS and all Less files into one file per type
       # to reduce request count. Setting it to false will load all assets individually. Note: if this is set to
       # false, no minification will take place regardless of the minify setting below.
       bundle: true

       # If set to true, OctoPrint will minify its viewmodels (that includes those of plugins). Note: if bundle is
       # set to false, no minification will take place either.
       minify: true

       # Whether to delete generated web assets on server startup (forcing a regeneration)
       clean_on_startup: true

     # Settings for the virtual printer
     virtualPrinter:

       # Whether to enable the virtual printer and include it in the list of available serial connections.
       # Defaults to false.
       enabled: true

       # Whether to send an additional "ok" after a resend request (like Repetier)
       okAfterResend: false

       # Whether to force checksums and line number in the communication (like Repetier), if set to true
       # printer will only accept commands that come with linenumber and checksum and throw an error for
       # lines that don't. Defaults to false
       forceChecksum: false

       # Whether to send "ok" responses with the line number that gets acknowledged by the "ok". Defaults
       # to false.
       okWithLinenumber: false

       # Number of extruders to simulate on the virtual printer.
       numExtruders: 1

       # Whether to include the current tool temperature in the M105 output as separate T segment or not.
       #
       # True:  > M105
       #        < ok T:23.5/0.0 T0:34.3/0.0 T1:23.5/0.0 B:43.2/0.0
       # False: > M105
       #        < ok T0:34.3/0.0 T1:23.5/0.0 B:43.2/0.0
       includeCurrentToolInTemps: true

       # Whether to include the selected filename in the M23 File opened response.
       #
       # True:  > M23 filename.gcode
       #        < File opened: filename.gcode  Size: 27
       # False: > M23 filename.gcode
       #        > File opened
       includeFilenameInOpened: true

       # The maximum movement speeds of the simulated printer's axes, in mm/s
       movementSpeed:
         x: 6000
         y: 6000
         z: 200
         e: 300

       # Whether the simulated printer should also simulate a heated bed or not
       hasBed: true

       # If enabled, reports the set target temperatures as separate messages from the firmware
       #
       # True:  > M109 S220.0
       #        < TargetExtr0:220.0
       #        < ok
       #        > M105
       #        < ok T0:34.3 T1:23.5 B:43.2
       # False: > M109 S220.0
       #        < ok
       #        > M105
       #        < ok T0:34.3/220.0 T1:23.5/0.0 B:43.2/0.0
       repetierStyleTargetTemperature: false

       # If enabled, uses repetier style resends, sending multiple resends for the same line
       # to make sure nothing gets lost on the line
       repetierStyleResends: false

       # If enabled, reports the first extruder in M105 responses as T instead of T0
       #
       # True:  > M105
       #        < ok T:34.3/0.0 T1:23.5/0.0 B:43.2/0.0
       # False: > M105
       #        < ok T0:34.3/0.0 T1:23.5/0.0 B:43.2/0.0
       smoothieTemperatureReporting: false

       # Whether M20 responses will include filesize or not
       #
       # True:  <filename> <filesize in bytes>
       # False: <filename>
       extendedSdFileList: false

       # Forced pause for retrieving from the outgoing buffer
       throttle: 0.01

       # Whether to send "wait" responses every "waitInterval" seconds when serial rx buffer is empty
       sendWait: false

       # Interval in which to send "wait" lines when rx buffer is empty
       waitInterval: 1

       # Size of the simulated RX buffer in bytes, when it's full a send from OctoPrint's
       # side will block
       rxBuffer: 64

       # Size of simulated command buffer
       commandBuffer: 4

       # Whether to support the M112 command with simulated kill
       supportM112: true

       # Whether to send messages received via M117 back as "echo:" lines
       echoOnM117: true

       # Whether to simulate broken M29 behaviour (missing ok after response)
       brokenM29: true

.. _sec-configuration-config_yaml-estimation:

Estimation
----------

The following settings provide parameters for estimators within OctoPrint. Currently only
the estimation of the left print time during an active job utilizes this section.

.. code-block:: yaml

   estimation:
     # Parameters for the print time estmation during an ongoing print job
     printTime:
       # Until which percentage to do a weighted mixture of statistical duration (analysis or
       # past prints) with the result from the calculated estimate if that's already available.
       # Utilized to compensate for the fact that the earlier in a print job, the least accuracy
       # even a stable calculated estimate provides.
       statsWeighingUntil: 0.5

       # Range the assumed percentage (based on current estimated statistical, calculated or mixed
       # total vs elapsed print time so far) needs to be around the actual percentage for the
       # result to be used
       validityRange: 0.15

       # If no estimate could be calculated until this percentage and no statistical data is available,
       # use dumb linear estimate
       forceDumbFromPercent: 0.3

       # If no estimate could be calculated until this many minutes into the print and no statistical
       # data is available, use dumb linear estimate
       forceDumbAfterMin: 30

       # Average fluctuation between individual calculated estimates to consider in stable range. Seconds
       # of difference.
       stableThreshold: 60

.. _sec-configuration-config_yaml-events:

Events
------

Use the following settings to add shell/gcode commands to be executed on certain :ref:`events <sec-events>`:

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

.. _sec-configuration-config_yaml-feature:

Feature
-------

Use the following settings to enable or disable OctoPrint features:

.. code-block:: yaml

   feature:
     # Whether to enable the gcode viewer in the UI or not
     gCodeVisualizer: true

     # Whether to enable the temperature graph in the UI or not
     temperatureGraph: true

     # Specifies whether OctoPrint should wait for the start response from the printer before trying to send commands
     # during connect.
     waitForStartOnConnect: false

     # Specifies whether OctoPrint should send linenumber + checksum with every printer command. Needed for
     # successful communication with Repetier firmware
     alwaysSendChecksum: false

     # Specifies whether OctoPrint should also send linenumber + checksum with commands that are *not*
     # detected as valid GCODE (as in, they do not match the regular expression "^\s*([GM]\d+|T)").
     sendChecksumWithUnknownCommands: false

     # Specifies whether OctoPrint should also use up acknowledgments ("ok") for commands that are *not*
     # detected as valid GCODE (as in, they do not match the regular expression "^\s*([GM]\d+|T)").
     unknownCommandsNeedAck: false

     # Whether to ignore the first ok after a resend response. Needed for successful communication with
     # Repetier firmware
     swallowOkAfterResend: false

     # Specifies whether support for SD printing and file management should be enabled
     sdSupport: true

     # Specifies whether firmware expects relative paths for selecting SD files
     sdRelativePath: false

     # Whether to always assume that an SD card is present in the printer.
     # Needed by some firmwares which don't report the SD card status properly.
     sdAlwaysAvailable: false

     # Whether the printer sends repetier style target temperatures in the format
     #   TargetExtr0:<temperature>
     # instead of attaching that information to the regular M105 responses
     repetierTargetTemp: false

     # Whether to enable external heatup detection (to detect heatup triggered e.g. through the printer's LCD panel or
     # while printing from SD) or not. Causes issues with Repetier's "first ok then response" approach to
     # communication, so disable for printers running Repetier firmware.
     externalHeatupDetection: true

     # Whether to enable the keyboard control feature in the control tab
     keyboardControl: true

     # Whether to actively poll the watched folder (true) or to rely on the OS's file system
     # notifications instead (false)
     pollWatched: false

     # Whether to ignore identical resends from the printer (true, repetier) or not (false)
     ignoreIdenticalResends: false

     # If ignoredIdenticalResends is true, how many consecutive identical resends to ignore
     identicalResendsCount: 7

     # Whether to support F on its own as a valid GCODE command (true) or not (false)
     supportFAsCommand: false

     # Whether to enable model size detection and warning (true) or not (false)
     modelSizeDetection: true

     # Whether to attempt to auto detect the firmware of the printer and adjust settings
     # accordingly (true) or not and rely on manual configuration (false)
     firmwareDetection: true

     # Whether to show a confirmation on print cancelling (true) or not (false)
     printCancelConfirmation: true

     # Whether to block all sending to the printer while a G4 (dwell) command is active (true, repetier)
     # or not (false)
     blockWhileDwelling: false

.. _sec-configuration-config_yaml-folder:

Folder
------

Use the following settings to set custom paths for folders used by OctoPrint:

.. code-block:: yaml

   folder:
     # Absolute path where to store gcode uploads. Defaults to the uploads folder in the OctoPrint settings folder
     uploads: /path/to/upload/folder

     # Absolute path where to store finished timelapse recordings. Defaults to the timelapse folder in the OctoPrint
     # settings dir
     timelapse: /path/to/timelapse/folder

     # Absolute path where to store temporary timelapse files. Defaults to the timelapse/tmp folder in the OctoPrint
     # settings dir
     timelapse_tmp: /path/to/timelapse/tmp/folder

     # Absolute path where to store log files. Defaults to the logs folder in the OctoPrint settings dir
     logs: /path/to/logs/folder

     # Absolute path to the virtual printer's simulated SD card. Only useful for development, just ignore
     # it otherwise
     virtualSd: /path/to/virtualSd/folder

     # Absolute path to a folder being watched for new files which then get automatically
     # added to OctoPrint (and deleted from that folder). Can e.g. be used to define a folder which
     # can then be mounted from remote machines and used as local folder for quickly adding downloaded
     # and/or sliced objects to print in the future.
     watched: /path/to/watched/folder

     # Absolute path to a folder where manually installed plugins may reside
     plugins: /path/to/plugins/folder

     # Absolute path where to store slicing profiles
     slicingProfiles: /path/to/slicingProfiles/folder

     # Absolute path where to store printer profiles
     printerProfiles: /path/to/printerProfiles/folder

     # Absolute path where to store (GCODE) scripts
     scripts: /path/to/scripts/folder

.. _sec-configuration-config_yaml-gcodeanalysis:

GCODE Analysis
--------------

Settings pertaining to the server side GCODE analysis implementation.

.. code-block:: yaml

   # Maximum number of extruders to support/to sanity check for
   maxExtruders: 10

   # Pause between each processed GCODE line in normal priority mode, seconds
   throttle_normalprio: 0.01

   # Pause between each processed GCODE line in high priority mode (e.g. on fresh
   # uploads), seconds
   throttle_highprio: 0.0

.. _sec-configuration-config_yaml-gcodeviewer:

GCODE Viewer
------------

Settings pertaining to the built in GCODE Viewer.

.. code-block:: yaml

   # Whether to enable the GCODE viewer in the UI
   enabled: true

   # Maximum size a GCODE file may have on mobile devices to automatically be loaded
   # into the viewer, defaults to 2MB
   mobileSizeThreshold: 2097152

   # Maximum size a GCODE file may have to automatically be loaded into the viewer,
   # defaults to 20MB
   sizeThreshold: 20971520

.. _sec-configuration-config_yaml-plugins:

Plugin settings
---------------

The ``plugins`` section is where plugins can store their specific settings. It is also where the installed but disabled
plugins are tracked:

.. code-block:: yaml

   # Settings for plugins
   plugins:

     # Identifiers of installed but disabled plugins
     _disabled:
     - ...

     # The rest are individual plugin settings, each tracked by their identifier, e.g.:
     some_plugin:
       some_setting: true
       some_other_setting: false

.. _sec-configuration-config_yaml-printerprofiles:

Printer Profiles
----------------

Defaults settings for printer profiles.

.. code-block:: yaml

   # Settings for printer profiles
   printerProfiles:

     # Name of the printer profile to default to
     default: _default

     # Default printer profile
     defaultProfile:
       ...

.. _sec-configuration-config_yaml-scripts:

Scripts
-------

Default scripts and snippets. You'd usually not edit the ``config.yaml`` file to adjust those but instead create the
corresponding files in ``~/.octoprint/scripts/``. See :ref:`GCODE Script <sec-features-gcode_scripts>`.

.. code-block:: yaml

   # Configured scripts
   scripts:

     # GCODE scripts and snippets
     gcode:

       # Script called after OctoPrint connected to the printer.
       afterPrinterConnected:

       # Script called before a print was started.
       beforePrintStarted:

       # Script called after a print was cancelled.
       afterPrintCancelled: "; disable motors\nM84\n\n;disable all heaters\n{% snippet 'disable_hotends' %}\nM140 S0\n\n;disable fan\nM106 S0"

       # Script called after a print was successfully completed.
       afterPrintDone:

       # Script called after a print was paused.
       afterPrintPaused:

       # Script called before a print was resumed.
       beforePrintResumed:

       # Snippets that may be used in scripts
       snippets:
         disable_hotends: "{% for tool in range(printer_profile.extruder.count) %}M104 T{{ tool }} S0\n{% endfor %}"

.. _sec-configuration-config_yaml-serial:

Serial
------

Use the following settings to configure the serial connection to the printer:

.. code-block:: yaml

   serial:
     # Use the following option to define the default serial port, defaults to unset (= AUTO)
     port: /dev/ttyACM0

     # Use the following option to define the default baudrate, defaults to unset (= AUTO)
     baudrate: 115200

     # Whether to automatically connect to the printer on server startup (if available)
     autoconnect: false

     # Whether to log whole communication to serial.log (warning: might decrease performance)
     log: false

     # Timeouts used for the serial connection to the printer, you might want to adjust these if you are
     # experiencing connection problems
     timeout:

       # Timeout for waiting for a response from the currently tested port during autodetect, in seconds.
       # Defaults to 0.5 sec
       detection: 0.5

       # Timeout for waiting to establish a connection with the selected port, in seconds.
       # Defaults to 2 sec
       connection: 2

       # Timeout during serial communication, in seconds.
       # Defaults to 30 sec
       communication: 30

       # Timeout after which to query temperature when no target is set
       temperature: 5

       # Timeout after which to query temperature when a target is set
       temperatureTargetSet: 2

       # Timeout after which to query the SD status while SD printing
       sdStatus: 1

     # Maximum number of consecutive communication timeouts after which the printer will be considered
     # dead and OctoPrint disconnects with an error.
     maxCommunicationTimeouts:

       # max. timeouts when the printer is idle
       idle: 2

       # max. timeouts when the printer is printing
       printing: 5

       # max. timeouts when a long running command is active
       long: 5

     # Maximum number of write attempts to serial during which nothing can be written before the communication
     # with the printer is considered dead and OctoPrint will disconnect with an error
     maxWritePasses:

     # Use this to define additional patterns to consider for serial port listing. Must be a valid
     # "glob" pattern (see http://docs.python.org/2/library/glob.html). Defaults to not set.
     additionalPorts:
     - /dev/myPrinterSymlink

     # Use this to define additional baud rates to offer for connecting to serial ports. Must be a
     # valid integer. Defaults to not set
     additionalBaudrates:
     - 123456

     # Commands which are known to take a long time to be acknowledged by the firmware. E.g.
     # homing, dwelling, auto leveling etc. Defaults to the below commands.
     longRunningCommands:
     - G4
     - G28
     - G29
     - G30
     - G32
     - M400
     - M226
     - M600

     # Commands which need to always be send with a checksum. Defaults to only M110
     checksumRequiringCommands:
     - M110

     # Command to send in order to initiate a handshake with the printer.
     # Defaults to "M110 N0" which simply resets the line numbers in the firmware and which
     # should be acknowledged with a simple "ok".
     helloCommand: M110 N0

     # Whether to disconnect on errors or not
     disconnectOnErrors: true

     # Whether to completely ignore errors from the firmware or not
     ignoreErrorsFromFirmware: false

     # Whether to log resends to octoprint.log or not. Invaluable debug tool without performance
     # impact, leave on if possible please
     logResends: true

     # Whether to support resends without follow-up ok or not
     supportResendsWithoutOk: false

     # Whether to "manually" trigger an ok for M29 (a lot of versions of this command are buggy and
     # the responds skips on the ok)
     triggerOkForM29: true

.. _sec-configuration-config_yaml-server:

Server
------

Use the following settings to configure the server:

.. code-block:: yaml

   server:
     # Use this option to define the host to which to bind the server, defaults to "0.0.0.0" (= all
     # interfaces)
     host: 0.0.0.0

     # Use this option to define the port to which to bind the server, defaults to 5000
     port: 5000

     # If this option is true, OctoPrint will show the First Run wizard and set the setting to
     # false after that completes
     firstRun: false

     # If this option is true, OctoPrint will enable safe mode on the next server start and
     # reset the setting to false
     startOnceInSafeMode: false

     # Secret key for encrypting cookies and such, randomly generated on first run
     secretKey: someSecretKey

     # Settings if OctoPrint is running behind a reverse proxy (haproxy, nginx, apache, ...).
     # These are necessary in order to make OctoPrint generate correct external URLs so
     # that AJAX requests and download URLs work.
     reverseProxy:

       # The request header from which to determine the URL prefix under which OctoPrint
       # is served by the reverse proxy
       prefixHeader: X-Script-Name

       # The request header from which to determine the scheme (http or https) under which
       # a specific request to OctoPrint was made to the reverse proxy
       schemeHeader: X-Scheme

       # The request header from which to determine the host under which OctoPrint
       # is served by the reverse proxy
       hostHeader: X-Forwarded-Host

       # Use this option to define an optional URL prefix (with a leading /, so absolute to your
       # server's root) under which to run OctoPrint. This should only be needed if you want to run
       # OctoPrint behind a reverse proxy under a different root endpoint than `/` and can't configure
       # said reverse proxy to send a prefix HTTP header (X-Script-Name by default, see above) with
       # forwarded requests.
       prefixFallback:

       # Use this option to define an optional forced scheme (http or https) under which to run
       # OctoPrint. This should only be needed if you want to run OctoPrint behind a reverse
       # proxy that also does HTTPS determination but can't configure said reverse proxy to
       # send a scheme HTTP header (X-Scheme by default, see above) with forwarded requests.
       schemeFallback:

       # Use this option to define an optional forced host under which to run OctoPrint. This should
       # only be needed if you want to run OctoPrint behind a reverse proxy with a different hostname
       # than OctoPrint itself but can't configure said reverse proxy to send a host HTTP header
       # (X-Forwarded-Host by default, see above) with forwarded requests.
       hostFallback:

     # Settings for file uploads to OctoPrint, such as maximum allowed file size and
     # header suffixes to use for streaming uploads. OctoPrint does some nifty things internally in
     # order to allow streaming of large file uploads to the application rather than just storing
     # them in memory. For that it needs to do some rewriting of the incoming upload HTTP requests,
     # storing the uploaded file to a temporary location on disk and then sending an internal request
     # to the application containing the original filename and the location of the temporary file.
     uploads:

       # Maximum size of uploaded files in bytes, defaults to 1GB.
       maxSize: 1073741824

       # Suffix used for storing the filename in the file upload headers when streaming uploads.
       nameSuffix: name

       # Suffix used for storing the path to the temporary file in the file upload headers when
       # streaming uploads.
       pathSuffix: path

     # Maximum size of requests other than file uploads in bytes, defaults to 100KB.
     maxSize: 102400

     # Commands to restart/shutdown octoprint or the system it's running on
     commands:

       # Command to restart OctoPrint, defaults to being unset
       serverRestartCommand: sudo service octoprint restart

       # Command to restart the system OctoPrint is running on, defaults to being unset
       systemRestartCommand: sudo shutdown -r now

       # Command to shut down the system OctoPrint is running on, defaults to being unset
       systemShutdownCommand: sudo shutdown -h now

     # Configuration of the regular online connectivity check
     onlineCheck:
       # whether the online check is enabled, defaults to false due to valid privacy concerns
       enabled: false

       # interval in which to check for online connectivity (in seconds)
       interval: 300

       # DNS host against which to check (default: 8.8.8.8 aka Google's DNS)
       host: 8.8.8.8

       # DNS port against which to check (default: 53 - the default DNS port)
       port: 53

     # Settings of when to display what disk space warning
     diskspace:

       # Threshold (bytes) after which to consider disk space becoming sparse,
       # defaults to 500MB
       warning: 63488000

       # Threshold (bytes) after which to consider disk space becoming critical,
       # defaults to 200MB
       critical: 209715200

     # Configuration of the preemptive cache
     preemptiveCache:

       # which server paths to exclude from the preemptive cache
       exceptions:
       - /some/path

       # How many days to leave unused entries in the preemptive cache config
       until: 7


.. note::

   If you want to run OctoPrint behind a reverse proxy such as HAProxy or Nginx and use a different base URL than the
   server root ``/`` you have two options to achieve this. One approach is using the configuration settings ``baseUrl`` and
   ``scheme`` mentioned above in which OctoPrint will only work under the configured base URL.

   The second and better approach is to make your proxy send a couple of custom headers with each forwarded requests:

     * ``X-Script-Name``: should contain your custom baseUrl (absolute server path), e.g. ``/octoprint``
     * ``X-Scheme``: should contain your custom URL scheme to use (if different from ``http``), e.g. ``https``

   If you use these headers OctoPrint will work both via the reverse proxy as well as when called directly. Take a look
   `into OctoPrint's wiki <https://github.com/foosel/OctoPrint/wiki/Reverse-proxy-configuration-examples>`_ for some
   examples on how to configure this.

.. _sec-configuration-config_yaml-slicing:

Slicing
-------

Settings for the built-in slicing support:

.. code-block:: yaml

   # Slicing settings
   slicing:

     # Whether to enable slicing support or not
     enabled:

     # Default slicer to use
     defaultSlicer: cura

     # Default slicing profiles per slicer
     defaultProfiles:
       cura: ...

.. _sec-configuration-config_yaml-system:

System
------

Use the following settings to add custom system commands to the "System" dropdown within OctoPrint's top bar.

Commands consist of a name, an action identifier, the commandline to execute and an optional confirmation message to
display before actually executing the command (should be set to False if a confirmation dialog is not desired).

The following example defines a command for shutting down the system under Linux. It assumes that the user under which
OctoPrint is running is allowed to do this without password entry:

.. code-block:: yaml

   system:
     actions:
     - name: Shutdown
       action: shutdown
       command: sudo shutdown -h now
       confirm: You are about to shutdown the system.

You can also add an divider by setting action to divider like this:

.. code-block:: yaml

   system:
     actions:
     - action: divider


.. _sec-configuration-config_yaml-temperature:

Temperature
-----------

Use the following settings to configure temperature profiles which will be displayed in the temperature tab:

.. code-block:: yaml

   temperature:
     profiles:
     - name: ABS
       extruder: 210
       bed: 100
     - name: PLA
       extruder: 180
       bed: 60

.. _sec-configuration-config_yaml-terminalfilters:

Terminal Filters
----------------

Use the following settings to define a set of terminal filters to display in the terminal tab for filtering certain
lines from the display terminal log.

Use `Javascript regular expressions <https://developer.mozilla.org/en/docs/Web/JavaScript/Guide/Regular_Expressions>`_:

.. code-block:: yaml

   # A list of filters to display in the terminal tab. Defaults to the filters shown below
   terminalFilters:
   - name: Suppress temperature messages
     regex: '(Send: (N\d+\s+)?M105)|(Recv: ok T:)'
   - name: Suppress SD status messages
     regex: '(Send: (N\d+\s+)?M27)|(Recv: SD printing byte)'
   - name: Suppress wait responses
     regex: 'Recv: wait'

.. _sec-configuration-config_yaml-webcam:

Webcam
------

Use the following settings to configure webcam support:

.. code-block:: yaml

   webcam:
     # Use this option to enable display of a webcam stream in the UI, e.g. via MJPG-Streamer.
     # Webcam support will be disabled if not set
     stream: http://<stream host>:<stream port>/?action=stream

     # Use this option to enable timelapse support via snapshot, e.g. via MJPG-Streamer.
     # Timelapse support will be disabled if not set
     snapshot: http://<stream host>:<stream port>/?action=snapshot

     # Path to ffmpeg binary to use for creating timelapse recordings.
     # Timelapse support will be disabled if not set
     ffmpeg: /path/to/ffmpeg

     # Number of how many threads to instruct ffmpeg to use for encoding. Defaults to 1.
     # Should be left at 1 for RPi1.
     ffmpegThreads: 1

     # The bitrate to use for rendering the timelapse video. This gets directly passed to ffmpeg.
     bitrate: 5000k

     # Whether to include a "created with OctoPrint" watermark in the generated timelapse movies
     watermark: true

     # Whether to flip the webcam horizontally
     flipH: false

     # Whether to flip the webcam vertically
     flipV: false

     # Whether to rotate the webcam 90° counter clockwise
     rotate90: false

     # The default timelapse settings.
     timelapse:

       # The timelapse type. Can be either "off", "zchange" or "timed". Defaults to "off"
       type: timed

       # The framerate at which to render the movie
       fps: 25

       # The number of seconds in the rendered video to add after a finished print. The exact way how the
       # additional images will be recorded depends on timelapse type. Timed timelapses continue to
       # record just like at the beginning, so the recording will continue another
       # fps * postRoll * interval seconds. Zchange timelapses will take one final picture and add it fps * postRoll
       postRoll: 0

       # Additional options depending on the timelapse type. All timelapses take a postRoll and an fps setting.
       options:

         # Timed timelapses only: The interval which to leave between images in seconds
         interval: 2

         # Timed timelapses only: Whether to capture the snapshots for the post roll (true) or just copy
         # the last captured snapshot from the print over and over again (false)
         capturePostRoll: true

         # ZChange timelapses only: Z-hop height during retractions to ignore for capturing snapshots
         retractionZHop: 0.0

     # After how many days unrendered timelapses will be deleted
     cleanTmpAfterDays: 7
