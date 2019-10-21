.. _sec-development-environment:

Setting up a Development environment
====================================

.. _sec-development-environment-source:

Obtaining, building and running the source
------------------------------------------

This describes the general steps in obtaining, building and running. OS specific instructions can be found
below.

  * Prerequisites:

    * `Python 2.7 <https://python.org>`_ including ``pip``, ``setuptools`` and ``virtualenv``
    * `Git <https://git-scm.com>`_

  * Checkout the OctoPrint sources from their Git repository: ``git clone https://github.com/foosel/OctoPrint.git``
  * Enter the checked out source folder: ``cd OctoPrint``
  * Create a virtual environment in the checked out source folder to use for installing and running OctoPrint and its
    dependencies (this avoids potential versioning issues for the dependencies with system wide installed
    instances): ``virtualenv venv``
  * Activate the virtual environment: ``source venv/bin/activate`` (Linux, MacOS) or
    ``source venv/Scripts/activate`` (Git Bash under Windows, see below)
  * Update ``pip`` in the virtual environment: ``pip install --upgrade pip``
  * Install OctoPrint in `"editable" mode <https://pip.pypa.io/en/stable/reference/pip_install/#editable-installs>`_,
    including its regular *and* development and plugin development dependencies: ``pip install -e .[develop,plugins]``

When the virtual environment is activated you can then:

  * run the OctoPrint server via ``octoprint serve``
  * run the test suite from the checked out source folder via ``nosetests --with-doctest``
  * build the documentation from the ``docs`` sub folder of the checked out sources via ``sphinx-build -b html . _build``

.. _sec-development-environment-source-linux:

Linux
.....

This assumes you'll host your OctoPrint development checkout at ``~/devel/OctoPrint``. If you want to use a different
location, please substitute accordingly.

First make sure you have python including its header files, pip, setuptools, virtualenv, git and some build requirements
installed:

  * On apt based distributions (e.g. Debian, Ubuntu, ...):

    .. code-block:: none

       sudo apt-get install python python-pip python-dev python-setuptools python-virtualenv git libyaml-dev build-essential

  * On zypper based distributions (example below for SLES 12 SP2):

    .. code-block:: none

       sudo zypper ar https://download.opensuse.org/repositories/devel:/languages:/python/SLE_12_SP2/ python_devel
       sudo zypper ref
       sudo zypper in python python-pip python-devel python-setuptools python-virtualenv git libyaml-devel
       sudo zypper in -t pattern Basis-Devel

.. todo::

   Using a Linux distribution that doesn't use ``apt`` or ``zypper``? Please send a
   `Pull Request <https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md#pull-requests>`_ to get the necessary
   steps into this guide!

Then:

.. code-block:: none

   cd ~/devel
   git clone https://github.com/foosel/OctoPrint.git
   cd OctoPrint
   virtualenv venv
   source ./venv/bin/activate
   pip install --upgrade pip
   pip install -e .[develop,plugins]

You can then start OctoPrint via ``~/devel/OctoPrint/venv/bin/octoprint`` or just ``octoprint`` if you activated the virtual
environment.

.. _sec-development-environment-windows:

Windows
.......

This assumes you'll host your OctoPrint development checkout at ``C:\Devel\OctoPrint``. If you want to use a different
location, please substitute accordingly.

First download & install:

  * `Python 2.7.12 Windows x86 MSI installer <https://www.python.org/downloads/release/python-2712/>`_

    * make sure to have the installer add Python to the ``PATH`` and have it install ``pip`` too

  * `Microsoft Visual C++ Compiler for Python 2.7 <http://www.microsoft.com/en-us/download/details.aspx?id=44266>`_
  * `Git for Windows <https://git-for-windows.github.io/>`_

Open the Git Bash you just installed and in that:

.. code-block:: none

   pip install virtualenv
   cd /c/Devel
   git clone https://github.com/foosel/OctoPrint.git
   cd OctoPrint
   virtualenv venv
   source ./venv/Scripts/activate
   pip install --upgrade pip
   pip install -e .[develop,plugins]

.. _sec-development-environment-mac:

Mac OS X
........

.. note::

   This guide is based on the `Setup Guide for Mac OS X on OctoPrint's wiki <https://github.com/foosel/OctoPrint/wiki/Setup-on-Mac/>`_.
   Please report back if it works for you, due to lack of access to a Mac I cannot test it myself. Thanks.

