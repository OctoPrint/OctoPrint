---
layout: post
author: foosel
title: "OctoPi Release Candidate 0.14rc1 needs testers!"
date: 2017-03-31 19:00:00 +0200
excerpt: Guy Sheffer just published a release candidate for the next OctoPi release 0.14 and is looking for feedback!
card: /assets/img/blog/2017-03/2017-03-31-octopi-release-candidate.png
featuredimage: /assets/img/blog/2017-03/2017-03-31-octopi-release-candidate.png

---

[Guy Sheffer](https://github.com/guysoft) just published a
[release candidate](https://github.com/guysoft/OctoPi/issues/332) for the next OctoPi release 0.14.

Apart from adding support for the Pi Zero W and of course shipping with the current stable OctoPrint version
1.3.2, 0.14 also contains the following changes:

>  * Added note to `/root/bin/webcamd` to use `octopi.txt` for configuration
>  * Added note to `octopi-network.txt` for Mac OS X users to not use Textedit/properly configure Textedit
>  * Added note with further instructions on usage to boot and login screen
>  * Allow configuration of multiple wifi networks via `octopi-wpa-supplicant.txt`
>  * Better "service not running" error pages
>  * Enabled SSH by default (we usually run headless, disabling it is not an option)
>  * Updated stock `config.yaml` and init script for OctoPrint to 1.3.0+
>  * Updated `install-desktop` script to only pull in needed packages
>  * Fixes:
>    * Prevent NTP updates from failing on RPi3 wifi ([#327](https://github.com/guysoft/OctoPi/pull/327))
>    * Prevent weird SSH issues on RPi3 ([#294](https://github.com/guysoft/OctoPi/issues/294))
>    * Prevent duplicate X-Scheme headers in haproxy ([#239](https://github.com/guysoft/OctoPi/issues/239))
>    * Workaround for an issue with recent `pip` versions and pyasn1 ([#276](https://github.com/guysoft/OctoPi/issues/276))

If you've been waiting for a new OctoPi release, this is your chance to give the candidate a test drive
and [report any findings back](https://github.com/guysoft/OctoPi/issues/332) so we can make sure the
release is solid!

You can find the download links in the [ticket](https://github.com/guysoft/OctoPi/issues/332).
