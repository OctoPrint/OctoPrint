---

layout: post
title: 'New release candidate: 1.3.0rc3'
author: foosel
date: 2016-12-02 14:00:00 +0100
card: /assets/img/blog/2016-12/2016-12-02-release-candidate-card.png
featuredimage: /assets/img/blog/2016-12/2016-12-02-release-candidate-card.png
excerpt: The third release candidate for the upcoming huge 1.3.0
  release, now available for your testing pleasure!

---

I thought long and hard whether to release yet another RC after all or
not, but considering a bug I discovered with the settings caching I
decided it would probably be better after all.

The result is 1.3.0rc3, which besides a fix for that settings caching
issue also contains a bunch of other fixes and also the improvement
of a piece of documentation and a doctest. Overall, the changes are
very small, but the caching issue made me nervous enough to leave in
to push out another RC. You can find the full changelog 
and release notes as usual [on Github](https://github.com/foosel/OctoPrint/releases/tag/1.3.0rc3).

**If you are tracking the "Devel RC" release channel**, you
should soon get an update notification just like you are used to from
stable releases. **If you are coming from 1.3.0rc1**, you might run into
an update error that actually isn't one, please see the 
["Note for Upgraders coming from 1.3.0rc1" in the release notes for 1.3.0rc2](https://github.com/foosel/OctoPrint/releases/tag/1.3.0rc2) 
for more details on this.

**If you are tracking the "Maintenance RC" release channel**, you will
*not* get an update notification for this release candidate. If you want
to give it a test whirl, you'll need to switch to the "Devel RC" release
channel.

**If you are not interested in helping to test devel release candidates**, just
ignore this post, 1.3.0 stable will hit your instance via the usual
way once it's ready :)

Depending on the feedback regarding this version I'll either look into
releasing 1.3.0 stable within the next week, or fixing any bugs and
regressions in a follow-up RC. In the latter case though we'll not see
1.3.0 before the holidays, in order to minimize the risk of any issues
for people with new printers. Let's hope it won't come to that though,
I really want to get 1.3.0 out ASAP :)

### Links

  * [Changelog and Release Notes](https://github.com/foosel/OctoPrint/releases/tag/1.3.0rc3)
  * [Using Release Channels](https://github.com/foosel/OctoPrint/wiki/Using-Release-Channels)
  * [How to file a bug report](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md#how-to-file-a-bug-report)
  * [Contribution Guidelines (also relevant for creating bug reports!)](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md)
  * [FAQ](https://github.com/foosel/OctoPrint/wiki/FAQ)
  * [Documentation](http://docs.octoprint.org/)
  * [How to roll back to an earlier release (OctoPi)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-revert-to-an-older-version-of-the-octoprint-installation-on-my-octopi-image)
  * [How to roll back to an earlier release (manual install)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-roll-back-to-an-earlier-version-after-an-update)

### Footnotes

  [^1]: Mostly thanks to a severe clogged <s>nozzle</s>nose issue that 
        is sadly all too common in the northern hemisphere this time of 
        the year.
