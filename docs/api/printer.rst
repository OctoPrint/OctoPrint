.. _sec-api-printer:

***************
Printer Control
***************

.. _sec-api-printer-printhead:

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

   **Example Jog Request**

   Jog the print head by 10mm in X, -5mm in Y and 0.02mm in Z.

   .. sourcecode:: http

      POST /api/printer/printhead HTTP/1.1
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

      POST /api/printer/printhead HTTP/1.1
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
   :statuscode 200: No error
   :statuscode 400: Invalid axis specified, invalid value for travel amount for a jog command or otherwise invalid
                    request.
   :statuscode 403: If the printer is not operational or currently printing.

.. _sec-api-printer-hotend:

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
   :statuscode 200: No error
   :statuscode 400: If ``temps`` or ``offsets`` contains a property other than ``hotend`` or ``bed``, the
                    target or offset temperature is not a valid number or outside of the supported range, or if the
                    request is otherwise invalid.
   :statuscode 403: If the printer is not operational.

.. _sec-api-printer-feeder:

Issue a feeder command
======================

.. http:post:: /api/control/printer/feeder

   Feeder commands allow extrusion/extraction of filament. Available commands are:

   extrude
     Extrudes the given amount of filament. Additional parameters:

     * ``amount``: The amount of filament to extrude in mm. May be negative to retract.

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
   :statuscode 200: No error
   :statuscode 400: If the value given for `amount` is not a valid number or the request is otherwise invalid.
   :statuscode 403: If the printer is not operational or currently printing.