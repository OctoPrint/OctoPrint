.. _sec-jsclientlib-printer:

:mod:`OctoPrintClient.printer`
------------------------------

.. note::

   All commands here that interact with the printer (anything that sends a command) will
   resolve the returned `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ when the
   request to the server enqueuing the command has been processed, *not* when the command
   was actually sent to or processed by the printer.

   See :ref:`the note here <sec-api-printer>` for an explanation why that is the case.

.. contents::
   :local:

.. js:function:: OctoPrintClient.printer.getFullState(flags, opts)

   Retrieves the full printer state, including temperature information, sd state and general
   printer state.

   The ``flags`` object can be used to specify the data to retrieve further via the following
   properties:

     * ``history``: a boolean value to specify whether the temperature history should be included (``true``)
       or not (``false``), defaults to it not being included
     * ``limit``: an integer value to specify how many history entries to include
     * ``exclude``: a string value of comma-separated fields to exclude from the returned result.

   See :ref:`Retrieve the current printer state <sec-api-printer-state>` for more details.

   :param object flags: Flags that further specify which data to retrieve, see above for details
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.printer.getToolState(flags, opts)

   Retrieves the current printer extruder state/temperature information, and optionally also the temperature
   history.

   The ``flags`` object can be used to specify the data to retrieve further via the following
   properties:

     * ``history``: a boolean value to specify whether the temperature history should be included (``true``)
       or not (``false``), defaults to it not being included
     * ``limit``: an integer value to specify how many history entries to include

   See :ref:`Retrieve the current tool state <sec-api-printer-toolstate>` for more details.

   :param object flags: Flags that further specify which data to retrieve, see above for details
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.printer.setToolTargetTemperatures(targets, opts)

   Sets the given temperatures on the printer's extruders.

   ``targets`` is expected to be an object mapping tool identifier to target temperature to set.

   **Example:**

   Set first hotend to 220°C and second to 205°C.

   .. code-block:: javascript

      OctoPrint.printer.setToolTargetTemperatures({"tool0": 220, "tool1": 205});

   See the ``target`` command in :ref:`Issue a tool command <sec-api-printer-toolcommand>` for more details.

   :param object targets: The targets to set
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.printer.setToolTemperatureOffsets(offsets, opts)

   Sets the given temperature offsets for the printer's extruders.

   ``offsets`` is expected to be an object mapping tool identifier to offset to set.

   **Example:**

   Set the offset for the first hotend's temperature to +10°C and the offset for the second hotend's
   temperature to -5°C.

   .. code-block:: javascript

      OctoPrint.printer.setToolTemperatureOffsets({"tool0": 10, "tool1": -5});

   See the ``offset`` command in :ref:`Issue a tool command <sec-api-printer-toolcommand>` for more details.

   :param object offsets: The offsets to set
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.printer.selectTool(tool, opts)

   Selects the printer's current extruder.

   ``tool`` is the identifier of the extruder to select.

   **Example:**

   Select the second tool, extrude 5mm of filament, then select the first tool.

   .. code-block:: javascript

      OctoPrint.printer.selectTool("tool1")
          .done(function(response) {
              OctoPrint.printer.extrude(5.0)
                  .done(function(response) {
                      OctoPrint.printer.selectTool("tool0");
                  });
          });

   See the ``select`` command in :ref:`Issue a tool command <sec-api-printer-toolcommand>` for more details.

   :param string tool: The tool identifier of the extruder to select
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.printer.extrude(amount, opts)

   Extrudes or retracts ``amount`` mm of filament on the currently selected extruder.

   **Example:**

   Extrude 5mm of filament on the current extruder, then retract 2mm.

   .. code-block:: javascript

      OctoPrint.printer.extrude(5.0)
          .done(function(response) {
              OctoPrint.printer.extrude(-2.0);
          });

   See the ``extrude`` command in :ref:`Issue a tool command <sec-api-printer-toolcommand>` for more details.

   :param float amount: The amount of filament to extrude/retract.
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.printer.setFlowrate(factor, opts)

   Sets the current flowrate multiplier.

   ``factor`` is expected to be a integer value between 75 and 125 representing the new flowrate percentage.

   See the ``flowrate`` command in :ref:`Issue a tool command <sec-api-printer-toolcommand>` for more details.

   :param integer factor: The flowrate as percentage
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.printer.getBedState(data, opts)

   Retrieves the current printer bed state/temperature information, and optionally also the temperature
   history.

   The ``flags`` object can be used to specify the data to retrieve further via the following
   properties:

     * ``history``: a boolean value to specify whether the temperature history should be included (``true``)
       or not (``false``), defaults to it not being included
     * ``limit``: an integer value to specify how many history entries to include

   See :ref:`Retrieve the current bed state <sec-api-printer-bedstate>` for more details.

   :param object flags: Flags that further specify which data to retrieve, see above for details
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.printer.setBedTargetTemperature(target, opts)

   Sets the given temperature on the printer's heated bed (if available).

   ``target`` is expected to be a the target temperature as a float value.

   **Example:**

   Set the bed to 90°C.

   .. code-block:: javascript

      OctoPrint.printer.setBedTargetTemperature(90.0);

   See the ``target`` command in :ref:`Issue a bed command <sec-api-printer-bedcommand>` for more details.

   :param float target: The target to set
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.printer.setBedTemperatureOffset(offset, opts)

   Sets the given temperature offset for the printer's heated bed (if available).

   ``offset`` is expected to be the temperature offset to set.

   **Example:**

   Set the offset for the bed to -5°C.

   .. code-block:: javascript

      OctoPrint.printer.setBedTemperatureOffset(-5);

   See the ``offset`` command in :ref:`Issue a bed command <sec-api-printer-bedcommand>` for more details.

   :param object offsets: The offsets to set
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.printer.jog(amounts, opts)

   Jogs the specified axes by the specified ``amounts``.

   ``amounts`` is expected to be an object with properties reflecting the axes to be jogged by the specified
   amount given as value.

   **Example:**

   Jog X by 10mm.

   .. code-block:: javascript

      OctoPrint.printer.jog({"x", 10.0});

   Jog Y by -5mm and Z by 0.2mm.

   .. code-block:: javascript

      OctoPrint.printer.jog({"y": -5.0, "z": 0.2});

   See the ``jog`` command in :ref:`Issue a print head command <sec-api-printer-printheadcommand>` for more details.

   :param object amounts: Key-value-pairs of axes to jog and amount to jog it.
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.printer.home(axes, opts)

   Homes the specified ``axes``.

   ``axes`` is expected to be an array of strings specifying the axes to home.

   **Example:**

   Home the X and Y axis.

   .. code-block:: javascript

      OctoPrint.printer.home(["x", "y"]);

   Home the Z axis.

   .. code-block:: javascript

      OctoPrint.printer.home(["z"]);

   See the ``home`` command in :ref:`Issue a print head command <sec-api-printer-printheadcommand>` for more details.

   :param array axes: List of axes to home
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.printer.setFeedrate(factor, opts)

   Sets the feedrate multiplier to use.

   ``factor`` is expected to be a integer value between 0 and 200 representing the new feedrate percentage.

   See the ``feedrate`` command in :ref:`Issue a print head command <sec-api-printer-printheadcommand>` for more details.

   :param integer factor: The feedrate multiplier as percentage
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.printer.getSdState(opts)

   Retrieves the current ready state of the printer's SD card.

   See :ref:`Retrieve the current SD state <sec-api-printer-sdstate>` for more details.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.printer.initSd(opts)

   Instructs the printer to initialize its SD card (if present).

   See the ``init`` command in :ref:`Issue an SD command <sec-api-printer-sdcommand>` for more details.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.printer.refreshSd(opts)

   Instructs the printer to refresh the list of files on the SD card (if present).

   See the ``refresh`` command in :ref:`Issue an SD command <sec-api-printer-sdcommand>` for more details.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.printer.releaseSd(opts)

   Instructs the printer to release its SD card (if present).

   See the ``release`` command in :ref:`Issue an SD command <sec-api-printer-sdcommand>` for more details.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. seealso::

   :ref:`REST API: Printer operations <sec-api-printer>`
       Documentation of the API functionality covered with this client library module.
