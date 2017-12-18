.. _sec-features-gcode_scripts:

GCODE Scripts
=============

.. contents::

OctoPrint allows you to define custom GCODE scripts to be executed on specified occasions, e.g. when a print
starts, when OctoPrint connects to a printer, or when a :ref:`button defined as a custom control <sec-features-custom_controls>`
is clicked.

Unless :ref:`configured otherwise <sec-configuration-config_yaml-folder>`, OctoPrint expects scripts to be located in
the ``scripts/gcode`` folder in OctoPrint configuration directory (per default ``~/.octoprint`` on Linux, ``%APPDATA%\OctoPrint``
on Windows and ``~/Library/Application Support/OctoPrint`` on MacOS).

These GCODE scripts are backed by the templating engine Jinja2, allowing more than just
simple "send-as-is" scripts but making use of a full blown templating language in order to create your scripts. To
this end, OctoPrint injects some variables into the :ref:`template rendering context <sec-features-gcode_scripts-context>`
as described below.

You can find the docs on the Jinja templating engine as used in OctoPrint at `jinja.octoprint.org <http://jinja.octoprint.org/templates.html>`_.

.. note::

   Due to backwards compatibility issues with Jinja versions 2.9+, OctoPrint currently only supports Jinja 2.8. For this
   reason use the template documentation at `jinja.octoprint.org <http://jinja.octoprint.org/templates.html>`_ instead of the
   documentation of current stable Jinja versions.

.. _sec-features-gcode_scripts-predefined:

Predefined Scripts
------------------

The following GCODE scripts are sent by OctoPrint automatically:

  * ``afterPrinterConnected``: Sent after OctoPrint successfully connected to a printer. Defaults to an empty script.
  * ``beforePrinterDisconnected``: Sent just before OctoPrint (actively) closes the connection to the printer. Defaults
    to an empty script. Note that this will *not* be sent for unexpected connection cut offs, e.g. in case of errors
    on the serial line, only when the user clicks the "Disconnect" button or the printer requests a disconnect via an
    :ref:`action command <sec-features-action_commands>` .
  * ``beforePrintStarted``: Sent just before a print job is started. Defaults to an empty script.
  * ``afterPrintCancelled``: Sent just after a print job was cancelled. Defaults to the
    :ref:`bundled script listed below <sec-features-gcode_scripts-bundled>`.
  * ``afterPrintDone``: Sent just after a print job finished. Defaults to an empty script.
  * ``afterPrintPaused``: Sent just after a print job was paused. Defaults to an empty script.
  * ``beforePrintResumed``: Sent just before a print job is resumed. Defaults to an empty script.

.. note::

   Plugins may extend these scripts through :ref:`a hook <sec-plugins-hook-comm-protocol-scripts>`.

.. _sec-features-gcode_scripts-snippets:

Snippets
--------

For making small GCODE snippets reusable in a template (e.g. for :ref:`disabling all hotends <sec-features-gcode_scripts-bundled>`)
there's an additional Jinja template command ``{% snippet '<snippet name>' %}`` available which allows including
snippets stored under ``scripts/gcode/snippets`` in OctoPrint's configuration directory. They fully support
the whole spectrum of the Jinja2 templating language (that includes including other snippets).

.. _sec-features-gcode_scripts-context:

Context
-------

All GCODE scripts have access to the following template variables through the template context:

  * ``printer_profile``: The currently selected Printer Profile, including
    information such as the extruder count, the build volume size, the filament diameter etc.
  * ``last_position``: Last position reported by the printer via `M114` (might be unset if no `M114` was sent so far!).
    Consists of ``x``, ``y``, ``z`` and ``e`` coordinates as received by the printer and tracked values for ``f`` and
    current tool ``t`` taken from commands sent through OctoPrint. All of these coordinates might be ``None`` if no
    position could be retrieved from the printer or the values could not be tracked (in case of ``f`` and ``t``)!
  * ``last_temperature``: Last actual and target temperature reported for all available tools and if available the
    heated bed. This is a dictionary of key-value pairs. The keys are the indices of the available tools (``0``, ``1``,
    ...) and ``b`` for the heated bed. The values are a dictionary consisting of ``actual`` and ``target`` keys mapped
    to the corresponding temperature in degrees celsius. Note that not all tools your printer has must necessarily be
    present here, neither must the heated bed - it depends on whether OctoPrint has values for a tool or the bed. Also
    note that ``actual`` and ``target`` might be ``None``.
  * ``script``: An object wrapping the script's type (``gcode``) and name (e.g. ``afterPrintCancelled``) as ``script.type``
    and ``script.name`` respectively.

There are a few additional template variables available for the following specific scripts:

  * ``afterPrintPaused`` and ``beforePrintResumed``

    * ``pause_position``: Position reported by the printer via ``M114`` immediately before the print was paused. See
      ``last_position`` above for the structure to expect here.

      **Please note:** This will not be available if you disable
      "Log position on pause" under Settings > Serial > Advanced options!
    * ``pause_temperature``: Last known temperature values when the print was paused. See ``last_temperature`` above
      for the structure to expect here.

  * ``afterPrintCancelled``

    * ``cancel_position``: Position reported by the printer via ``M114`` immediately before the print was cancelled.
      See ``last_position`` above for the structure to expect here.

      **Please note:** This will not be available if you disable
      "Log position on cancel" under Settings > Serial > Advanced options!
    * ``cancel_temperature``: Last known temperature values when the print was cancelled. See ``last_temperature`` above
      for the structure to expect here.


