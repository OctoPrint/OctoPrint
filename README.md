OctoPrint
=========

[![Flattr this git repo](http://api.flattr.com/button/flattr-badge-large.png)](https://flattr.com/submit/auto?user_id=foosel&url=https://github.com/foosel/OctoPrint&title=OctoPrint&language=&tags=github&category=software)

OctoPrint provides a responsive web interface for controlling a 3D printer (RepRap, Ultimaker, ...). It currently
allows

* uploading .gcode files to the server and managing them via the UI
* selecting a file for printing, getting the usual stats regarding filament length etc (stats can be disabled for
  faster initial processing)
* starting, pausing and canceling a print job
* while connected to the printer, gaining information regarding the current temperature of both head and bed (if available) in a nice shiny javascript-y temperature graph
* while printing, gaining information regarding the current progress of the print job (height, percentage etc)
* reading the communication log and send arbitrary codes to be executed by the printer
* moving the X, Y and Z axis (jog controls), extruding, retracting and custom controls
* optional: previewing the GCODE of the selected model to print (via gCodeVisualizer), including rendering of the progress during printing
* optional: visual monitoring of the printer via webcam stream integrated into the UI (using e.g. MJPG-Streamer)
* optional: creation of timelapse recordings of the printjob via webcam stream (using e.g. MJPG-Streamer) -- currently two timelaspe methods are implemented, triggering a shot on z-layer change or every "n" seconds

The intended usecase is to run OctoPrint on a single-board computer like the Raspberry Pi and a WiFi module,
connect the printer to the server and therefore create a WiFi-enabled 3D printer. If you want to add a webcam for visual
monitoring and timelapse support, you'll need a **powered** USB hub.

OctoPrint is Free Software and released under the [GNU Affero General Public License V3](http://www.gnu.org/licenses/agpl.html).

Dependencies
------------

OctoPrint depends on a couple of python modules to do its job. Those are listed in requirements.txt and can be
installed using `pip`:

    pip install -r requirements.txt

You should also do this after pulling from the repository, since the dependencies might have changed.

OctoPrint currently only supports Python 2.7.

Usage
-----

Just start the server via

    ./run

By default it binds to all interfaces on port 5000 (so pointing your browser to `http://127.0.0.1:5000`
will do the trick). If you want to change that, use the additional command line parameters `host` and `port`,
which accept the host ip to bind to and the numeric port number respectively. If for example you want the server
to only listen on the local interface on port 8080, the command line would be

    ./run --host=127.0.0.1 --port=8080

Alternatively, the host and port on which to bind can be defined via the configuration.

If you want to run OctoPrint as a daemon (only supported on Linux), use

   ./run --daemon {start|stop|restart} [--pid PIDFILE]

If you do not supply a custom pidfile location via `--pid PIDFILE`, it will be created at `/tmp/octoprint.pid`.

You can also specify the configfile or the base directory (for basing off the `uploads`, `timelapse` and `logs` folders),
e.g.:

    ./run --config /path/to/another/config.yaml --basedir /path/to/my/basedir

See `run --help` for further information.

Configuration
-------------

If not specified via the commandline, the configfile `config.yaml` for OctoPrint is expected in its settings folder,
which is located at `~/.octoprint` on Linux, at `%APPDATA%/OctoPrint` on Windows and at
`~/Library/Application Support/OctoPrint` on MacOS.

The following example config should explain the available options, most of which can also be configured via the
settings dialog within OctoPrint:

    # Use the following settings to configure the serial connection to the printer
    serial:
      # Use the following option to define the default serial port, defaults to unset (= AUTO)
      port: /dev/ttyACM0

      # Use the following option to define the default baudrate, defaults to unset (= AUTO)
      baudrate: 115200

    # Use the following settings to configure the web server
    server:
      # Use this option to define the host to which to bind the server, defaults to "0.0.0.0" (= all interfaces)
      host: 0.0.0.0

      # Use this option to define the port to which to bind the server, defaults to 5000
      port: 5000

    # Use the following settings to configure webcam support
    webcam:
      # Use this option to enable display of a webcam stream in the UI, e.g. via MJPG-Streamer.
      # Webcam support will be disabled if not set
      stream: http://<stream host>:<stream port>/?action=stream

      # Use this option to enable timelapse support via snapshot, e.g. via MJPG-Streamer.
      # Timelapse support will be disabled if not set
      snapshot: http://<stream host>:<stream port>/?action=snapshot

      # Path to ffmpeg binary to use for creating timelapse recordings.
      # Timelapse support will be disabled if not set
      ffmpeg: /path/to/ffmpeg

      # The bitrate to use for rendering the timelapse video. This gets directly passed to ffmpeg.
      bitrate: 5000k

    # Use the following settings to enable or disable OctoPrint features
    feature:
      # Whether to enable the gcode viewer in the UI or not
      gCodeVisualizer: true

      # Specified whether OctoPrint should wait for the start response from the printer before trying to send commands
      # during connect
      waitForStartOnConnect: false

    # Use the following settings to set custom paths for folders used by OctoPrint
    folder:
      # Absolute path where to store gcode uploads. Defaults to the uploads folder in the OctoPrint settings folder
      uploads: /path/to/upload/folder

      # Absolute path where to store finished timelapse recordings. Defaults to the timelapse folder in the OctoPrint
      # settings dir
      timelapse: /path/to/timelapse/folder

      # Absolute path where to store temporary timelapse files. Defaults to the timelapse/tmp folder in the OctoPrint
      # settings dir
      timelapse_tmp: /path/to/timelapse/tmp/folder

      # Absolute path where to store log files. Defaults to the logs folder in the OctoPrint settings dir
      logs: /path/to/logs/folder

    # Use the following settings to configure temperature profiles which will be displayed in the temperature tab.
    temperature:
      profiles:
      - name: ABS
        extruder: 210
        bed: 100
      - name: PLA
        extruder: 180
        bed: 60

    # Use the following settings to configure printer parameters
    printerParameters:
      # Use this to define the movement speed on X, Y, Z and E to use for the controls on the controls tab
      movementSpeed:
        x: 6000
        y: 6000
        z: 200
        e: 300

    # Use the following settings to tweak OctoPrint's appearance a bit to better distinguish multiple instances/printers
    appearance:
      # Use this to give your printer a name. It will be displayed in the title bar (as "<Name> [OctoPrint]") and in the
      # navigation bar (as "OctoPrint: <Name>")
      name: My Printer Model

      # Use this to color the navigation bar. Supported colors are red, orange, yellow, green, blue, violet and default.
      color: blue

    # Use the following settings to add custom controls to the "Controls" tab within OctoPrint
    #
    # Controls consist at least of a name, a type and type-specific further attributes. Currently recognized types are
    # - section: Creates a visual section in the UI, you can use this to separate functional blocks
    # - command: Creates a button that sends a defined GCODE command to the printer when clicked
    # - commands: Creates a button that sends multiple defined GCODE commands to the printer when clicked
    # - parametric_command: Creates a button that sends a parameterized GCODE command to the printer, parameters
    #   needed for the command are added to the UI as input fields, are named and can such be referenced from the command
    # - parametric_commands: Like parametric_command, but supports multiple commands
    #
    # The following example defines a control for enabling the cooling fan with a variable speed defined by the user
    # (default 255) and a control for disabling the fan, all within a section named "Fan", and two example controls with
    # multiple commands in a section "Example for multiple commands".
    controls:
      - name: Fan
        type: section
        children:
          - name: Enable Fan
            type: parametric_command
            command: M106 S%(speed)s
            input:
              - name: Speed (0-255)
                parameter: speed
                default: 255
          - name: Disable Fan
            type: command
            command: M107
      - name: Example for multiple commands
        type: section
        children:
        - name: Move X (static)
          type: commands
          commands:
          - G91
          - G1 X10 F3000
          - G90
        - name: Move X (parametric)
          type: parametric_commands
          commands:
          - G91
          - G1 X%(distance)s F%(speed)s
          - G90
          input:
          - default: 10
            name: Distance
            parameter: distance
          - default: 3000
            name: Speed
            parameter: speed

    # Use the following settings to add custom system commands to the "System" dropdown within OctoPrint's top bar
    #
    # Commands consist of a name, an action identifier, the commandline to execute and an optional confirmation message
    # to display before actually executing the command (should be set to False if a confirmation dialog is not desired).
    #
    # The following example defines a command for shutting down the system under Linux. It assumes that the user under
    # which OctoPrint is running is allowed to do this without password entry.
    system:
      actions:
      - name: Shutdown
        action: shutdown
        command: sudo shutdown -h now
        confirm: You are about to shutdown the system.

Setup on a Raspberry Pi running Raspbian
----------------------------------------

A comprehensive setup guide can be found [on the wiki](https://github.com/foosel/OctoPrint/wiki/Setup-on-a-Raspberry-Pi-running-Raspbian).

Credits
-------

OctoPrint started out as a fork of Cura (https://github.com/daid/Cura) for adding a web interface to its
printing functionality and was originally named Printer WebUI. It still uses Cura's communication code for talking to
the printer, but has been reorganized to only include those parts of Cura necessary for its targeted use case.

It also uses the following libraries and frameworks for backend and frontend:

* Flask: http://flask.pocoo.org/
* Tornado: http://www.tornadoweb.org/
* Tornadio2: https://github.com/MrJoes/tornadio2
* PyYAML: http://pyyaml.org/
* Socket.io: http://socket.io/
* jQuery: http://jquery.com/
* Bootstrap: http://twitter.github.com/bootstrap/
* Knockout.js: http://knockoutjs.com/
* Underscore.js: http://underscorejs.org/
* Flot: http://www.flotcharts.org/
* jQuery File Upload: http://blueimp.github.com/jQuery-File-Upload/
* Pines Notify: http://pinesframework.org/pnotify/
* gCodeVisualizer: https://github.com/hudbrog/gCodeViewer

The following software is recommended for Webcam support on the Raspberry Pi:

* MJPG-Streamer: http://sourceforge.net/apps/mediawiki/mjpg-streamer/index.php?title=Main_Page

I also want to thank [Janina Himmen](http://jhimmen.de/) for providing the kick-ass logo!

Why is it called OctoPrint and what's with the crystal ball in the logo?
------------------------------------------------------------------------

It so happens that I needed a favicon and also OctoPrint's first name -- Printer WebUI -- simply lacked a certain coolness to it. So I asked The Internet(tm) for advise. After some brainstorming, the idea of a cute Octopus watching his print job remotely through a crystal ball was born... [or something like that](https://plus.google.com/u/0/106003970953341660077/posts/UmLD5mW8yBQ).

What do I have to do after the rename from Printer WebUI to OctoPrint?
----------------------------------------------------------------------

If you did checkout OctoPrint from its previous location at https://github.com/foosel/PrinterWebUI.git, you'll have to
update your so-called remote references in git in order to make `git pull` use the new repository location as origin.

To do so you'll only need to execute the following command in your OctoPrint/PrinterWebUI folder:

    git remote set-url origin https://github.com/foosel/OctoPrint.git

After that you might also want to rename your base directory (which probably still is called `PrinterWebUI`) to `OctoPrint`
and delete the folder `printer_webui` in your base folder (which stays there thanks to Python's compiled bytecode files
even after a rename of the Python package to `octoprint`).

After that you are set, the configuration files are migrated automatically.
