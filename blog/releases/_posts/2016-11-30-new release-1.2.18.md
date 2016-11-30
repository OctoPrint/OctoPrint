---
layout: post
title: 'New release: 1.2.18'
author: foosel
date: 2016-11-30 12:30:00 +0100
card: /assets/img/blog/2016-11/2016-11-30-release-card.png
featuredimage: /assets/img/blog/2016-11/2016-11-30-release-card.png

---

With 1.2.18 I hereby present you with what will hopefully be the final
1.2.x release we see. The idea is to fix a couple of things just in case
1.3.0 won't prove to be stable enough for a pre-holiday release after all.

<!-- more -->

For this reason we are only looking at a very short change list here, which 
pretty much boils down to this:

  * Allow arbitrary frame rates for creating timelapses by improving
    the parameterization of the render command. That should solve any
    "unsupported framerate" messages you might have run into.
  * Made it clearer what kind of Cura profiles are supported by the
    bundled CuraEngine slicer plugin.
  * Added support for the `R` parameter for `M109` or `M190` as 
    temperature target. 
  * Fixed issues with selecting the default printer profile, propagating
    the target temperature, handling of restricted settings and IPv6 
    compatibility.

Quick heads-up for you **if you are already running 1.3.0rc2**: OctoPrint
might show you a notification for 1.2.18. But you won't be able to "update"
(or rather downgrade) to it unless you first switch back to
either the Stable or the Maintenance RC release channels[^1].

You can find the full changelog and release notes as usual 
[on Github](https://github.com/foosel/OctoPrint/releases/tag/1.2.18).

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

  * [Changelog and Release Notes](https://github.com/foosel/OctoPrint/releases/tag/1.2.18)
  * [FAQ](https://github.com/foosel/OctoPrint/wiki/FAQ)
  * [Documentation](http://docs.octoprint.org/)
  * [Contribution Guidelines (also relevant for creating bug reports!)](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md)
  * [How to file a bug report](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md#how-to-file-a-bug-report)
  * [How to roll back to an earlier release (OctoPi)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-revert-to-an-older-version-of-the-octoprint-installation-on-my-octopi-image)
  * [How to roll back to an earlier release (manual install)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-roll-back-to-an-earlier-version-after-an-update)

### Footnotes

  [^1]: I'll have to figure out why you even get shown that a lower 
        numbered release is out (you shouldn't), but since it's only 
        cosmetic in nature I will not schedule another 1.3.0 RC for 
        fixing that - we'll get that ironed out in 1.3.1 I guess :)