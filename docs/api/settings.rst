.. _sec-api-settings:

********
Settings
********

.. contents::

.. _sec-api-settings-retrieve:

Retrieve current settings
=========================

.. http:get:: /api/settings

   Retrieves the current configuration of OctoPrint.

   Returns a :http:statuscode:`200` with the current settings as a JSON object in the
   response body.

   The :ref:`data model <sec-api-settings-datamodel>` is similar to what can be found in
   :ref:`config.yaml <sec-configuration-config_yaml>`, see below for details.

.. _sec-api-settings-save:

Save settings
=============

.. http:post:: /api/settings

   Saves the provided settings in OctoPrint.

   Expects a JSON object with the settings to change as request body. This can be either a
   full settings tree, or only a partial tree containing only those fields that should
   be updated.

   Returns the currently active settings on success, as part of a :http:statuscode:`200` response.

   Requires admin rights.

   **Example**

   Only change the UI color to black.

   .. sourcecode:: http

      POST /api/settings HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...
      Content-Type: application/json

      {
        "appearance": {
          "color": "black"
        }
      }

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "api": {
          "enabled": true
        },
        "appearance": {
          "color": "black"
        }
      }

.. _sec-api-settings-generateapikey:

Regenerate the system wide API key
==================================

.. http:post:: /api/settings/apikey

   Generates a new system wide API key.

   Does not expect a body. Will return the generated API key as ``apikey``
   property in the JSON object contained in the response body.

   Requires admin rights.

   :status 200:     No error
   :status 403:     No admin rights

.. _sec-api-settings-datamodel:

Data model
==========

The data model on the settings API mostly reflects the contents of
:ref:`config.yaml <sec-configuration-config_yaml>`. The settings tree
returned by the API contains the following fields, which are directly
mapped from the same fields in ``config.yaml`` unless otherwise noted:

