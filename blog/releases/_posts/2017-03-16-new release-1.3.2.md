---
layout: post
title: 'New release: 1.3.2'
author: foosel
date: 2017-03-16 15:00:00 +0100
card: /assets/img/blog/2017-03/2017-03-16-release-card.png
featuredimage: /assets/img/blog/2017-03/2017-03-16-release-card.png
images:
- url: /assets/img/blog/2017-03/2017-03-10-restart-in-safemode.png
  title: The new "Restart OctoPrint in safe mode" system menu entry
- url: /assets/img/blog/2017-03/2017-03-16-folder-name.png
  title: The name of the current folder is now displayed in the file menu
- url: /assets/img/blog/2017-03/2017-03-16-shared-nozzle.gif
  title: Configuring a shared nozzle for the printer profile
excerpt: Now switched to a longer release cycle to leave some more time for
  working on new functionality and similar things, I present you 1.3.2

---

I didn't get any feedback concerning 1.3.2rc1 at all - I'm assuming that means
that all is well with it and not that nobody tried it ;)

This a true maintenance release again, consisting of various improvements and
fixes.

Some highlights from the release notes:

  * Better handling of really long "dwell"/`G4` commands on Repetier firmware -
    especially interesting for Wanhao D6/Monoprice Maker Select users, since
    for those printers end GCODE that sends a several minute long `G4` before
    switching off the nozzle fan appears to be quite common and caused problems
    with OctoPrint running into timeouts before.
  * The safe mode introduced in 1.3.0 is now way more accessible through a new
    entry in the "System" menu (if the restart command is configured). See below
    for a screenshot. You can learn more about safe mode in [the documentation](http://docs.octoprint.org/en/master/features/safemode.html).
    Please also note that the bug reporting guide now instructs you to test if
    a bug you are reporting manifests in safe mode - if not it's likely caused
    by a third party plugin and should be reported there.
  * Better error resilience in various cases (wonky plugins, wonky printer firmware,
    wonky update configurations).
  * Found a work around for a timelapse color distortion issue that has been
    plaguing some people for a long time now.
  * OctoPrint now allows defining a shared nozzle for multi extruder setups in
    its printer profiles. If a shared nozzle is configured, OctoPrint will only
    track one hotend temperature in the temperature tab but still allow extruding
    from any of the configured extruders on the Control tab. See below for a short
    GIF on how to do that.
  * When navigating into sub folders in the file list, OctoPrint will now display
    the path to the currently active folder beneath the "Back" button. This should
    help to not get lost in your file hierarchy ;) See below for a screenshot.

There is a heads-up for plugin authors who extend the JavaScript Client Library, to quote
the [Changelog](https://github.com/foosel/OctoPrint/releases/tag/1.3.2):

> **If you maintain a plugin that extends OctoPrint's [JavaScript Client Library](http://docs.octoprint.org/en/master/jsclientlib/index.html)** like demonstrated in e.g. the bundled Software Update Plugin you'll need to update the way you register your plugin to depend on `OctoPrintClient` and registering your extension as shown [here](https://github.com/foosel/OctoPrint/blob/6e793c2/src/octoprint/plugins/softwareupdate/static/js/softwareupdate.js#L1-L84) instead of directly writing to `OctoPrint.plugins` (like it was still done [here](https://github.com/foosel/OctoPrint/blob/23744cd/src/octoprint/plugins/softwareupdate/static/js/softwareupdate.js#L1-L81)). That way your extensions will be available on all instances of `OctoPrintClient`, not just the global instance `OctoPrint` that gets created on startup of the core web interface.
>
> If all you plugin does with regards to JavaScript is registering a custom view model and you have no idea what I'm talking about regarding extending the client library, no action is necessary. This heads-up is really only relevant if you extended the JavaScript Client Library.

The full list of changes can of course be found in the
[Changelog](https://github.com/foosel/OctoPrint/releases/tag/1.3.2)
 - as always.

Also see the **Further Information** and **Links** below for more information,
where to find help and how to roll back. Thanks!

### Further Information

It may take up to 24h for your update notification to pop up, so don't 
be alarmed if it doesn't show up immediately after reading this. You
can force the update however via Settings > Software Update > 
Advanced options > Force check for update.

If you don't get an "Update Now" button with your update notification, 
read [this](https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update#making-octoprint-updateable-on-existing-installations)
or - even more specifically - [this](https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update#octoprint--125).

If you are running 1.2.7, get an "Update Now" button but the update is immediately 
reported to be successful without any changes, read 
[this](https://github.com/foosel/OctoPrint/wiki/FAQ#im-running-127-i-tried-to-update-to-a-newer-version-via-the-software-update-plugin-but-im-still-on-127-after-restart).

If you are running 1.2.16, get an "Update Now" button but the update is immediately
producing an error message, read [this](https://github.com/foosel/OctoPrint/wiki/FAQ#im-running-1216-i-tried-to-update-to-a-newer-version-via-the-software-update-plugin-but-i-get-an-error).

If you have any problems with your OctoPrint installation, please seek 
support in the [G+ Community](https://plus.google.com/communities/102771308349328485741)
or the [Mailinglist](https://groups.google.com/group/octoprint). 

### Links

  * [Changelog and Release Notes](https://github.com/foosel/OctoPrint/releases/tag/1.3.2)
  * [FAQ](https://github.com/foosel/OctoPrint/wiki/FAQ)
  * [Documentation](http://docs.octoprint.org/)
  * [Contribution Guidelines (also relevant for creating bug reports!)](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md)
  * [How to file a bug report](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md#how-to-file-a-bug-report)
  * [How to roll back to an earlier release (OctoPi)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-revert-to-an-older-version-of-the-octoprint-installation-on-my-octopi-image)
  * [How to roll back to an earlier release (manual install)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-roll-back-to-an-earlier-version-after-an-update)

