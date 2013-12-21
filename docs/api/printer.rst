.. _sec-api-printer:

***************
Printer Control
***************

.. contents::

Printer control is mostly achieved through the use of commands, issued to resources reflecting components of the
printer. OctoPrint currently knows the following components:

Print head
  Print head commands allow jogging and homing the print head in all three axes. See :ref:`sec-api-printer-printheadcommand`.
Heater
  Heater commands allow setting the temperature and temperature offsets for the printer's hotend and bed. Currently
  OctoPrint only supports one hotend heater (this will change in the future). See :ref:`sec-api-printer-heatercommand`.
Feeder
  Feeder commands allow extrusion/extraction of filament. Currently OctoPrint only supports one feeder (this will
  change in a future version). See :ref:`sec-api-printer-feedercommand`.
SD card
  SD commands allow initialization, refresh and release of the printer's SD card (if available). See :ref:`sec-api-printer-sdcommand`.

.. _sec-api-printer-printheadcommand:

Issue a print head command
==========================

.. http:post:: /api/control/printer/printhead

   Print head commands allow jogging and homing the print head in all three axes. Available commands are:

   jog
     Jogs the print head (relatively) by a defined amount in one or more axes. Additional parameters are:

     * ``x``: Optional. Amount to jog print head on x axis, must be a valid number corresponding to the distance to travel in mm.
     * ``y``: Optional. Amount to jog print head on y axis, must be a valid number corresponding to the distance to travel in mm.
     * ``z``: Optional. Amount to jog print head on z axis, must be a valid number corresponding to the distance to travel in mm.

   home
     Homes the print head in all of the given axes. Additional parameters are:

     * ``axes``: A list of axes which to home, valid values are one or more of ``x``, ``y``, ``z``.

   All of these commands may only be sent if the printer is currently operational and not printing. Otherwise a
   :http:statuscode:`409` is returned.

   Upon success, a status code of :http:statuscode:`204` and an empty body is returned.

   **Example Jog Request**

   Jog the print head by 10mm in X, -5mm in Y and 0.02mm in Z.

   .. sourcecode:: http

      POST /api/control/printer/printhead HTTP/1.1
      Host: example.com
      Content-Type: application/json
      X-Api-Key: abcdef...

      {
        "command": "jog",
        "x": 10,
        "y": -5,
        "z": 0.02
      }

   **Example Home Request**

   Home the X and Y axes.

   .. sourcecode:: http

      POST /api/control/printer/printhead HTTP/1.1
      Host: example.com
      Content-Type: application/json
      X-Api-Key: abcdef...

      {
        "command": "home",
        "axes": ["x", "y"]
      }

   :json string command: The command to issue, either ``jog`` or ``home``.
   :json number x:       ``jog`` command: The amount to travel on the X axis in mm.
   :json number y:       ``jog`` command: The amount to travel on the Y axis in mm.
   :json number z:       ``jog`` command: The amount to travel on the Z axis in mm.
   :json array axes:     ``home`` command: The axes which to home, valid values are one or more of ``x``, ``y`` and ``z``.
   :statuscode 204: No error
   :statuscode 400: Invalid axis specified, invalid value for travel amount for a jog command or otherwise invalid
                    request.
   :statuscode 409: If the printer is not operational or currently printing.

.. _sec-api-printer-heatercommand:

Issue a heater command
======================

.. http:post:: /api/control/printer/heater

   Heater commands allow setting the temperature and temperature offsets for the printer's hotend and bed. Available
   commands are:

   temp
     Sets the given target temperature on the printer's hotend and/or bed. Additional parameters:

     * ``temps``: Target temperature(s) to set, allowed properties are:

       * ``hotend``: New target temperature of the printer's hotend in centigrade.
       * ``bed``: New target temperature of the printer's bed in centigrade.

   offset
     Sets the given temperature offset on the printer's hotend and/or bed. Additional parameters:

     * ``offsets``: Offset(s) to set, allowed properties are:

       * ``hotend``: New offset of the printer's hotend temperature in centigrade, max/min of +/-50°C.
       * ``bed``: New offset of the printer's bed temperature in centigrade, max/min of +/-50°C.

   All of these commands may only be sent if the printer is currently operational and not printing. Otherwise a
   :http:statuscode:`409` is returned.

   Upon success, a status code of :http:statuscode:`204` and an empty body is returned.

   **Example Target Temperature Request**

   Set the printer's hotend target temperature to 220°C and the bed target temperature to 75°C.

   .. sourcecode:: http

      POST /api/control/printer/heater HTTP/1.1
      Host: example.com
      Content-Type: application/json
      X-Api-Key: abcdef...

      {
        "command": "temp",
        "temps": {
          "hotend": 220,
          "bed": 75
        }
      }

   **Example Offset Temperature Request**

   Set the offset for hotend temperatures to +10°C and for bed temperatures to -5°C.

   .. sourcecode:: http

      POST /api/control/printer/heater HTTP/1.1
      Host: example.com
      Content-Type: application/json
      X-Api-Key: abcdef...

      {
        "command": "offset",
        "offsets": {
          "hotend": 10,
          "bed": -5
        }
      }

   :json string command: The command to issue, either ``temp`` or ``offset``
   :json object temps:   ``temp`` command: The target temperatures to set. Valid properties are ``hotend`` and ``bed``
   :json object offsets: ``offset`` command: The offset temperature to set. Valid properties are ``hotend`` and ``bed``
   :statuscode 204: No error
   :statuscode 400: If ``temps`` or ``offsets`` contains a property other than ``hotend`` or ``bed``, the
                    target or offset temperature is not a valid number or outside of the supported range, or if the
                    request is otherwise invalid.
   :statuscode 409: If the printer is not operational.

