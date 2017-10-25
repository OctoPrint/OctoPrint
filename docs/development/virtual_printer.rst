.. _sec-development-virtual-printer:

Setting up the virtual printer for debugging
============================================

OctoPrint includes, by default, a virtual printer plugin. This plugin allows you to debug OctoPrint's serial
communication without connecting to an actual printer. Furthermore, it is possible to create certain edge conditions
that may be hard to reproduce with a real printer.

.. _sec-development-virtual-printer-enable:

Enabling the virtual printer
----------------------------

The virtual printer is enabled by editing OctoPrint's config.yaml file. Details on the configuration file can
be found in the full :ref:`config.yaml documentation <sec-configuration-config_yaml>`.

The steps to take are as follows:

* Find config.yaml in the OctoPrint settings folder. Usually in ``~/.octoprint`` on Linux, in ``%APPDATA%/OctoPrint`` on Windows and in ``~/Library/Application Support/OctoPrint`` on MacOS.
* Add or extend the ``devel`` section with:

.. code-block:: yaml

   devel:
     virtualPrinter:
       enabled: true

* Restart OctoPrint.
* In the connection panel, a new option will appear in the Serial Port dropdown labeled ``VIRTUAL``.
* Select this option and click ``connect``.
* The virtual printer is now active.

.. _sec-development-virtual-printer-config:

Virtual printer configuration options
-------------------------------------

The config.yaml file has many configuration options for the virtual printer that allow you to fine-tune its behavior.

Please see the relevant :ref:`config.yaml section <sec-configuration-config_yaml-devel>` for the full details.

.. _sec-development-virtual-printer-log:

Log file
--------

Once activated, the virtual printer will log all serial communication in the ``plugin_virtual_printer_serial.log`` file
that can be found in the OctoPrint settings folder.

.. _sec-development-virtual-printer-debug:

Debug commands
--------------

You can simulate certain conditions and communications through the terminal tab in OctoPrint's interface.

All commands start with ``!!DEBUG:`` and are followed by the command you want to execute. For instance, sending
``!!DEBUG:action_disconnect`` will disconnect the printer. Sending ``!!DEBUG`` without command will show a help
message with all the available commands.

Action Triggers
...............

``action_pause``
Sends a "// action:pause" action trigger to the host.

``action_resume``
Sends a "// action:resume" action trigger to the host.

``action_disconnect``
Sends a "// action:disconnect" action trigger to the host.

``action_custom <action>[ <parameters>]``
Sends a custom "// action:<action> <parameters>" action trigger to the host.

Communication Errors
....................

``dont_answer``
Will not acknowledge the next command.

``go_awol``
Will completely stop replying.

``trigger_resend_lineno``
Triggers a resend error with a line number mismatch

``trigger_resend_checksum``
Triggers a resend error with a checksum mismatch

``drop_connection``
Drops the serial connection

``prepare_ok <broken ok>``
Will cause <broken ok> to be enqueued for use, will be used instead of actual "ok"

Reply Timing / Sleeping
.......................
``sleep <int:seconds>``
Sleep <seconds> s

``sleep_after <str:command> <int:seconds>``
Sleeps <seconds> s after each execution of <command>

``sleep_after_next <str:command> <int:seconds>``
Sleeps <seconds> s after execution of next <command>

Misc
....

``help``
Show the available commands.

``send <str:message>``
Sends back <message>
