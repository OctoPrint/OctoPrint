.. _sec-development-environment:

************************************
Setting up a Development environment
************************************

.. _sec-development-environment-source:

Obtaining, building and running the source
==========================================

This describes the **general, platform agnostic** steps in obtaining, building and running. OS specific instructions can be found
below.

  * Prerequisites:

    * `Latest stable Python 3 <https://python.org>`_ including ``pip``, ``setuptools`` and ``virtualenv``
    * `Git <https://git-scm.com>`_

  * Checkout the OctoPrint sources from their Git repository:

      * ``git clone https://github.com/OctoPrint/OctoPrint.git``

  * Enter the checked out source folder: ``cd OctoPrint``
  * Create a virtual environment in the checked out source folder to use for
    installing and running OctoPrint and its dependencies. Creating virtual environments avoids potential versioning
    issues for the dependencies with system wide installed instances: ``virtualenv --python=python3 venv``

    .. note::

       This assumes that the ``python3`` binary is available directly on your ``PATH``. If
       it cannot be found on your ``PATH`` like this you'll need to specify the full path here,
       e.g. ``virtualenv --python=/path/to/python3/bin/python venv``

  * Activate the virtual environment: ``source venv/bin/activate`` (Linux, macOS) or ``source venv/Scripts/activate`` (Git Bash under Windows, see below)

  * Update ``pip`` in the virtual environment:

      * ``pip install --upgrade pip``

  * Install OctoPrint in `"editable" mode <https://pip.pypa.io/en/stable/reference/pip_install/#editable-installs>`_,
    including its regular *and* development and plugin development dependencies:

      * ``pip install -e '.[develop,plugins,docs]'``

  * Set up the pre-commit hooks that make sure any changes you do adhere to the styling rules:

      * ``pre-commit install``

  * Tell ``git`` where to find the file with revisions to exclude for ``git blame``:

      * ``git config blame.ignoreRevsFile .git-blame-ignore-revs``

When the virtual environment is activated you can then:

  * run the OctoPrint server via ``octoprint serve``
  * run the test suite from the checked out source folder via ``pytest``
  * trigger the pre-commit check suite manually from the checked out source folder via
    ``pre-commit run --hook-stage manual --all-files``
  * build the documentation running ``sphinx-build -b html . _build`` in the ``docs``
    folder -- the documentation will be available in the newly created ``_build``
    directory. You can simply browse it locally by opening ``index.html``

.. _sec-development-environment-source-linux:

Linux
-----

This assumes you'll host your OctoPrint development checkout at ``~/devel/OctoPrint``. If you want to use a different
location, please substitute accordingly.

First make sure you have python 3 including its header files, pip, setuptools, virtualenv, git and some build requirements
installed:

  * On apt based distributions (e.g. Debian, Ubuntu, ...):

    .. code-block:: none

       sudo apt-get install python3 python3-pip python3-dev python3-setuptools python3-virtualenv git libyaml-dev build-essential

Then:

.. code-block:: none

   cd ~/devel
   git clone https://github.com/OctoPrint/OctoPrint.git
   cd OctoPrint
   virtualenv --python=python3 venv
   source ./venv/bin/activate
   pip install --upgrade pip
   pip install -e '.[develop,plugins,docs]'
   pre-commit install
   git config blame.ignoreRevsFile .git-blame-ignore-revs


.. todo::

   Using a Linux distribution that doesn't use ``apt``? Please send a
   `Pull Request <https://github.com/OctoPrint/OctoPrint/blob/master/CONTRIBUTING.md#pull-requests>`_ to get the necessary
   steps into this guide!

.. _sec-development-environment-windows:

Windows
-------

This assumes you'll host your OctoPrint development checkout at ``C:\Devel\OctoPrint``. If you want to use a different
location, please substitute accordingly.

First download & install:

  * `Git for Windows <https://git-for-windows.github.io/>`_

  * `Latest *stable* Python 3 release from python.org <https://www.python.org/downloads/windows/>`_

    * make sure to have the installer add Python to the ``PATH`` and have it install ``pip`` too
    * it's recommended to install Python 3 into ``C:\Python3`` - if you select
      different install locations please substitute accordingly
    * it's also recommended to install for all users

  * `Build Tools For Visual Studio 2019 <https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2019>`_

    * install "C++ build tools" and ensure the latest versions of "MSVCv142 - VS 2019 C++ x64/x86 build tools" and
      "Windows 10 SDK" are checked under individual components.


Open the Git Bash you just installed and in that:

.. code-block:: none

   pip install virtualenv
   cd /c/Devel
   git clone https://github.com/OctoPrint/OctoPrint.git
   cd OctoPrint
   virtualenv --python=C:/Python3/python.exe venv
   source ./venv/Scripts/activate
   pip install --upgrade pip
   python -m pip install -e '.[develop,plugins,docs]'
   pre-commit install
   git config blame.ignoreRevsFile .git-blame-ignore-revs

