---

layout: post
title: 'New release candidate: 1.2.17rc3'
author: foosel
date: 2016-10-13 17:00:00 +0200
card: /assets/img/blog/2016-10/2016-10-13-release-candidate-card2.png
featuredimage: /assets/img/blog/2016-10/2016-10-13-release-candidate-card2.png
excerpt: This RC for 1.2.17 fixes a regression that was introduced by 
  1.2.17rc2 released earlier today.

---

1.2.17rc2 as released earlier today sadly introduced a regression: by
making the UI more resilient against JS errors from plugins I also
changed the order in which the JS files were loaded, and I did that in 
a way that caused issues with plugins that needed to register their own
components within OctoPrint.

This new RC should fix this issue by fixing the JS loading order again.

**If you are tracking the "Maintenance RC" release channel**, you
should soon get an update notification just like you are used to from
stable releases.

**If you are not interested in helping to test release candidates**, just
ignore this post, 1.2.17 stable will hit your instance via the usual
way once it's ready :)

You can find the full changelog and release notes as usual 
[on Github](https://github.com/foosel/OctoPrint/releases/tag/1.2.17rc3).

Depending on how the feedback for this release candidate turns out, I'll
either look into releasing 1.2.17 or fix any observed regressions and push 
out a second release candidate within the next week.

### Links

  * [Changelog and Release Notes](https://github.com/foosel/OctoPrint/releases/tag/1.2.17rc3)
  * [Using Release Channels](https://github.com/foosel/OctoPrint/wiki/Using-Release-Channels)
  * [How to file a bug report](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md#how-to-file-a-bug-report)
  * [Contribution Guidelines (also relevant for creating bug reports!)](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md)
  * [FAQ](https://github.com/foosel/OctoPrint/wiki/FAQ)
  * [Documentation](http://docs.octoprint.org/)
  * [How to roll back to an earlier release (OctoPi)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-revert-to-an-older-version-of-the-octoprint-installation-on-my-octopi-image)
  * [How to roll back to an earlier release (manual install)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-roll-back-to-an-earlier-version-after-an-update)
