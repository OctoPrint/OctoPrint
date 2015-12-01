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

These GCODE scripts are backed by the templating engine `Jinja2 <http://jinja.pocoo.org/>`_, allowing more than just
simple "send-as-is" scripts but making use of a full blown templating language in order to create your scripts. To
this end, OctoPrint injects a couple of variables into the :ref:`template rendering context <sec-features-gcode_scripts-context>`
as described below.

.. _sec-features-gcode_scripts-predefined:

Predefined Scripts
------------------

The following GCODE scripts are sent by OctoPrint automatically:

  * ``afterPrinterConnected``: Sent after OctoPrint successfully connected to a printer. Defaults to an empty script.
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
  * ``script``: An object wrapping the script's type (``gcode``) and name (e.g. ``afterPrintCancelled``) as ``script.type``
    and ``script.name`` respectively.

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
   [% snippet 'disable_bed' %}

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

.. seealso::

   `Jinja Template Designer Documentation <http://jinja.pocoo.org/docs/dev/templates/>`_
      Jinja's Template Designer Documentation describes the syntax and semantics of the template language used
      also by OctoPrint's GCODE scripts.
