Cura
====

If you are reading this, then you are looking at the *development* version of Cura. If you just want to use Cura look at the following location: https://github.com/daid/Cura/wiki

Development
===========

Cura is developed in Python. Getting Cura up and running for development is not very difficult. If you copy the python and pypy from a release into your Cura development checkout then you can use Cura right away, just like you would with a release.
For development with git, check the help on github. Pull requests is the fastest way to get changes into Cura.

Mac OS X
--------
The following section describes how to prepare environment for developing and packaing for Mac OS X.

###Python
You'll need non-system, framework-based, universal with min deployment target set to 10.6 build of Python 2.7

**non-system**: it was not bundeled with distribution of Mac OS X. You can check this by `python -c "import sys; print sys.prefix"`. Output should *not* start with *"/System/Library/Frameworks/Python.framework/"*

**framework-based**: Output of `python -c "import distutils.sysconfig as c; print(c.get_config_var('PYTHONFRAMEWORK'))"` should be non-empty string

**universal**: output of ``lipo -info `which python` `` include both i386 and x86_64. E.g *"Architectures in the fat file: /usr/local/bin/python are: i386 x86_64"*

**deployment target set to 10.6**: Output of ``otool -l `which python` `` should contain *"cmd LC_VERSION_MIN_MACOSX ... version 10.6"*

The easiest way to install it is via [Homebrew](http://mxcl.github.com/homebrew/): `brew install --fresh osx_python_cura.rb --universal` (TODO: upload the formula). Note you'll need to uninstall Python if you already have it installed

###virtualenv
You may skip this step if you don't bother to use [virtualenv](http://pypi.python.org/pypi/virtualenv). It's not a requirement.

The main problem with virtualenv is that wxWidgets cannot be installed via pip. We'll have to build it manually from source by specifing prefix to our virtualenv. Assume you have virtualenv at *~/.virtualenvs/Cura*.

1. Download [the sources](http://sourceforge.net/projects/wxpython/files/wxPython/2.9.4.0/wxPython-src-2.9.4.0.tar.bz2)
2. Configure project with the following flags: `./configure
3. `make install`
4. cd into the *wxPython* directory
5. Build extension:
6. Install Python bindings to wxWidgets

Another problem is that with current installation you'll be only able to package the app, but not test it. The problem is that Mac OS X requires to bundle GUI code.
The workaround is to add another executable which we will use only for debugging. Add the following script to *~/.virtualenvs/Cura/bin*:

    #!/bin/bash
    ENV=`python -c "import sys; print sys.prefix"
    PYTHON=`python -c "import sys; print sys.real_prefix`/bin/python
    export PYTHONHOME=$ENV
    exec $PYTHON "$@"

Then to pacakge the app use the default virtualenv python and this script if you want to debug your code.

###requirements




Packaging
---------

Cura development comes with a script "package.sh", this script has been designed to run under unix like OSes (Linux, MacOS). Running it from sygwin is not a priority.
The "package.sh" script generates a final release package. You should not need it during development, unless you are changing the release process. If you want to distribute your own version of Cura, then the package.sh script will allow you to do that.
