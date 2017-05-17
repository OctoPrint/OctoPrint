---

layout: post
title: 'New release candidate: 1.3.3rc2'
author: foosel
date: 2017-05-17 11:45:00 +0200
card: /assets/img/blog/2017-05/2017-05-17-card.png
featuredimage: /assets/img/blog/2017-05/2017-05-17-card.png
excerpt: The second release candidate of the 1.3.3 release, fixing
  three minor regressions found in 1.3.3rc1.

---

This second release candidate of the 1.3.3 release fixes three minor
regressions that were found in 1.3.3rc1:

  * [#1917](https://github.com/foosel/OctoPrint/issues/1917) - Fix job
    data resetting on print job completion.
  * [#1918](https://github.com/foosel/OctoPrint/issues/1918) - Fix "save
    as default" checkbox not being disabled when other controls are
    disabled.
  * [#1919](https://github.com/foosel/OctoPrint/issues/1919) - Fix call
    to no longer existing function in Plugin Manager UI.

**If you are tracking the "Maintenance RC" release channel**, you
should soon get an update notification just like you are used to from
stable releases.

**If you are not interested in helping to test release candidates**, just
ignore this post, 1.3.3 stable will hit your instance via the usual
way once it's ready :)

You can find the full changelog and release notes as usual
[on Github](https://github.com/foosel/OctoPrint/releases/tag/1.3.3rc2).

**Please provide feedback** on this RC. For general feedback you can use
[this ticket on the tracker](https://github.com/foosel/OctoPrint/issues/1921).
Note that the information that everything works fine for you is also
valuable feedback :). For bug reports please follow
["How to file a bug report"](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md#how-to-file-a-bug-report).

Depending on how the feedback for this release candidate turns out, I'll
either look into releasing 1.3.3 or fix any observed regressions and push
out a third release candidate within the next couple of days.

### Links

  * [Ticket for general feedback](https://github.com/foosel/OctoPrint/issues/1921)
  * [Changelog and Release Notes](https://github.com/foosel/OctoPrint/releases/tag/1.3.3rc2)
  * [Using Release Channels](https://github.com/foosel/OctoPrint/wiki/Using-Release-Channels)
  * [How to file a bug report](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md#how-to-file-a-bug-report)
  * [Contribution Guidelines (also relevant for creating bug reports!)](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md)
  * [FAQ](https://github.com/foosel/OctoPrint/wiki/FAQ)
  * [Documentation](http://docs.octoprint.org/)
  * [How to roll back to an earlier release (OctoPi)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-revert-to-an-older-version-of-the-octoprint-installation-on-my-octopi-image)
  * [How to roll back to an earlier release (manual install)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-roll-back-to-an-earlier-version-after-an-update)