.. _sec-development-environment-windows-optional:

Optional but recommended tools
..............................

These are some tools that are recommended but not required to have on hand:

  * `Visual Studio Code <https://code.visualstudio.com/download>`_

  * `Windows Terminal <https://github.com/microsoft/terminal>`_

    Add the following profile to ``profiles.list`` in the settings, that will allow you to
    easily start Git Bash from the terminal:

    .. code-block:: js

       {
           "guid": "{3df4550c-eebd-496c-a189-e55f2f8b01ce}",
           "hidden": false,
           "name": "Git Bash",
           "commandline": "C:\\Program Files\\Git\\bin\\bash.exe --login -i",
           "startingDirectory": "C:\\Devel",
           "tabTitle": "Git Bash",
           "suppressApplicationTitle": true
       },

.. _sec-development-environment-mac:

Mac OS X
--------

.. note::

   This guide is based on the `Setup Guide for Mac OS X on OctoPrint's Community Forum <https://community.octoprint.org/t/setting-up-octoprint-on-macos/13425>`_.
   Please report back if it works for you, due to lack of access to a Mac I cannot test it myself. Thanks.

This assumes you'll host your OctoPrint development checkout at ``~/devel/OctoPrint``. If you want to use a different
location, please substitute accordingly.

You'll need a user account with administrator privileges.

  * Install the latest version of Xcode suitable for your OS. For example, OS X 10.11 (El Capitan) requires Xcode 7.
  * Install Xcode's command line tools:

    * ``xcode-select --install``
    * ``sudo xcodebuild`` (ensure the license was accepted)
    * If you have more than one Xcode installed: ``sudo xcode-select -s /Applications/Xcode.app/Contents/Developer``

  * Install Homebrew and use that to install Python 3:

    * ``ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"``
    * ``brew install python``

  * Install `pip <https://pip.pypa.io/en/stable/installation/#supported-methods>`_

    * ``python -m ensurepip --upgrade``

  * Install `virtualenv <https://virtualenv.pypa.io/>`_

    * ``pip install virtualenv``

  * Install OctoPrint

    .. code-block:: none

       cd ~/devel
       git clone https://github.com/OctoPrint/OctoPrint.git
       cd OctoPrint
       virtualenv venv
       source venv/bin/activate
       pip install --upgrade pip
       pip install -e '.[develop,plugins]'
       pre-commit install
       git config blame.ignoreRevsFile .git-blame-ignore-revs

.. _sec-development-environment-ides:

IDE Setup
=========

.. todo::

   Using another IDE than the ones below? Please send a
   `Pull Request <https://github.com/OctoPrint/OctoPrint/blob/master/CONTRIBUTING.md#pull-requests>`_ to get the necessary
   steps into this guide!

.. _sec-development-environment-ides-pycharm:

