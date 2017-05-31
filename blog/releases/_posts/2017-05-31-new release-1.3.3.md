---
layout: post
title: 'New release: 1.3.3'
author: foosel
date: 2017-05-31 16:45:00 +0200
card: /assets/img/blog/2017-05/2017-05-31-1.3.3-card.png
featuredimage: /assets/img/blog/2017-05/2017-05-31-1.3.3-card.png
images:
- url: /assets/img/blog/2017-05/2017-05-11-webcam-placeholder.png
  title: No more jumping controls - the webcam stream now has a fixed height with adjustable aspect ratio.
- url: /assets/img/blog/2017-05/2017-05-11-timelapse-management.gif
  title: Confirmation for deleted timelapses - and to still allow you fast deletions of multiple timelapses a new bulk delete feature.
- url: /assets/img/blog/2017-05/2017-05-11-plugin-notices.png
  title: The new plugin notice mechanism to give you a heads-up regarding any important issues with your installed plugins.

---

After three release candidates I'm happy to finally present you OctoPrint
1.3.3. This a true maintenance release again, consisting of various improvements and
fixes.

<!-- more -->

Some highlights from the release notes:

  * The webcam stream now (finally ;)) has a fixed height in landscape/unrotated
    mode as well, meaning no more jumping controls when it
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
    maintainer. So far the [@OctoPrint3D twitter feed](https://twitter.com/OctoPrint3D)
    was the only option to reach some of you that were affected by this.
    Not any more - the plugin manager now also fetches plugin specific
    notices from the plugin repository and will display them to you if
    you have the relevant plugin installed (optionally limited to
    specific versions). Note that not every plugin author
    can freely send such notices - they'll need to do a pull request
    against the plugin repository for this, so you shouldn't have to
    worry about drowning in notices :)
  * And of course there is a long list of bugs that got fixed too, from
    simple typos over issues with the gcode analysis to race conditions
    that have been driving me crazy for months now. Good riddance :)

Since Github experienced a major service outage earlier today, a small
heads-up that will hopefully resolve itself over the course of today
(May 31st, 2017) - to quote the [Changelog](https://github.com/foosel/OctoPrint/releases/tag/1.3.3):

> **Current Github hiccups might impede updating for a bit (May 31st, 2017)**
>
> This might resolve itself within the next couple of hours: Github currently still appears to suffer from some hiccups (they had an outage earlier today, May 31st 2017). That might cause your update to take longer than usual or maybe even not run properly at all - the update mechanism is based on Github's releases API & repositories being available. So: if you happen to run into any issues during updating, please just wait a couple more hours. I sadly have no influence there at all and can just hope that those issues will be resolved soon.

There is also a note for those of you who run a Malyan M200 or
Monoprice Select Mini printer, to quote the
[Changelog](https://github.com/foosel/OctoPrint/releases/tag/1.3.3):

> **Note for owners of Malyan M200/Monoprice Select Mini**
>
> OctoPrint's firmware autodetection is now able to detect this printer. Currently when this printer is detected, the following firmware specific features will be enabled automatically:
>
>   * Always assume SD card is present (`feature.sdAlwaysAvailable`)
>   * Send a checksum with the command: Always (`feature.alwaysSendChecksum`)
>
> Since the firmware is a very special kind of beast and its sources are so far unavailable, only tests with a real printer will show if those are sufficient settings for communication with this printer to fully function correctly. Thus, if you run into any issues with enabled firmware autodetection on this printer model, please add a comment in [#1762](https://github.com/foosel/OctoPrint/issues/1762) and explain what kind of communication problem you are seeing. Also make sure to include a [`serial.log`](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md#where-can-i-find-those-log-files-you-keep-talking-about)!

The full list of changes can of course be found in the
[Changelog](https://github.com/foosel/OctoPrint/releases/tag/1.3.3) - as always.

Also see the **Further Information** and **Links** below for more information,
where to find help and how to roll back. Thanks!

### Further Information

It may take up to 24h for your update notification to pop up, so don't 
be alarmed if it doesn't show up immediately after reading this. You
can force the update however via Settings > Software Update > 
Advanced options > Force check for update.

If you don't get an "Update Now" button with your update notification, 
read [this](https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update#making-octoprint-updateable-on-existing-installations)
or - even more specifically - [this](https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update#octoprint--125).

If you are running 1.2.7, get an "Update Now" button but the update is immediately 
reported to be successful without any changes, read 
[this](https://github.com/foosel/OctoPrint/wiki/FAQ#im-running-127-i-tried-to-update-to-a-newer-version-via-the-software-update-plugin-but-im-still-on-127-after-restart).

If you are running 1.2.16, get an "Update Now" button but the update is immediately
producing an error message, read [this](https://github.com/foosel/OctoPrint/wiki/FAQ#im-running-1216-i-tried-to-update-to-a-newer-version-via-the-software-update-plugin-but-i-get-an-error).

If you have any problems with your OctoPrint installation, please seek 
support in the [G+ Community](https://plus.google.com/communities/102771308349328485741)
or the [Mailinglist](https://groups.google.com/group/octoprint). 

### Links

  * [Changelog and Release Notes](https://github.com/foosel/OctoPrint/releases/tag/1.3.3)
  * [FAQ](https://github.com/foosel/OctoPrint/wiki/FAQ)
  * [Documentation](http://docs.octoprint.org/)
  * [Contribution Guidelines (also relevant for creating bug reports!)](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md)
  * [How to file a bug report](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md#how-to-file-a-bug-report)
  * [How to roll back to an earlier release (OctoPi)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-revert-to-an-older-version-of-the-octoprint-installation-on-my-octopi-image)
  * [How to roll back to an earlier release (manual install)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-roll-back-to-an-earlier-version-after-an-update)

