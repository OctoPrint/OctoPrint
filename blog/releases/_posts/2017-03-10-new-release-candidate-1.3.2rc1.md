---

layout: post
title: 'New release candidate: 1.3.2rc1'
author: foosel
date: 2017-03-10 16:45:00 +0100
card: /assets/img/blog/2017-03/2017-03-10-release-candidate-card.png
featuredimage: /assets/img/blog/2017-03/2017-03-10-release-candidate-card.png
excerpt: The first release candidate of the 1.3.2 release, with various
   improvements and bug fixes.
images:
- url: /assets/img/blog/2017-03/2017-03-10-restart-in-safemode.png
  title: The new "Restart OctoPrint in safe mode" system menu entry


---

A shiny new release candidate marks the first phase of getting 1.3.2 out of
the door.

Since I've decided to spread stable releases a bit further apart now to
leave more time for the tasks outside of regular maintenance (e.g. new
development, but also project organization, brainstorming, planning and
such) this release might be a bit larger than the past pure maintenance
releases.

Some highlights from the release notes:

  * Better handling of really long "dwell"/`G4` commands on Repetier firmware -
    especially interesting for Wanhao D6/Monoprice Maker Select users, since
    for those printers end GCODE that sends a several minute long `G4` before
    switching of the nozzle fan appears to be quite common and caused problems
    with OctoPrint running into timeouts.
  * The safe mode introduced in 1.3.0 is now way more accessible through a new
    entry in the "System" menu (if the restart command is configured). You can
    learn more about safe mode in [the documentation](http://docs.octoprint.org/en/maintenance/features/safemode.html).
  * Better error resilience in various cases (wonky plugins, wonky printer firmware,
    wonky update configurations).
  * Found a work around for a timelapse color distortion issue that has been
    plaguing some people for a long time now.
  * OctoPrint now allows defining a shared nozzle for multi extruder setups in
    its printer profiles. If a shared nozzle is configured, OctoPrint will only
    track one hotend temperature in the temperature tab but still allow extruding
    from any of the configured extruders on the Control tab.
  * When navigating into sub folders in the file list, OctoPrint will now display
    the path to the currently active folder beneath the "Back" button. This should
    help to not get lost in your file hierarchy ;)

**If you are tracking the "Maintenance RC" release channel**, you
should soon get an update notification just like you are used to from
stable releases.

**If you are not interested in helping to test release candidates**, just
ignore this post, 1.3.2 stable will hit your instance via the usual
way once it's ready :)

You can find the full changelog and release notes as usual 
[on Github](https://github.com/foosel/OctoPrint/releases/tag/1.3.2rc1).

Depending on how the feedback for this release candidate turns out, I'll
either look into releasing 1.3.2 or fix any observed regressions and push
out a second release candidate within the next couple of days.

### Links

  * [Changelog and Release Notes](https://github.com/foosel/OctoPrint/releases/tag/1.3.2rc1)
  * [Using Release Channels](https://github.com/foosel/OctoPrint/wiki/Using-Release-Channels)
  * [How to file a bug report](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md#how-to-file-a-bug-report)
  * [Contribution Guidelines (also relevant for creating bug reports!)](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md)
  * [FAQ](https://github.com/foosel/OctoPrint/wiki/FAQ)
  * [Documentation](http://docs.octoprint.org/)
  * [How to roll back to an earlier release (OctoPi)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-revert-to-an-older-version-of-the-octoprint-installation-on-my-octopi-image)
  * [How to roll back to an earlier release (manual install)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-roll-back-to-an-earlier-version-after-an-update)
