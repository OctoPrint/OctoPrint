.. _sec-bundledplugins-virtual_printer:

Virtual Printer
===============

.. versionchanged:: 1.4.1

The Virtual Printer plugin provides a virtual printer to connect to during development. It is able to simulate various
firmware quirks, communication issues and can be heavily configured through ``config.yaml``. See
:ref:`the development documentation on details and usage <sec-development-virtual-printer>`.

The virtual printer has been included in OctoPrint ever since the first releases back in 2013, however as of
OctoPrint 1.4.1 it has finally been fully extracted into its own bundled plugin.

.. _sec-bundledplugins-virtual_printer-configuration:

Configuring the plugin
----------------------

Please refer to :ref:`the development documentation <sec-development-virtual-printer-config>`.

.. _sec-bundledplugins-virtual_printer-sourcecode:

Source Code
-----------

The source of the Virtual Printer plugin is bundled with OctoPrint and can be
found in its source repository under ``src/octoprint/plugins/virtual_printer``.
