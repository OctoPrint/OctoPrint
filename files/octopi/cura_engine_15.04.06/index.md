---
layout: page
title: CuraEngine 15.04.06 for OctoPi
---

This is a build of **CuraEngine 15.04.06** for a Raspberry Pi running **OctoPi 0.13.0+** (or Raspbian 2016-03-18).

It was built on Raspbian Jessie Lite 2016-03-18 as described 
[in the docs for the OctoPrint Cura Plugin](http://docs.octoprint.org/en/devel/bundledplugins/cura.html#compiling-for-raspbian)
from the sources of [CuraEngine release 15.04.06](https://github.com/Ultimaker/CuraEngine/tree/15.04.06). CuraEngine is 
Open Source software, released under the terms of [the AGPLv3](http://www.gnu.org/licenses/agpl.html).

## Usage

1. Download in your browser and copy to a folder on your Pi, for example via SSH **or** 
   download on your Pi: `wget http://octoprint.org/files/octopi/cura_engine_15.04.06/cura_engine` 
2. Make executable: `chmod +x /path/to/cura_engine`
3. Test if it runs: `/path/to/cura_engine --help`
4. Configure `/path/to/cura_engine` as the path to CuraEngine in [OctoPrint's Cura Plugin](http://docs.octoprint.org/en/devel/bundledplugins/cura.html)
5. Enjoy slicing on your Pi

## Download

[cura_engine](./cura_engine)