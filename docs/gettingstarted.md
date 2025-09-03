# Getting Started

## Installation

Installation instructions for installing from source for different operating
systems can be found [on the forum](https://community.octoprint.org/tags/c/support/guides/15/setup).

If you want to run OctoPrint on a Raspberry Pi, you really should take a look at [OctoPi](https://github.com/guysoft/OctoPi)
which is a custom SD card image that includes OctoPrint plus dependencies.

The generic steps that should basically be done regardless of operating system
and runtime environment are the following (as *regular
user*, please keep your hands *off* of the `sudo` command here!) - this assumes
you already have Python 3.9+, pip and virtualenv and their dependencies set up on your system:

1. Create a user-owned virtual environment therein: `virtualenv venv`. If you want to specify a specific python
   to use instead of whatever version your system defaults to, you can also explicitly require that via the `--python`
   parameter, e.g. `virtualenv --python=python3 venv`.
2. Install OctoPrint *into that virtual environment*: `./venv/bin/pip install OctoPrint`

You may then start the OctoPrint server via `/path/to/OctoPrint/venv/bin/octoprint`, see [Usage](#usage)
for details.

After installation, please make sure you follow the first-run wizard and set up
access control as necessary.

## Dependencies

OctoPrint depends on a few python modules to do its job. Those are automatically installed when installing
OctoPrint via `pip`.

OctoPrint currently supports Python 3.9, 3.10, 3.11, 3.12 and 3.13.

## Usage

Running the pip install via

    pip install OctoPrint

installs the `octoprint` script in your Python installation's scripts folder
(which, depending on whether you installed OctoPrint globally or into a virtual env, will be in your `PATH` or not). The
following usage examples assume that the `octoprint` script is on your `PATH`.

You can start the server via

    octoprint serve

By default it binds to all interfaces on port 5000 (so pointing your browser to `http://127.0.0.1:5000`
will do the trick). If you want to change that, use the additional command line parameters `host` and `port`,
which accept the host ip to bind to and the numeric port number respectively. If for example you want the server
to only listen on the local interface on port 8080, the command line would be

    octoprint serve --host=127.0.0.1 --port=8080

Alternatively, the host and port on which to bind can be defined via the config file.

If you want to run OctoPrint as a daemon (only supported on Linux), use

    octoprint daemon {start|stop|restart} [--pid PIDFILE]

If you do not supply a custom pidfile location via `--pid PIDFILE`, it will be created at `/tmp/octoprint.pid`.

You can also specify the config file or the base directory (for basing off the `uploads`, `timelapse` and `logs` folders),
e.g.:

    octoprint serve --config /path/to/another/config.yaml --basedir /path/to/my/basedir

To start OctoPrint in safe mode - which disables all third party plugins that do not come bundled with OctoPrint - use
the ``--safe`` flag:

    octoprint serve --safe

See `octoprint --help` for more information on the available command line parameters.

OctoPrint also ships with a `run` script in its source directory. You can invoke it to start the server. It
takes the same command line arguments as the `octoprint` script.

## Configuration

If not specified via the command line, the config file `config.yaml` for OctoPrint is expected in the settings folder,
which is located at `~/.octoprint` on Linux, at `%APPDATA%/OctoPrint` on Windows and
at `~/Library/Application Support/OctoPrint` on MacOS.

A comprehensive overview of all available configuration settings can be found
[in the configuration docs](configuration/config_yaml).

Please note that the most commonly used configuration settings can also easily
be edited from OctoPrint's settings dialog.
