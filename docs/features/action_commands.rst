.. _sec-features-action_commands:

Action Commands
===============

Action commands are a feature defined for the GCODE based RepRap communication protocol. To quote from the
`GCODE node of the RepRap wiki <http://reprap.org/wiki/Gcode#Replies_from_the_RepRap_machine_to_the_host_computer>`_:

    The RepRap machine may also send lines that look like this:

    **// This is some debugging or other information on a line on its own. It may be sent at any time.**

    Such lines will always be preceded by //.

    On the latest version of Pronterface and [...] OctoPrint a special comment of the form:

    **// action:command**

    is allowed to be sent from the firmware[. T]he command can currently be pause, resume or disconnect which will
    execute those commands on the host. As this is also a comment other hosts will just ignored these commands.

OctoPrint out of the box supports handling of the above mentioned commands:

pause
    When this command is received from the printer, OctoPrint will pause streaming of a current print job just like if the
    "Pause" button had been clicked.

resume
    When this command is received from the printer, OctoPrint will resume streaming of a current print job just like if
    the "Resume" button had been clicked.

disconnect
    When this command is Received from the printer, OctoPrint will immediately disconnect from it.

Support for additional commands may be added by plugins by implementing a handler for the
:ref:`octoprint.comm.protocol.action <sec-plugins-hook-comm-protocol-action>` hook.