PyCharm
-------

  - "File" > "Open ...", select OctoPrint checkout folder (e.g. ``~/devel/OctoPrint`` or ``C:\Devel\OctoPrint``)
  - Register virtual environments:

    - **(Linux, Windows)** "File" > "Settings ..." > "Project: OctoPrint" > "Project Interpreter" > "Add local ...",
      select OctoPrint ``venv`` folder (e.g. ``~/devel/OctoPrint/venv`` or ``C:\Devel\OctoPrint\venv``).
    - **(macOS)** "PyCharm" > "Preferences ..." > "Project: OctoPrint" > "Project Interpreter" > "Add ..." >
      "Virtualenv Environment > "Existing Environment", select OctoPrint ``venv`` folder (e.g. ``~/devel/OctoPrint/venv``).

    If desired, repeat for any other additional Python venvs (e.g. for separate Python 3 versions).

  - Right click "src" in project tree, mark as source folder
  - Add Run/Debug Configuration, select "Python":

    * Name: OctoPrint server
    * Module name: ``octoprint``
    * Parameters: ``serve --debug``
    * Project: ``OctoPrint``
    * Python interpreter: Project Default
    * Working directory: the OctoPrint checkout folder (e.g. ``~/devel/OctoPrint`` or ``C:\Devel\OctoPrint``)
    * If you want build artifacts to be cleaned up on run (recommended): "Before Launch" > "+" > "Run external tool" > "+"

      * Name: Clean build directory
      * Program: ``$ModuleSdkPath$``
      * Parameters: ``setup.py clean``
      * Working directory: ``$ProjectFileDir$``

    * If you want dependencies to auto-update on run if necessary (recommended): "Before Launch" > "+" > "Run external tool" > "+"

      * Name: Update OctoPrint dependencies
      * Program: ``$ModuleSdkPath$``
      * Parameters: ``-m pip install -e '.[develop,plugins]'``
      * Working directory: ``$ProjectFileDir$``

      Note that sadly that seems to cause some hiccups on current PyCharm versions due to ``$PyInterpreterDirectory$``
      being empty sometimes, so if this fails to run on your installation, you should update your dependencies manually
      for now.

  - Add Run/Debug Configuration, select "Python tests" and therein "pytest":

    * Name: OctoPrint tests
    * Target: Custom
    * Project: ``OctoPrint``
    * Python interpreter: Project Default
    * Working directory: the OctoPrint checkout folder (e.g. ``~/devel/OctoPrint`` or ``C:\Devel\OctoPrint``)
    * Just like with the run configuration for the server you can also have the dependencies auto-update on run of
      the tests, see above on how to set this up.

  - Add Run/Debug Configuration, select "Python":

    * Name: OctoPrint docs
    * Module name: ``sphinx.cmd.build``
    * Parameters: ``-v -T -E ./docs ./docs/_build -b html``
    * Project: ``OctoPrint``
    * Python interpreter: ``venv`` environment
    * Working directory: the OctoPrint checkout folder (e.g. ``~/devel/OctoPrint`` or ``C:\Devel\OctoPrint``)
    * Just like with the run configuration for the server you can also have the dependencies auto-update when building
      the documentation, see above on how to set this up.

    Note that this requires you to also have installed the additional ``docs`` dependencies into the Python 3 venv as
    described above via ``pip install -e '.[develop,plugins,docs]'``.

  - Settings > Tools > File Watchers (you might have to enable this, it's a bundled plugin), add new:

    * Name: pre-commit
    * File type: Python
    * Scope: Module 'OctoPrint'
    * Program: ``<OctoPrint venv folder>/bin/pre-commit`` (Linux) or ``<OctoPrint venv folder>/Scripts/pre-commit`` (Windows)
    * Arguments: ``run --hook-stage manual --files $FilePath$``
    * Output paths to refresh: ``$FilePath$``
    * Working directory: ``$ProjectFileDir$``
    * disable "Auto-save edited files to trigger the watched"
    * enable "Trigger the watched on external changes"

To switch between virtual environments (e.g. Python 3.7 and 3.8), all you need to do now is change the Project Default Interpreter and restart
OctoPrint. On current PyCharm versions you can do that right from a small selection field in the footer of the IDE.
Otherwise go through Settings.

.. note::

   Make sure you are running a PyCharm version of 2016.1 or later, or manually fix
   `a debugger bug contained in earlier versions <https://youtrack.jetbrains.com/issue/PY-18365>`_ or plugin management
   will not work in your developer install when running OctoPrint from PyCharm in debug mode.

Visual Studio Code (vscode)
---------------------------

  - Install Visual Studio Code from `code.visualstudio.com <https://code.visualstudio.com/Download>`_
  - Open folder select OctoPrint checkout folder (e.g. ``~/devel/OctoPrint`` or ``C:\Devel\OctoPrint``)

  - Create a directory ``.vscode`` if not already present in the root of the project

  - Create the following files inside the ``.vscode`` directory

    settings.json
      .. code-block:: json

         {
             "python.defaultInterpreterPath": "venv/bin/python",
             "python.formatting.provider": "black",
             "python.formatting.blackArgs": [
                 "--config",
                 "black.toml"
             ],
             "editor.formatOnSave": true,
             "python.sortImports.args": [
                 "--profile=black",
             ],
             "[python]": {
                 "editor.codeActionsOnSave": {
                     "source.organizeImports": true
                 }
             },
             "python.linting.pylintEnabled": false,
             "python.linting.flake8Enabled": true,
             "python.linting.enabled": true
         }

    tasks.json
      .. code-block:: json

         {
           "version": "2.0.0",
           "tasks": [
             {
                 "label": "clean build artifacts",
                 "type": "shell",
                 "command": "python ./setup.py clean"
             },
             {
                 "label": "build docs",
                 "type": "shell",
                 "command": "sphinx-build -b html ./docs ./docs/_build"
             }
           ]
         }


    launch.json
      .. code-block:: json

         {
           "version": "0.2.0",
           "configurations": [
               {
                   "name": "OctoPrint",
                   "type": "python",
                   "request": "launch",
                   "module": "octoprint",
                   "args": [
                       "serve",
                       "--debug"
                   ],
                   "cwd": "${workspaceFolder}/src",
                   "preLaunchTask": "clean build artifacts"
               }
           ]
         }

  In the terminal install the python extension by running this command:

    .. code-block:: bash

      code --install-extension ms-python.python

  In vscode terminal, or with venv active install code formatter black and linter flake8 by running:

    .. code-block:: bash

      python -m pip install -U black flake8 flake8-bugbear

  Summary of vscode config:

  * Pressing ``F5`` will now start OctoPrint in debug mode

  * Your terminal inside vscode uses the virtual python environment

  * Saving a file will run an auto formatter and import sort

  * ``Ctrl+Shift+B`` can be used to run the ``build docs`` task to rebuild the documentation


