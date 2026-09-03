.. _sec-development-virtual-printer:

Setting up the virtual printer for debugging
============================================

OctoPrint includes, by default, a :ref:`virtual printer plugin <sec-bundledplugins-virtual_printer>`. This plugin allows you to debug OctoPrint's serial
communication without connecting to an actual printer. Furthermore, it is possible to create certain edge conditions
that may be hard to reproduce with a real printer.

.. _sec-development-virtual-printer-enable:

Enabling the virtual printer
----------------------------

The virtual printer can be enabled through its Settings panel.

.. _sec-development-virtual-printer-config:

Virtual printer configuration options
-------------------------------------

There are many configuration options via ``config.yaml`` for the virtual printer that allow you to fine-tune its behavior:

Defaults
........

.. pydantic-example:: octoprint.plugins.virtual_printer.VirtualPrinterConfig
   :key: plugins.virtual_printer

Data model 
..........

.. pydantic-table:: octoprint.plugins.virtual_printer.VirtualPrinterConfig

.. _sec-development-virtual-printer-log:

Log file
--------

Once activated, the virtual printer will log all serial communication in the ``plugin_virtual_printer_serial.log`` file
that can be found in the OctoPrint logs folder.

.. _sec-development-virtual-printer-debug:

Debug commands
--------------

You can simulate certain conditions and communications through the terminal tab in OctoPrint's interface.

All commands start with ``!!DEBUG:`` and are followed by the command you want to execute. For instance, sending
``!!DEBUG:action_disconnect`` will disconnect the printer. Sending ``!!DEBUG`` without command will show a help
message with all the available commands:

.. literalinclude:: ../../src/octoprint/plugins/virtual_printer/virtual.py
   :start-after: DEBUG_USAGE = """
   :end-before: """  # END DEBUG_USAGE

