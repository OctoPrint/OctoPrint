Cura
====

If you are reading this, then you are looking at the *development* version of Cura. If you just want to use Cura look at the following location: https://github.com/daid/Cura/wiki

Development
===========

Cura is developed in Python. Getting Cura up and running for development is not very difficult. If you copy the python and pypy from a release into your Cura development checkout then you can use Cura right away, just like you would with a release.
For development with git, check the help on github. Pull requests is the fastest way to get changes into Cura.


Packaging
---------

Cura development comes with a script "package.sh", this script has been designed to run under unix like OSes (Linux, MacOS). Running it from sygwin is not a priority.
The "package.sh" script generates a final release package. You should not need it during development, unless you are changing the release process. If you want to distribute your own version of Cura, then the package.sh script will allow you to do that.


Mac OS X
--------
The following section describes how to prepare environment for developing and packaing for Mac OS X.

###Python
You'll need non-system, framework-based, universal with min deployment target set to 10.6 build of Python 2.7

**non-system**: it was not bundeled with distribution of Mac OS X. You can check this by `python -c "import sys; print sys.prefix"`. Output should *not* start with *"/System/Library/Frameworks/Python.framework/"*

**framework-based**: Output of `python -c "import distutils.sysconfig as c; print(c.get_config_var('PYTHONFRAMEWORK'))"` should be non-empty string

**universal**: output of ``lipo -info `which python` `` include both i386 and x86_64. E.g *"Architectures in the fat file: /usr/local/bin/python are: i386 x86_64"*

**deployment target set to 10.6**: Output of ``otool -l `which python` `` should contain *"cmd LC_VERSION_MIN_MACOSX ... version 10.6"*

The easiest way to install it is via [Homebrew](http://mxcl.github.com/homebrew/): `brew install --fresh osx_python_cura.rb --universal` (TODO: upload the formula). Note you'll need to uninstall Python if you already have it installed via Homebrew.

###Virtualenv
You may skip this step if you don't bother to use [virtualenv](http://pypi.python.org/pypi/virtualenv). It's not a requirement.

The main problem with virtualenv is that wxWidgets cannot be installed via pip. We'll have to build it manually from source by specifing prefix to our virtualenv.

Assuming you have virtualenv at *~/.virtualenvs/Cura*:

1. Download [wxPython sources](http://sourceforge.net/projects/wxpython/files/wxPython/2.9.4.0/wxPython-src-2.9.4.0.tar.bz2)
2. Configure project with the following flags: `./configure --prefix=$HOME/.virtualenvs/Cura/ --enable-optimise --with-libjpeg=builtin --with-libpng=builtin --with-libtiff=builtin --with-zlib=builtin --enable-monolithic --with-macosx-version-min=10.6 --disable-debug --enable-unicode --enable-std_string --enable-display --with-opengl --with-osx_cocoa --enable-dnd --enable-clipboard --enable-webkit --enable-svg --with-expat --enable-universal_binary=i386,x86_64`
3. `make install`
4. cd into the *wxPython* directory
5. Build wxPython modules: `python setup.py build_ext WXPORT=osx_cocoa WX_CONFIG=$HOME/.virtualenvs/Cura/bin/wx-config UNICODE=1 INSTALL_MULTIVERSION=0 BUILD_GLCANVAS=1 BUILD_GIZMOS=1 BUILD_STC=1` (Note that python is the python of your virtualenv)
6. Install wxPython and modules: `python setup.py install --prefix=$HOME/.virtualenvs/Cura/ WXPORT=osx_cocoa WX_CONFIG=$HOME/virtualenvs/Cura/bin/wx-config UNICODE=1 INSTALL_MULTIVERSION=0 BUILD_GLCANVAS=1 BUILD_GIZMOS=1 BUILD_STC=1` (Note that python is the python of your virtualenv)

Another problem is that python in virtualenv is not suitable for running GUI code. Mac OS X requires python to be inside the bundle. To workaround this issue, we will add the following script to the ~/.virtualenvs/Cura/bin:

    #!/bin/bash
    ENV=`python -c "import sys; print sys.prefix"`
    PYTHON=`python -c "import sys; print sys.real_prefix"`/bin/python
    export PYTHONHOME=$ENV
    exec $PYTHON "$@"

I typically name this script `pythonw`.

At this point virtualenv is configured for wxPython development. Remember to use `python` to pacakge the app and `pythonw` to run app without packaging (e.g. for debugging).

###Requirements
Following packages are required for development:

    PyOpenGL>=3.0.2
    numpy>=1.6.2
    pyserial>=2.6
    pyobjc>=2.5

Following packages are required for packaging Cura into app:

    py2app>=0.7.2

The easiest way to install all this packages is to use virtualenv's pip: `pip install requirements_darwin.txt`

####PyObjC
At time of writing, pyobjc 2.5 is not available at pypi. You have to clone repo and install it manually:

    hg clone https://bitbucket.org/ronaldoussoren/pyobjc
    hg checkout c42c98d6e941 # last tested commit
    python install.py

###Packaging
To package Cura into application bundle simply do `python setup.py py2app`. Resulting bundle is self-contained -- it includes Python and all needed packages.
