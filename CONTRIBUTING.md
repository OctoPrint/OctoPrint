# Contribution Guidelines

This document outlines what you need to know before **[creating tickets](#issues-tickets-however-you-may-call-them)**
or **[creating pull requests](#pull-requests)**.

## Contents

  * [Issues, Tickets, however you may call them](#issues-tickets-however-you-may-call-them)
  * [How to file a bug report](#how-to-file-a-bug-report)
    * [What should I do before submitting a bug report?](#what-should-i-do-before-submitting-a-bug-report)
    * [What should I include in a bug report?](#what-should-i-include-in-a-bug-report)
    * [Where can I find which version and branch I'm on?](#where-can-i-find-which-version-and-branch-im-on)
    * [Where can I find those log files you keep talking about?](#where-can-i-find-those-log-files-you-keep-talking-about)
    * [Where can I find my browser's error console?](#where-can-i-find-my-browsers-error-console)
  * [Pull requests](#pull-requests)
  * [What do the branches mean?](#what-do-the-branches-mean)
  * [How OctoPrint is versioned](#how-octoprint-is-versioned)
  * [History](#history)
  * [Footnotes](#footnotes)

## Issues, Tickets, however you may call them

Please read the following short instructions fully and follow them. You can
help the project tremendously this way: not only do you help the maintainers
to **address problems in a timely manner** but also keep it possible for them
to **fix bugs, add new and improve on existing functionality** instead of doing
nothing but ticket management.

![Ticket flow chart](http://i.imgur.com/qYSZyuw.png)

- **[Read the FAQ](https://github.com/foosel/OctoPrint/wiki/FAQ)**
- If you want to report a **bug**, [read "How to file a bug report" below](#how-to-file-a-bug-report)
  and *[use the provided template](#what-should-i-include-in-a-ticket)*.
  You do not need to do anything else with your ticket.
- If you want to post a **feature request** or a **documentation request**, add `[Request]`
  to your issue's title (e.g. `[Request] Awesome new feature`). A question on how to run/change/setup
  something is **not** what qualifies as a request here, use the
  [Mailinglist](https://groups.google.com/group/octoprint) or the
  [Google+ Community](https://plus.google.com/communities/102771308349328485741) for
  such support issues.
- If you are a **developer** that wants to brainstorm a pull request or possible
  changes to the plugin system, add [Brainstorming] to your issue's title (e.g.
  `[Brainstorming] New plugin hook for doing some cool stuff`).
- If you need **support**, have a **question** or some **other reason** that
  doesn't fit any of the above categories, the issue tracker is not the right place.
  Consult the [Mailinglist](https://groups.google.com/group/octoprint) or the
  [Google+ Community](https://plus.google.com/communities/102771308349328485741) instead.

No matter what kind of ticket you create, never mix two or more "ticket reasons"
into one ticket: One ticket per bug, request, brainstorming thread please.

----

**Note**: A bot is in place that monitors new tickets, automatically
categorizes them and checks new bug reports for usage of the provided template.
That bot will only bother you if you open a ticket that appears to be a bug (no
`[Request]` or `[Brainstorming]` in the title) without the template, and it
will do that only to ensure that all information needed to solve the issue is
available for the maintainers to directly start tackling that problem.

----

## How to file a bug report

If you encounter an issue with OctoPrint, you are welcome to
[submit a bug report](https://goo.gl/GzkGv9).

Before you do that for the first time though please take a moment to read the
following section *completely*. Thank you! :)

### What should I do before submitting a bug report?

1. **Make sure you are at the right location**. This is the Github repository
   of the official version of OctoPrint, which is the 3D print server and
   corresponding web interface itself.

   **This is not the Github respository of OctoPi**, which is the preconfigured
   Raspberry Pi image including OctoPrint among other things - that one can be found
   [here](https://github.com/guysoft/OctoPi). Please note that while we do have
   some entries regarding OctoPi in the FAQ, any bugs should be reported in the
   [proper bug tracker](https://github.com/guysoft/OctoPi/issues) which - again -
   is not here.

   **This is also not the Github repository of any OctoPrint Plugins you
   might have installed**. Report any issues with those in their corresponding
   bug tracker (probably linked to from the plugin's homepage).

   Finally, **this is also not the right issue tracker if you are running an
   forked version of OctoPrint**. Seek help for such unofficial versions from
   the people maintaining them instead.

2. Please make sure to **test out the current version** of OctoPrint to see
   whether the problem you are encountering still exists, and **test without
   any non-bundled plugins enabled** to make sure it's not a misbehaving
   plugin causing the issue at hand.

   If you are feeling up to it you might also want to try the current development
   version of OctoPrint (if you aren't already). Refer to the [FAQ](https://github.com/foosel/OctoPrint/wiki/FAQ)
   for information on how to do this.

3. The problem still exists? Then please **look through the
   [existing tickets](https://github.com/foosel/OctoPrint/issues?state=open)
   (use the [search](https://github.com/foosel/OctoPrint/search?q=&ref=cmdform&type=Issues))**
   to check if there already exists a report of the issue you are encountering.
   Sorting through duplicates of the same issue sometimes causes more work than
   fixing it. Take the time to filter through possible duplicates and be really
   sure that your problem definitely is a new one. Try more than one search query
   (e.g. do not only search for "webcam" if you happen to run into an issue
   with your webcam, also search for "timelapse" etc). Do not only read the subject lines
   of tickets that look like they might be related, but also read the ticket itself!

   **Very important:** Please make absolutely sure that if you find a bug that looks like
   it is the same as your's, it actually behaves the same as your's. E.g. if someone gives steps
   to reproduce his bug that looks like your's, reproduce the bug like that if possible,
   and only add a "me too" if you actually can reproduce the same
   issue. Also **provide all information** as [described below](#what-should-i-include-in-a-bug-report)
   and whatever was additionally requested over the course of the ticket
   even if you "only" add to an existing ticket. The more information available regarding a bug, the higher
   the chances of reproducing and solving it. But "me too" on an actually unrelated ticket
   makes it more difficult due to on top of having to figure out the original problem
   there's now also a [red herring](https://en.wikipedia.org/wiki/Red_herring) interfering - so please be
   very diligent here!

### What should I include in a bug report?

Always use the following template (you can remove what's within `[...]`, that's
only provided here as some additional information for you), **even if only adding a
"me too" to an existing ticket**:

    #### What were you doing?

    [Please be as specific as possible here. The maintainers will need to reproduce
    your issue in order to fix it and that is not possible if they don't know
    what you did to get it to happen in the first place. If you encountered
    a problem with specific files of any sorts, make sure to also include a link to a file
    with which to reproduce the problem.]

    #### What did you expect to happen?

    #### What happened instead?

    #### Branch & Commit or Version of OctoPrint

    [Can be found in the lower left corner of the web interface.]

    #### Printer model & used firmware incl. version

    [If applicable, always include if unsure.]

    #### Browser and Version of Browser, Operating System running Browser

    [If applicable, always include if unsure.]

    #### Link to octoprint.log

    [On gist.github.com or pastebin.com. Always include and never truncate.]

    #### Link to contents of terminal tab or serial.log

    [On gist.github.com or pastebin.com. If applicable, always include if unsure or
    reporting communication issues. Never truncate.]

    #### Link to contents of Javascript console in the browser

    [On gist.github.com or pastebin.com or alternatively a screenshot. If applicable -
    always include if unsure or reporting UI issues.]

    #### Screenshot(s) showing the problem:

    [If applicable. Always include if unsure or reporting UI issues.]

    I have read the FAQ.

Copy-paste this template **completely**. Do not skip any lines!

### Where can I find which version and branch I'm on?

You can find out all of them by taking a look into the lower left corner of the
OctoPrint UI:

![Current version and git branch info in OctoPrint's UI](http://i.imgur.com/HyHMlY2.png)

If you don't have access to the UI you can find out that information via the
command line as well. Either `octoprint --version` or `python setup.py version`
in OctoPrint's folder will tell you the version of OctoPrint you are running
(note: if it doesn't then you are running a version older than 1.1.0,
*upgrade now*). A `git branch` in your OctoPrint installation folder will mark
the branch you are on with a little *. `git rev-parse HEAD` will tell you the
current commit.

### Where can I find those log files you keep talking about?

OctoPrint by default provides two log outputs, a third one can be enabled if
more information is needed.

One is contained in the **"Terminal" tab** within OctoPrint's UI and is a log
of the last 300 lines of communication with the printer. Please copy-paste
this somewhere (disable auto scroll to make copying the contents easier) -
e.g. http://pastebin.com or http://gist.github.com - and include a link in
your bug report.

There is also **OctoPrint's application log file** or in short `octoprint.log`,
which is by default located at `~/.octoprint/logs/octoprint.log` on Linux,
`%APPDATA%\OctoPrint\logs\octoprint.log` on Windows and
`~/Library/Application Support/OctoPrint/logs/octoprint.log` on MacOS. Please
copy-paste this to pastebin or gist as well and include a link in your bug
report.

It might happen that you are asked to provide a more **thorough log of the
communication with the printer** if you haven't already done so, the `serial.log`.
This is not written by default due to performance reasons, but you can enable
it in the settings dialog. After enabling that log, please reproduce the problem
again (connect to the printer, do whatever triggers it), then copy-paste
`~/.octoprint/logs/serial.log` (Windows: `%APPDATA%\OctoPrint\logs\serial.log`,
MacOS: `~/Library/Application Support/OctoPrint/logs/serial.log`) to pastebin
or gist and include the link in the bug report.

You might also be asked to provide a log with an increased log level. You can
find information on how to do just that in the
[docs](http://docs.octoprint.org/en/master/configuration/logging_yaml.html).

### Where can I find my browser's error console?

See [How to open the Javascript Console in different browsers](https://webmasters.stackexchange.com/questions/8525/how-to-open-the-javascript-console-in-different-browsers)

## Pull requests

1. If you want to add a new feature to OctoPrint, **please always first
   consider if it wouldn't be better suited for a plugin.** As a general rule
   of thumb, any feature that is only of interest to a small sub group should
   be moved into a plugin. If the current plugin system doesn't allow you to
   implement your feature as a plugin, create a "Brainstorming" ticket to get
   the discussion going on how best to solve *this* in OctoPrint's plugin
   system - maybe that's the actual PR you have been waiting for to contribute :)
2. If you plan to make **any large or otherwise disruptive changes to the
   code or appearance, please open a "Brainstorming" ticket first** so
   that we can determine if it's a good time for your specific pull
   request. It might be that we're currently in the process of making
   heavy changes to the code locations you'd target as well, or your
   approach doesn't fit the general "project vision", and that would
   just cause unnecessary work and frustration for everyone or
   possibly get the PR rejected.
3. Create your pull request **from a custom branch** on your end (e.g.
   `dev/myNewFeature`)[1] **against the `devel` branch**. Create **one pull request
   per feature/bug fix**. If your PR contains an important bug fix, we will
   make sure to backport it to the `maintenance` branch to also include it in
   the next release.
4. Make sure there are **only relevant changes** included in your PR. No
   changes to unrelated files, no additional files that don't belong (e.g.
   commits of your full virtual environment). Make sure your PR consists
   **ideally of only one commit** (use git's rebase and squash functionality).
5. Make sure you **follow the current coding style**. This means:
     * Tabs instead of spaces in the Python files[2]
     * Spaces instead of tabs in the Javascript sources
     * English language (code, variables, comments, ...)
     * Comments where necessary: Tell *why* the code does something like it does
       it, structure your code
     * Following the general architecture
     * If your PR needs to make changes to the Stylesheets, change the
       ``.less`` files from which the CSS is compiled.
     * Make sure you do not add dead code (e.g. commented out left-overs
       from experiments).
6. Ensure your changes **pass the existing unit tests**. PRs that break
   those cannot be accepted.
7. **Test your changes thoroughly**. That also means testing with usage
   scenarios you don't normally use, e.g. if you only use access control, test
   without and vice versa. If you only test with your printer, test with the
   virtual printer and vice versa. State in your pull request how your tested
   your changes. Ideally **add unit tests** - OctoPrint severly lacks in that
   department, but we are trying to change that, so any new code already covered
   with a test suite helps a lot!
8. In your pull request's description, **state what your pull request does**,
   as in, what feature does it implement, what bug does it fix. The more
   thoroughly you explain your intent behind the PR here, the higher the
   chances it will get merged fast. There is a template provided below
   that can help you here.
9. Don't forget to **add yourself to the [AUTHORS](./AUTHORS.md)
   file** :)

Template to use for Pull Request descriptions:

```
#### What does this PR do and why is it necessary?

#### How was it tested? How can it be tested by the reviewer?

#### Any background context you want to provide?

#### What are the relevant tickets if any?

#### Screenshots (if appropriate)

#### Further notes
```

## What do the branches mean?

There are three main branches in OctoPrint:

  * `master`: The master branch always contains the current stable release. It
    is *only* updated on new releases. Will have a version number following
    the scheme `x.y.z` (e.g. `1.2.9`) or - if it's absolutely necessary to
    add a commit after release to this branch - `x.y.z.post<commits since x.y.z>`
    (e.g. `1.2.9.post1`).
  * `maintenance`: Improvements and fixes of the current release that make up
    the next release go here. More or less continously updated. You can consider
    this a preview of the next release version. It should be very stable at all
    times. Anything you spot in here helps tremendously with getting a rock solid
    next stable release, so if you want to help out development, running the
    `maintenance` branch and reporting back anything you find is a very good way
    to do that. Will usually have a version number following the scheme
    `x.y.z+1.dev.<commits since increase of z>` for an OctoPrint version of `x.y.z`
    (e.g. `1.2.10.dev12`).
  * `devel`: Ongoing development of new features that will go into the next bigger
    release (MINOR version number increases) will happen on this branch. Usually
    kept stable, sometimes stuff can break though or lose backwards compatibility
    temporarily. Can be considered the "bleeding edge". All PRs should target
    *this* branch. Important improvements and fixes from PRs here are backported to
    `maintenance` as needed. Will usually have a version number following the
    scheme `x.y+1.0.dev<commits since increase of y>` for an OctoPrint version
    of `x.y.z` (e.g. `1.3.0.dev123`).

Additionally, from time to time you might see other branches pop up in the repository.
Those usually have one of the following prefixes:

  * `fix/...`: Fixes under development that are to be merged into the `maintenance`
    and `devel` branches.
  * `improve/...`: Improvements under development that are to be merged into the
    `maintenance` and `devel` branches.
  * `dev/...` or `feature/...`: New functionality under development that is to be merged
    into the `devel` branch.

There is also the `gh-pages` branch, which holds OctoPrint's web page, and a couple of
older development branches that are slowly being migrated or deleted.

## How OctoPrint is versioned

OctoPrint follows the [semantic versioning scheme](http://semver.org/) of **MAJOR.MINOR.PATCH**.

The **PATCH** version number is the one increasing most often due to OctoPrint's maintenance releases.
Releases that only change the patch number indicate that they contain bug fixes and small improvements
of existing functionality. Example: 1.2.8 to 1.2.9.

The **MINOR** version number increases with releases that add a lot of new functionality and
large features. Example: 1.2.x to 1.3.0.

Finally, the **MAJOR** version number increases if there are breaking API changes that concern any of the
documented interfaces (REST API, plugin interfaces, ...). So far this hasn't happened. Example: 1.x.y to 2.0.0.

OctoPrint's version numbers are automatically generated using [versioneer](https://github.com/warner/python-versioneer)
and depend on the selected git branch, nearest git tag and commits. The generated version number
should always be [PEP440](https://www.python.org/dev/peps/pep-0440/) compatible. Unless a git tag
is used for version number determination, the version number will also contain the git hash within
the local version identifier to allow for an exact determination of the active code base
(e.g. `1.2.9.dev68+g46c7a9c`). Additionally, instances with active uncommitted changes will contain
`.dirty` in the local version identifier.

## History

  * 2015-01-23: More guidelines for creating pull requests, support/questions
    redirected to Mailinglist/G+ community
  * 2015-01-27: Added another explicit link to the FAQ
  * 2015-07-07: Added step to add yourself to AUTHORS when creating a PR :)
  * 2015-12-01: Heavily reworked to include examples, better structure and
    all information in one document.
  * 2016-02-10: Added information about branch structure and versioning.
  * 2016-02-16: Added requirement to add information from template to existing
    tickets as well, explained issue with "me too" red herrings.
  * 2016-03-14: Some more requirements for PRs, and a PR template.

## Footnotes
  * [1] - If you are wondering why, the problem is that anything that you add
    to your PR's branch will also become part of your PR, so if you create a
    PR from your version of `devel` chances are high you'll add changes to the
    PR that do not belong to the PR.
  * [2] - Yes, we know that this goes against PEP-8. OctoPrint started out as
    a fork of Cura and hence stuck to the coding style found therein. Changing
    it now would make the history and especially `git blame` completely
    unusable, so for now we'll have to deal with it (this decision might be
    revisited in the future).
