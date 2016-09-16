---

layout: post
title: 'New release candidate: 1.2.16rc2'
author: foosel
date: 2016-09-16 13:30:00 +0200
card: /assets/img/blog/2016-09/2016-09-16-release-candidate-card.png
featuredimage: /assets/img/blog/2016-09/2016-09-16-release-candidate-card.png
excerpt: The second release candidate of the 1.2.16 release, with
  two bug fixes and a small improvement.

---

The first release candidate of 1.2.16rc1 turned out to still have a tiny
bug with the new release channel feature, and since that meant a second
release candidate for 1.2.16 was necessary to fix that I also
took the opportunity to take care of two other things reported in the 
mean time.

**If you are already running 1.2.16rc1** and followed the instructions in the 
[announcement of 1.2.16rc1](//octoprint.org/blog/2016/09/09/new-release-candidate-1.2.16rc1/)
including the switch of the release channel to "Maintenance RCs" you
should soon get an update notification just like you are used to from
stable releases. Please report back on the bug tracker (links below) if
anything goes wrong here. I actually consider it lucky that I had to push
out a second RC for the simple reason that you'll now also be able to test
the new RC update path ;)

**If you are not yet running 1.2.16rc1** but want to give this RC a test
drive, you'll need to follow the manual instructions as found in the
[announcement of 1.2.16rc1](//octoprint.org/blog/2016/09/09/new-release-candidate-1.2.16rc1/).

**If you are not interested in helping to test release candidates**, just
ignore this post, 1.2.16 stable will hit your instance via the usual
way once it's ready :)

You can find the full changelog and release notes as usual 
[on Github](https://github.com/foosel/OctoPrint/releases/tag/1.2.16rc2).

Depending on how the feedback for this release candidate turns out, I'll
either look into releasing 1.2.16 or fix any observed regressions and push 
out another release candidate within the next week.

### Links

  * [Changelog and Release Notes](https://github.com/foosel/OctoPrint/releases/tag/1.2.16rc2)
  * [Using Release Channels](https://github.com/foosel/OctoPrint/wiki/Using-Release-Channels)
  * [How to file a bug report](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md#how-to-file-a-bug-report)
  * [Contribution Guidelines (also relevant for creating bug reports!)](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md)
  * [FAQ](https://github.com/foosel/OctoPrint/wiki/FAQ)
  * [Documentation](http://docs.octoprint.org/)
  * [How to roll back to an earlier release (OctoPi)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-revert-to-an-older-version-of-the-octoprint-installation-on-my-octopi-image)
  * [How to roll back to an earlier release (manual install)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-roll-back-to-an-earlier-version-after-an-update)
