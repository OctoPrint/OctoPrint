---
layout: post
title: 'New release: 1.3.0'
author: foosel
date: 2016-12-08 14:00:00 +0100
card: /assets/img/blog/2016-12/2016-12-08-release-card.png
featuredimage: /assets/img/blog/2016-12/2016-12-08-release-card.png
images:
- url: /assets/img/blog/2016-10/2016-10-19-folders.png
  title: The new folder support
- url: /assets/img/blog/2016-10/2016-10-19-wizard.png
  title: The new wizard dialog system in action
- url: /assets/img/blog/2016-10/2016-10-19-ui-example-mrbeam.png
  title: A custom UI by Mr Beam tailored to their laser cutter, done through a UiPlugin
- url: /assets/img/blog/2016-10/2016-10-19-ui-example-leapfrog.png
  title: A custom UI by Leapfrog for their printers, done through a UiPlugin
- url: /assets/img/blog/2016-10/2016-10-19-ui-example-forcelogin.png
  title: A login-only view forced for logged out/anonymous users, done through a UiPlugin
- url: /assets/img/blog/2016-11/2016-11-24-bounding-box.png
  title: Configuring a custom safe bounding box
- url: /assets/img/blog/2016-11/2016-11-24-firmware-detection.gif
  title: New firmware auto detection feature
excerpt: After over a year of work and overshadowed by a full blown project
  funding crisis, today the much anticipated 1.3.0 release finally sees 
  the light of day!

---

*Phew!*

