---
layout: page
title: Download & Setup
---

OctoPi
======

[Guy Sheffer](https://github.com/guysoft) maintains ["OctoPi"](https://octopi.octoprint.org),
a [Raspbian based](http://www.raspbian.org/) SD card image for the Raspberry Pi
that already includes OctoPrint plus everything you need to run it:

* OctoPrint plus its dependencies
* [MJPG-Streamer](https://github.com/jacksonliam/mjpg-streamer)
  for live viewing of prints and timelapse video creation, compatible with various
  USB webcams and the Raspberry Pi camera
* [CuraEngine 15.04](https://github.com/Ultimaker/CuraEngine) for slicing directly
  on your Raspberry Pi
* [OctoPiPanel](https://github.com/jonaslorander/OctoPiPanel), which is an LCD
  app that works with OctoPrint

You can download the latest version via the following button:

<a class="btn btn-primary btn-large" href="https://octopi.octoprint.org/latest"><i class="icon-download-alt icon-large"></i>&nbsp;&nbsp;Download&nbsp;OctoPi&nbsp;0.12</a>

<small>MD5Sum: <code>a6db7912bc4cf429865a05253cbe017b</code></small>

Compatible with Raspberry Pi A, B, A+, B+, B2. For Raspberry Pi 3 and Zero please use a [nightly build](http://docstech.net/OctoPiMirror/nightly/) for now.

Getting Started with OctoPi
---------------------------

Please follow these steps after downloading

1. Unzip the image and install the contained ``.img`` file to an SD card
   [like any other Raspberry Pi image](https://www.raspberrypi.org/documentation/installation/installing-images/README.md).
2. Configure your WiFi connection by editing ``octopi-network.txt`` on the root of the
   flashed card when using it like a thumb drive.
3. Boot the Pi from the card.
4. Log into your Pi via SSH (it is located at ``octopi.local``
   [if your computer supports bonjour](https://learn.adafruit.com/bonjour-zeroconf-networking-for-windows-and-linux/overview)
   or the IP address assigned by your router), default username is "pi",
   default password is "raspberry". Change the password using the ``passwd``
   command and expand the filesystem of the SD card through the corresponding
   option when running ``sudo raspi-config``.
5. Access OctoPrint through ``http://octopi.local`` or ``http://<your pi's ip address>``.

Please also refer to [OctoPi's README](https://github.com/guysoft/OctoPi), especially the ["How to use it" section](https://github.com/guysoft/OctoPi#how-to-use-it).

[Thomas Sanladerer](https://www.youtube.com/channel/UCb8Rde3uRL1ohROUVg46h1A) created a great video guide on how to get OctoPi 0.12 up an running.

<div>
    <iframe width="560" height="315" src="//www.youtube.com/embed/MwsxO3ksxm4" frameborder="0" allowfullscreen="allowfullscreen">&nbsp;</iframe>
</div>

----

Installing from source
======================

The generic setup instructions boil down to

1. Installing [Python 2.7](https://www.python.org/) including [pip](https://pip.pypa.io/en/latest/installing.html)
2. Obtaining the source through either of:
   1. cloning the [source repository](https://github.com/foosel/OctoPrint.git): ``git clone https://github.com/foosel/OctoPrint.git``
   2. downloading an [archive of the current stable version](https://github.com/foosel/OctoPrint/archive/master.zip) from Github and unpacking it
3. In the source code folder from the command line: ``python setup.py install``
4. Start OctoPrint through ``octoprint`` from the command line

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
