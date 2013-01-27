OctoPrint
=========

OctoPrint provides a responsive web interface for controlling a 3D printer (RepRap, Ultimaker, ...). It currently
allows

* uploading .gcode files to the server and managing them via the UI
* selecting a file for printing, getting the usual stats regarding filament length etc (stats can be disabled for
  faster initial processing)
* starting, pausing and canceling a print job
* while connected to the printer, gaining information regarding the current temperature of both head and bed (if available) in a nice shiny javascript-y temperature graph
* while printing, gaining information regarding the current progress of the print job (height, percentage etc)
* reading the communication log and send arbitrary codes to be executed by the printer
* moving the X, Y and Z axis (jog controls, although very ugly ones right now)
* changing the speed modifiers for inner & outer wall, fill and support
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

    python -m octoprint.server

or alternatively

    ./run

By default it binds to all interfaces on port 5000 (so pointing your browser to `http://127.0.0.1:5000`
will do the trick). If you want to change that, use the additional command line parameters `host` and `port`,
which accept the host ip to bind to and the numeric port number respectively. If for example you want to the server
to only listen on the local interface on port 8080, the command line would be

    python -m octoprint.server --host=127.0.0.1 --port=8080

or

    ./run --host=127.0.0.1 --port=8080

Alternatively, the host and port on which to bind can be defined via the configuration.

Configuration
-------------

The config-file `config.ini` for OctoPrint is expected in its settings folder, which is located at `~/.octoprint`
on Linux, at `%APPDATA%/OctoPrint` on Windows and at `~/Library/Application Support/OctoPrint` on MacOS.

The following example config should explain the available options:

    [serial]
    # Use the following option to define the default serial port, defaults to unset (= AUTO)
    port = /dev/ttyACM0

    # Use the following option to define the default baudrate, defaults to unset (= AUTO)
    baudrate = 115200

    [server]
    # Use this option to define the host to which to bind the server, defaults to "0.0.0.0" (= all interfaces)
    host = 0.0.0.0

    # Use this option to define the port to which to bind the server, defaults to 5000
    port = 5000

    [webcam]
    # Use this option to enable display of a webcam stream in the UI, e.g. via MJPG-Streamer.
    # Webcam support will be disabled if not set
    stream = http://<stream host>:<stream port>/?action=stream

    # Use this option to enable timelapse support via snapshot, e.g. via MJPG-Streamer.
    # Timelapse support will be disabled if not set
    snapshot = http://<stream host>:<stream port>/?action=snapshot

    # Path to ffmpeg binary to use for creating timelapse recordings.
    # Timelapse support will be disabled if not set
    ffmpeg = /path/to/ffmpeg

    [feature]
    # Whether to enable gcode analysis for displaying needed filament and estimated print time. Disabling this (set
    # to False) will speed up the loading of gcode files before printing significantly, but the mentioned statistical
    # data will not be available
    analyzeGcode = True

    [folder]
    # Absolute path where to store gcode uploads. Defaults to the uploads folder in the OctoPrint settings folder
    uploads = /path/to/upload/folder

    # Absolute path where to store finished timelapse recordings. Defaults to the timelapse folder in the OctoPrint
    # settings dir
    timelapse = /path/to/timelapse/folder

    # Absolute path where to store temporary timelapse files. Defaults to the timelapse/tmp folder in the OctoPrint
    # settings dir
    timelapse_tmp = /path/timelapse/tmp/folder

Setup on a Raspberry Pi running Raspbian
----------------------------------------

