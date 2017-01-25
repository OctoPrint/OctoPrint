---
layout: post
title: 'New release: 1.3.1'
author: foosel
date: 2017-01-25 11:20:00 +0100
card: /assets/img/blog/2017-01/2017-01-25-release-card.png
featuredimage: /assets/img/blog/2017-01/2017-01-25-release-card.png
excerpt:

---

As the first release of 2017, 1.3.1 brings you a long list of fixes and improvements
again.

<!-- more -->

Judging by some of the feedback I got over the past couple of weeks since
releasing 1.3.0 one of the most anticipated changes in this release might
be <strong>support for disabling the cancel confirmation</strong> by
unchecking "Settings > Features > Confirm before cancelling a print". If I'd known how
strongly a lot of you apparently think about this, I'd shipped 1.3.0 directly with
this, so make sure to give me feedback *during development* instead of after :)

Making the cancel confirmation optional naturally is not the only thing
that went into this release though, here's a small excerpt from the Changelog:

  * Way better support for various password managers.
  * Support for calculating filament volume for GCODE files sliced
    with Simplify3D.
  * Improved set of stock terminal filters. Please note that if you
    modified your terminal filters you'll need to update the included
    stock filters manually if needed, see the Changelog for details on this.
  * Fixed some left over issues with folder management.
  * Fixed backwards compatibility of the new command line interface.
  * Fixed a bug in the model size calculation that caused wrong sizes
    to be calculated under specific circumstances.

The full list of changes can of course be found in the
[Changelog](https://github.com/foosel/OctoPrint/releases/tag/1.3.1)
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

  * [Changelog and Release Notes](https://github.com/foosel/OctoPrint/releases/tag/1.3.1)
  * [FAQ](https://github.com/foosel/OctoPrint/wiki/FAQ)
  * [Documentation](http://docs.octoprint.org/)
  * [Contribution Guidelines (also relevant for creating bug reports!)](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md)
  * [How to file a bug report](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md#how-to-file-a-bug-report)
  * [How to roll back to an earlier release (OctoPi)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-revert-to-an-older-version-of-the-octoprint-installation-on-my-octopi-image)
  * [How to roll back to an earlier release (manual install)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-roll-back-to-an-earlier-version-after-an-update)

