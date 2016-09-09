---

layout: post
title: 'New release candidate: 1.2.16rc1'
author: foosel
date: 2016-09-09 10:30:00 +0200
card: /assets/img/blog/2016-09/2016-09-09-release-candidate-card.png
images:
- /assets/img/blog/2016-09/2016-09-09-release-channel-screenie.png
featuredimage: /assets/img/blog/2016-09/2016-09-09-release-candidate-card.png
excerpt: The first release candidate of the 1.2.16 release, with
  various improvements and bug fixes plus the new release channel
  feature.

---

After the compatibility issues we saw in 1.2.14 and which prompted the 
release of 1.2.15 only ~48h later, I promised to look into settings up
an opt-in beta program to give more people a chance to test new 
releases prior to making them available to everyone.

This release candidate is the **first step** in achieving this goal: not only
is it the first release candidate of a maintenance release ever, it also 
introduces the new release channel functionality that will allow you
to comfortably switch to all release candidates to follow in the future,
and also switch back to the current stable version. Please [read more about
Release Channels on the wiki](https://github.com/foosel/OctoPrint/wiki/Using-Release-Channels).

Since current versions of OctoPrint do not yet have the release channel
feature, **if you want to help testing 1.2.16rc1 you'll sadly need to perform
a couple of manual steps** to switch over to the `rc/maintenance`
branch and install the new version from that. Please see below for more details
on that.

**If you are not interested in helping to test release candidates**, just
ignore this post, 1.2.16 stable will hit your instance via the usual
way once it's ready :)

You can find the full changelog and release notes as usual 
[on Github](https://github.com/foosel/OctoPrint/releases/tag/1.2.16rc1).

Depending on how the feedback for this release candidate turns out, I'll
either look into releasing 1.2.16 or fix any observed regressions and push 
out a second release candidate within the next week.

### Manually updating to this RC

For OctoPi:

  * cd ~/OctoPrint
  * source ~/oprint/bin/activate
  * git pull
  * git checkout rc/maintenance
  * python setup.py clean
  * python setup.py install
  * sudo service octoprint restart

For manual installs following the official setup guide:

  * cd /path/to/OctoPrint
  * source ./venv/bin/activate
  * git pull
  * git checkout rc/maintenance
  * python setup.py clean
  * python setup.py install
  * Restart OctoPrint

For both install variants, make sure to select the "Maintenance RCs"
release channel after your 1.2.16rc1 OctoPrint instance has started
via "Settings" > "Software Update" and clicking the little wrench icon
there. If you don't do that, you won't get any update notifications
about any further RCs and will be prompted to revert to stable (currently
1.2.15) instead.

Also see ["Using Release Channels" on the wiki](https://github.com/foosel/OctoPrint/wiki/Using-Release-Channels).

### Links

  * [Changelog and Release Notes](https://github.com/foosel/OctoPrint/releases/tag/1.2.16rc1)
  * [Using Release Channels](https://github.com/foosel/OctoPrint/wiki/Using-Release-Channels)
  * [How to file a bug report](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md#how-to-file-a-bug-report)
  * [Contribution Guidelines (also relevant for creating bug reports!)](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md)
  * [FAQ](https://github.com/foosel/OctoPrint/wiki/FAQ)
  * [Documentation](http://docs.octoprint.org/)
  * [How to roll back to an earlier release (OctoPi)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-revert-to-an-older-version-of-the-octoprint-installation-on-my-octopi-image)
  * [How to roll back to an earlier release (manual install)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-roll-back-to-an-earlier-version-after-an-update)