.. _sec-api-printer-feedercommand:

Issue a feeder command
======================

.. http:post:: /api/control/printer/feeder

   Feeder commands allow extrusion/extraction of filament. Available commands are:

   extrude
     Extrudes the given amount of filament. Additional parameters:

     * ``amount``: The amount of filament to extrude in mm. May be negative to retract.

   All of these commands may only be sent if the printer is currently operational and not printing. Otherwise a
   :http:statuscode:`409` is returned.

   Upon success, a status code of :http:statuscode:`204` and an empty body is returned.

   **Example Extrude Request**

   Extrudes 1mm of filament

   .. sourcecode:: http

      POST /api/control/printer/feeder HTTP/1.1
      Host: example.com
      Content-Type: application/json
      X-Api-Key: abcdef...

      {
        "command": "extrude",
        "amount": 1
      }

   **Example Retract Request**

   Retracts 3mm of filament

   .. sourcecode:: http

      POST /api/control/printer/feeder HTTP/1.1
      Host: example.com
      Content-Type: application/json
      X-Api-Key: abcdef...

      {
        "command": "extrude",
        "amount": -3
      }

   :json string command: The command to issue, only ``extrude`` is supported right now.
   :json number amount:  ``extrude`` command: The amount of filament to extrude/retract in mm.
   :statuscode 204: No error
   :statuscode 400: If the value given for `amount` is not a valid number or the request is otherwise invalid.
   :statuscode 409: If the printer is not operational or currently printing.

.. _sec-api-printer-sdcommand:

Issue a SD command
==================

.. http:post:: /api/control/printer/sd

   SD commands allow initialization, refresh and release of the printer's SD card (if available).

   Available commands are:

   init
     Initializes the printer's SD card, making it available for use. This also includes an initial retrieval of the
     list of files currently stored on the SD card, so after issueing that command a :ref:`retrieval of the files
     on SD card <sec-api-fileops-retrieveorigin>` will return a successful result.

     .. note::
        If OctoPrint detects the availability of a SD card on the printer during connection, it will automatically attempt
        to initialize it.

   refresh
     Refreshes the list of files stored on the printer's SD card. Will return a :http:statuscode:`409` if the card
     has not been initialized yet (see the ``init`` command and :ref:`SD state <sec-api-printer-sdstate>`).

   release
     Releases the SD card from the printer. The reverse operation to ``init``. After issuing this command, the SD
     card won't be available anymore, hence and operations targeting files stored on it will fail. Will return a :http:statuscode:`409`
     if the card has not been initialized yet (see the ``init`` command and :ref:`SD state <sec-api-printer-sdstate>`).

   Upon success, a status code of :http:statuscode:`204` and an empty body is returned.

   **Example Init Request**

   .. sourcecode:: http

      POST /api/control/printer/sd HTTP/1.1
      Host: example.com
      Content-Type: application/json
      X-Api-Key: abcdef...

      {
        "command": "init"
      }

   **Example Refresh Request**

   .. sourcecode:: http

      POST /api/control/printer/sd HTTP/1.1
      Host: example.com
      Content-Type: application/json
      X-Api-Key: abcdef...

      {
        "command": "refresh"
      }

   **Example Release Request**

   .. sourcecode:: http

      POST /api/control/printer/sd HTTP/1.1
      Host: example.com
      Content-Type: application/json
      X-Api-Key: abcdef...

      {
        "command": "release"
      }

   :json string command: The command to issue, either ``init``, ``refresh`` or ``release``.
   :statuscode 204:      No error
   :statuscode 409:      If a ``refresh`` or ``release`` command is issued but the SD card has not been initialized (e.g.
                         via ``init``.

.. _sec-api-printer-sdstate:

Retrieve the current SD state
=============================

.. http:get:: /api/control/printer/sd

   Retrieves the current state of the printer's SD card. For this request no authentication is needed.

   If SD support has been disabled in OctoPrint's settings, a :http:statuscode:`404` is returned.

   Returns a :http:statuscode:`200` with an :ref:`SD State Response <sec-api-printer-datamodel-sdstate>` in the body
   upon success.

   **Example Request**

   .. sourcecode:: http

      GET /api/control/printer/sd HTTP/1.1
      Host: example.com

   **Example Response**

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "ready": true
      }

   :statuscode 200: No error
   :statuscode 404: If SD support has been disabled in OctoPrint's config.

.. _sec-api-printer-datamodel:

Datamodel
=========

.. _sec-api-printer-datamodel-sdstate:

SD State Response
-----------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``ready``
     - 1
     - Boolean
     - Whether the SD card has been initialized (``true``) or not (``false``).