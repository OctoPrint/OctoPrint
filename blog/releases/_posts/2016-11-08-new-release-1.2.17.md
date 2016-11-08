---
layout: post
title: 'New release: 1.2.17'
author: foosel
date: 2016-11-08 15:10:00 +0100
card: /assets/img/blog/2016-11/2016-11-08-release-card.png
featuredimage: /assets/img/blog/2016-11/2016-11-08-release-card.png

---

Another true maintenance release with various improvements and a couple
of bug fixes for good measure: I finally present you 1.2.17!

<!-- more -->

First things first though: **If you are currently running 1.2.16**, make sure
you open the Settings dialog once before updating and clicking "Save" there.
You don't have to make any changes, just click "Save" once in the Settings
dialog. Why? To work around a small bug preventing you from upgrading
to 1.2.17 due to a missing migration step in 1.2.16 (that issue has since been
fixed in 1.2.17), causing an error if the settings were *never* saved 
under 1.2.16. Sadly, update bugs are very good at hiding themselves until you
are ready to push out the next version, and then it's too late. But at least
this time there's an easy workaround that doesn't require you to install
a plugin :)

A small glance at what else is new besides the above bug fix:

  * `SettingsPlugin`s can now mark configuration paths as restricted. <strong>Heads-up
    plugin authors:</strong> This is relevant for you for security reasons, please read the 
    [release notes](https://github.com/foosel/OctoPrint/releases/tag/1.2.17)!
  * A rather stupid problem was solved that made log out not work properly if you still had
    an old remember me cookie from 1.2.15 or earlier lying around in your browser.
  * Configuration files created and managed by OctoPrint, such as ``config.yaml`` or
    ``users.yaml``, will now persist their existing permissions, with a lower and
    upper permission bound for sanitization (e.g. removing executable flags on configuration
    files, but keeping group read/write permissions if found). This is of special interest
    to people who persisted their configs on shared network drives which enforced certain
    permissions. And while looking at that anyhow, fixed a small forced ``config.yaml``
    save on each startup that was unnecessary and the result of an assumed migration.
  * More error resilience against issues in plugin assets (e.g. JS files).

This is only an excerpt, you can find the full changelog and release notes as usual 
[on Github](https://github.com/foosel/OctoPrint/releases/tag/1.2.17).

And if you are monitoring the release candidates and are wondering why
it took so long from 1.2.17rc4 to 1.2.17: I was out sick, then traveling,
then sick again, which sadly caused this delay.

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

  * [Changelog and Release Notes](https://github.com/foosel/OctoPrint/releases/tag/1.2.17)
  * [FAQ](https://github.com/foosel/OctoPrint/wiki/FAQ)
  * [Documentation](http://docs.octoprint.org/)
  * [Contribution Guidelines (also relevant for creating bug reports!)](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md)
  * [How to file a bug report](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md#how-to-file-a-bug-report)
  * [How to roll back to an earlier release (OctoPi)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-revert-to-an-older-version-of-the-octoprint-installation-on-my-octopi-image)
  * [How to roll back to an earlier release (manual install)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-roll-back-to-an-earlier-version-after-an-update)
