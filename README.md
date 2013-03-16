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

If not specified via the commandline, the configfile `config.yaml` for OctoPrint is expected in the settings folder, which is located at ~/.octoprint on Linux, at %APPDATA%/OctoPrint on Windows and at ~/Library/Application Support/OctoPrint on MacOS.

A comprehensive overview of all available configuration settings can be found [on the wiki](https://github.com/foosel/OctoPrint/wiki/Configuration).

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