After over a year of work - constantly interrupted by intermittent
maintenance releases of 1.2.x I might add ;) - and unmeasured hours of implementation, testing and debugging
plus also a [full blown funding crisis](http://octoprint.org/blog/2016/05/25/state-of-octoprint/)
in between, the day is finally here: 1.3.0 is released. 

Before I talk a bit more about what you'll find in this release, let me take a short
moment for another huge **THANK YOU** from the bottom of my heart towards
everyone who helped getting this on the road. That includes everyone who
contributed even the tiniest amount of code, documentation or typo fix, engaged in valuable discussions
about how to solve certain issues, provided feedback on stuff that was
or wasn't working. It includes everyone who helped test the release
candidates and reported back. And of course it includes every single one of
over a thousand Patrons on [Patreon](https://patreon.com/foosel) and of course all of you who
[contributed via PayPal](https://paypal.me/foosel) to make my continued full time work
on OctoPrint financially possible. Getting this release out wouldn't have
worked out without the community!

With that being said, on to what's new! There's a multitude of new 
features and improvements plus of course also a handful of bug fixes in 
this release, way too much to list all of it here, but let's at least take 
a look at some of them:

  * Finally there's a way to keep all of your files for one project 
    together in one place thanks to the newly added **folder support**.
    Along with that OctoPrint now also exposes copy and move functionality
    on the API, which the **[File Manager Plugin by Salandora](https://github.com/Salandora/OctoPrint-FileManager)**
    will utilize to offer a full fledged file manager to make working with
    your new folders even easier.
  * A new **wizard dialog system** replaces the old "first run" dialog,
    leads through first time setup and/or consecutive setup steps and
    is also extendable by plugin authors to query information from users
    about freshly installed or updated plugins they need in order to
    run[^1]. See the screenshots below for an [example](#image-2)
  * Plugins may now temporarily or completely **replace the web interface**. 
    It would for example be possible to have OctoPrint
    show you a different UI when connecting from a mobile device vs.
    your desktop machine, or from a specific machine vs all other
    machines. And to take some of the boilerplate out of connecting
    to the API from custom UIs, I've extracted out an API client into
    a **[Client JS library](http://docs.octoprint.org/en/devel/jsclientlib/index.html)** too.
    I've also prepared a small proof-of-concept example of a plugin utilizing
    the new possibilities by checking the login status of a user and
    delivering a login-only UI to anonymous users instead of the stock
    UI[^2]: [the ForceLogin plugin](https://github.com/OctoPrint/OctoPrint-ForceLogin).
    UiPlugins and the JS Client Lib together open up a lot of possibilities 
    in creating full blown dashboard systems, alternative UIs and 
    customizations and I'm excited to see what plugin authors will do 
    with these new toys! There are screenshots 
    [of](#image-3) [some](#image-4) [examples](#image-5) below.
  * OctoPrint will now **track the current print head position on pause and 
    cancel** and provide it as new template variables 
    ``pause_position``/``cancel_position`` for the relevant GCODE scripts. 
    This will allow more intelligent pause codes that park the print head 
    at a rest position during pause and move it back to the exact position 
    it was before the pause on resume 
    ([Example](https://gist.github.com/foosel/1c09e269b1c0bb7a471c20eef50c8d3e)). 
    Note that OctoPrint does NOT ship with such scripts in place. For now
    you will have to adjust the pause and resume GCODE scripts yourself since position 
    tracking with multiple extruders or when printing from SD is currently 
    not fool proof thanks to firmware limitations regarding reliable 
    tracking of the various ``E`` values and the currently selected 
    tool ``T``. Thanks to those limitations I did not feel comfortable
    to make this a preconfigured out-of-the box feature, but maybe there'll
    be some way to change that in future versions!
  * There is now an (optional) **firmware auto detection** in place. This 
    should hopefully reduce issues for first-time users running
    a firmware that needs specific flags to be set for proper
    support.
  * A lot of **UI improvements** like e.g. test buttons for various settings
    like the webcam URLs or paths to executable like ffmpeg, a refactored
    printer profile editor, and a lot more tiny adjustments all around the
    UI.
  * **More verbosity during updates** of OctoPrint and installed plugins
    for logged in admins.
  * Better (and earlier) **error reporting for timelapse issues**.
  * Aggressive caching for APIs and UIs for **improved load times** and
    less resource consumption.
  * Centrally managed **server commands** for restarting OctoPrint and
    rebooting and shutting down the system its running on. For those
    OctoPrint will now generate entries in the System menu automatically
    and they will also be used for restarting after updates or after
    installing plugins that necessitate that.

That is only the tip of the iceberg, best take a look at the 
[Changelog](https://github.com/foosel/OctoPrint/releases/tag/1.3.0rc1)
for a more comprehensive overview.

Finally, if you run into any problems with this OctoPrint or its bundled
plugins in this release, please [report them](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md#how-to-file-a-bug-report)
since I cannot fix issues I know nothing about. I've tested this version excessively
over the past couple of months, and I guess so have a lot of you running the 
"Devel RCs" [release channel](https://github.com/foosel/OctoPrint/wiki/Using-Release-Channels) 
or even the ``devel`` branch itself. This *is* a huge release though and as I've 
[mentioned before](http://octoprint.org/blog/2016/07/30/new-release-1.2.15/)
all of you together run way more combinations of printers, controllers
and firmware plus usage scenarios than I (or any single person for that
matter) could ever hope to cover in tests. So if something doesn't work
in OctoPrint or any of the bundled plugins, keep that in mind and just 
report it back so that it can be fixed :)

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

  * [Changelog and Release Notes](https://github.com/foosel/OctoPrint/releases/tag/1.2.18)
  * [FAQ](https://github.com/foosel/OctoPrint/wiki/FAQ)
  * [Documentation](http://docs.octoprint.org/)
  * [Contribution Guidelines (also relevant for creating bug reports!)](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md)
  * [How to file a bug report](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md#how-to-file-a-bug-report)
  * [How to roll back to an earlier release (OctoPi)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-revert-to-an-older-version-of-the-octoprint-installation-on-my-octopi-image)
  * [How to roll back to an earlier release (manual install)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-roll-back-to-an-earlier-version-after-an-update)

### Footnotes

  [^1]: Note that this will also trigger for the CuraEngine plugin 
        after you update if you haven't yet setup a slicing profile. 
        Just skip the wizard once, reload as instructed and it will not 
        ask you again :)

  [^2]: Please note that this will only protect OctoPrint's UI. It will
        *not* be able to protect your webcam since that's not served by
        OctoPrint, OctoPrint is only embedding it (as a side-note though, 
        I'm working on a solution for that too). So do not use that in a
        setting were a) the URL of the webcam stream might be guessable and
        b) someone anonymously accessing the webcam would be a serious
        privacy issue.
