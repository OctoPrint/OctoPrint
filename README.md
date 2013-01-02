Printer WebUI
=============

The Printer WebUI provides a responsive web interface for controlling a 3D printer (RepRap, Ultimaker, ...). It currently
allows

* uploading .gcode files to the server and managing them via the UI
* selecting a file for printing, getting the usual stats regarding filament length etc
* starting, pausing and canceling a print job
* while connected to the printer, gaining information regarding the current temperature of both head and bed (if available) in a nice shiny javascript-y temperature graph
* while printing, gaining information regarding the current progress of the print job (height, percentage etc)
* reading the communication log and send arbitrary codes to be executed by the printer
* moving the X, Y and Z axis (jog controls, although very ugly ones right now)
* changing the speed modifiers for inner & outer wall, fill and support
* optional: visual monitoring of the printer via webcam stream integrated into the UI (using MJPG-Streamer)

The intended usecase is to run the Printer WebUI on a single-board computer like the Raspberry Pi and a WiFi module,
connect the printer to the server and therefore create a WiFi-enabled 3D printer.

Dependencies
------------

Printer WebUI depends on a couple of python modules to do its job. Those are listed in requirements.txt and can be
installed using `pip`:

    pip install -r requirements.txt

Printer WebUI currently only supports Python 2.7.

Usage
-----

Just start the server via

    python -m printer_webui.server

By default it binds to all interfaces on port 5000 (so pointing your browser to `http://127.0.0.1:5000`
will do the trick). If you want to change that, use the additional command line parameters `host` and `port`,
which accept the host ip to bind to and the numeric port number respectively. If for example you want to the server
to only listen on the local interface on port 8080, the command line would be

    python -m printer_webui.server --host=127.0.0.1 --port=8080

Alternatively, the host and port on which to bind can be defined via the configuration.

Configuration
-------------

The config-file for Printer WebUI is expected at `~/.printerwebui/config.ini` for Linux, at `%APPDATA%/PrinterWebUI/config.ini`
for Windows and at `~/Library/Application Support/config.ini` for MacOS X.
The following example config should explain the available options:

    [serial]
    # use the following option to define the default serial port, defaults to unset (= AUTO)
    port = /dev/ttyACM0
    # use the following option to define the default baudrate, defaults to unset (= AUTO)
    baudrate = 115200

    [server]
    # use this option to define the host to which to bind the server, defaults to "0.0.0.0" (= all interfaces)
    host = 0.0.0.0
    # use this option to define the port to which to bind the server, defaults to 5000
    port = 5000

    [webcam]
    # use this option to enable display of a webcam stream in the UI, e.g. via MJPG-Streamer
    stream = http://10.0.0.2:8080/?action=stream

Setup on a Raspberry Pi running Raspbian
----------------------------------------

I currently run the Printer WebUI on a Raspberry Pi running Raspbian (http://www.raspbian.org/). For the basic
package you'll need Python 2.7 (should be installed by default), pip and flask:

    cd ~
    sudo apt-get install python-pip git
    git clone https://github.com/foosel/PrinterWebUI.git
    cd PrinterWebUI
    pip install -r requirements.txt

You should then be able to start the WebUI server:

    pi@raspberrypi ~/PrinterWebUI $ python -m printer_webui.server
     * Running on http://0.0.0.0:5000/

If you also want webcam support, you'll need to download and compile MJPG-Streamer:

    cd ~
    sudo apt-get install libjpeg8-dev imagemagick
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

If you now point your browser to http://<your Raspi's IP>:8080/?action=stream, you should see a moving picture at 5fps.
Open `~/.printerwebui/config.ini` and add the following lines to it:

    [webcam]
    stream = http://<your Raspi's IP>:8080/?action=stream

Restart the WebUI server and reload its frontend. You should now see a Webcam tab with content.

If everything works, add the startup commands to `/etc/rc.local`.

Credits
-------

The Printer WebUI started out as a fork of Cura (https://github.com/daid/Cura) for adding a web interface to its
printing functionality. It still uses Cura's communication code for talking to the printer, but has been reorganized to
only include those parts of Cura necessary for its targeted usecase.

It also uses the following libraries and frameworks for backend and frontend:

* Flask: http://flask.pocoo.org/
* jQuery: http://jquery.com/
* Bootstrap: http://twitter.github.com/bootstrap/
* Knockout.js: http://knockoutjs.com/
* Flot: http://www.flotcharts.org/
* jQuery File Upload: http://blueimp.github.com/jQuery-File-Upload/

And this for Webcam support:

* MJPG-Streamer: http://sourceforge.net/apps/mediawiki/mjpg-streamer/index.php?title=Main_Page