.. list-table::
   :header-rows: 1

   * - Field
     - Notes
   * - ``api.enabled``
     -
   * - ``api.key``
     - Only maps to ``api.key`` in ``config.yaml`` if request is sent with admin rights, set to ``n/a`` otherwise.
       Starting with OctoPrint 1.3.3 setting this field via :ref:`the API <sec-api-settings-save>` is not possible,
       only :ref:`regenerting it <sec-api-settings-generateapikey>` is supported. Setting a custom value is only
       possible through `config.yaml`.
   * - ``api.allowCrossOrigin``
     -
   * - ``appearance.name``
     -
   * - ``appearance.color``
     -
   * - ``appearance.colorTransparent``
     -
   * - ``appearance.defaultLanguage``
     -
   * - ``appearance.showFahrenheitAlso``
     -
   * - ``feature.gcodeViewer``
     - Maps to ``gcodeViewer.enabled`` in ``config.yaml``
   * - ``feature.sizeThreshold``
     - Maps to ``gcodeViewer.sizeThreshold`` in ``config.yaml``
   * - ``feature.mobileSizeThreshold``
     - Maps to ``gcodeViewer.mobileSizeThreshold`` in ``config.yaml``
   * - ``feature.temperatureGraph``
     -
   * - ``feature.waitForStart``
     -
   * - ``feature.alwaysSendChecksum``
     -
   * - ``feature.neverSendChecksum``
     -
   * - ``feature.sdSupport``
     -
   * - ``feature.sdReleativePath``
     -
   * - ``feature.sdAlwaysAvailable``
     -
   * - ``feature.swallowOkAfterResend``
     -
   * - ``feature.repetierTargetTemp``
     -
   * - ``feature.externalHeatupDetection``
     -
   * - ``feature.keyboardControl``
     -
   * - ``feature.pollWatched``
     -
   * - ``feature.ignoreIdenticalResends``
     -
   * - ``feature.modelSizeDetection``
     -
   * - ``feature.firmwareDetection``
     -
   * - ``feature.printCancelConfirmation``
     -
   * - ``feature.blockWhileDwelling``
     -
   * - ``folder.uploads``
     -
   * - ``folder.timelapse``
     -
   * - ``folder.timelapseTmp``
     - Maps to ``folder.timelapse_tmp`` in ``config.yaml``
   * - ``folder.logs``
     -
   * - ``folder.watched``
     -
   * - ``plugins``
     - Plugin settings as available from ``config.yaml`` and :class:`~octoprint.plugin.SettingsPlugin` implementations
   * - ``printer.defaultExtrusionLength``
     - Maps to ``printerParameters.defaultExtrusionLength`` in ``config.yaml``
   * - ``scripts.gcode``
     - Whole subtree of configured :ref:`GCODE scripts <sec-features-gcode_scripts>`
   * - ``serial.port``
     - Current serial port
   * - ``serial.baudrate``
     - Current serial baudrate
   * - ``serial.portOptions``
     - Available serial ports
   * - ``serial.baudrateOptions``
     - Available serial baudrates
   * - ``serial.autoconnect``
     -
   * - ``serial.timeoutConnection``
     - Maps to ``serial.timeout.connection`` in ``config.yaml``
   * - ``serial.timeoutDetection``
     - Maps to ``serial.timeout.detection`` in ``config.yaml``
   * - ``serial.timeoutCommunication``
     - Maps to ``serial.timeout.communication`` in ``config.yaml``
   * - ``serial.timeoutTemperature``
     - Maps to ``serial.timeout.temperature`` in ``config.yaml``
   * - ``serial.timeoutTemperatureTargetSet``
     - Maps to ``serial.timeout.temperatureTargetSet`` in ``config.yaml``
   * - ``serial.timeoutSdStatus``
     - Maps to ``serial.timeout.sdStatus`` in ``config.yaml``
   * - ``serial.log``
     -
   * - ``serial.additionalPorts``
     -
   * - ``serial.additionalBaudrates``
     -
   * - ``serial.longRunningCommands``
     -
   * - ``serial.checksumRequiringCommands``
     -
   * - ``serial.helloCommand``
     -
   * - ``serial.ignoreErrorsFromFirmware``
     -
   * - ``serial.disconnectOnErrors``
     -
   * - ``serial.triggerOkForM29``
     -
   * - ``serial.supportResendsWIthoutOk``
     -
   * - ``serial.maxTimeoutsIdle``
     - Maps to ``serial.maxCommunicationTimeouts.idle`` in ``config.yaml``
   * - ``serial.maxTimeoutsPrinting``
     - Maps to ``serial.maxCommunicationTimeouts.printing`` in ``config.yaml``
   * - ``serial.maxTimeoutsLong``
     - Maps to ``serial.maxCommunicationTimeouts.long`` in ``config.yaml``
   * - ``server.commands.systemShutdownCommand``
     -
   * - ``server.commands.systemRestartCommand``
     -
   * - ``server.commands.serverRestartCommand``
     -
   * - ``server.diskspace.warning``
     -
   * - ``server.diskspace.critical``
     -
   * - ``system.actions``
     - Whole subtree taken from ``config.yaml``
   * - ``system.events``
     - Whole subtree taken from ``config.yaml``
   * - ``temperature.profiles``
     - Whole subtree taken from ``config.yaml``
   * - ``temperature.cutoff``
     -
   * - ``terminalFilters``
     - Whole subtree taken from ``config.yaml``
   * - ``webcam.streamUrl``
     - Maps to ``webcam.stream`` in ``config.yaml``
   * - ``webcam.snapshotUrl``
     - Maps to ``webcam.snapshot`` in ``config.yaml``
   * - ``webcam.ffmpegPath``
     - Maps to ``webcam.ffmpeg`` in ``config.yaml``
   * - ``webcam.bitrate``
     -
   * - ``webcam.ffmpegThreads``
     -
   * - ``webcam.watermark``
     -
   * - ``webcam.flipH``
     -
   * - ``webcam.flipV``
     -
   * - ``webcam.rotate90``
     -