This assumes you'll host your OctoPrint development checkout at ``~/devel/OctoPrint``. If you want to use a different
location, please substitute accordingly.

You'll need a user account with administrator privileges.

  * Install the latest version of Xcode suitable for your OS. For example, OS X 10.11 (El Capitan) requires Xcode 7.
  * Install Xcode's command line tools:

    * ``xcode-select --install``
    * ``sudo xcodebuild`` (ensure the license was accepted)
    * If you have more than one Xcode installed: ``sudo xcode-select -s /Applications/Xcode.app/Contents/Developer``

  * Install Homebrew and use that to install Python:

    * ``ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"``
    * ``brew install python``

  * Install `virtualenv <https://virtualenv.pypa.io/>`_

    * ``pip install virtualenv``

  * Install OctoPrint

    .. code-block:: none

       cd ~/devel
       git clone https://github.com/foosel/OctoPrint.git
       cd OctoPrint
       virtualenv venv
       source venv/bin/activate
       pip install --upgrade pip
       pip install -e .[develop,plugins]

.. _sec-development-environment-ides:

IDE Setup
---------

.. todo::

   Using another IDE than the ones below? Please send a
   `Pull Request <https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md#pull-requests>`_ to get the necessary
   steps into this guide!

.. _sec-development-environment-ides-pycharm:

PyCharm
.......

  - "File" > "Open ...", select OctoPrint checkout folder (e.g. ``~/devel/OctoPrint`` or ``C:\Devel\OctoPrint``)
  - "File" > "Settings ..." > "Project: OctoPrint" > "Project Interpreter" > "Add local ...", select OctoPrint venv
    folder (e.g. ``~/devel/OctoPrint/venv`` or ``C:\Devel\OctoPrint\venv``)
  - Right click "src" in project tree, mark as source folder
  - Add Run/Debug Configuration, select "Python":

    * Name: OctoPrint server
    * Script: path to ``run`` in the OctoPrint checkout folder (e.g. ``~/devel/OctoPrint/run`` or ``C:\Devel\OctoPrint\run``)
    * Script parameters: ``serve --debug``
    * Project: ``OctoPrint``
    * Python interpreter: the ``venv`` local virtual environment
    * Working directory: the OctoPrint checkout folder (e.g. ``~/devel/OctoPrint`` or ``C:\Devel\OctoPrint``)
    * If you want dependencies to auto-update on run if necessary: "Before Launch" > "+" > "Run external tool" > "+"

      * Name: Update OctoPrint dependencies
      * Program: ``$PyInterpreterDirectory$/pip`` (or ``$PyInterpreterDirectory$/pip.exe`` on Windows)
      * Parameters: ``install -e .[develop,plugins]``
      * Working directory: ``$ProjectFileDir$``

  - Add Run/Debug Configuration, select "Python tests" and therein "Nosetests":

    * Name: OctoPrint nosetests
    * Target: Path, ``.``
    * Project: ``OctoPrint``
    * Python interpreter: the ``venv`` local virtual environment
    * Working directory: the OctoPrint checkout folder (e.g. ``~/devel/OctoPrint`` or ``C:\Devel\OctoPrint``)
    * Just like with the run configuration for the server you can also have the dependencies auto-update on run of
      the tests, see above on how to set this up.

  - Add Run/Debug Configuration, select "Python docs" and therein "Sphinx task"

    * Name: OctoPrint docs
    * Command: ``html``
    * Input: the ``docs`` folder in the OctoPrint checkout folder (e.g. ``~/devel/OctoPrint/docs`` or
      ``C:\Devel\OctoPrint\docs``)
    * Output: the ``docs/_build`` folder in the OctoPrint checkout folder (e.g. ``~/devel/OctoPrint/docs/_build`` or
      ``C:\Devel\OctoPrint\docs\_build``)
    * Project: ``OctoPrint``
    * Python interpreter: the ``venv`` local virtual environment
    * Just like with the run configuration for the server you can also have the dependencies auto-update when building
      the documentation, see above on how to set this up.

.. note::

   Make sure you are running a PyCharm version of 2016.1 or later, or manually fix
   `a debugger bug contained in earlier versions <https://youtrack.jetbrains.com/issue/PY-18365>`_ or plugin management
   will not work in your developer install when running OctoPrint from PyCharm in debug mode.
