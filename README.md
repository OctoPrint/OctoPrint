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

The intended usecase is to run the Printer WebUI on a single-board computer like the Raspberry Pi and a WiFi module,
connect the printer to the server and therefore create a WiFi-enabled 3D printer.

Dependencies
------------

Printer WebUI depends on a couple of python modules to do its job. Those are listed in requirements.txt and can be
installed using `pip`:

    pip install -r requirements.txt

Usage
-----

Just start the server via

    python -m printer_webui.server

By default it binds to all interfaces on port 5000 (so pointing your browser to `http://127.0.0.1:5000`
will do the trick). If you want to change that, use the additional command line parameters `host` and `port`,
which accept the host ip to bind to and the numeric port number respectively. If for example you want to the server
to only listen on the local interface on port 8080, the command line would be

    python -m printer_webui.server --host=127.0.0.1 --port=8080

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
