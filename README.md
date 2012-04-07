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

