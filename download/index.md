---
layout: page
title: Download & Setup
---
OctoPrint is currently available in the following forms:

* as a source package
* as part of a specialized distribution for the RaspberryPi called "OctoPi"

A binary package for Debian-based Linux-systems is currently in the works. I'll also look into packages
for other distributions/Windows/MacOS X if sufficient demand exists.

Source package
==============

Linux
-----

For installing OctoPrint from source, please take a look at [the setup instructions for Raspbian on the wiki](https://github.com/foosel/OctoPrint/wiki/Setup-on-a-Raspberry-Pi-running-Raspbian).
They should be pretty identical on other Linux distributions.

Windows
-------

OctoPrint is being developed under Windows 7, therefore it will run there as well although its targeted use case
is running it on low-powered embedded devices with Linux. If you want to give it a try on Windows, you can find
instructions on what to do [on the wiki](https://github.com/foosel/OctoPrint/wiki/Setup-on-Windows).

OctoPi
======

<img src="{{ BASE_PATH }}/assets/img/OctoPi.png" style="float: right">
[Guy Sheffer](https://github.com/guysoft) maintains "OctoPi", an SD card image for the Raspberry Pi that already includes
OctoPrint plus everything you need to run it:

* OctoPrint plus its dependencies
* [MJPG-Streamer](http://sourceforge.net/apps/mediawiki/mjpg-streamer/index.php?title=Main_Page)

You can download the most current version [from here](http://www.gitiverse.com/octopi/).
The source is available [here](https://github.com/guysoft/OctoPi).

After flashing the image to SD and booting your RaspberryPi with it (if you don't know how to do that take a look
at [these instructions](http://elinux.org/RPi_Easy_SD_Card_Setup) which apply here as well), it should be available at `http://octopi.local` -- if
you are running Windows, you might need to install ["Bonjour for Windows"](http://support.apple.com/kb/DL999) first for this to work --
or alternatively at its regular IP.
