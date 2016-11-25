---

layout: post
title: 'New release candidate: 1.3.0rc2'
author: foosel
date: 2016-11-24 14:30:00 +0200
card: /assets/img/blog/2016-11/2016-11-24-release-candidate-card.png
featuredimage: /assets/img/blog/2016-11/2016-11-24-release-candidate-card.png
images:
- url: /assets/img/blog/2016-11/2016-11-24-bounding-box.png
  title: Configuring a custom safe bounding box
- url: /assets/img/blog/2016-11/2016-11-24-firmware-detection.gif
  title: New firmware auto detection feature
excerpt: The second release candidate for the upcoming huge 1.3.0
  release, now available for your testing pleasure!

---

A bit later than originally anticipated[^1], today I can finally present
you the second release candidate for the upcoming 1.3.0 release!

Compared to 1.3.0rc1 this RC fixes some regressions that some of you
or I observed (and a full hearted **Thank You!** btw to everyone who switched
to 1.3.0rc1 and reported back on their experiences, every tiny bit helped
a lot!) and improves on quite a number of things that were still not
ideal. I also did add four new features I had planned to include in
1.3.0 but didn't manage to finish in time for 1.3.0rc1 and which have
been something I wanted to do for ages now, to improve the user experience
and supportability.

Short overview of the larger points from the [changelog](https://github.com/foosel/OctoPrint/releases/tag/1.3.0rc2):

  * OctoPrint will now track the current print head position on pause and 
    cancel and provide it as new template variables 
    ``pause_position``/``cancel_position`` for the relevant GCODE scripts. 
    This will allow more intelligent pause codes that park the print head 
    at a rest position during pause and move it back to the exact position 
    it was before the pause on resume 
    ([Example](https://gist.github.com/foosel/1c09e269b1c0bb7a471c20eef50c8d3e)). 
    Note that this is NOT enabled by default and for now will necessitate 
    adjusting the pause and resume GCODE scripts yourself since position 
    tracking with multiple extruders or when printing from SD is currently 
    not fool proof thanks to firmware limitations regarding reliable 
    tracking of the various ``E`` values and the currently selected 
    tool ``T``.
  * There is now an (optional) firmware auto detection in place. This 
    should hopefully reduce issues for first-time users running
    a firmware that needs specific flags to be set for proper
    support.
  * New command line safe mode flag ``--safe`` and config setting 
    ``server.startOnceInSafeMode`` that disables all third party plugins when 
    active during startup. The config setting will automatically be removed from 
    `config.yaml` after the server has started through successfully.
    Through the new ``octoprint config`` command it can also be easily
    set from command line by issuing ``octoprint config set --bool server.startOnceInSafeMode true``.
    In the long run I also hope to add a specific "Restart in safe mode"
    command, but for 1.3.0 we'll leave it as it is now.
  * Auto migration of the old manually configured system commands
    (restart, reboot and shutdown) to the new application wide commands.
    That means that you will no longer have duplicated entries in your
    system menu if you had both configured ;) (I also made it do a 
    backup of your `config.yaml` before that migration, just in case
    you want to roll back to 1.2.x again)
  * The new bounding box warning feature now allows to define a custom
    bounding box for your printer (in its printer profile) for which no
    out-of-bounds warning should be issued. That should hopefully make all
    you Prusa i3 Mk2 owners happy where I've heard a nozzle priming
    outside of the print volume is part of the standard start GCODE
    sequence.

You can find the full changelog and release notes as usual 
[on Github](https://github.com/foosel/OctoPrint/releases/tag/1.3.0rc2).

**If you are tracking the "Devel RC" release channel**, you
should soon get an update notification just like you are used to from
stable releases. If you are coming from 1.3.0rc1, **you might run into
an update error** that actually isn't one, please see the 
["Note for Upgraders coming from 1.3.0rc1" in the release notes](https://github.com/foosel/OctoPrint/releases/tag/1.3.0rc2) 
for more details on this.

**If you are tracking the "Maintenance RC" release channel**, you will
*not* get an update notification for this release candidate. If you want
to give it a test whirl, you'll need to switch to the "Devel RC" release
channel.

**If you are not interested in helping to test devel release candidates**, just
ignore this post, 1.3.0 stable will hit your instance via the usual
way once it's ready :)

Depending on the feedback regarding this version I'll look into fixing 
any observed regressions and bugs and pushing out a follow-up version 
within the next two weeks. I really hope we'll see a stable 1.3.0 release
before the holidays :)

### Links

  * [Changelog and Release Notes](https://github.com/foosel/OctoPrint/releases/tag/1.3.0rc2)
  * [Using Release Channels](https://github.com/foosel/OctoPrint/wiki/Using-Release-Channels)
  * [How to file a bug report](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md#how-to-file-a-bug-report)
  * [Contribution Guidelines (also relevant for creating bug reports!)](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md)
  * [FAQ](https://github.com/foosel/OctoPrint/wiki/FAQ)
  * [Documentation](http://docs.octoprint.org/)
  * [How to roll back to an earlier release (OctoPi)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-revert-to-an-older-version-of-the-octoprint-installation-on-my-octopi-image)
  * [How to roll back to an earlier release (manual install)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-roll-back-to-an-earlier-version-after-an-update)

### Footnotes

  [^1]: Mostly thanks to a severe clogged <s>nozzle</s>nose issue that 
        is sadly all too common in the northern hemisphere this time of 
        the year.