I currently run the OctoPrint on a Raspberry Pi running Raspbian (http://www.raspbian.org/). I recommend to use
a maximum baudrate of 115200 baud in your printer firmware, as the used Python serial module does not support 
250000 baud in all Linux distributions yet (Raspbian being not one of them, at least according to my experience). 

For the basic package you'll need Python 2.7 (should be installed by default), pip and a couple of dependencies
listed in requirements.txt:

    cd ~
    sudo apt-get install python-pip git
    git clone https://github.com/foosel/OctoPrint.git
    cd OctoPrint
    sudo pip install -r requirements.txt

You should then be able to start the OctoPrint server:

    pi@raspberrypi ~/OctoPrint $ ./run
     * Running on http://0.0.0.0:5000/

If you also want webcam and timelapse support, you'll need to download and compile MJPG-Streamer:

    cd ~
    sudo apt-get install subversion libjpeg8-dev imagemagick libav-tools
    wget -Omjpg-streamer.tar.gz http://mjpg-streamer.svn.sourceforge.net/viewvc/mjpg-streamer/mjpg-streamer/?view=tar
    tar xfz mjpg-streamer.tar.gz
    cd mjpg-streamer
    make

This should hopefully run through without any compilation errors. You should then be able to start the webcam server:

    pi@raspberrypi ~/mjpg-streamer $ ./mjpg_streamer -i "./input_uvc.so" -o "./output_http.so"
    MJPG Streamer Version: svn rev:
     i: Using V4L2 device.: /dev/video0
     i: Desired Resolution: 640 x 480
     i: Frames Per Second.: 5
     i: Format............: MJPEG
    [...]
     o: www-folder-path...: disabled
     o: HTTP TCP port.....: 8080
     o: username:password.: disabled
     o: commands..........: enabled

If you now point your browser to `http://<your Raspi's IP>:8080/?action=stream`, you should see a moving picture at 5fps.
Open `~/.octoprint/config.ini` and add the following lines to it:

    [webcam]
    stream = http://<your Raspi's IP>:8080/?action=stream
    snapshot = http://127.0.0.1:8080/?action=snapshot
    ffmpeg = /usr/bin/avconv

Restart the OctoPrint server and reload its frontend. You should now see a Webcam tab with content.

If everything works, add the startup commands to `/etc/rc.local`.

Credits
-------

The OctoPrint started out as a fork of Cura (https://github.com/daid/Cura) for adding a web interface to its
printing functionality and was originally named Printer WebUI. It still uses Cura's communication code for talking to
the printer, but has been reorganized to only include those parts of Cura necessary for its targeted usecase.

It also uses the following libraries and frameworks for backend and frontend:

* Flask: http://flask.pocoo.org/
* Tornado: http://www.tornadoweb.org/
* Tornadio2: https://github.com/MrJoes/tornadio2
* Socket.io: http://socket.io/
* jQuery: http://jquery.com/
* Bootstrap: http://twitter.github.com/bootstrap/
* Knockout.js: http://knockoutjs.com/
* Flot: http://www.flotcharts.org/
* jQuery File Upload: http://blueimp.github.com/jQuery-File-Upload/

The following software is recommended for Webcam support on the Raspberry Pi:

* MJPG-Streamer: http://sourceforge.net/apps/mediawiki/mjpg-streamer/index.php?title=Main_Page

I also want to thank [Janina Himmen](http://jhimmen.de/) for providing the kick-ass logo!

Why is it called OctoPrint and what's with the crystal ball in the logo?
------------------------------------------------------------------------

It so happens that I needed a favicon and also OctoPrint's first name -- Printer WebUI -- simply lacked a certain coolness to it. So I asked The Internet(tm) for advise. After some brainstorming, the idea of a cute Octopus watching his print job remotely through a crystal ball was born... [or something like that](https://plus.google.com/u/0/106003970953341660077/posts/UmLD5mW8yBQ).

What do I have to do after the rename from Printer WebUI to OctoPrint?
----------------------------------------------------------------------

If you did checkout OctoPrint from its previous location at https://github.com/foosel/PrinterWebUI.git, you'll have to
update your so-called remote references in git in order to make 'git pull' use the new repository location as origin.

To do so you'll only need to execute the following command in your OctoPrint/PrinterWebUI folder:

  git remote set-url origin https://github.com/foosel/OctoPrint.git

After that you might also want to rename your base directory (which probably still is called 'PrinterWebUI') to 'OctoPrint'
and delete the folder 'printer_webui' in your base folder (which stays there thanks to Python's compiled bytecode files
even after a rename of the Python package to 'octoprint').

After that you are set, the configuration files are migrated automatically :)