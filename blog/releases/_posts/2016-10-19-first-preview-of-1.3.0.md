---

layout: post
title: 'First preview of 1.3.0!'
author: foosel
date: 2016-10-19 14:00:00 +0200
card: /assets/img/blog/2016-10/2016-10-19-preview-card.png
featuredimage: /assets/img/blog/2016-10/2016-10-19-preview-card.png
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

---

I'm very happy to finally present you with a first preview
of the upcoming major 1.3.0 release: 1.3.0rc1!

<!-- more -->

There's a multitude of new features and improvements plus of course also
a small handful of bug fixes going to be in this release, way too much 
to list all of it here, but let's at least take a look at some of them:

  * Finally there's a way to keep all of your files for one project 
    together in one place thanks to the newly added **folder support**.
    Along with that OctoPrint now also exposes copy and move functionality
    on the API, which the [File Manager Plugin by Salandora](https://github.com/Salandora/OctoPrint-FileManager)
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
    OctoPrint will now generate entries in the System menu automatically[^3]
    and they will also be used for restarting after updates or after
    installing plugins that necessitate that.

That is only the tip of the iceberg, best take a look at the 
[Changelog](https://github.com/foosel/OctoPrint/releases/tag/1.3.0rc1)
for a more comprehensive overview.

Please note that **this is most likely not the final version** that will be turned
into the stable 1.3.0 release. I definitely expect there to still be bugs! 
And the goal of pushing this out now is to find those bugs in order to iron them 
out. I need your help with that since at this point I simply am not 
seeing the wood for all the trees anymore.

Still, please **only install this if you are comfortable** with having to
do a manual roll back if push comes to shove and something does indeed 
break for you. It should not, but it could.

**If you are tracking the "Devel RC" release channel**, you
should soon get an update notification just like you are used to from
stable releases.

**If you are tracking the "Maintenance RC" release channel**, you will
*not* get an update notification for this release candidate. If you want
to give it a test whirl, you'll need to switch to the "Devel RC" release
channel.

**If you are not interested in helping to test devel release candidates**, just
ignore this post, 1.3.0 stable will hit your instance via the usual
way once it's ready :)

You can find the full changelog and release notes as usual 
[on Github](https://github.com/foosel/OctoPrint/releases/tag/1.3.0rc1).

Depending on the feedback regarding this version I'll look into fixing 
any observed regressions and bugs and pushing out a follow-up version 
within the next two or three weeks.

### Links

  * [Changelog and Release Notes](https://github.com/foosel/OctoPrint/releases/tag/1.3.0rc1)
  * [Using Release Channels](https://github.com/foosel/OctoPrint/wiki/Using-Release-Channels)
  * [How to file a bug report](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md#how-to-file-a-bug-report)
  * [Contribution Guidelines (also relevant for creating bug reports!)](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md)
  * [FAQ](https://github.com/foosel/OctoPrint/wiki/FAQ)
  * [Documentation](http://docs.octoprint.org/)
  * [How to roll back to an earlier release (OctoPi)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-revert-to-an-older-version-of-the-octoprint-installation-on-my-octopi-image)
  * [How to roll back to an earlier release (manual install)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-roll-back-to-an-earlier-version-after-an-update)

### Footnotes

  [^1]: Note that this will also trigger for the CuraEngine plugin 
        after you update if you haven't yet setup a slicing profile). 
        Just skip the wizard once and it will not ask you again :)

  [^2]: Please note that this will only protect OctoPrint's UI. It will
        *not* be able to protect your webcam since that's not served by
        OctoPrint, OctoPrint is only embedding it (as a side-note though, 
        I'm working on a solution for that too). So do not use that in a
        setting were a) the URL of the webcam stream might be guessable and
        b) someone anonymously accessing the webcam would be a serious
        privacy issue.
        
  [^3]: If you already had the system commands configured manually or 
        had gotten them preconfigured through OctoPi, they'll now show 
        up twice - this can be rectified by simply removing
        the manually configured system commands, but you might want to wait
        with that until the stable release of 1.3.0 :) I might also still
        add some migration step for that.
