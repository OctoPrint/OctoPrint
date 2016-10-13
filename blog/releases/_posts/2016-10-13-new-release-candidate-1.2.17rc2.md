---

layout: post
title: 'New release candidate: 1.2.17rc2'
author: foosel
date: 2016-10-13 13:20:00 +0200
card: /assets/img/blog/2016-10/2016-10-13-release-candidate-card.png
featuredimage: /assets/img/blog/2016-10/2016-10-13-release-candidate-card.png
excerpt: Another release candidate for 1.2.17 that fixes another bug from
  1.2.16 and adds some internal improvements as well.

---

And just when I wanted to release 1.2.17 proper, during the final test
run yesterday evening I stumbled across another bug, introduced in 
1.2.16 and - for extra fun times - causing updating to 1.2.17 to fail. 
Well, at least unless one has clicked the "Save" button in the Settings 
dialog for whatever reason (e.g. to switch to another release channel ;)).

So another release candidate was necessary to fix that, and since I
spent some hours over the last few days with a long due overhaul of some 
parts of the logging subsystem I figured I should add that to this RC as
well.

So in a nutshell:

  * This RC fixes a bug in the updater those of you on the 
    "Maintenance RC" release channel probably had no chance to even 
    notice, unless you switched to the channel manually by directly 
    editing `config.yaml` and then never ever hit Save in the Settings
    after that ;)
  * It also finally made the logging subsystem clean up after itself 
    properly, really delete old `octoprint.log`s and made the `serial.log`
    a bit more intelligent, rolling it over for each serial connection 
    (if you have enabled it - which you really only should have when
    debugging communication issues or during development if necessary).
  * And finally I made OctoPrint as a whole more resilient against 
    broken JS code from plugins by splitting the asset bundles of the 
    JS that makes up the frontend logic into "safe" core + bundled plugins
    and "unsafe" external plugins - if there's an error in the latter, 
    the former now should still load fine :)

**If you are tracking the "Maintenance RC" release channel**, you
should soon get an update notification just like you are used to from
stable releases.

**If you are not interested in helping to test release candidates**, just
ignore this post, 1.2.17 stable will hit your instance via the usual
way once it's ready :)

You can find the full changelog and release notes as usual 
[on Github](https://github.com/foosel/OctoPrint/releases/tag/1.2.17rc2).

Depending on how the feedback for this release candidate turns out, I'll
either look into releasing 1.2.17 or fix any observed regressions and push 
out a second release candidate within the next week.

### Links

  * [Changelog and Release Notes](https://github.com/foosel/OctoPrint/releases/tag/1.2.17rc2)
  * [Using Release Channels](https://github.com/foosel/OctoPrint/wiki/Using-Release-Channels)
  * [How to file a bug report](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md#how-to-file-a-bug-report)
  * [Contribution Guidelines (also relevant for creating bug reports!)](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md)
  * [FAQ](https://github.com/foosel/OctoPrint/wiki/FAQ)
  * [Documentation](http://docs.octoprint.org/)
  * [How to roll back to an earlier release (OctoPi)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-revert-to-an-older-version-of-the-octoprint-installation-on-my-octopi-image)
  * [How to roll back to an earlier release (manual install)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-roll-back-to-an-earlier-version-after-an-update)
