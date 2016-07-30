---
layout: post
title: 'New release: 1.2.15'
author: foosel
date: 2016-07-30 09:00:00 +0200
card: /assets/img/blog/2016-07/2016-07-30-release-card.png
featuredimage: /assets/img/blog/2016-07/2016-07-30-release-card.png
---

Late on the 28th it sadly came to my attention that some users were
experiencing severe problems with their printer communication after
upgrading to the 1.2.14 release just published earlier that day. I immediately 
stopped the roll out of 1.2.14 and went to investigate.

<!-- more -->
 
Since I couldn't reproduce the issue myself, I had to depend
on affected users to help in determining the cause of the problems.

Yesterday morning we narrowed in on a single commit introducing the 
behaviour and a fix I pushed shortly after solved the problem for 
everyone who so far reported back. I decided on having people test
this fix until today to make sure it really was the reason for the
communication issues. 

At this point, let me extend a big big **"Thank You!"** 
to everyone who helped identifying the cause of the problem and 
verifying the fix!

On top of those issues, users depending on the
[GPX](http://plugins.octoprint.org/plugins/gpx/) and the 
[M33 Fio](http://plugins.octoprint.org/plugins/m33fio/) plugins
were also running into problems caused by a compatibility issue between
the serial wrappers in these plugins and 1.2.14. I took the opportunity
to also add a workaround to OctoPrint detecting that incompatibility and
wiggling around it. Both plugins have since also been updated though.

Two other minor issues reported after the release of 1.2.14 
were also fixed.

**So, how do we prevent something like this from happening again?** 

Sadly
no matter how many days I invest into testing new releases against 
actual printers, it is impossible to test all potential combinations
considering that they are pretty much endless. 
Things like the above may slip through simply because they do not
reproduce for me, be it because I have the wrong printer, the wrong
controller, the wrong firmware, the wrong firmware configuration or
EEPROM settings, a slightly slower or faster testing machine or just more luck.

But apparently you, 
OctoPrint's users, are very good at covering every single possible 
hardware/software/usage scenario combination under the 
sun! So let's try something new. I'll set up an **opt-in beta program** and will 
put new releases through that first - let's say, a week before full 
release. That will give a wider audience easy access to upcoming 
releases and increase the likelihood of catching issues like the above 
before they are rolled out to everyone, with direct help if problems 
are encountered to get things going again, and of course with the goal
to find and implement a general solution.

Also, to make sure you always know how to roll back to an earlier version,
this and all future release announcements will also include **explicit links to
the roll back instructions** on the wiki - see "Links" below. I'll also think about
some tool support to make rolling back even easier.

For now though, here's 1.2.15, the better 1.2.14.

You can find the full changelog and release notes as usual 
[on Github](https://github.com/foosel/OctoPrint/releases/tag/1.2.15).

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

  * [Changelog and Release Notes](https://github.com/foosel/OctoPrint/releases/tag/1.2.15)
  * [FAQ](https://github.com/foosel/OctoPrint/wiki/FAQ)
  * [Documentation](http://docs.octoprint.org/)
  * [Contribution Guidelines (also relevant for creating bug reports!)](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md)
  * [How to file a bug report](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md#how-to-file-a-bug-report)
  * [How to roll back to an earlier release (OctoPi)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-revert-to-an-older-version-of-the-octoprint-installation-on-my-octopi-image)
  * [How to roll back to an earlier release (manual install)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-roll-back-to-an-earlier-version-after-an-update)
