---
layout: post
title: 'New release: 1.3.4'
author: foosel
date: 2017-06-01 16:00:00 +0200
card: /assets/img/blog/2017-06/2017-06-01-1.3.4-card.png
featuredimage: /assets/img/blog/2017-06/2017-06-01-1.3.4-card.png

---

Due to reports from three people who ran into
[a particular issue](https://github.com/foosel/OctoPrint/issues/1942) with
the 1.3.3 release overnight I decided to push out a hotfix release 1.3.4, even though
only a very small number of users seem to be affected.

<!-- more -->

Apparently under particular (and so far unknown) circumstances the
default printer profile can become corrupted in a way that leads to a **server crash on startup if
auto-connect is configured and the printer plugged in**. I so far have not
been able to reproduce the issue leading to the corruption in the first
place, I'm not even entirely sure it originates within OctoPrint, but I
have been able to fix the particular bits that caused
the consequenting crash. **If you've already updated to 1.3.3 and are
experiencing this**, temporarily disconnect your printer from your OctoPrint
instance, that should make things startup fine again and allow you to
update to 1.3.4.

I did not hear anything at all about this during the release candidate phase
(otherwise I'd of course fixed it then), and I also received a lot of
positive feedback about the update to 1.3.3 since yesterday. That makes
me assume this is in fact a very rare and hard to trigger issue. Still,
I'd rather have the update experience be smooth sailing for everyone,
not just *most* of you, hence this release. **If you already updated to 1.3.3
and did not experience any problems at all** it's probably safe to assume
that you did not run into this issue.

This being a hotfix release means that I did not push out any
release candidates beforehand and the only change contained is a fix
for this particular issue, as visible in the
[Changelog](https://github.com/foosel/OctoPrint/releases/tag/1.3.4).

If you haven't yet,
**please also make sure to read the [release announcement for 1.3.3](/blog/2017/05/31/new-release-1.3.3/)**
as that contains more information about the things that changed
since 1.3.2. Same goes for the [Changelog for 1.3.3](https://github.com/foosel/OctoPrint/releases/tag/1.3.3).

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

  * [Changelog and Release Notes](https://github.com/foosel/OctoPrint/releases/tag/1.3.4)
  * [FAQ](https://github.com/foosel/OctoPrint/wiki/FAQ)
  * [Documentation](http://docs.octoprint.org/)
  * [Contribution Guidelines (also relevant for creating bug reports!)](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md)
  * [How to file a bug report](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md#how-to-file-a-bug-report)
  * [How to roll back to an earlier release (OctoPi)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-revert-to-an-older-version-of-the-octoprint-installation-on-my-octopi-image)
  * [How to roll back to an earlier release (manual install)](https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-roll-back-to-an-earlier-version-after-an-update)

