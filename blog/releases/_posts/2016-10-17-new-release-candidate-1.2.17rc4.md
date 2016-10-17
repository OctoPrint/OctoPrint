---

layout: post
title: 'New release candidate: 1.2.17rc4'
author: foosel
date: 2016-10-17 13:30:00 +0200
card: /assets/img/blog/2016-10/2016-10-17-release-candidate-card.png
featuredimage: /assets/img/blog/2016-10/2016-10-17-release-candidate-card.png
excerpt: Another RC after all before we get out the stable 1.2.17 release,
  due to another bug that was found and fixed since pushing out 1.2.17rc3.

---

There was an issue introduced in 1.2.17rc2, causing an internal server
error in OctoPrint under specific circumstances (no external plugins with
JS assets installed). Which means we'll sadly need yet another RC before
1.2.17 can be considered stable: 1.2.17rc4.

The only change compared to 1.2.17rc3 of this RC is the fix of the 
aforementioned error.

Considering that one minor improvement in 1.2.17rc2 (to make OctoPrint more
resilient against errors in JS files from plugins) now already caused
two more RCs to be necessary, I'll limit what may go into RCs after the
first RC has been pushed out further. So far I also allowed minor
improvements and fixes of little issues reported since the first RC that
were neither regressions nor bugs introduced by the RC. From now on, 
follow-up RCs will only be allowed to contain singular fixes of 
regressions or bugs in the RC functionality itself.

On top of that, I've also adjusted my own test steps to include a completely
clean and fresh OctoPrint instance, without even the small helper plugin 
I use to speed up pre-release smoke testing - that should hopefully
make sure that I'll find issues like the one above earlier too.

**If you are tracking the "Maintenance RC" release channel**, you
should soon get an update notification just like you are used to from
stable releases.

**If you are not interested in helping to test release candidates**, just
ignore this post, 1.2.17 stable will hit your instance via the usual
way once it's ready :)

You can find the full changelog and release notes as usual 
[on Github](https://github.com/foosel/OctoPrint/releases/tag/1.2.17rc4).

Depending on how the feedback for this release candidate turns out, I'll
either look into releasing 1.2.17 or fix any observed regressions and push 
out a second release candidate within the next couple of days.

### Links

  * [Changelog and Release Notes](https://github.com/foosel/OctoPrint/releases/tag/1.2.17rc4)
  * [Using Release Channels](https://github.com/foosel/OctoPrint/wiki/Using-Release-Channels)
  * [How to file a bug report](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md#how-to-file-a-bug-report)
  * [Contribution Guidelines (also relevant for creating bug reports!)](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md)
  * [FAQ](https://github.com/foosel/OctoPrint/wiki/FAQ)
  * [Documentation](http://docs.octoprint.org/)
  * [How to roll back to an earlier release (OctoPi)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-revert-to-an-older-version-of-the-octoprint-installation-on-my-octopi-image)
  * [How to roll back to an earlier release (manual install)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-roll-back-to-an-earlier-version-after-an-update)
