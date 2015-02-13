---
layout: page
title: Download & Setup
---
OctoPrint is currently available in the following forms:

* as part of a specialized distribution for the RaspberryPi called "OctoPi"
* as a source package

A binary package for Debian-based Linux-systems is currently in the works. I'll also look into packages
for other distributions/Windows/MacOS X if sufficient demand exists.

OctoPi
======

[Guy Sheffer](https://github.com/guysoft) maintains "OctoPi", an SD card image for the Raspberry Pi that already includes
OctoPrint plus everything you need to run it:

* OctoPrint plus its dependencies
* [MJPG-Streamer](http://sourceforge.net/apps/mediawiki/mjpg-streamer/index.php?title=Main_Page)

You can download the most current version and nightly builds from one of the following mirrors:

* [Mirror #1](http://docstech.net/OctoPiMirror/)
* [Mirror #2](http://mariogrip.com/OctoPiMirror/)

The source is available [here](https://github.com/guysoft/OctoPi).

[Thomas Sanladerer](https://www.youtube.com/channel/UCb8Rde3uRL1ohROUVg46h1A) created a great video guide on how to get OctoPi up an running:

<div>
    <iframe width="560" height="315" src="//www.youtube.com/embed/EHzN_MwunmE" frameborder="0" allowfullscreen="allowfullscreen">&nbsp;</iframe>
</div>

After flashing the image to SD and booting your RaspberryPi with it (if you don't know how to do that take a look
at [these instructions](http://elinux.org/RPi_Easy_SD_Card_Setup) which apply here as well), it should be available at `http://octopi.local` -- if
you are running Windows, you will need to install ["Bonjour for Windows"](http://support.apple.com/kb/DL999) first for this to work (also see [this FAQ entry with some more details on this](https://github.com/foosel/OctoPrint/wiki/FAQ#i-cant-reach-my-octopi-under-octopilocal-under-windows-why)) --
or alternatively at its regular IP.

Source package
==============

The generic setup instructions boil down to 

1. Installing [Python 2.7]() including [pip]()
2. Obtaining the source through either of:
   1. cloning the [source repository](https://github.com/foosel/OctoPrint.git): ``git clone https://github.com/foosel/OctoPrint.git``
   2. downloading an archive of the current source from Github and unpacking it: [archive of the current stable version](https://github.com/foosel/OctoPrint/archive/master.zip)
3. In the source code folder: ``python setup.py install``
4. Starting OctoPrint through: ``octoprint``

More specific setup instructions for the most common runtime environments can be found below.

Linux
-----

For installing OctoPrint from source, please take a look at [the setup instructions for Raspbian on the wiki](https://github.com/foosel/OctoPrint/wiki/Setup-on-a-Raspberry-Pi-running-Raspbian).
They should be pretty identical on other Linux distributions.

Windows
-------

OctoPrint is being developed under Windows 7, therefore it will run there as well although its targeted use case
is running it on low-powered embedded devices with Linux. If you want to give it a try on Windows, you can find
instructions on what to do [on the wiki](https://github.com/foosel/OctoPrint/wiki/Setup-on-Windows).

Mac
---

For installing OctoPrint on a Mac, please take a look at [the setup instructions for MacOS on the wiki](https://github.com/foosel/OctoPrint/wiki/Setup-on-Mac).

