---
layout: post
title: 'New release: 1.2.16'
author: foosel
date: 2016-09-23 11:00:00 +0200
card: /assets/img/blog/2016-09/2016-09-23-release-card.png
images:
- /assets/img/blog/2016-09/2016-09-09-release-channel-screenie.png
featuredimage: /assets/img/blog/2016-09/2016-09-23-release-card.png

---

Another shiny maintenance release with various improvements and bug fixes
plus the new release channel feature awaits you!

<!-- more -->

A small glance and what's new:

  * After the 1.2.14 issues I [promised](http://octoprint.org/blog/2016/07/30/new-release-1.2.15/) to
    look into a way to allow more users to easily run pre release versions,
    to find issues like the one that troubled 1.2.14 earlier, before they
    hit a larger audience. With the new release channel feature built
    into 1.2.16, this is now possible. [Read more about Release Channels on the wiki](https://github.com/foosel/OctoPrint/wiki/Using-Release-Channels).
  * Wildly inaccurate print time estimates at the beginning of the print
    (which are sadly unavoidable if you didn't give OctoPrint time to 
    analyse the file to get a better prediction) are now suppressed again 
    until further into the print.
  * The algorithm for fuzzying up the print time estimates was adjusted
    to be adaptive to the current estimate: the larger the time the more fuzzy
    it gets, better reflecting the accuracy of things.
  * A small bug with Slic3r's OctoPrint export was fixed that caused filenames sent by
    Slic3r that contained non-ASCII-characters to cause an error within OctoPrint.
  * Uploading files to OctoPrint's ``uploads`` folder outside of OctoPrint - though
    discouraged! - should now be better supported: OctoPrint will sanitize 
    the names of any such files it detects and hence make sure they are processable.

This is only an excerpt, you can find the full changelog and release notes as usual 
[on Github](https://github.com/foosel/OctoPrint/releases/tag/1.2.16).

### Further Information

It may take up to 24h for your update notification to pop up, so don't 
be alarmed if it doesn't show up immediately after reading this. You
can force the update however via Settings > Software Update > 
Advanced options > Force check for update.

If you don't get an "Update Now" button with your update notification, 
read [this](https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update#making-octoprint-updateable-on-existing-installations)
or - even more specifically - [this](https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update#octoprint--125).

If you do get an "Update Now" button but the update is immediately 
reported to be successful without any changes, read 
[this](https://github.com/foosel/OctoPrint/wiki/FAQ#im-running-127-i-tried-to-update-to-a-newer-version-via-the-software-update-plugin-but-im-still-on-127-after-restart).

If you have any problems with your OctoPrint installation, please seek 
support in the [G+ Community](https://plus.google.com/communities/102771308349328485741)
or the [Mailinglist](https://groups.google.com/group/octoprint). 

### Links

  * [Changelog and Release Notes](https://github.com/foosel/OctoPrint/releases/tag/1.2.16)
  * [FAQ](https://github.com/foosel/OctoPrint/wiki/FAQ)
  * [Documentation](http://docs.octoprint.org/)
  * [Contribution Guidelines (also relevant for creating bug reports!)](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md)
  * [How to file a bug report](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md#how-to-file-a-bug-report)
  * [How to roll back to an earlier release (OctoPi)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-revert-to-an-older-version-of-the-octoprint-installation-on-my-octopi-image)
  * [How to roll back to an earlier release (manual install)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-roll-back-to-an-earlier-version-after-an-update)
