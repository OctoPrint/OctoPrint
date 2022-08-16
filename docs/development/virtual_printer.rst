.. _sec-development-virtual-printer:

Setting up the virtual printer for debugging
============================================

OctoPrint includes, by default, a :ref:`virtual printer plugin <sec-bundledplugins-virtual_printer>`. This plugin allows you to debug OctoPrint's serial
communication without connecting to an actual printer. Furthermore, it is possible to create certain edge conditions
that may be hard to reproduce with a real printer.

.. _sec-development-virtual-printer-enable:

Enabling the virtual printer
----------------------------

The virtual printer can be enabled through its Settings pane.

.. _sec-development-virtual-printer-config:

Virtual printer configuration options
-------------------------------------

There many configuration options via ``config.yaml`` for the virtual printer that allow you to fine-tune its behavior:

.. code-block:: yaml

   plugins:

     # Settings for the virtual printer
     virtual_printer:

       # Whether to enable the virtual printer and include it in the list of available serial connections.
       # Defaults to false.
       enabled: true

       # Whether to send an additional "ok" after a resend request (like Repetier)
       okAfterResend: false

       # Whether to force checksums and line number in the communication (like Repetier), if set to true
       # printer will only accept commands that come with linenumber and checksum and throw an error for
       # lines that don't. Defaults to false
       forceChecksum: false

       # Whether to send "ok" responses with the line number that gets acknowledged by the "ok". Defaults
       # to false.
       okWithLinenumber: false

       # Number of extruders to simulate on the virtual printer. Map from tool id (0, 1, ...) to temperature
       # in °C
       numExtruders: 1

       # Allows pinning certain hotends to a fixed temperature
       pinnedExtruders: null

       # Whether to include the current tool temperature in the M105 output as separate T segment or not.
       #
       # True:  > M105
       #        < ok T:23.5/0.0 T0:34.3/0.0 T1:23.5/0.0 B:43.2/0.0
       # False: > M105
       #        < ok T0:34.3/0.0 T1:23.5/0.0 B:43.2/0.0
       includeCurrentToolInTemps: true

       # Whether to include the selected filename in the M23 File opened response.
       #
       # True:  > M23 filename.gcode
       #        < File opened: filename.gcode  Size: 27
       # False: > M23 filename.gcode
       #        > File opened
       includeFilenameInOpened: true

       # Whether the simulated printer should also simulate a heated bed or not
       hasBed: true

       # Whether the simulated printer should also simulate a heated chamber or not
       hasChamber: false

       # If enabled, reports the set target temperatures as separate messages from the firmware
       #
       # True:  > M109 S220.0
       #        < TargetExtr0:220.0
       #        < ok
       #        > M105
       #        < ok T0:34.3 T1:23.5 B:43.2
       # False: > M109 S220.0
       #        < ok
       #        > M105
       #        < ok T0:34.3/220.0 T1:23.5/0.0 B:43.2/0.0
       repetierStyleTargetTemperature: false

       # If enabled, uses repetier style resends, sending multiple resends for the same line
       # to make sure nothing gets lost on the line
       repetierStyleResends: false

       # If enabled, ok will be sent before a commands output, otherwise after or inline (M105)
       #
       # True:  > M20
       #        < ok
       #        < Begin file list
       #        < End file list
       # False: > M20
       #        < Begin file list
       #        < End file list
       #        < ok
       okBeforeCommandOutput: false

       # If enabled, reports the first extruder in M105 responses as T instead of T0
       #
       # True:  > M105
       #        < ok T:34.3/0.0 T1:23.5/0.0 B:43.2/0.0
       # False: > M105
       #        < ok T0:34.3/0.0 T1:23.5/0.0 B:43.2/0.0
       smoothieTemperatureReporting: false

       # Settings related to the SD file list output
       sdFiles:
         # Whether M20 responses will include filesize or not
         #
         # True:  <filename> <filesize in bytes>
         # False: <filename>
         size: true

         # Whether M20 responses will include timestamp or not (only if size = true as well)
         #
         # True: <filename> <filesize in bytes> <timestamp as hex>
         # False: <filename> <filesize in bytes>
         timestamp: false

         # Whether M20 responses will include longname or not (only if size = true as well)
         #
         # True:  <filename> <filesize in bytes> <longname>
         # False: <filename> <filesize in bytes>
         longname: false

       # Forced pause for retrieving from the outgoing buffer
       throttle: 0.01

       # Whether to send "wait" responses every "waitInterval" seconds when serial rx buffer is empty
       sendWait: false

       # Interval in which to send "wait" lines when rx buffer is empty
       waitInterval: 1

       # Size of the simulated RX buffer in bytes, when it's full a send from OctoPrint's
       # side will block
       rxBuffer: 64

       # Size of simulated command buffer, number of commands. If full, buffered commands will block
       # until a slot frees up
       commandBuffer: 4

       # Whether to support the M112 command with simulated kill
       supportM112: true

       # Whether to send messages received via M117 back as "echo:" lines
       echoOnM117: true

       # Whether to simulate broken M29 behaviour (missing ok after response)
       brokenM29: true

       # Whether F is supported as individual command
       supportF: false

       # Firmware name to report (useful for testing firmware detection)
       firmwareName: Virtual Marlin 1.0

       # Simulate a shared nozzle
       sharedNozzle: false

       # Send "busy" messages if busy processing something
       sendBusy: false

       # Simulate a reset on connect
       simulateReset: true

       # Lines to send on simulated reset
       resetLines:
       - start
       - "Marlin: Virtual Marlin!"
       - "SD card ok"

       # Initial set of prepared oks to use instead of regular ok (e.g. to simulate
       # mis-sent oks). Can also be filled at runtime via the debug command prepare_ok
       preparedOks: []

       # Format string for ok response.
       #
       # Placeholders:
       # - lastN: last acknowledged line number
       # - buffer: empty slots in internal command buffer
       #
       # Example format string for "extended" ok format:
       #   ok N{lastN} P{buffer}
       okFormatString: ok

       # Format string for M115 output.
       #
       # Placeholders:
       # - firmare_name: The firmware name as defined in firmwareName
       m115FormatString: "FIRMWARE_NAME: {firmware_name} PROTOCOL_VERSION:1.0"

       # Whether to include capability report in M115 output
       m115ReportCapabilites: false

       # Capabilities to report if capability report is enabled
       capabilities:
         AUTOREPORT_TEMP: true

       # Simulated ambient temperature in °C
       ambientTemperature: 21.3

       # Response to M105 when there is a target
       # Placeholders:
       # - heater: The heater id (eg. T0, T1, B)
       # - actual: The actual temperature of the heater
       # - target: The target temperature of heater
       m105TargetFormatString: {heater}:{actual:.2f}/ {target:.2f}

       # Response to M105 when there is no target
       # Placeholders:
       # - heater: The heater id (eg. T0, T1, B)
       # - actual: The actual temperature of the heater
       m105NoTargetFormatString: {heater}:{actual:.2f}

       # Enable virtual EEPROM
       # If enabled, a file `eeprom.json` will be created in the plugin data folder
       # to enable settings persistence across connections. Enables M500/1/2/4 commands
       # And a selection of other settings commands. Responses modeled on Marlin 2.0
       enable_eeprom: true

       # Support M503
       support_m503: true

       # Resend ratio to simulate noise on the line
       resend_ratio: 0

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

