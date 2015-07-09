---
layout: post
author: foosel
title: "New OctoPi Release: 0.13.0"
date: 2016-05-02 16:50:00 +0200
images:
- https://raw.githubusercontent.com/guysoft/OctoPi/devel/media/OctoPi.png
---

[Guy Sheffer](https://github.com/guysoft) just released a new version of 
OctoPi, version 0.13.0.

The long awaited release brings not only Raspberry Pi 3 (and Zero) support
out of the box by being based on Raspbian Jessie, but also utilizes
the new lite image as base for the build, meaning the download size could
be halfed.

<!-- more -->

The desktop subsystem is not included by default anymore since *most*
people don't actually use it (OctoPi is meant to run as a headless
network appliance), but in case you need it, we also put a little helper
script on there which will allow you to quickly install the desktop
environment. Just SSH into your OctoPi instance, execute

```
sudo ./scripts/install-desktop
```

and then follow the instructions.

You can download OctoPi 0.13.0 from the [usual](http://octoprint.org/download/) 
[places](https://octopi.octoprint.org). 

The release notes can be found at 
[github](https://github.com/guysoft/OctoPi/releases/tag/0.13.0).
