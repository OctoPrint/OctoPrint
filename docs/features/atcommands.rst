.. _sec-features-atcommands:

@ Commands
==========

@ commands (also known as host commands elsewhere) are special commands you may include in GCODE files streamed
through OctoPrint to your printer or send as part of GCODE scripts, through the Terminal Tab, the API or plugins.
Contrary to other commands they will never be sent to the printer but instead trigger functions inside OctoPrint.

They are always of the form ``@<command>[ <parameters>]``, e.g. ``@pause`` or ``@custom_command with some parameters``.

Out of the box OctoPrint supports handling of these commands starting with version 1.3.7:

@cancel
    OctoPrint will cancel the current print job like if the "Cancel" button had been clicked. This command doesn't
    take any parameters.

@abort
    Same as ``cancel``.

@pause
    OctoPrint will pause the current print job just like if the "Pause" button had been clicked. This command doesn't
    take any parameters.

@resume
    OctoPrint will resume the current print job just like if the "Resume" button had been clicked. This command doesn't
    take any parameters.

Support for additional commands may be added by plugins by implementing a handler for one of the
:ref:`octoprint.comm.protocol.atcommand <sec-plugins-hook-comm-protocol-atcommand-phase>` hooks.
