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

start
    When this command is received from the printer, a job is currently selected and *not* active, OctoPrint
    will start it just like if the "Start"/"Restart" button had been clicked.

    .. versionadded:: 1.5.0

cancel
    When this command is received from the printer, OctoPrint will cancel a current print job just like if the
    "Cancel" button had been clicked.

pause
    When this command is received from the printer, OctoPrint will pause a current print job just like if the
    "Pause" button had been clicked.

paused
    When this command is received from the printer, OctoPrint will pause a current print job but *without* triggering
    any GCODE scripts or sending SD print control commands to the printer. This might be interesting for firmware
    that wants to signal to OctoPrint that a print should be paused but without any control interference from
    OctoPrint, e.g. in case of a filament change fully managed by the firmware.

resume
    When this command is received from the printer, OctoPrint will resume a current print job just like if
    the "Resume" button had been clicked.

resumed
    When this command is received from the printer, OctoPrint will resume a current print job but *without* triggering
    any GCODE scripts or sending SD print control commands to the printer. This might be interesting for firmware
    that wants to signal to OctoPrint that a print should be resumed but without any control interference from
    OctoPrint, e.g. in case of a filament change fully managed by the firmware.

disconnect
    When this command is received from the printer, OctoPrint will immediately disconnect from it.

sd_inserted
    When this command is received from the printer, OctoPrint will assume an SD card is present in the printer,
    set the corresponding internal state flags and send a file list request. This command is only recognized
    if SD support is enabled in OctoPrint.

    .. versionadded:: 1.6.0

sd_ejected
    When this command is received from the printer, OctoPrint will assume the SD card has been removed from
    the printer and clear the corresponding internal state flags. This command is only recognized
    if SD support is enabled in OctoPrint.

    .. versionadded:: 1.6.0

sd_updated
    When this command is received from the printer, OctoPrint will assume something on the SD card in the
    printer has changed and trigger a file list request. This command is only recognized
    if SD support is enabled in OctoPrint.

    .. versionadded:: 1.6.0

shutdown
    When this command is received from the printer, **support for it is enabled in its settings**
    and a working system shutdown command is configured, OctoPrint will immediately shutdown the system.
    This command is not enabled by default due to the high risk of seeing it abused by malicious
    firmware or manipulated GCODE, but can be enabled in the OctoPrint settings via Serial Connection >
    Firmware & Protocol > Action Commands if so desired by the user.

    .. versionadded:: 1.8.0

If the bundled :ref:`Action Command Prompt Support Plugin <sec-bundledplugins-action_command_prompt>` is enabled (which
should be the case by default), OctoPrint will also support interactive dialog creation
through its :ref:`supported commands <sec-bundledplugins-action_command_prompt-action_commands>`.

Support for additional commands may be added by plugins by implementing a handler for the
:ref:`octoprint.comm.protocol.action <sec-plugins-hook-comm-protocol-action>` hook.