.. warning::

   Note that current firmware implementations only report back one ``E`` value, the current extrusion value for the current
   extruder. Retrieving all ``E`` values by cycling through all extruders on pause and cancel is something OctoPrint
   currently does NOT do since it would simply take too long. That means that if you want to write a ``beforePrintResumed``
   script that basically resets everything back to the point when the printer was paused *and* you are running with
   multiple extruders, you'll have to find some other way to have your ``E`` values set correctly for all your available
   extruders - the data available in ``pause_position`` will *not* suffice. Additionally, most firmwares don't report
   the currently selected tool in the ``M114`` response, meaning that the only way OctoPrint can keep track of that is
   by tracking it itself. Same goes for the current feed rate ``F``. So if you are printing from SD, this data will be
   *wrong*. This is also the reason why OctoPrint currently doesn't bundle a more sophisticated pause and resume script
   that would actually move the print head out of the way and pause and back to the original position on resume - it
   might cause issues for the multitude of users out there with multi-extruder setups or for people printing from the
   printer's SD, thanks to the lack of information the firmware provides.

The :ref:`predefined GCODE scripts <sec-features-gcode_scripts-predefined>` are also called with the following additional
template variables:

  * ``event``: The payload of the ``Connected``, ``PrintStarted``, ``PrintCancelled``, ``PrintDone``, ``PrintPaused`` or
    ``PrintResumed`` event. See :ref:`the documentation of events <sec-events-available_events>` for the contained values.

GCODE scripts attached to :ref:`custom controls <sec-features-custom_controls>` are called with the following
additional template variables:

  * ``parameters``: The parameters as defined for the custom control, if it has any inputs.
  * ``context``: Additional ``context`` included in the definition of the custom control.

.. _sec-features-gcode_scripts-bundled:

Bundled Scripts
---------------

Out of the box, OctoPrint defaults to the following script setup for ``afterPrintCancelled``:

.. code-block:: jinja
   :caption: Default ``afterPrintCancelled`` script

   ; disable motors
   M84

   ;disable all heaters
   {% snippet 'disable_hotends' %}
   {% snippet 'disable_bed' %}

   ;disable fan
   M106 S0

The ``disable_hotends`` snippet is defined as follows:

.. code-block:: jinja
   :caption: Default ``disable_hotends`` snippet

   {% for tool in range(printer_profile.extruder.count) %}
   M104 T{{ tool }} S0
   {% endfor %}

The ``disable_bed`` snippet is defined as follows:

.. code-block:: jinja
   :caption: Default ``disable_bed`` snippet

   {% if printer_profile.heatedBed %}
   M140 S0
   {% endif %}

As you can see, the ``disable_hotends`` and ``disable_bed`` snippets utilize the
``printer_profile`` context variable in order to iterate through all available
extruders and set their temperature to 0, and to also set the bed temperature
to 0 if a heated bed is configured.

.. _sec-features-gcode_scripts-examples:

Examples
--------

.. _sec-features-gcode_scripts-examples-more_nifty_pause_and_resume:

More nifty pause and resume
...........................

If you do not have a multi-extruder setup, aren't printing from SD and have "Log position on pause" enabled under
Settings > Serial > Advanced options, the following ``afterPrintPaused`` and
``beforePrintResumed`` scripts might be interesting for you. With something like them in place, OctoPrint will move your print head
out of the way to a safe rest position (here ``G1 X0 Y0``, you might want to adjust that) on pause and move it back
to the persisted pause position on resume, making sure to also reset the extruder and feedrate.

.. code-block:: jinja
   :caption: ``afterPrintPaused`` script

   {% if pause_position.x is not none %}
   ; relative XYZE
   G91
   M83

   ; retract filament, move Z slightly upwards
   G1 Z+5 E-5 F4500

   ; absolute XYZE
   M82
   G90

   ; move to a safe rest position, adjust as necessary
   G1 X0 Y0
   {% endif %}

.. code-block:: jinja
   :caption: ``beforePrintResumed`` script

   {% if pause_position.x is not none %}
   ; relative extruder
   M83

   ; prime nozzle
   G1 E-5 F4500
   G1 E5 F4500
   G1 E5 F4500

   ; absolute E
   M82

   ; absolute XYZ
   G90

   ; reset E
   G92 E{{ pause_position.e }}

   ; move back to pause position XYZ
   G1 X{{ pause_position.x }} Y{{ pause_position.y }} Z{{ pause_position.z }} F4500

   ; reset to feed rate before pause if available
   {% if pause_position.f is not none %}G1 F{{ pause_position.f }}{% endif %}
   {% endif %}

.. warning::

   As mentioned in the warning above and the description of the example itself, this will *only* work if you are
   not printing from SD and not using multiple extruders since OctoPrint will only then be able to track the
   necessary position data and print parameters due to firmware limitations.

.. seealso::

   `Jinja Template Designer Documentation <http://jinja.octoprint.org/templates.html>`_
      Jinja's Template Designer Documentation describes the syntax and semantics of the template language used
      also by OctoPrint's GCODE scripts. Linked here are the docs for Jinja 2.8.1, which OctoPrint still
      relies on for backwards compatibility reasons.