.. code-block:: none

   OctoPrint Virtual Printer debug commands

   help
   ?
   | This help.

   # Action Triggers

   action_pause
   | Sends a "// action:pause" action trigger to the host.
   action_resume
   | Sends a "// action:resume" action trigger to the host.
   action_disconnect
   | Sends a "// action:disconnect" action trigger to the
   | host.
   action_custom <action>[ <parameters>]
   | Sends a custom "// action:<action> <parameters>"
   | action trigger to the host.

   # Communication Errors

   dont_answer
   | Will not acknowledge the next command.
   go_awol
   | Will completely stop replying
   trigger_resend_lineno
   | Triggers a resend error with a line number mismatch
   trigger_resend_checksum
   | Triggers a resend error with a checksum mismatch
   trigger_missing_checksum
   | Triggers a resend error with a missing checksum
   trigger_missing_lineno
   | Triggers a "no line number with checksum" error w/o resend request
   drop_connection
   | Drops the serial connection
   prepare_ok <broken ok>
   | Will cause <broken ok> to be enqueued for use,
   | will be used instead of actual "ok"

   # Reply Timing / Sleeping

   sleep <int:seconds>
   | Sleep <seconds> s
   sleep_after <str:command> <int:seconds>
   | Sleeps <seconds> s after each execution of <command>
   sleep_after_next <str:command> <int:seconds>
   | Sleeps <seconds> s after execution of next <command>

   # SD printing

   start_sd <str:file>
   | Select and start printing file <file> from SD
   select_sd <str:file>
   | Select file <file> from SD, don't start printing it yet. Use
   | start_sd to start the print
   cancel_sd
   | Cancels an ongoing SD print

   # Misc

   send <str:message>
   | Sends back <message>
   reset
   | Simulates a reset. Internal state will be lost.
