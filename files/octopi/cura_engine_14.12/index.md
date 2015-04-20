---
layout: page
title: CuraEngine 14.12 for OctoPi
---

This is a build of **CuraEngine 14.12** for a Raspberry Pi running **OctoPi 0.11.0+** (or Raspbian 2015-01-31).

It was built on Raspbian 2015-01-31 as described [in the installation instructions for the OctoPrint Cura Plugin](https://github.com/foosel/OctoPrint/wiki/Plugin:-Cura#compiling-for-raspbian)
from the sources of [CuraEngine release 14.12](https://github.com/Ultimaker/CuraEngine/tree/14.12). CuraEngine is 
Open Source software, released under the terms of [the AGPLv3](http://www.gnu.org/licenses/agpl.html).

## Usage

1. Download in your browser and copy to a folder on your Pi, for example via SSH **or** 
   download on your Pi: `wget http://octoprint.org/files/cura_engine_14.12/cura_engine` 
2. Make executable: `chmod +x /path/to/cura_engine`
3. Test if it runs: `/path/to/cura_engine --help`
4. Configure `/path/to/cura_engine` as the path to CuraEngine in [OctoPrint's Cura Plugin](https://github.com/foosel/OctoPrint/wiki/Plugin:-Cura)
5. Enjoy slicing on your Pi

---

**Note:** Should also work just fine for setting up [slicing on the `master` branch](https://github.com/foosel/OctoPrint/wiki/Cura-Integration).

---

## Download

[cura_engine](./cura_engine)