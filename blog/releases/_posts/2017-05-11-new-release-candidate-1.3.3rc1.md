---

layout: post
title: 'New release candidate: 1.3.3rc1'
author: foosel
date: 2017-05-11 17:00:00 +0200
card: /assets/img/blog/2017-05/2017-05-11-card.png
featuredimage: /assets/img/blog/2017-05/2017-05-11-card.png
excerpt: The first release candidate of the 1.3.3 release, with various
   improvements and bug fixes.
images:
- url: /assets/img/blog/2017-05/2017-05-11-webcam-placeholder.png
  title: No more jumping controls - the webcam stream now has a fixed height with adjustable aspect ratio.
- url: /assets/img/blog/2017-05/2017-05-11-timelapse-management.gif
  title: Confirmation for deleted timelapses - and to still allow you fast deletions of multiple timelapses a new bulk delete feature.
- url: /assets/img/blog/2017-05/2017-05-11-plugin-notices.png
  title: The new plugin notice mechanism to give you a heads-up regarding any important issues with your installed plugins.

---

It's time to get a new release out of the door with what has accumulated
on the `maintenance` branch, and this shiny new release candidate is
the first step towards this new stable 1.3.3 release.

You might notice that the [changelog](https://github.com/foosel/OctoPrint/releases/tag/1.3.3rc1)
is a bit longer than what you are used to from past maintenance releases.
This is simply the consequence of these releases to be spread a bit
further apart now. I hope that doesn't initimidate you ;)

Some highlights from the release notes:

  * The webcam stream now (finally ;)) has a fixed height in landscape/
    unrotated mode as well, meaning no more jumping controls when it
    loads! The aspect ratio is selectable between 16:9 (the default)
    and 4:3 via a new setting. And the rotated view is now properly
    centered. Additionally a little notice informs you about whether the
    stream is still loading or if loading failed (and if so, what to
    do about that).
  * A new delete confirmation for the timelapses prevents you from
    accidents, and in order to still allow you quick and easy clean-up
    when you actually DO want to delete stuff, a new bulk delete option
    allows you to remove a lot of timelapse related clutter all at once.
  * It's happened a couple of times in the past that plugin authors
    approached me because there was something up with their plugin that
    required some manual action from their users - e.g. a misconfigured
    automatic update or things like a popular plugin looking for a new
    maintainer. So far the [@OctoPrint3D twitter feed]()
    was the only option to reach some of you that were affected by this.
    Not any more - the plugin manager now also fetches plugin specific
    notices from the plugin repository and will display them to you if
    they apply you because you have the relevant plugin installed (optionally
    limited to specific versions). Note that not every plugin author
    can freely send such notices - they'll need to do a pull request
    against the plugin repository for this, so you shouldn't have to
    worry about drowning in notices :)
  * Malyan M200/Monoprice Select Mini firmware should now be autodetected
    so that hopefully everything works with those printers out of the box
    too now.
  * And with regards to bug fixes, what prides me the most is that I managed
    to finally find and fix not one, not two, but three race conditions
    in the code that previously lead to very rare and pretty much
    impossible to reproduce bugs. This might not be a big deal for you,
    but considering how hard it can be to trace down race conditions it
    is for me ;) But apart from that there is also a long list of other
    bugs that got fixed, from simple typos to issues with the gcode
    analysis.

**If you are tracking the "Maintenance RC" release channel**, you
should soon get an update notification just like you are used to from
stable releases.

**If you are not interested in helping to test release candidates**, just
ignore this post, 1.3.3 stable will hit your instance via the usual
way once it's ready :)

You can find the full changelog and release notes as usual
[on Github](https://github.com/foosel/OctoPrint/releases/tag/1.3.3rc1).

Please **provide feedback** on this RC. For general feedback you can use
[this ticket on the tracker](https://github.com/foosel/OctoPrint/issues/1914).
If everything works fine for you, that is also valuable feedback :)

Depending on how the feedback for this release candidate turns out, I'll
either look into releasing 1.3.3 or fix any observed regressions and push
out a second release candidate within the next couple of days.

### Links

  * [Changelog and Release Notes](https://github.com/foosel/OctoPrint/releases/tag/1.3.3rc1)
  * [Using Release Channels](https://github.com/foosel/OctoPrint/wiki/Using-Release-Channels)
  * [How to file a bug report](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md#how-to-file-a-bug-report)
  * [Contribution Guidelines (also relevant for creating bug reports!)](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md)
  * [FAQ](https://github.com/foosel/OctoPrint/wiki/FAQ)
  * [Documentation](http://docs.octoprint.org/)
  * [How to roll back to an earlier release (OctoPi)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-revert-to-an-older-version-of-the-octoprint-installation-on-my-octopi-image)
  * [How to roll back to an earlier release (manual install)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-roll-back-to-an-earlier-version-after-an-update)
