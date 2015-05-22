OctoPrint
=========

[![Flattr this git repo](http://api.flattr.com/button/flattr-badge-large.png)](https://flattr.com/submit/auto?user_id=foosel&url=https://github.com/foosel/OctoPrint&title=OctoPrint&language=&tags=github&category=software)

OctoPrint provides a responsive web interface for controlling a 3D printer (RepRap, Ultimaker, ...). It is Free Software
and released under the [GNU Affero General Public License V3](http://www.gnu.org/licenses/agpl.html).

Its website can be found at [octoprint.org](http://octoprint.org).

Contributing
------------

Please see the project's [Contribution Guidelines](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md).

Installation
------------

Installation instructions for installing from source for different operating systems can be found [on the wiki](https://github.com/foosel/OctoPrint/wiki#assorted-guides).

If you want to run OctoPrint on a Raspberry Pi you might want to take a look at [OctoPi](https://github.com/guysoft/OctoPi)
which is a custom SD card image that includes OctoPrint plus dependencies.

Dependencies
------------

OctoPrint depends on a couple of python modules to do its job. Those are automatically installed when installing
OctoPrint via `setup.py`:

    python setup.py install

You should also do this every time after pulling from the repository, since the dependencies might have changed.

OctoPrint currently only supports Python 2.7.

Usage
-----

Running the `setup.py` script installs the `octoprint` script in your Python installation's scripts folder
(which depending on whether you installed OctoPrint globally or into a virtual env will be on your `PATH` or not). The
following usage examples assume that said `octoprint` script is on your `PATH`.

You can start the server via

    octoprint

By default it binds to all interfaces on port 5000 (so pointing your browser to `http://127.0.0.1:5000`
will do the trick). If you want to change that, use the additional command line parameters `host` and `port`,
which accept the host ip to bind to and the numeric port number respectively. If for example you want the server
to only listen on the local interface on port 8080, the command line would be

    octoprint --host=127.0.0.1 --port=8080

Alternatively, the host and port on which to bind can be defined via the configuration.

If you want to run OctoPrint as a daemon (only supported on Linux), use

    octoprint --daemon {start|stop|restart} [--pid PIDFILE]

If you do not supply a custom pidfile location via `--pid PIDFILE`, it will be created at `/tmp/octoprint.pid`.

You can also specify the configfile or the base directory (for basing off the `uploads`, `timelapse` and `logs` folders),
e.g.:

    octoprint --config /path/to/another/config.yaml --basedir /path/to/my/basedir

See `octoprint --help` for further information.

OctoPrint also ships with a `run` script in its source directory. You can also invoke that to start up the server, it
takes the same command line arguments as the `octoprint` script.

Configuration
-------------

If not specified via the commandline, the configfile `config.yaml` for OctoPrint is expected in the settings folder,
which is located at `~/.octoprint` on Linux, at `%APPDATA%/OctoPrint` on Windows and
at `~/Library/Application Support/OctoPrint` on MacOS.

A comprehensive overview of all available configuration settings can be found
[on the wiki](https://github.com/foosel/OctoPrint/wiki/Configuration). Please note that the most commonly used
configuration settings can also easily be edited from OctoPrint's settings dialog.
