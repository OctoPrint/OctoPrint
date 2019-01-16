# OctoPrint Changelog

## 1.3.10 (2018-12-10)

### Heads-up for plugin authors regarding the `sarge` dependency

OctoPrint has updated its `sarge` dependency. The new version 0.1.5 has a small breaking change - the `async` keyword 
was renamed to `async_` for compatibility reasons with Python 3.7. This might also affect your plugin if you happen to 
use `sarge` somewhere therein. OctoPrint has a workaround for this in place so your plugin will continue to function for
now. However, you should look into updating it to use `async_` instead of `async` if running against OctoPrint 1.3.10+.

See also [here](https://sarge.readthedocs.io/en/latest/overview.html#id1) for the `sarge` changelog.

### Improvements

  * [#1504](https://github.com/foosel/OctoPrint/issues/1504) - Added detection of `EMERGENCY_PARSER` firmware capability and if it's present add `M108` to the cancel procedure, to cancel blocking heatups.
  * [#2674](https://github.com/foosel/OctoPrint/issues/2674) - Improved error handling when the file OctoPrint is currently printing from becomes unreadable.
  * [#2698](https://github.com/foosel/OctoPrint/pull/2698) - Made favicon color match custom theme color.
  * [#2717](https://github.com/foosel/OctoPrint/pull/2717) - Various speed ups of the GCODE viewer.
  * [#2723](https://github.com/foosel/OctoPrint/pull/2723) - Always allow the file analysis to run, even if the slicer does provide analysis data. Allows plugins implementing the analysis hook to override behaviour in all cases.
  * [#2729](https://github.com/foosel/OctoPrint/issues/2729) - Allow additional video formats to appear in the timelapse tab.
  * [#2730](https://github.com/foosel/OctoPrint/pull/2730) & [#2739](https://github.com/foosel/OctoPrint/pull/2739) & [#2742](https://github.com/foosel/OctoPrint/pull/2742) - Improved GCODE analysis speed.
  * [#2740](https://github.com/foosel/OctoPrint/issues/2740) & [#2859](https://github.com/foosel/OctoPrint/issues/2859) - Make the connection panel reflect the current connection parameters.
  * [#2769](https://github.com/foosel/OctoPrint/issues/2769) - Cura Plugin: Improve error handling a profile import fails.
  * [#2802](https://github.com/foosel/OctoPrint/pull/2802) - Updated the temperature filters to ignore more sent and received lines belonging to temperature requests/responses that so far weren't covered.
  * [#2806](https://github.com/foosel/OctoPrint/pull/2806) - Refactored some unit tests.
  * [#2827](https://github.com/foosel/OctoPrint/pull/2827) - Spelling fixes in the documentation.
  * [#2839](https://github.com/foosel/OctoPrint/issues/2839) - Recognize position reports that include a space after the axis, as e.g. observed in the firmware of AlfaWise U20
  * [#2854](https://github.com/foosel/OctoPrint/issues/2854) - Auto detect Teacup firmware.
  * [#2865](https://github.com/foosel/OctoPrint/pull/2865) - Added `speed` parameter to `extrude` command on the `/api/printer/tool` API endpoint which allows to set the feedrate to use for the extrude per request.
  * Improve SD print detection
  * Added the Anonymous Usage Tracking Plugin. Tracking will only take place if the plugin is enabled and you’ve decided to opt-in during initial setup (or enabled it manually afterwards, through the corresponding switch in the settings). The tracking data will give insight into how OctoPrint is used, which versions are running and on what kind of hardware OctoPrint gets installed. You can learn about what will get tracked (if you opt-in) on [tracking.octoprint.org](https://tracking.octoprint.org). Please consider helping development by participating in the anonymous usage tracking. 
  * The OctoPi Support Plugin is now the Pi Support Plugin:
    * Always enabled when running on a Raspberry Pi, regardless of whether OctoPi is used or not.
    * Now detects undervoltage/overheat issues and displays an alert on the UI if such an issue is found.
    * Changed detection method of the Raspberry Pi Model to something a bit more future proof.
  * Added the Application Keys Plugin: The new bundled plugin offers an authorization for third party apps that doesn't involve manually copying API keys or using QR codes. Third party client developers are strongly advised to implement this workflow in their apps. Read more [in the documentation](http://docs.octoprint.org/en/maintenance/bundledplugins/appkeys.html).
  * Added the Backup & Restore Plugin: The new bundled plugin will allow you to make a backup of your OctoPrint settings, files and list of installed plugins, and to restore from such a backup on the
    same or another instance. This should make migration paths from outdated installations to newer ones easier.
  * Software Update Plugin: Automatic updates in outdated environments are no longer supported. After repeated issues out in the fields with ancient installations and ancient underlying Python environments, OctoPrint will no longer allow automatic updates of itself or plugins via the Software Update Plugin if a certain set of minimum versions of Python, `pip` and `setuptools` isn't detected. The current minimum versions reflect the environment found on OctoPi 0.14.0: Python 2.7.9, pip 9.0.1, setuptools 5.5.1. See also the [related FAQ entry](https://faq.octoprint.org/unsupported-python-environment).
  * OctoPrint will now longer allow itself to be installed on Python versions less than 2.7.3 or higher than 2.7.x, to avoid peope running into issues in unsupported environments.
  * Protect/educate against the dangers of opening up OctoPrint on the public internet:
    * Detect connections to the UI from external IPs and display a warning in such cases.
    * Added explicit warning to the first run wizard.
    * Added explicit warning to the documentation.
    * Added the ForcedLogin Plugin: Disables anonymous read-only access. To get back the old behaviour you'll have to explicitely disable this plugin.
  * Removed printed/visited layer counts from the GCODE viewer since it was confusing people more than helping them.
  * Added a warning to the documentation re expensive code in gcode hooks.  
  * Added the `no_firstrun_access` decorator.
  * Only disable autoscroll in the terminal when scrolling up, not when scrolling down.
  * Added a new asset type `clientjs` for JS client library components.
  * Added new options for the `showConfirmationDialog` UI helper:
    * `oncancel`: callback to call when the cancel button is pressed
    * `noclose`: don't allow dismissing/closing the dialog without having chosen to proceed or cancel.
  * Allow further access restrictions on API and Tornado routes by third party plugins.
  * Support using the JS client library with an unset API key.
  * Added documentation for `octoprint.util.commandline` module
  * More resilience against third party plugins that happily block or kill important startup threads
  * Improved backwards compatibility of the `sarge` dependency by monkey patching it to support the old `async` keyword parameter. Plugin authors are still advised to switch to the new `async_` parameter if running against `sarge>=0.1.5`, unmodified plugins should continue to work now however. For reference, OctoPrint 1.3.10 requires `sarge==0.1.5post0`.
  * Better detection of ipv6 support by the underlying OS.
  * Updated several dependencies to current versions where possible.
  * Announcements Plugin: Add documentation.
  * Anonymous Usage Tracking: Added elapsed time & reason of print failure to tracking (to be able to distinguish cancelled from errored out prints)
  * Anonymous Usage Tracking: Added undervoltage/overheat detection on Pis to tracking (to correlate print failures to power issues, see also [#2878](https://github.com/foosel/OctoPrint/pull/2878)).
  * Backup: Exclude `generated`, `logs` and `watched` folders from backup
  * Backup: Use base version for version check on restore
  * Pi Support plugin: Better wording on the "undervoltage & overheat" popover & added a link to the FAQ entry
  * Printer Safety Plugin: Added Ender 3 stock firmware, Micro3D stock firmware and iME firmware to detection

### Bug fixes

  * [#2629](https://github.com/foosel/OctoPrint/issues/2629) - Cura Plugin: Fixed wrong gcode snippet being used when slicing against a printer profile with multiple extruders.
  * [#2696](https://github.com/foosel/OctoPrint/pull/2696) - Fixed a comment.
  * [#2697](https://github.com/foosel/OctoPrint/pull/2697) - Fixed documentation regarding unit of `estimatedPrintTime` field in the analysis result.
  * [#2705](https://github.com/foosel/OctoPrint/issues/2705) - Fixed internal server error on GET request for files on the printer's SD card.
  * [#2706](https://github.com/foosel/OctoPrint/issues/2706) - Fixed a documentation error regarding HTTP status code returned on invalid API key
  * [#2712](https://github.com/foosel/OctoPrint/issues/2712) - Fixed updating via commandline (`octoprint plugins softwareupdate:update`).
  * [#2749](https://github.com/foosel/OctoPrint/issues/2749) - Fixed empty API key being treated as anonymous API key.
  * [#2752](https://github.com/foosel/OctoPrint/issues/2752) - Only reset timeout to shorter "busy" timeout once the busy configuration command has been sent to the printer.
  * [#2772](https://github.com/foosel/OctoPrint/issues/2772) & [#2764](https://github.com/foosel/OctoPrint/issues/2764) - Stop sending commands to the printer if a fatal error is reported that results in a `kill()`, even if OctoPrint is configured to keep the connection going on firmware errors.
  * [#2774](https://github.com/foosel/OctoPrint/issues/2774) - Fixed autoscroll in the terminal stopping when switching browser windows or tabs.
  * [#2780](https://github.com/foosel/OctoPrint/issues/2780) - Fixed error when trying to save timeout settings.
  * [#2800](https://github.com/foosel/OctoPrint/pull/2800) - Fixed a conjugation error in the documentation.
  * [#2805](https://github.com/foosel/OctoPrint/issues/2805) - Fixed duplicated method name in a unit test.
  * [#2846](https://github.com/foosel/OctoPrint/issues/2846) - Removed requirement to have `messages.pot` exist to use `babel_extract` for translating plugins (see also [#2846](https://github.com/foosel/OctoPrint/pull/2847)).
  * [#2850](https://github.com/foosel/OctoPrint/issues/2850) - Fixed a race condition in the web socket causing the push connection to fail (see also [#2858](https://github.com/foosel/OctoPrint/pull/2858)).
  * [#2852](https://github.com/foosel/OctoPrint/issues/2852) - Fixed issue with zeroconf announcement failing for the second instance of OctoPrint on the same Linux host due to a name conflict.
  * [#2872](https://github.com/foosel/OctoPrint/issues/2872) (regression) - Fix Timeout when connecting to printer that doesn't send `start` on connect
  * [#2873](https://github.com/foosel/OctoPrint/issues/2873) (regression) - Fix GCODE viewer no longer being able to load files.
  * [#2876](https://github.com/foosel/OctoPrint/issues/2876) (regression) - Fix semi functional UI when access control is disabled
  * [#2879](https://github.com/foosel/OctoPrint/issues/2879) (regression) - Fix favicon in Firefox
  * [#2897](https://github.com/foosel/OctoPrint/issues/2897) (regression) - Improved error resilience of `is_lan_address` so an error during its execution no longer nukes requests
  * [#2898](https://github.com/foosel/OctoPrint/issues/2898) (regression) - ForceLogin plugin no longer interferes with websocket messages sent by plugins right on UI load but instead puts them into a (limited) backlog and then sends them out in received order once the user has authenticated on the socket.
  * [#2903](https://github.com/foosel/OctoPrint/issues/2903) - Backup plugin: Support for ZIP64 extensions for large zip files
  * [#2903](https://github.com/foosel/OctoPrint/issues/2903) - Backup plugin: Better error reporting
  * [#2908](https://github.com/foosel/OctoPrint/issues/2908) (regression) - Tracking: Use the file's `path` instead of just the `name` for file name hashing.
  * [#2920](https://github.com/foosel/OctoPrint/issues/2920) - Backup plugin: Fix wrong compatibility check logic in plugin install during restore
  * Fixed an issue with collision free SD name detection.
  * Fixed some JS warnings in the GCODE viewer.
  * Fixed wrongly used `.error` instead of the correct `.fail` in the UI's logout handler.
  * Fixed the `disable_hotends` snippet in case of a shared nozzle setup.
  * Logout socket on UI logout
  * Announcements Plugin: Fix an issue with atom feeds.
  * Anonymous Usage Tracking: More error resilience for the wizard to possibly work around issues observed with the first RC (for which sadly no information was provided to reproduce and analyse).
  * Anonymous Usage Tracking: Fixed homepage link in plugin manager
  * Backup: Disable restore on Windows servers where it's not supported thanks to the Windows file system
  * Backup: Fix reporting of restore failure due to version mismatch or other cases of an invalid backup
  * Backup: Fix feedback in UI during restore, start feedback right on upload of backup
  * Printer Safety: Fix localization of warning message
  * Software Update Plugin: Fixed the update button being visible although the update is impossible.
  * Software Update Plugin: More resilience against invalid data in config
  * Software Update Plugin: Fixed version output of CLI update message

### Special thanks to all the contributors!

Special thanks to everyone who contributed to this release candidate, especially [@BillyBlaze](https://github.com/BillyBlaze), 
[@bradcfisher](https://github.com/bradcfisher), [@eyal0](https://github.com/eyal0), [@fieldOfView](https://github.com/fieldOfView), 
[@gdombiak](https://github.com/gdombiak), [@gerfderp](https://github.com/gerfderp), [@hashashin](https://github.com/hashashin) 
and [@tedder](https://github.com/tedder) for their PRs.

### More information

  * [Commits](https://github.com/foosel/OctoPrint/compare/1.3.9...1.3.10)
  * Release Candidates:
    * [1.3.10rc1](https://github.com/foosel/OctoPrint/releases/tag/1.3.10rc1)
    * [1.3.10rc2](https://github.com/foosel/OctoPrint/releases/tag/1.3.10rc2)
    * [1.3.10rc3](https://github.com/foosel/OctoPrint/releases/tag/1.3.10rc3)
    * [1.3.10rc4](https://github.com/foosel/OctoPrint/releases/tag/1.3.10rc4)
    * A big **Thank you!** to everyone who reported back on these release candidates this time: [@andrivet](https://github.com/andrivet), [@arminth](https://github.com/arminth), [@autonumous](https://github.com/autonumous), [@benlye](https://github.com/benlye), [@BillyBlaze](https://github.com/BillyBlaze), [@bradcfisher](https://github.com/bradcfisher), [@Charly333](https://github.com/Charly333), [@ChrisHeerschap](https://github.com/ChrisHeerschap), [@Crowlord](https://github.com/Crowlord), [@ctgreybeard](https://github.com/ctgreybeard), [@devildant](https://github.com/devildant), [@dimkin-eu](https://github.com/dimkin-eu), [@DominikPalo](https://github.com/DominikPalo), [@duncanlovett](https://github.com/duncanlovett), [@EddyMI3d](https://github.com/EddyMI3d), [@FanDjango](https://github.com/FanDjango), [@FormerLurker](https://github.com/FormerLurker), [@gdombiak](https://github.com/gdombiak), [@GhostlyCrowd](https://github.com/GhostlyCrowd), [@goeland86](https://github.com/goeland86), [@Goodeid](https://github.com/Goodeid), [@hamster65](https://github.com/hamster65), [@hashashin](https://github.com/hashashin), [@jenilliii](https://github.com/jenilliii), [@JohnOCFII](https://github.com/JohnOCFII), [@kmanley57](https://github.com/kmanley57), [@louispires](https://github.com/louispires), [@markuskruse](https://github.com/markuskruse), [@Nervemanna](https://github.com/Nervemanna), [@nionio6915](https://github.com/nionio6915), [@ntoff](https://github.com/ntoff), [@paukstelis](https://github.com/paukstelis), [@racenviper](https://github.com/racenviper), [@ramsesiden](https://github.com/ramsesiden), [@rtbon](https://github.com/rtbon), [@skohls](https://github.com/skohls), [@stough](https://github.com/stough), [@tech-rat](https://github.com/tech-rat), [@tedder](https://github.com/tedder), [@ThaliaFromPrussia](https://github.com/ThaliaFromPrussia), [@thisiskeithb](https://github.com/thisiskeithb), [@trendelkamp](https://github.com/trendelkamp), [@truglodite](https://github.com/truglodite), [@tteckenburg](https://github.com/tteckenburg), [@varazir](https://github.com/varazir), [@Webstas](https://github.com/Webstas) and [@zeroflow](https://github.com/zeroflow)

## 1.3.9 (2018-07-25)

### Still running OctoPrint 1.3.6? Heads-up!

OctoPrint 1.3.9 includes a couple of dependency updates whose update during switch to 1.3.9 are known to trigger an "update failed" message within OctoPrint's update dialog:

```

[...]
OSError: [Errno 2] No such file or directory: '/home/pi/oprint/local/lib/python2.7/site-packages/python_dateutil-2.6.0-py2.7.egg'
Successfully installed OctoPrint-1.3.9rc4 backports-abc-0.5 frozendict-1.2 markdown-2.6.11 pkginfo-1.4.2 pyserial-3.4 python-dateutil-2.6.1 singledispatch-3.4.0.3 tornado-4.5.3
The update did not finish successfully. Please consult the log for details.

``` 

The update did in fact succeed and the issue lies with a change in the underlying update mechanism concerning the dependencies. This problem has been fixed in 1.3.7/1.3.8 and versions prior to 1.3.6 aren't yet affected, so there you won't ever see this message there. If you are still running 1.3.6 though and updating from it, **simply run the update a second time through Settings > Software Update > Check for updates and clicking "Update now" in the reshown update notification**.

### Running NGINX as reverse proxy? Be sure to configure HTTP protocol version 1.1!

OctoPrint 1.3.9 updates the internal webserver Tornado from 4.0.2 to 4.5.3. Among many many fixes and improvements this also includes a change (actually a fix) in the websocket implementation that requires you to tell your NGINX to use HTTP 1.1 instead of the default 1.0 to talk to OctoPrint. You can do this by simply adding 

```
proxy_http_version 1.1;
```

to the `location` config. The [configuration examples](https://discourse.octoprint.org/t/reverse-proxy-configuration-examples/1107) have been adjusted accordingly. See also [#2526](https://github.com/foosel/OctoPrint/issues/2526).

### Disabled IPv6 and now there are issues with the server after the update? Bind to IPv4 addresses only!

Starting with this release OctoPrint natively supports IPv6 and will attempt to bind to such addresses if it detects support in the underlying OS. If for whatever reason your OS doesn't support IPv6 even though Python's `socket` says otherwise, you can tell OctoPrint to bind to an IPv4 address only either via the `--host` command line parameter or `server.host` in `config.yaml`. Use `127.0.0.1` for localhost only, `0.0.0.0` for all IPv4 addresses or whatever specific IPv4 address you want to bind to.

### Plugin author and still dependent on the legacy plugin bundling flag? Fix your plugin!

As [announced with the release of OctoPrint 1.3.6](https://octoprint.org/blog/2017/12/12/new-release-1.3.6/), the legacy plugin bundling flag has now been removed again. [Make sure to check and if necessary fix your plugins](https://octoprint.org/blog/2017/12/01/heads-up-plugin-authors/) if you haven't done that so far!

### Improvements

  * [#652](https://github.com/foosel/OctoPrint/issues/652) & [#1545](https://github.com/foosel/OctoPrint/issues/1545) - Added name of user who started a job to job info (see also [#2576](https://github.com/foosel/OctoPrint/pull/2576)).
  * [#1203](https://github.com/foosel/OctoPrint/issues/1203) & [#1905](https://github.com/foosel/OctoPrint/issues/1905) & [#1797](https://github.com/foosel/OctoPrint/issues/1797) & [#2514](https://github.com/foosel/OctoPrint/issues/2514) - Added support for plugins to override GCODE analysis provider and live print time estimation with their own implementations through two new hooks [`octoprint.filemanager.analysis.factory`](http://docs.octoprint.org/en/maintenance/plugins/hooks.html#octoprint-filemanager-analysis-factory) and [`octoprint.printer.estimation.factory`](http://docs.octoprint.org/en/maintenance/plugins/hooks.html#octoprint-printer-estimation-factory). 
  * [#1217](https://github.com/foosel/OctoPrint/issues/1217) - Software Update Plugin: Block the UI in general when an update is in progress (even in browser windows that didn't start it and logged in as user) so that no prints can be accidentally started during that.
  * [#1513](https://github.com/foosel/OctoPrint/issues/1513) - Option to allow sending `M0`/`M1` to the printer instead of swallowing it.
  * [#2318](https://github.com/foosel/OctoPrint/issues/2318) - Gcode Viewer: Visualize "current" print head location with a marker.
  * [#2351](https://github.com/foosel/OctoPrint/issues/2351) - Support for binding to IPv6 addresses. OctoPrint will now default to binding to `::` if IPv6 support is detected, and to `0.0.0.0` if not. Both the intermediary server  and Tornado are instructed to bind their sockets to both IP versions. Positive IPv6 support detection relies on
    * `socket.has_ipv6` being `True`
    * `socket.IPPROTO_IPV6` and `socket.IPV6_V6ONLY` being available (or redefined in case of Windows) in order to ensure dual stack binding for the intermediary server)
  * [#2379](https://github.com/foosel/OctoPrint/issues/2379) - File and plugin list now use the browser's native scrollbar instead of slimscroll. Slimscroll is still bundled though, in case third party plugins might depend on it.
  * [#2487](https://github.com/foosel/OctoPrint/issues/2487) - Improved documentation of system command configuration (see also [#2498](https://github.com/foosel/OctoPrint/pull/2498)).
  * [#2495](https://github.com/foosel/OctoPrint/pull/2495) - Removed unneeded filter from a template.
  * [#2498](https://github.com/foosel/OctoPrint/pull/2498) - Improved documentation of the `async` flags of custom system commands.
  * [#2512](https://github.com/foosel/OctoPrint/issues/2512) - Log files will now contain client IP as provided by first entry in X-Forwarded-For header (or more if `server.reverseProxy.trustDownstream` is configured accordingly).
  * [#2518](https://github.com/foosel/OctoPrint/issues/2518) - Display absolute file upload date and time on hover (see also [#2630](https://github.com/foosel/OctoPrint/pull/2630)).
  * [#2522](https://github.com/foosel/OctoPrint/issues/2522) - Perform logging to disk asynchronously to avoid slow downs caused by it.
  * [#2541](https://github.com/foosel/OctoPrint/pull/2541) - Added link to instructions to reset passwords. Part of solving [#1239](https://github.com/foosel/OctoPrint/issues/1239).
  * [#2543](https://github.com/foosel/OctoPrint/pull/2543) - Added `--no-cache-dir` to pip calls to work around `MemoryErrors`. See also [#2535](https://github.com/foosel/OctoPrint/pull/2535) and [pypa/pip#2984](https://github.com/pypa/pip/issues/2984) for more details.
  * [#2558](https://github.com/foosel/OctoPrint/issues/2558) - Have the watched folder processor ignore hidden files.
  * [#2572](https://github.com/foosel/OctoPrint/issues/2572) - More error resilience in `ItemListHelper` against empty child elements.
  * [#2573](https://github.com/foosel/OctoPrint/pull/2573) - Added `M118` to commands to never automatically upper case.
  * [#2583](https://github.com/foosel/OctoPrint/issues/2583) - Handle scripts that are part of a job like other lines coming from a job and thus allow them to be kept back using `job_on_hold`.
  * [#2597](https://github.com/foosel/OctoPrint/issues/2597) - Disabled animation on cancel print confirmation.
  * [#2463](https://github.com/foosel/OctoPrint/issues/2463) - Added documentation for `printingarea` and `dimensions` in `gcodeAnalysis` data model (see also [#2540](https://github.com/foosel/OctoPrint/pull/2540)).
  * [#2615](https://github.com/foosel/OctoPrint/issues/2615) - Allowed more granular control over components to be upgraded through the software update plugin in its settings dialog.
  * [#2620](https://github.com/foosel/OctoPrint/pull/2620) - Save `ItemListHelper` page sizes to local storage.
  * [#2642](https://github.com/foosel/OctoPrint/pull/2642) - Added methods for adding and updating items to `ItemListHelper`.
  * [#2644](https://github.com/foosel/OctoPrint/issues/2644) - Detect broken symlinks in configured folders on startup (see also further below).
  * [#2648](https://github.com/foosel/OctoPrint/pull/2648) - Allowed class methods as callbacks in view models.
  * A new API endpoint [`/api/settings/templates`](http://docs.octoprint.org/en/maintenance/api/settings.html#fetch-template-data) allows (admin only) access to information regarding the loaded templates and their order in the UI. That should allow plugins wishing to offer modification of ordering of tabs, sidebar components and so on to retrieve the data they need for that.
  * Have the watched folder processor handle vanished files gracefully.
  * Removed [`legacyPluginAssets` flag](https://octoprint.org/blog/2017/12/01/heads-up-plugin-authors/).
  * Improved requirement detection in `octoprint_setuptools`, added unit tests for that.
  * Bundled `sockjs-tornado` dependency. It hasn't been updated by the author in a while although there exist a number of issues plus patches for them, so we now vendor it.
  * Disabled position logging on cancel by default. If you need this, please explicitly enable it, it is causing too many issues in the field with misbehaving firmware.
  * Extended URL test API to allow whitelist/blacklist check for the returned content type, used that to verify that the webcam snapshot URL actually returns images.
  * Added timeout for position logging on pause/cancel. This should work around firmware which doesn't provide a proper `M114` resport that might be unparseable so we won't get stuck in those cases.
  * Migrated file storage metadata to json instead of YAML since it performs way way better.
  * Added `missing linenumber` to recognized non-fatal error messages.
  * Got rid of some Python 2 only code.
  * Added sanity checks for configured folders (see also [#2644](https://github.com/foosel/OctoPrint/issues/2644)):
    * on startup: check they are writable, if not revert to defaults
    * on settings save: check they are writable, if not return an HTTP 400
    * in the settings dialog: allow quick check of writability via test buttons
  * Never send referrers with links
  * Confirmation dialog helper now supports an HTML body.
  * Sort serial ports naturally (e.g. `tty1`, `tty2`, ..., `tty10` instead of `tty1`, `tty10`, ...)
  * Added `paused` and `resumed` action commands, [see here for details](http://docs.octoprint.org/en/maintenance/features/action_commands.html).
  * Added two new hooks for firmware information, [`octoprint.comm.firmware.info`](http://docs.octoprint.org/en/maintenance/plugins/hooks.html#octoprint-comm-firmware-info) and [`octoprint.comm.firmware.capabilities`](http://docs.octoprint.org/en/maintenance/plugins/hooks.html#octoprint-comm-firmware-capabilities).
  * Added view model list to `OctoPrint.coreui` UI module.
  * Improved logging of `FatalStartupError`s.
  * Add sanity check for disabled plugin list (see also [#2687 (comment)](https://github.com/foosel/OctoPrint/issues/2687#issuecomment-399797596)).
  * Improve logging of exceptions triggered inside the state update worker (see also [#2715](https://github.com/foosel/OctoPrint/issues/2715)).
  * Workaround for a potential `pip` issue when updating components through the Software Update plugin.
  * Fix resend and timeout handling during an active `job_on_hold`.
  * Updated some dependencies:
    * Tornado to 4.5. Version 5 sadly has issues with web socket handling when access behind `haproxy`. So far no solution has been found, so we stay at 4.5 for now.
    * jQuery to 3.3.1
    * Several other Python dependencies
  * Announcement Plugin: Don't reload all notifications if one is marked as read.
  * Printer Safety Plugin: Added new detected firmwares:
    * Anycubic Mega
    * Malyan M200
    * CR-10S
    * all Repetier firmware versions prior to 0.92
    * any firmware that reports the `THERMAL_PROTECTION` capability as disabled to thermal protection warning (see also [MarlinFirmware/Marlin#10465](https://github.com/MarlinFirmware/Marlin/pull/10465))
  * Software Update Plugin: Default to `force_base = False` for version checks.
  * Virtual Printer Plugin: Allow defining custom `M114` response formats.

### Bug fixes

  * [#2333](https://github.com/foosel/OctoPrint/issues/2333) (Part 3/3) - Updated to PySerial 3.4 and utilize read and write cancelling to work around disconnect delays.
  * [#2355](https://github.com/foosel/OctoPrint/issues/2355) - Fixed non deterministic sorting of files with missing fields (e.g. date for SD card files) in OctoPrint's frontend.
  * [#2496](https://github.com/foosel/OctoPrint/issues/2496) - Fixed files API not allowing to walk through the directory tree unless fetching the full listing recursively by making sure that first level children nodes are always provided. 
  * [#2502](https://github.com/foosel/OctoPrint/pull/2502) - Fixed some invalid HTML
  * [#2504](https://github.com/foosel/OctoPrint/pull/2504) & [#2532](https://github.com/foosel/OctoPrint/pull/2532) & [#2552](https://github.com/foosel/OctoPrint/pull/2552) - Fixed various typos
  * [#2505](https://github.com/foosel/OctoPrint/issues/2505) - Fixed user switch to `_api` user on use of the global API key inside the browser.
  * [#2509](https://github.com/foosel/OctoPrint/issues/2509) - Properly handle a printer reset while printing and don't get stuck in "Cancelling" state
  * [#2517](https://github.com/foosel/OctoPrint/issues/2517) - Fixed baudrate negotiation with printers that need a bit of a delay between connection establishment and probing (e.g. Prusa MK3).
  * [#2520](https://github.com/foosel/OctoPrint/issues/2520) - Fixed temperature presets being saved as strings  instead of numbers.
  * [#2533](https://github.com/foosel/OctoPrint/pull/2533) - Fixed API key copy button being enabled and generate button being disabled when no API key is set.
  * [#2534](https://github.com/foosel/OctoPrint/issues/2534) - Fixed stale data in API key/user editor. See also [#2604](https://github.com/foosel/OctoPrint/pull/2604).
  * [#2539](https://github.com/foosel/OctoPrint/issues/2539) - Made serial and baud rate lists consistent between connection panel and settings (see also [#2606](https://github.com/foosel/OctoPrint/pull/2606)).
  * [#2547](https://github.com/foosel/OctoPrint/issues/2547) - Fixed `PrintFailed` being triggered in case of an error while processing the `afterPrintJobDone` GCODE script through introduction of `Resuming` and `Finishing` states.
  * [#2549](https://github.com/foosel/OctoPrint/issues/2549) - Fixed "uninstall plugin" icon in Plugin Manager staying clickable even if disabled.
  * [#2549](https://github.com/foosel/OctoPrint/issues/2549) - Fixed issue with detection uninstallation of disabled plugins (see also [#2650](https://github.com/foosel/OctoPrint/pull/2650)).
  * [#2551](https://github.com/foosel/OctoPrint/issues/2551) - Fixed `0` being allowed for various intervals and timeouts where that values doesn't make sense.
  * [#2554](https://github.com/foosel/OctoPrint/pull/2554) - Fixed a JSON example in the docs.
  * [#2568](https://github.com/foosel/OctoPrint/pull/2568) - Fixed a dead link in the plugin hooks documentation in the docs.
  * [#2579](https://github.com/foosel/OctoPrint/issues/2579) - Fixed print time left of "a couple of seconds" even after the print job has finished.
  * [#2581](https://github.com/foosel/OctoPrint/issues/2581) & [#2587](https://github.com/foosel/OctoPrint/issues/2587) - Fixed OctoPrint getting stuck in "Pausing" or "Cancelling" state due to a race condition.
  * [#2589](https://github.com/foosel/OctoPrint/issues/2589) - Added missing `typePath` field on API response for files on the printer's SD card.
  * [#2591](https://github.com/foosel/OctoPrint/pull/2591) - Fixed markup of some HTML labels.
  * [#2595](https://github.com/foosel/OctoPrint/pull/2595) - Fixed some UI appearance issues.
  * [#2601](https://github.com/foosel/OctoPrint/issues/2601) - Properly handle relative paths for selection via `printer.select_file`.
  * [#2621](https://github.com/foosel/OctoPrint/issues/2621) - Fixed framerate not being read from config for rendering unrendered timelapses.
  * [#2625](https://github.com/foosel/OctoPrint/issues/2625) - Fixed incompatibility of OctoPrint's plugin subsystem with Python wheels, which are the default mode of installing plugins from pip version 10.0.0 onward.
  * [#2632](https://github.com/foosel/OctoPrint/issues/2632) - Fixed race condition in resend handling on missing `ok`s.
  * [#2675](https://github.com/foosel/OctoPrint/issues/2675) - Fixed a possible division by zero on SD upload.
  * [#2677](https://github.com/foosel/OctoPrint/issues/2677) (regression) - Fix a deadlock when `job_on_hold` is utilized (causing issues at least with Octolapse)
  * [#2683](https://github.com/foosel/OctoPrint/pull/2683) - Fixed two missing spaces in the german translation.
  * [#2715](https://github.com/foosel/OctoPrint/issues/2715) (regression) - Fix broken estimator initialization on SD print start and resulting crash of the state update worker.
  * [#2719](https://github.com/foosel/OctoPrint/issues/2719) (regression) - Fix live print time estimation
  * [#2737](https://github.com/foosel/OctoPrint/issues/2737) (regression) - Fix print button being enabled even though no file is selected.
  * [#2738](https://github.com/foosel/OctoPrint/issues/2738) (regression) - Limit the use of the `--no-cache-dir` argument added to `pip` calls to such versions of `pip` that already support it (anything newer than 1.5.6).
  * Properly handle absolute paths for recovery data comparison.
  * Fixed snapshot test button not resetting on error.
  * Fixed decoupling of metadata logs in the file manager.
  * Fixed "remember me" and IPv4/IPv6 sessions. This might also solve [#1881](https://github.com/foosel/OctoPrint/issues/1881).
  * Removed Repetier resend repetition detection and handling code. It was buggy and introducing issues.
  * Fixed script order: `beforePrint*` should always precede any commands from the print job.
  * Only perform write tests on directories where necessary. Especially avoid them on page rendition to prevent misconfigured folders from triggering an HTTP 500. (regression) 

### Special thanks to all the contributors!

Special thanks to everyone who contributed to this release, especially [@benlye](https://github.com/benlye), [@dadosch](https://github.com/dadosch), [@dforsi](https://github.com/dforsi), [@ganey](https://github.com/ganey),[@malnvenshorn](https://github.com/malnvenshorn), [@ntoff](https://github.com/ntoff), [@tedder](https://github.com/tedder) and [@vitormhenrique](https://github.com/vitormhenrique) for their PRs.

### More information

  * [Commits](https://github.com/foosel/OctoPrint/compare/1.3.8...1.3.9)
  * Release Candidates:
    * [1.3.9rc1](https://github.com/foosel/OctoPrint/releases/tag/1.3.9rc1)
    * [1.3.9rc2](https://github.com/foosel/OctoPrint/releases/tag/1.3.9rc2)
    * [1.3.9rc3](https://github.com/foosel/OctoPrint/releases/tag/1.3.9rc3)
    * [1.3.9rc4](https://github.com/foosel/OctoPrint/releases/tag/1.3.9rc4)
    * A big **Thank you!** to everyone who reported back on these release candidates this time:
      [arhi](https://github.com/arhi), [b-morgan](https://github.com/b-morgan), [brandstaetter](https://github.com/brandstaetter), [buchnoun](https://github.com/buchnoun), [CapnBry](https://github.com/CapnBry), [chatrat12](https://github.com/chatrat12), [ChrisHeerschap](https://github.com/ChrisHeerschap), [christianlupus](https://github.com/christianlupus), [chrisWhyTea](https://github.com/chrisWhyTea), [Crowlord](https://github.com/Crowlord), [ctgreybeard](https://github.com/ctgreybeard), [Cyberwizzard](https://github.com/Cyberwizzard), [DrJuJu](https://github.com/DrJuJu), [ejjenkins](https://github.com/ejjenkins), [fieldOfView](https://github.com/fieldOfView), [FormerLurker](https://github.com/FormerLurker), [four-of-four](https://github.com/four-of-four), [Galfinite](https://github.com/Galfinite), [gege2b](https://github.com/gege2b), [HFMan](https://github.com/HFMan), [jjlink](https://github.com/jjlink), [jneilliii](https://github.com/jneilliii), [JohnOCFII](https://github.com/JohnOCFII), [jwg3](https://github.com/jwg3), [kazibole](https://github.com/kazibole), [larp-welt](https://github.com/larp-welt), [McFly99](https://github.com/McFly99), [mod38](https://github.com/mod38), [ntoff](https://github.com/ntoff), [OutsourcedGuru](https://github.com/OutsourcedGuru), [paukstelis](https://github.com/paukstelis), [pingywon](https://github.com/pingywon), [pscrespo](https://github.com/pscrespo), [Rapsey](https://github.com/Rapsey), [tech-rat](https://github.com/tech-rat), [tedder](https://github.com/tedder), [thess](https://github.com/thess), [Thisismydigitalself](https://github.com/Thisismydigitalself), [tibmeister](https://github.com/tibmeister)

## 1.3.8 (2018-04-13)

### Bug fixes

  * [#2577](https://github.com/foosel/OctoPrint/issues/2577) - Pin `psutil` dependency to version 5.4.3 since 5.4.4 as released today introduces a breaking change.

([Commits](https://github.com/foosel/OctoPrint/compare/1.3.7...1.3.8))

## 1.3.7 (2018-04-09)

### Improvements

  * [#324](https://github.com/foosel/OctoPrint/issues/324) & [#2414](https://github.com/foosel/OctoPrint/issues/2414) - Native support for the following [@ commands](http://docs.octoprint.org/en/maintenance/features/atcommands.html): `@pause` (pauses the print), `@resume` (resumes the print), `@cancel` or `@abort` (cancels the print). More commands can be added through the plugin hooks [`octoprint.comm.protocol.atcommand.*`](http://docs.octoprint.org/en/maintenance/plugins/hooks.html#octoprint-comm-protocol-atcommand-phase).
  * [#1951](http://github.com/foosel/OctoPrint/issues/1951) - Fixed plugins being able to modify internal state data (e.g. progress, job), causing concurrent modification and resulting run time errors in the printer state processing.
  * [#2208](https://github.com/foosel/OctoPrint/issues/2208) - New plugin hook [`octoprint.comm.protocol.gcode.error`](http://docs.octoprint.org/en/maintenance/plugins/hooks.html#octoprint-comm-protocol-gcode-error) to allow plugins to override OctoPrint's handling of `Error:`/`!!` messages reported by the firmware. Can be used to "downgrade" errors that aren't actually fatal errors that make the printer halt.
  * [#2213](https://github.com/foosel/OctoPrint/issues/2213) - Made sure to prevent accidental configuration of a temperature cutoff value less than 1min for the temperature graph.
  * [#2250](https://github.com/foosel/OctoPrint/pull/2250) - Added [`octoprint.util.ResettableTimer`](http://docs.octoprint.org/en/maintenance/modules/util.html#octoprint.util.ResettableTimer) helper class.
  * [#2287](https://github.com/foosel/OctoPrint/issues/2287) - Added confirmation for attempting to disconnect during an ongoing print. See also [#2466](https://github.com/foosel/OctoPrint/pull/2466).
  * [#2302](https://github.com/foosel/OctoPrint/issues/2302) - Detect invalid tools as reported by firmware and blacklist them for `T` commands.
  * [#2317](https://github.com/foosel/OctoPrint/issues/2317) - Removed capturing of post roll images for time based timelapses, was causing too much confusion and surprise.
  * [#2335](https://github.com/foosel/OctoPrint/issues/2335) - First throw at detecting if a print from the printer's SD was started outside of OctoPrint via the printer's control panel. Requires some specific requirements to be fulfilled by the printer's firmware to function properly:
      * Firmware must send a "File opened: ..." message on start of the print
      * Firmware must respond to an immediately sent `M27` with `SD printing byte <current>/<total>`
      * Firmware must stay responsive during ongoing print to allow for regular M27 polls (or push those automatically) or M25 to pause/cancel the print through OctoPrint.
      * Firmware must send `Done printing file` or respond to `M27` with `Not SD printing` when SD printing finishes (either due to being done or to having been cancelled by the user).
  * [#2362](https://github.com/foosel/OctoPrint/issues/2362) - Added option to configure timelapse snapshot timeout.
  * [#2367](https://github.com/foosel/OctoPrint/issues/2367) - Added support for `//action:cancel` action command.
  * [#2378](https://github.com/foosel/OctoPrint/issues/2378) - Made GCODE viewer gracefully handle GCODE subcodes.
  * [#2385](https://github.com/foosel/OctoPrint/pull/2385) - Made valid boolean trues check case insensitive.
  * [#2304](https://github.com/foosel/OctoPrint/pull/2304) & [#2405](https://github.com/foosel/OctoPrint/pull/2405) - Added support to trust Basic Authentication headers for user login. Currently requires [manual configuration through `config.yaml`](http://docs.octoprint.org/en/maintenance/configuration/config_yaml.html#access-control), see the `accessControl.trustBasicAuthentication` and `accessControl.checkBasicAuthenticationPassword` settings.
  * [#2338](https://github.com/foosel/OctoPrint/pull/2338) - Allowed plugins to define GCODE script variables using the `octoprint.comm.protocol.scripts` hook.
  * [#2406](https://github.com/foosel/OctoPrint/pull/2406) - Extracted log management into its own bundled plugin and allow fine tuning of log levels.
  * [#2409](https://github.com/foosel/OctoPrint/pull/2409) - Added `m4v` and `mkv` to the list of accepted timelapse extensions.
  * [#2444](https://github.com/foosel/OctoPrint/pull/2444) - Support additional CSS classes on custom control buttons.
  * [#2448](https://github.com/foosel/OctoPrint/issues/2448) - Also detect plugins in `~/.octoprint/plugins` that are provided as bytecode `pyc` instead of source `py` files.
  * [#2455](https://github.com/foosel/OctoPrint/issues/2455) - Added option to configure SSL validation for snapshot URL.
  * Support `M114` response format of RepRapFirmware (uses `X:... Y:... Z:... E0:... E1:...` instead of
`X:... Y:... Z:... E:...`)
  * Added refresh button to connection panel for easy refresh of the available ports to connect to without having to reload the whole page.
  * Increased upper bound of PySerial dependency from 2.7 to 3.4. See also [#2333](https://github.com/foosel/OctoPrint/issues/2333).
  * Switch to lower communication timeouts if support of the `busy` protocol by the firmware is detected.
  * Refactored serial settings dialog, now has sub tabs and more explanations.
  * Allow to disable support for certain firmware capabilities, even if reported as supported by the firmware: `busy` protocol, temperature auto reporting, SD status auto reporting
  * Attached tags to GCODE commands moving through the comm layer and allowed plugins to access and extend these tags through the GCODE hooks. Makes it possible for plugins to detect the origin of a command (streamed file vs. GCODE script vs. user input vs. plugin), the point where it entered the system and so on. Also added a new logger `octoprint.util.comm.command_phases` that if set to `DEBUG` will log the lifecycle of commands through the comm layer including tags to `octoprint.log`. See also [the docs here](http://docs.octoprint.org/en/maintenance/plugins/hooks.html#octoprint-comm-protocol-gcode-phase).
  * Added new [`job_on_hold`](http://docs.octoprint.org/en/maintenance/modules/printer.html#octoprint.printer.PrinterInterface.job_on_hold) and [`set_job_on_hold`](http://docs.octoprint.org/en/maintenance/modules/printer.html#octoprint.printer.PrinterInterface.set_job_on_hold) methods on the printer instance, allowing plugins to quickly stall the streaming of a queue. This should be used sparingly - abuse will have significant negative effects on the print job. Read the docs if you plan to utilize this.
  * Support extraction of plugin metadata even from disabled and blacklisted plugins through the AST of the module.
  * Better logging of printer callback errors and utilization of `frozendict` for internal printer state propagation in an attempt to narrow down on [#1951](https://github.com/foosel/OctoPrint/issues/1951). Should `frozendict` cause issues it can be disabled through the settings in `config.yaml`, just set `devel.useFrozenDictForPrinterState` to `false` 
  * Log comm state changes to `octoprint.log`.
  * Added a regular server heartbeat to the log (every 15min).
  * Support SD status auto report by the firmware.
  * Added `Not SD printing` to default "SD status" terminal filters.
  * Added custom `readline` implementation for the serial port. Instead of relying on PySerial's `readline` that depending on the installed version might only read from the port one byte at the time, we now wait for one byte and then read everything available into a persistent buffer which then is used to fetch lines from. 
  * Ensure that `callViewModelIf` doesn't try to call null or uncallable `method`s.
  * Added links to the new [Community Forum](https://discourse.octoprint.org) and the new location of the [FAQ](https://faq.octoprint.org).
  * Improved pip utility logging, `LocalPipHelper` wasn't producing output, making it hard to debug such non writable install directories.
  * Added a new bundled plugin "Printer Safety Check" that will try to identify printer/printer firmware with known safety issues such as missing thermal runaway protection.
  * Plugin Manager: Reduce notification spam. See also [#2260](https://github.com/foosel/OctoPrint/issues/2260).
  * Software Update Plugin: Better detection if an update is already running.
  * Software Update Plugin: Refer to `plugin_softwareupdate_console.log` on update errors in log and notification.

### Bugfixes

  * [#2294](https://github.com/foosel/OctoPrint/issues/2294) - Improved resilience against errors during gathering the file list (e.g. permission errors)
  * [#2296](https://github.com/foosel/OctoPrint/issues/2296) - Fixed `X-Forwarded-For` handling in Flask Login through monkey patched backport.
  * [#2297](https://github.com/foosel/OctoPrint/issues/2297) - Return `403` instead of `401` on missing/insufficient credentials.
  * [#2311](https://github.com/foosel/OctoPrint/issues/2311) - Fixed server not auto connecting on startup if port is set to `AUTO` (see also [#2311](https://github.com/foosel/OctoPrint/pull/2337)).
  * [#2316](https://github.com/foosel/OctoPrint/issues/2316) - Check for valid queue entry in file analysis queue before trying to dequeue, fix for a HTTP `500` on upload of a file not supported for analysis. 
  * [#2321](https://github.com/foosel/OctoPrint/issues/2321) & [#2449](https://github.com/foosel/OctoPrint/issues/2449) - Fixed wrong queuing order of cancel script & first line from printed file on quick start-cancel-start scenarios by introducing a two new states "Cancelling" and "Pausing".
  * [#2324](https://github.com/foosel/OctoPrint/pull/2324) - Fixed 500 error when 
  * [#2333](https://github.com/foosel/OctoPrint/issues/2333) (Part 1/3) - Workaround for an update problem caused by interaction of `pip` with dependencies formerly installed as eggs through `python setup.py install`. 
  * [#2333](https://github.com/foosel/OctoPrint/issues/2333) (Part 2/3) - If supported by the underlying PySerial version, cancel all reads and writes on disconnect if possible for a faster connection release. Part 3 (forcing an upgrade of PySerial to 3.4 so this should work in more cases) will in OctoPrint 1.3.8.
  * [#2364](https://github.com/foosel/OctoPrint/issues/2364) - Fixed firmware error reporting in case of cancelling a print due to a firmware error.
  * [#2368](https://github.com/foosel/OctoPrint/issues/2368) - Fixed for incorrect handling of unicode filenames in cura slicer profiles
  * [#2371](https://github.com/foosel/OctoPrint/issues/2371) - Removed "just now"/"gerade eben" label from temperature graph to work around a graph resize issue caused by that.
  * [#2392](https://github.com/foosel/OctoPrint/issues/2392) - Fixed "Copy all" on terminal tab only working the first time.
  * [#2406](https://github.com/foosel/OctoPrint/pull/2406) - Fixed `showTab` JS function of about dialog.
  * [#2426](https://github.com/foosel/OctoPrint/issues/2426) - Made resend logging to `octoprint.log` unicode safe
  * [#2442](https://github.com/foosel/OctoPrint/issues/2442) - Don't even import disabled plugins, use a dummy entry for them just like for backlisted plugins. More resilience against misbehaving plugins.
  * [#2461](https://github.com/foosel/OctoPrint/issues/2461) - Fixed OctoPrint not properly disconnecting in case of a firmware error.
  * [#2494](https://github.com/foosel/OctoPrint/issues/2494) - Fixed `undefined` values not saving in the settings. 
  * [#2499](https://github.com/foosel/OctoPrint/issues/2499) (regression) - Fixed communication error notification lacking the actual error message.
  * [#2501](https://github.com/foosel/OctoPrint/issues/2501) (regression) - Fixed a bug causing log downloads to fail with an HTTP 500 error.
  * [#2506](https://github.com/foosel/OctoPrint/issues/2506) (regression) - Fixed `printer.get_current_data` and `printer.get_current_job` returning `frozendict` instead of `dict` instances, causing issues with plugins relying on being able to modify the returned data (e.g. [dattas/OctoPrint-DetailedProgress#26](https://github.com/dattas/OctoPrint-DetailedProgress/issues/26)).
  * [#2508](https://github.com/foosel/OctoPrint/issues/2508) (regression) - Fixed HTTP 500 error on `/api/slicing` in case of an unconfigured slicer.
  * [#2524](https://github.com/foosel/OctoPrint/issues/2524) - Ignore `wait` while job is on hold.
  * [#2536](https://github.com/foosel/OctoPrint/issues/2536) - Fix a wrong state tracking when starting an SD print through the controller, causing a disconnect due to a timeout.
  * [#2544](https://github.com/foosel/OctoPrint/issues/2544) (regression) - Fix an exception when connecting to the raw websocket at `/sockjs/websocket` (instead of `/sockjs/<server_id>/<session_id>/websocket`).
  * [#2546](https://github.com/foosel/OctoPrint/issues/2546) (regression) - Fix the `PRINT_FAILED` event getting triggered twice on print failure due to disconnect
  * Use `pkg_resources` to determine pip version during environment check instead of `import pip; pip.__version__` since the latter causes issues with pip version 9.0.2. In the same spirit make `pip.main` approach of calling `pip` in the PipCaller the last resort during auto detection, only after trying `pip` or `pip.exe` inside the same folder as the Python executable.
  * Use `octoprint.util.monotonic_time` instead of `monotonic.monotonic` in comm layer.
  * Fixed timelapse not stopping on print failure due to firmware error due to missing `PrintFailed` event.
  * Announcement Plugin: Fixed a missing line break in case of more than three announcements in a notification.
  * Docs: Documentation for printer profile related bits and pieces
  * Docs: Various fixes of typos and grammar.
  * Have `OctoPrintJsonEncoder` fall back to regular flask JSON encoder, otherwise we might not be able to serialize some data types we need to be able to serialize. (regression)

### Known bugs

  * [#2547](https://github.com/foosel/OctoPrint/issues/2547) - Error during processing of afterPrintJobDone script will trigger PRINT_FAILED event even though PRINT_DONE event was already triggered 

### More Information

  * [Commits](https://github.com/foosel/OctoPrint/compare/1.3.6...1.3.7)
  * Release Candidates:
    * [1.3.7rc1](https://github.com/foosel/OctoPrint/releases/tag/1.3.7rc1)
    * [1.3.7rc2](https://github.com/foosel/OctoPrint/releases/tag/1.3.7rc2)
    * [1.3.7rc3](https://github.com/foosel/OctoPrint/releases/tag/1.3.7rc3)
    * [1.3.7rc4](https://github.com/foosel/OctoPrint/releases/tag/1.3.7rc4)
    * A special **Thank you!** to everyone who reported back on these release candidates this time: 
      [aaronkeck](https://github.com/aaronkeck), [akurz42](https://github.com/akurz42), [andrivet](https://github.com/andrivet), [anthonyst91](https://github.com/anthonyst91), [arhi](https://github.com/arhi), [b-morgan](https://github.com/b-morgan), [BryanSmithDev](https://github.com/BryanSmithDev), [chippypilot](https://github.com/chippypilot), [ChrisHeerschap](https://github.com/ChrisHeerschap), [Crowlord](https://github.com/Crowlord), [dforsi](https://github.com/dforsi), [drdelaney](https://github.com/drdelaney), [FormerLurker](https://github.com/FormerLurker), [goeland86](https://github.com/goeland86), [inspiredbylife](https://github.com/inspiredbylife), [jbjones27](https://github.com/jbjones27), [jesasi](https://github.com/jesasi), [jneilliii](https://github.com/jneilliii), [JohnOCFII](https://github.com/JohnOCFII), [kantlivelong](https://github.com/kantlivelong), [lnx13](https://github.com/lnx13), [makaper](https://github.com/makaper), [markwal](https://github.com/markwal), [MiquelAdell](https://discourse.octoprint.org/u/MiquelAdell), [ml0w](https://github.com/ml0w), [mmotley999](https://github.com/mmotley999), [mrhanman](https://github.com/mrhanman), [SCiunczyk](https://github.com/SCiunczyk), [tdub415](https://github.com/tdub415), [tedder42](https://discourse.octoprint.org/u/tedder42), [thatjoshguy](https://github.com/thatjoshguy), [wescrockett](https://github.com/wescrockett)

## 1.3.6 (2017-12-12)

### Note for upgraders and plugin authors: Change in the bundling of JS assets can lead to issues in plugins

A change to solve issues with plugins bundling JS assets that cause interference with other plugins (e.g. through the declaration of `"use strict"`) and in general to add better isolation and error handling might cause errors for some plugins that go beyond your run-off-the-mill view model and also implicitly declare new globals.

If you happen to run into any such issues, you can switch back to the old way of bundling JS assets via the newly introduced "Settings > Feature > Enable legacy plugin asset bundling" toggle (check it, save the settings, restart the server). This is provided to allow for a minimally invasive adjustment period until affected plugins have been updated.

You can find out more about the change, how to know if a plugin is even affected and what do about it [on the OctoBlog](https://octoprint.org/blog/2017/12/01/heads-up-plugin-authors/).

### Improvements

  * [#203](https://github.com/foosel/OctoPrint/issues/203) - Allow selecting the current tab via URL hashs. Also update URL hash when switching tabs, thus adding this to the browser history and allowing quicker back and forth navigation through the browser's back and forward buttons.
  * [#1026](https://github.com/foosel/OctoPrint/issues/1026) - Automatically upper case parameters in GCODE commands sent from the Terminal tab. A black list is in place that prevent upper casing of parameters for GCODE commands where it doesn't make sense (default: `M117`). See also [#2177](https://github.com/foosel/OctoPrint/pull/2177).
  * [#2050](https://github.com/foosel/OctoPrint/issues/2050) - New hook [`octoprint.comm.protocol.temperatures.received`](http://docs.octoprint.org/en/maintenance/plugins/hooks.html#octoprint-comm-protocol-temperatures-received) that allows plugins to further preprocess/sanitize temperature data received from the printer. 
  * [#2055](https://github.com/foosel/OctoPrint/issues/2055) - Increased the size of the API key field in the settings.
  * [#2056](https://github.com/foosel/OctoPrint/issues/2056) - Added a Copy button to the API key field in the settings and user settings.
  * [#2094](https://github.com/foosel/OctoPrint/issues/2094) - Allow UTF-8 display names for uploaded files. The files will still get an ASCII only name on disk, but the UTF-8 name used during upload will also be persisted and shown in the file list. This also allows using emojis in your file and folder names now.
  * [#2104](https://github.com/foosel/OctoPrint/issues/2104) - Allow more URL schemes for installing plugins from. Supported schemes should now mirror what `pip` itself supports: `http`, `https`, `git`, `git+http`, `git+https`, `git+ssh`, `git+git`, `hg+http`, `hg+https`, `hg+static-http`, `hg+ssh`, `svn`, `svn+svn`, `svn+http`, `svn+https`, `svn+ssh`, `bzr+http`, `bzr+https`, `bzr+ssh`, `bzr+sftp`, `bzr+ftp`, `bzr+lp`.
  * [#2109](https://github.com/foosel/OctoPrint/pull/2109) - New decorator `@firstrun_only_access` for API endpoints that should only be available before first setup has been completed.
  * [#2111](https://github.com/foosel/OctoPrint/issues/2111) - Made the file list's scroll bar wider.
  * [#2131](https://github.com/foosel/OctoPrint/issues/2131) - Added warning to restart, shutdown, reboot and update confirmations that that may disrupt ongoing prints, even those run from the printer's internal storage/SD. See also [#2146](https://github.com/foosel/OctoPrint/pull/2146) and [#2152](https://github.com/foosel/OctoPrint/pull/2152).
  * [#2138](https://github.com/foosel/OctoPrint/issues/2138) - Slightly longer timeout when attempting to read from serial during auto detection via programming mode. Might help with detection of some slower printer controllers under certain circumstances.
  * [#2200](https://github.com/foosel/OctoPrint/issues/2200) - Wrap all JS assets of plugins into one anonymous function per plugin. That way plugins using `"use strict";` won't cause hard to debug and weird issues with other plugins bundled after them. The down side is that plugins currently relying on implicit declaration of global helper functions or variables (`function convert(value) { ... }`) to be available outside of their own plugin's JS assets will now run into errors. To compensate for that while affected plugins are adjusted to declare globals explicitly (`window.convert = function(value) { ... }`), a temporary feature flag was added as "Settings > Features > Enable legacy plugin asset bundling" that switches back to the old form of bundling until plugins you rely on are updated. This flag will be removed again in a later version (currently planned for 1.3.8). See also the note above and [#2246](https://github.com/foosel/OctoPrint/issues/2246).
  * [#2229](https://github.com/foosel/OctoPrint/issues/2229) - Added note to printer profile dialog that the nozzle offsets for multi extruder setups are only to be configured if they are not already set in the printer's firmware.
  * [#2232](https://github.com/foosel/OctoPrint/issues/2232) - Disable movement distance buttons when not connected to the printer or when printing, since they don't have any use then.
  * [#2239](https://github.com/foosel/OctoPrint/pull/2239) - Improved the check summing speed, thus improving the general achievable throughput on the comm layer.
  * Allow cancelling of file transfers
  * Made check of how old an unrendered timelapse is more lenient buy looking at both the creation and last modification date and using the younger one.
  * Made notifications in general auto-close faster.
  * Make the first profile saved for a slicer the default profile for that slicer.
  * New command `server` for testing server connections on the [JS test API](http://docs.octoprint.org/en/maintenance/api/util.html#post--api-util-test).
  * New hook [`octoprint.accesscontrol.keyvalidator`](http://docs.octoprint.org/en/maintenance/plugins/hooks.html#octoprint-accesscontrol-keyvalidator) that allows plugins to validate their own customized API keys to be used to access OctoPrint.
  * Updated `cookiecutter`, `requests` and `psutil` dependencies.
  * Added safety warning to first run wizard. 
  * More error resilience against broken view models.
  * New sub command `octoprint safemode`. Will set the `server.startOnceInSafeMode` setting in the config so that the next (re)start of the server after issuing this command will happen in safe mode.
  * New sub command `octoprint config effective`. Will report the effective config.
  * New centralized plugin blacklist (opt-in). Allows to prevent plugins/certain versions of plugins known to cause crippling issues with the normal operation of OctoPrint to be disabled from loading, if the user has opted to do so in the settings/wizard.
  * Log how to enable `serial.log` to `serial.log` if it's disabled. That will hopefully put at least a small dent in the amount of "It's empty!" responses in tickets ;)
  * Force new Pypi index URL in `requirements.txt` as an additional work around against old tooling.
  * Prefer plain `pip` over `git` for updating OctoPrint.
  * Added environment detection and logging on startup. That should give us more information about the environment to produce a reported bug in.
  * Added OctoPi support plugin that provides information about the detected OctoPi version. Will only load if OctoPi is detected.
  * More dynamic plugin mixin detection. Now using a base class instead of having to list all types manually. Should greatly reduce overhead of adding new mixin types.
  * Support leaf merging for file extension tree, allowing to add new file extensions to types registered by default.
  * Allow non GCODE SD file transfers if registered as `machinecode` through e.g. a plugin's file extension hook. Caution: This doesn't make streaming arbitrary files to the printer via serial work magically. It merely allows that, it's up to the firmware to actually be able to handle that. Also, the regular GCODE streaming protocol is used, so if the streamed file contains control characters from that (e.g. `M29` to signal the end of the streaming process), stuff will break!
  * Added a test button for the online connectivity check.
  * Announcements plugin: Added UTM Tags.
  * Cura plugin: Less `not configured yet` logging.
  * GCODE viewer: Added advanced options that allow configuring display of bounding boxes, sorting by layers and hiding of empty layers.
  * GCODE viewer: Persist all options to local storage so they will be automatically set again the next time the GCODE viewer is used in the same browser.
  * Software update: Auto-hide "Everything is up-to-date" notification.
  * Easier copying of terminal contents thanks to dedicated copy button.
  * Timelapse: [#2067](https://github.com/foosel/OctoPrint/issues/2067) - Added rate limiting to z-based timelapse capturing to prevent issues when accidentally leaving this mode on with vase mode prints.
  * Timelapse: Refactored configuration form & added reset button to switch back to currently active settings.
  * Timelapse: Sort timelapses by modification instead of creation time (creation time can be newer if a backup restore was done).
  * Virtual printer: Support configurable ambient temperature for testing.
  * Virtual printer: Support configurable reset lines.
  * Virtual printer: Added new debug trigger `trigger_missing_lineno`.
  * Virtual printer: Allow empty/`None` prepared oks, allowing to simulate lost acknowledgements right on start.
  * Docs: [#2142](https://github.com/foosel/OctoPrint/pull/2142) - Added documentation for the bundled virtual printer plugin.
  * Docs: [#2234](https://github.com/foosel/OctoPrint/pull/2234) - Added info on how to install under Suse Linux.
  * Docs: Added example PyCharm run configuration that includes automatic dependency updates on start.
  * Docs: Added information on how to run the test suite.
  * Various refactorings
  * Various documentation updates
  * Fetch plugin blacklist (and also announcements, plugin notices and plugin repository) via https instead of http.

### Bug fixes

  * [#2044](https://github.com/foosel/OctoPrint/pull/2044) - Fix various typos in strings and comments
  * [#2048](https://github.com/foosel/OctoPrint/pull/2048) & [#2176](https://github.com/foosel/OctoPrint/pull/2176) - Fixed various warnings during documentation generation.
  * [#2077](https://github.com/foosel/OctoPrint/issues/2077) - Fix an issue with shared nozzles and the temperature graph, causing temperature to not be reported properly when another tool but the first one is selected. See also [#2077](https://github.com/foosel/OctoPrint/pull/2123)
  * [#2108](https://github.com/foosel/OctoPrint/issues/2108) - Added no-op default action to login form so that username + password aren't sent as GET parameters if for some reason the user tries to log in before the view models are properly bound and thus the AJAX POST submission method is attached.
  * [#2111](https://github.com/foosel/OctoPrint/issues/2111) - Prevent file list's scroll bar from fading out.
  * [#2146](https://github.com/foosel/OctoPrint/issues/2147) - Fix initialization of temperature graph if it's not on the first tab due to tab reordering.
  * [#2166](https://github.com/foosel/OctoPrint/issues/2166) - Workaround for a Firefox bug that causes the Drag-n-Drop overlay to never go away if the file is dragged outside of the browser window.
  * [#2167](https://github.com/foosel/OctoPrint/issues/2167) - Fixed grammar of print time estimation tooltip
  * [#2175](https://github.com/foosel/OctoPrint/issues/2175) - Cancel printing when an external reset of the printer is detected on the serial connection.
  * [#2181](https://github.com/foosel/OctoPrint/issues/2181) - More resilience against non-standard `M115` responses.
  * [#2182](https://github.com/foosel/OctoPrint/pull/2182) - Don't start tracking non existing or nonfunctional tools if encountering a temperature command referencing said tool. See also [kantlivelong/OctoPrint-PSUControl#68](https://github.com/kantlivelong/OctoPrint-PSUControl/issues/68).
  * [#2196](https://github.com/foosel/OctoPrint/issues/2196) - Marked API key fields as `readonly` instead of `disabled` to allow their contents to be copied in Firefox (which wasn't possible before).
  * [#2203](https://github.com/foosel/OctoPrint/issues/2203) - Reset temperature offsets to 0 when disconnected from the printer.
  * [#2206](https://github.com/foosel/OctoPrint/issues/2206) - Disable pre-configured timelapse if snapshot URL of ffmpeg path are unset.
  * [#2214](https://github.com/foosel/OctoPrint/issues/2214) - Fixed temperature fields not selecting in MS Edge on focus.
  * [#2217](https://github.com/foosel/OctoPrint/pull/2217) - Fix an issue in `octoprint.util` causing a crash when running under PyPy instead of CPython.
  * [#2226](https://github.com/foosel/OctoPrint/issues/2226) - Handle `No Line Number with checksum, Last Line: ...` errors from the firmware.
  * [#2233](https://github.com/foosel/OctoPrint/pull/2233) - Respond with `411 Length Required` when content length is missing on file uploads.
  * [#2242](https://github.com/foosel/OctoPrint/issues/2242) - Fixed an issue where print time left could show "1 days" instead of "1 day".
  * [#2262](https://github.com/foosel/OctoPrint/issues/2262) (regression) - Fixed a bug causing `Error:checksum mismatch, Last Line: ...` errors from the firmware to be handled incorrectly.
  * [#2267](https://github.com/foosel/OctoPrint/issues/2267) (regression) - Fixed a bug causing the GCODE viewer to not get properly initialized due to a JS error on load if "Also show next layer" was selected.
  * [#2268](https://github.com/foosel/OctoPrint/issues/2268) (regression) - Fixed a bug causing a display error with the temperature offsets. If one offset was changed, all others seemed to revert back to 0.
  * Fixed cleanup of unrendered timelapses with certain names.
  * Fixed a caching issue with the file list API and the slicing API.
  * Fixed initial sizing of the temperature graph.
  * More resilience against corrupt `.metadata.yaml` files.
  * More resilience against corrupt/invalid entries for system actions.
  * More resilience against invalid JSON command requests.
  * More resilience against broken packages in the python environment.
  * Don't evaluate `onWebcamLoaded` more than once when switching to the webcam tab.
  * Fixed `octoprint config` sub command.
  * Fixed deactivated user accounts being able to login (albeit without a persistent session). Show fitting error instead.
  * Fixed temperature auto report after an external reset.
  * Don't log full request headers in Tornado on an error.
  * Fix displayed notification message for synchronous system commands. Was accidentally swapped with the one for asynchronous system commands.
  * GCODE viewer: Fix error on empty layers.
  * Virtual printer: Fix resend simuation.
  * Docs: Fixed CSS of line numbered listings.
  * Docs: Updated mermaid to fix a deprecation warning.
  * Fixed ordering of plugin assets, should be alphabetical based on the plugin identifier. (regression)
  * Fixed an issue causing redundant software update configuration settings to be written to `config.yaml`, in turn causing issues when downgrading to <1.3.5. (regression)
  * Fixed an issue detecting whether the installed version is a release version or a development version. (regression)

### More Information

  * [Commits](https://github.com/foosel/OctoPrint/compare/1.3.5...1.3.6)
  * Release Candidates:
    * [1.3.6rc1](https://github.com/foosel/OctoPrint/releases/tag/1.3.6rc1)
    * [1.3.6rc2](https://github.com/foosel/OctoPrint/releases/tag/1.3.6rc2)
    * [1.3.6rc3](https://github.com/foosel/OctoPrint/releases/tag/1.3.6rc3)
    * A special **Thank you!** to everyone who reported back on these release candidates this time: [andrivet](https://github.com/andrivet), [b-morgan](https://github.com/b-morgan), [bjarchi](https://github.com/bjarchi), [chippypilot](https://github.com/chippypilot), [ChrisHeerschap](https://github.com/ChrisHeerschap), [cosmith71](https://github.com/cosmith71), [Crowlord](https://github.com/Crowlord), [ctgreybeard](https://github.com/ctgreybeard), [fiveangle](https://github.com/fiveangle), [goeland86](https://github.com/goeland86), [jbjones27](https://github.com/jbjones27), [jneilliii](https://github.com/jneilliii), [JohnOCFII](https://github.com/JohnOCFII), [Kunsi](https://github.com/Kunsi), [Lordxv](https://github.com/Lordxv), [malnvenshorn](https://github.com/malnvenshorn), [mcp5500](https://github.com/mcp5500), [ntoff](https://github.com/ntoff), [ripp2003](https://github.com/ripp2003) and [schorsch3000](https://github.com/schorsch3000)

## 1.3.5 (2017-10-16)

### Improvements

  * [#1162](https://github.com/foosel/OctoPrint/pull/1162) - Allow `octoprint.comm.protocol.gcode.queuing` hook to return a list of commands.
  * [#1572](https://github.com/foosel/OctoPrint/issues/1572) & [#1881](https://github.com/foosel/OctoPrint/issues/1881) - Refactored web interface startup process to minimise risk of race conditions and speed improvements. Also added sequence diagram to the documentation showing the new processing order.
  * [#1640](https://github.com/foosel/OctoPrint/issues/1640) - Mouse over temperature graph to get exact data for that time.
  * [#1679](https://github.com/foosel/OctoPrint/issues/1679) - Support temperature autoreporting by the firmware instead of polling if the firmware reports to support it. For this to work with Marlin 1.1.0 to 1.1.3 you'll need to explicitly enable `EXTENDED_CAPABILITIES_REPORT` *and* `AUTO_REPORT_TEMPERATURES` in your firmware configuration, otherwise your firmware won't report that it actually supports this feature.
  * [#1737](https://github.com/foosel/OctoPrint/issues/1737) - Auto-detect Anet A8 firmware and treat as Repetier Firmware (which it actually appears to be, just renamed - thanks Anet for making this even harder). 
  * [#1842](https://github.com/foosel/OctoPrint/issues/1842) - Update bundled FontAwesome to 4.7 (see also [#1915](https://github.com/foosel/OctoPrint/pull/1915)).
  * [#1910](https://github.com/foosel/OctoPrint/issues/1910) - Make last/pause/cancel temperature available for GCODE scripts.
  * [#1925](https://github.com/foosel/OctoPrint/issues/1925) - Include configured webcam stream URL in "Webcam stream not loaded" message for logged in users/admins. Slightly different wording for guests vs users vs admins.
  * [#1941](https://github.com/foosel/OctoPrint/issues/1941) - Enable "block while dwelling" flag when Malyan firmware is detected since that firmware seems to handle `G4` identically to Repetier Firmware instead of Marlin (like it claims to). See also [#1762](https://github.com/foosel/OctoPrint/issues/1762).
  * [#1946](https://github.com/foosel/OctoPrint/issues/1946) - Add option to disable position logging on cancel/pause. See "Log position on cancel" and "Log position on pause" under Settings > Serial > Advanced options.
  * [#1971](https://github.com/foosel/OctoPrint/issues/1971) - Refactored temperature inputs. They now sport some fancy +/- buttons to increment/decrement the current temperature (which also auto submit after a couple of seconds) and easier editing by keyboard. The temperature offset was also slightly redesigned to make room for that.
  * [#1975](https://github.com/foosel/OctoPrint/issues/1975) - Better error reporting when deleting timelapses.
  * [#2010](https://github.com/foosel/OctoPrint/pull/2010) - Slight refactoring in the terminal tab: Full width input field, auto focus of input field when just clicking on terminal output.
  * [#2011](https://github.com/foosel/OctoPrint/issues/2011) - Centralized online connectivity check (with opt-in of course). None of the bundled plugins will attempt to fetch data from the net when the connectivity check indicates that would fail anyhow. This should improve server startup times and various requests when running isolated.
  * [#2025](https://github.com/foosel/OctoPrint/issues/2025) - More verbose logging of asynchronous system commands (e.g. restart/shutdown).
  * Allow timelapse configuration through UI even when not connected to the printer (suggested in [#1918](https://github.com/foosel/OctoPrint/issues/1918))
  * Disable "Upload to SD" UI elements while printing (suggested in [#1914](https://github.com/foosel/OctoPrint/issues/1914))
  * Update bundled SockJS to 1.1.2 incl. source maps
  * Set `X-Robots` HTTP header and remove `Server` header from all responses, also set `robots` meta tag in page.
  * Don't require to enter programmer mode for printer port autodetection when there's only one possible port candidate anyhow.
  * More sensible sorting of baudrates (additionally configured, then 115200, then 250000, then everything else).
  * Don't show "Unhandled communication error" on autodetection failure.
  * Make timeout after which to unload the webcam stream after navigating away from it configurable (as suggested in [#1937](https://github.com/foosel/OctoPrint/issues/1937))
  * Add `ToolChange` event and tool change GCODE scripts
  * Support parsing GCODE subcodes.
  * Add `octoprint.users.factory` hook, allowing plugins to extend/swap out the user manager OctoPrint uses.
  * Corewizard: Disable view model and client code if it's not actually required.
  * Corewizard: Disable injection of JS files into UI when it's not actually required.
  * GCODE analysis: Moved into its own subprocess. That should improve performance on multi core systems.
  * GCODE viewer: Ignore coordinates outside bed when zooming/centering on model. Those usually are nozzle priming routines.
  * JS Client Lib: Add centralized browser detection as `OctoPrint.coreui.browser`. Available properties: `chrome`, `firefox`, `safari`, `ie`, `edge`, `opera` as well as `mobile` and `desktop`, all of which are boolean values.
  * Plugin Manager plugin: Detect if a plugin requires a reconnect to the printer to become fully active/inactive.
  * Software Update plugin: Force exact version when updating OctoPrint and tracking releases.
  * Software Update plugin: "Devel RCs" release channel now also tracks maintenance RCs. That way people don't have to toggle between the two any more to get *all* RCs.
  * Software Update plugin: `bitbucket_commit` check type now supports API credentials (see also [#1993](https://github.com/foosel/OctoPrint/pull/1993)).
  * Wizard: Allow suppressing the "the settings got updated" dialog through subwizards, in case they need to update settings asynchronously as part of their workflow.
  * More resilience against expected folders being files.
  * More resilience against a wrong user manager class being configured.
  * Some code refactoring & cleanup.
  * Some HTML & CSS improvements.

### Bug fixes

  * [#1916](https://github.com/foosel/OctoPrint/issues/1916) - Fix webcam not loading if first/initial tab is "Control"
  * [#1924](https://github.com/foosel/OctoPrint/issues/1924) - Filter out source map links from bundled JS webassets.
  * [#1943](https://github.com/foosel/OctoPrint/issues/1943) - Fix issue causing unnecessary creation of default printer profile on startup
  * [#1946](https://github.com/foosel/OctoPrint/issues/1946) - Decouple writing of print log from everything else. Fixes delay in cancel processing.
  * [#1963](https://github.com/foosel/OctoPrint/issues/1963) & [#1974](https://github.com/foosel/OctoPrint/issues/1974) - Allow empty & custom size in print job events. Also fixes an issue with timelapses when printing from SD on printers that require the GPX plugin to work.
  * [#1996](https://github.com/foosel/OctoPrint/issues/1996) - Support all line ending variantes in the GCODE viewer. Solves an issue with GCODE generated for Prusa's multi material extruder since that uses only `\r` for some reason.
  * [#2007](https://github.com/foosel/OctoPrint/issues/2007) - Fix issue parsing temperature lines from the printer that contain negative values.
  * [#2012](https://github.com/foosel/OctoPrint/issues/2012) - Fix command line interface of Software Update plugin.
  * [#2017](https://github.com/foosel/OctoPrint/issues/2017) - Fix issue in GCODE viewer with files that contain a visit to the first layer twice (e.g. brim, then nose dive from higher z for actual model), causing all but the last layer segment to not be rendered.
  * [#2033](https://github.com/foosel/OctoPrint/issues/2033) (regression) - Temperature tab: Fix for legend in graph not updating with current values on mouse over.
  * [#2033](https://github.com/foosel/OctoPrint/issues/2033) (regression) - Temperature tab: Fix for new temperature inputs not fitting on one line in Firefox.
  * [#2033](https://github.com/foosel/OctoPrint/issues/2033) (regression) - Temperature tab & GCODE viewer: Fix for available tools (and offsets) not properly updating on change of printer profile.
  * [#2033](https://github.com/foosel/OctoPrint/issues/2033) (regression) - Wizard: Fix sorting of required wizards not properly handling non-ASCII unicode.
  * [#2035](https://github.com/foosel/OctoPrint/issues/2035) (regression) - Fix an issue of the server not starting up if there's a file in the analysis backlog. The reason for this is that spawning a new process while the intermediary server is active causes the server port to be blocked (this is due to how subprocessing works by default), in turn leading to an error on startup since the port cannot be bound by the actual server. Since the GCODE analysis takes now place in its own subprocess and hence triggers this problem, it had to be moved until after the actual server has already started up to avoid this problem.
  * [#2059](https://github.com/foosel/OctoPrint/issues/2059) (regression) - Fix an issue causing the new temperature controls to wrap on touch enabled devices when the temperature dropdown is opened.
  * [#2090](https://github.com/foosel/OctoPrint/issues/2090) (regression) - Fix an issue causing an aborted server startup under Windows if the timing is just right.
  * [#2135](https://github.com/foosel/OctoPrint/issues/2135) (regression) - Fix an issue causing import errors inside the GCODE analysis tool in certain environments due to `sys.path` entries causing relative imports.
  * [#2136](https://github.com/foosel/OctoPrint/issues/2136) (regression) - Fix wrong minimum version for `sockjs-tornado` dependency.
  * [#2137](https://github.com/foosel/OctoPrint/issues/2137) (regression) - Fix issue with session cookies getting lost when running an OctoPrint instance on a subpath of another (e.g. `octopi.local/` and `octopi.local/octoprint2`).
  * [#2140](https://github.com/foosel/OctoPrint/issues/2140) (regression) - Fix issue with locale dependent sorting of sub wizards during first time setup causing issues leading to the wizard not being able to complete.
  * Fix various popup buttons allowing multiple clicks (suggested in [#1914](https://github.com/foosel/OctoPrint/issues/1914))
  * Software Update Plugin: Perform server restart asynchronously. Should reduce restart times on updates significantly.
  * Don't hex-escape `\t`, `\r` or `\n` in terminal output
  * Use client side default printer profile if the default profile could not be found on the server
  * Use both "to" and "from" coordinates of a given move for min/max model coordinate calculation in GCODE analysis. Otherwise wrong values could be calculated under certain circumstances.  
  * Fix potential race condition in resend request handling.
  * Fix potential race condition in web socket handling.
  * Fix handling of tool offsets in GCODE analysis - diverted too far from firmware implementations, causing wrong calculations.
  * Fix `FileAdded`, `FileRemoved`, `FolderAdded`, `FolderRemoved` events not being fired with the correct event name.
  * Fix potential division by zero in progress reporting if the timing was just right.
  * Fix sorting order for multiple tools in the "State" panel.
  * Fix file position vs. line ending handling in GCODE viewer. Could lead to slightly off file position calculation and hence possibly to the wrong move being plotted when synchronizing with print progress.
  * Wizard: Fix `onWizardPreventSettingsRefreshDialog` callback invocation. (regression)
  * Corewizard plugin: Fix `firstrunonly` wizards (e.g. for printer profile configuration) being displayed again if _any_ of the sub wizards (e.g. for the online check opt-in and configuration) is active. (regression)
  * Fix an issue causing rollover of `serial.log` to fail under Windows. (regression)

### More Information

  * [Commits](https://github.com/foosel/OctoPrint/compare/1.3.4...1.3.5)
  * Release Candidates:
    * [1.3.5rc1](https://github.com/foosel/OctoPrint/releases/tag/1.3.5rc1)
    * [1.3.5rc2](https://github.com/foosel/OctoPrint/releases/tag/1.3.5rc2)
    * [1.3.5rc3](https://github.com/foosel/OctoPrint/releases/tag/1.3.5rc3)
    * [1.3.5rc4](https://github.com/foosel/OctoPrint/releases/tag/1.3.5rc4)
    * A special **Thank you!** to everyone who reported back on these release candidates this time: [alexxy](https://github.com/alexxy), [andrivet](https://github.com/andrivet), [b-morgan](https://github.com/b-morgan), [BillyBlaze](https://github.com/BillyBlaze), [CapnBry](https://github.com/CapnBry), [chippypilot](https://github.com/chippypilot), [ctgreybeard](https://github.com/ctgreybeard), [cxt666](https://github.com/cxt666), [DaSTIG](https://github.com/DaSTIG), [fhbmax](https://github.com/fhbmax), [fiveangle](https://github.com/fiveangle), [goeland86](https://github.com/goeland86), [JohnOCFII](https://github.com/JohnOCFII), [Kunsi](https://github.com/Kunsi), [mgrl](https://github.com/mgrl), [MoonshineSG](https://github.com/MoonshineSG), [nate-ubiquisoft](https://github.com/nate-ubiquisoft), [Neoolog](https://github.com/Neoolog), [ntoff](https://github.com/ntoff), [oferfrid](https://github.com/oferfrid), [roygilby](https://github.com/roygilby), [SAinc](https://github.com/SAinc), [sbts](https://github.com/sbts), [thess](https://github.com/thess), [tkurbad](https://github.com/tkurbad), [tsillini](https://github.com/tsillini) and [TylonHH](https://github.com/TylonHH).

## 1.3.4 (2017-06-01)

### Note for owners of Malyan M200/Monoprice Select Mini

OctoPrint's firmware autodetection is now able to detect this printer. Currently when this printer is detected, the following firmware specific features will be enabled automatically:

  * Always assume SD card is present (`feature.sdAlwaysAvailable`)
  * Send a checksum with the command: Always (`feature.alwaysSendChecksum`)

Since the firmware is a very special kind of beast and its sources are so far unavailable, only tests with a real printer will show if those are sufficient settings for communication with this printer to fully function correctly. Thus, if you run into any issues with enabled firmware autodetection on this printer model, please add a comment in [#1762](https://github.com/foosel/OctoPrint/issues/1762) and explain what kind of communication problem you are seeing. Also make sure to include a [`serial.log`](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md#where-can-i-find-those-log-files-you-keep-talking-about)!

### Bug fixes

  * [#1942](https://github.com/foosel/OctoPrint/issues/1942) - Fixed crash on startup in case of an invalid default printer profile combined with "auto-connect on startup" being selected and the printer available to connect to.

### More information

  * [Commits](https://github.com/foosel/OctoPrint/compare/1.3.1...1.3.2)
  * Release Candidates:
    * None since this constitutes a hotfix release to fix an apparently very rare bug introduced with 1.3.3 that seems to be affecting a small number of users.

## 1.3.3 (2017-05-31)

### Note for owners of Malyan M200/Monoprice Select Mini

OctoPrint's firmware autodetection is now able to detect this printer. Currently when this printer is detected, the following firmware specific features will be enabled automatically:

  * Always assume SD card is present (`feature.sdAlwaysAvailable`)
  * Send a checksum with the command: Always (`feature.alwaysSendChecksum`)

Since the firmware is a very special kind of beast and its sources are so far unavailable, only tests with a real printer will show if those are sufficient settings for communication with this printer to fully function correctly. Thus, if you run into any issues with enabled firmware autodetection on this printer model, please add a comment in [#1762](https://github.com/foosel/OctoPrint/issues/1762) and explain what kind of communication problem you are seeing. Also make sure to include a [`serial.log`](https://github.com/foosel/OctoPrint/blob/master/CONTRIBUTING.md#where-can-i-find-those-log-files-you-keep-talking-about)!

### Improvements

  * [#478](https://github.com/foosel/OctoPrint/issues/478) - Made webcam stream container fixed height (with selectable aspect ratio) to prevent jumps of the controls beneath it on load.
  * [#748](https://github.com/foosel/OctoPrint/issues/748) - Added delete confirmation and bulk delete for timelapses. See also the discussion in brainstorming ticket [#1807](https://github.com/foosel/OctoPrint/issues/1807).
  * [#1092](https://github.com/foosel/OctoPrint/issues/1092) - Added new events to the file manager: `FileAdded`, `FileRemoved`, `FolderAdded`, `FolderRemoved`. Contrary to the `Upload` event, `FileAdded` will always fire when a file was added to storage through the file manager, not only when added through the web interface. Extended documentation accordingly.
  * [#1521](https://github.com/foosel/OctoPrint/issues/1521) - Software update plugin: Display timestamp of last version cache refresh in "Advanced options" area.
  * [#1734](https://github.com/foosel/OctoPrint/issues/1734) - Treat default/initial printer profile like all other printer profiles, persisting it to disk instead of `config.yaml` and allowing deletion. OctoPrint will migrate the existing default profile to the new location on first start.
  * [#1734](https://github.com/foosel/OctoPrint/issues/1734) - Better communication of what actions are available for printer profiles.
  * [#1739](https://github.com/foosel/OctoPrint/issues/1739) - Software update plugin: Added option to hide update notification from users without admin rights, added "ignore" button and note to get in touch with an admit to update notifications for non admin users.
  * [#1762](https://github.com/foosel/OctoPrint/issues/1762) - Added Malyan M200/Monoprice Select Mini to firmware autodetection.
  * [#1811](https://github.com/foosel/OctoPrint/issues/1811) - Slight rewording and rearrangement in timelapse configuration, better feedback if settings have been saved.
  * [#1818](https://github.com/foosel/OctoPrint/issues/1818) - Support both Marlin/Repetier and Smoothieware interpretations of `G90` after an `M83` in GCODE viewer and analysis. Select "G90/G91 overrides relative extruder mode" in Settings > Features for the Smoothieware interpretation.
  * [#1858](https://github.com/foosel/OctoPrint/issues/1858) - Announcement plugin: Images from registered feeds now are lazy loading.
  * [#1862](https://github.com/foosel/OctoPrint/issues/1862) - Automatically re-enable fancy terminal functionality when performance recovers.
  * [#1875](https://github.com/foosel/OctoPrint/issues/1875) - Marked the command input field in the Terminal tab as not supporting autocomplete to work around an issue in Safari. Note that this is probably only a temporary workaround due to browser vendors [working on deprecating `autocomplete="off"` support](https://bugs.chromium.org/p/chromium/issues/detail?id=468153#c164) and a different solution will need to be found in the future.
  * Added link to [`SerialException` FAQ entry](https://github.com/foosel/OctoPrint/wiki/FAQ#octoprint-randomly-loses-connection-to-the-printer-with-a-serialexception) to terminal output when such an error is encountered, as suggested in [#1876](https://github.com/foosel/OctoPrint/issues/1876).
  * Force refresh of settings on login/logout.
  * Made system wide API key management mirror user API key management.
  * Make sure to always migrate and merge saved printer profiles with default profile to ensure all parameters are set. Should avoid issues with plugins trying to save outdated/incomplete profiles.
  * Added note on lack of language pack repository & to use the wiki for now.
  * Earlier validation of file to select for printing.
  * Limit verbosity of failed system event handlers.
  * Made bundled python client `octoprint_client` support multiple client instances.
  * Disable "Reload" button in the "Please reload" overlay once clicked, added spinner.
  * Updated pnotify to 2.1.0.
  * Get rid of ridiculous float precision in temperature commands.
  * Detect invalid settings data to persist (not a dict), send 400 status in such a case.
  * More logging for preemptive caching, to help narrow down any performance issues that might be related to this.
  * Further decoupling of some startup tasks from initial server startup thread for better parallelization and improved startup times.
  * Announcement plugin: Added combined OctoBlog feed, replacing news and spotlight feed, added corresponding config migration.
  * Announcement plugin: Subscribe to all registered feeds by default to ensure better communication flow (all subscriptions but the "Important" channel can however be unsubscribed easily, added corresponding note to the notifications and also a configuration button to the announcement reader).
  * Announcement plugin: Auto-hide announcements on logout.
  * Announcement plugin: Order channels server-side based on new order config setting.
  * Plugin manager: Show warning when disabling a bundled plugin that is not recommended to be disabled, including a reason why disabling it is not recommended. Applies to the bundled announcement, core wizard, discovery and software update plugins.
  * Plugin manager: Support for plugin notices for specific plugins from the plugin repository, e.g. to inform users of specific plugins about known issues with the plugin or instruct to update when the software update mechanism of the current plugin version turns out to be misconfigured. Supports matching installed plugin versions and OctoPrint versions to target only affected users.
  * Plugin manager: Better visualization of plugins disabled on the repository, no longer shown as "incompatible" but "disabled", with link to the plugin repository page that contains more information.
  * Plugin manager: Detect necessity to reinstall a plugin provided through archive URL or upload and immediately do that instead of reporting an "unknown error" without further information.
  * Plugin manager: Added `freebsd` for compatibility check.
  * Plugin manager: More general flexibility for OS compatibility check:
    * Support for arbitrary values to match against
    * Allow 1:1 check again `sys.platform` values (with `startswith`).
    * Support black listing (`!windows`) additionally to white listing. A detected OS must match all provided white list elements (if the white list is empty that is considered to be always the case) and none of the black list elements (if the black list is empty that is also considered to be always the case).
  * Software update plugin: New check type `bitbucket_commit` (see also [#1898](https://github.com/foosel/OctoPrint/pull/1898))
  * Docs: Now referring to dedicated Jinja 2.8 documentation as hosted at [jinja.octoprint.org](http://jinja.octoprint.org) for all template needs, to avoid confusion when consulting current Jinja documentation as available on its project page (2.9+, which OctoPrint can't upgrade to due to backwards incompatible changes).
  * Docs: Better documentation of what kind of input the `FileManager` accepts for `select_file`.
  * Docs: Specified OctoPrint version required for plugin tutorial.

### Bug fixes

  * [#202](https://github.com/foosel/OctoPrint/issues/202) - Fixed an issue with the drag-n-drop area flickering if the mouse was moved too slow while dragging (see also [#1867](https://github.com/foosel/OctoPrint/pull/1867)).
  * [#1671](https://github.com/foosel/OctoPrint/issues/1671) - Removed obsolete entry of no longer available filter for empty folders from file list options.
  * [#1821](https://github.com/foosel/OctoPrint/issues/1821) - Properly reset "Capture post roll images" setting in timelapse configuration when switching from "off" to "timed" timelapse mode.
  * [#1822](https://github.com/foosel/OctoPrint/issues/1822) - Properly reset file metadata when a file is overwritten with a new version.
  * [#1836](https://github.com/foosel/OctoPrint/issues/1836) - Fixed order of `PrintCancelled` and `PrintFailed` events on print cancel.
  * [#1837](https://github.com/foosel/OctoPrint/issues/1837) - Fixed a race condition causing OctoPrint trying to read data from the current job on job cancel that was no longer there.
  * [#1838](https://github.com/foosel/OctoPrint/issues/1838) - Fixed a rare race condition causing an error right at the very start of a print.
  * [#1863](https://github.com/foosel/OctoPrint/issues/1863) - Fixed an issue in the analysis of GCODE files containing coordinate offsets for X, Y or Z via `G92`, leading to a wrong calculation of the model size thanks to accumulating offsets.
  * [#1882](https://github.com/foosel/OctoPrint/issues/1882) - Fixed a rare race condition occurring at the start of streaming a file to the printer's SD card, leading to endless line number mismatches.
  * [#1884](https://github.com/foosel/OctoPrint/issues/1884) - CuraEngine plugin: Fixed a potential encoding issue when logging non-ASCII parameters supplied to CuraEngine
  * [#1891](https://github.com/foosel/OctoPrint/issues/1891) - Fixed error when handling unicode passwords.
  * [#1893](https://github.com/foosel/OctoPrint/issues/1893) - CuraEngine plugin: Fixed handling of multiple consecutive uploads of slicing profiles (see also [#1894](https://github.com/foosel/OctoPrint/issues/1894))
  * [#1897](https://github.com/foosel/OctoPrint/issues/1897) - Removed possibility to concurrently try to perform multiple tests of the configured snapshot URL.
  * [#1906](https://github.com/foosel/OctoPrint/issues/1906) - Fixed interpretation of `G92` in GCODE analysis.
  * [#1907](https://github.com/foosel/OctoPrint/issues/1907) - Don't send temperature commands with tool parameter when a shared nozzle is defined.
  * [#1917](https://github.com/foosel/OctoPrint/issues/1917) (regression) - Fix job data resetting on print job completion.
  * [#1918](https://github.com/foosel/OctoPrint/issues/1918) (regression) - Fix "save as default" checkbox not being disabled when other controls are disabled.
  * [#1919](https://github.com/foosel/OctoPrint/issues/1919) (regression) - Fix call to no longer existing function in Plugin Manager UI.
  * [#1934](https://github.com/foosel/OctoPrint/issues/1934) (regression) - Fix consecutive timed timelapse captures without configured post roll.
  * Fixed API key QR Code being shown (for "n/a" value) when no API key was set.
  * Fixed timelapse configuration API not returning 400 status code on some bad parameters.
  * Fixed a typo (see also [#1826](https://github.com/foosel/OctoPrint/pull/1826)).
  * Fixed `filter` and `force` parameters on `/api/files/<origin>`.
  * Fixed message catchall `*` not working in the socket client library.
  * Fixed analysis backlog calculation for sub folders.
  * Fixed `PrinterInterface.is_ready` to behave as documented.
  * Use black listing instead of white listing again to detect if the `daemon` sub command is supported or not. Should resolve issues users of FreeBSD and the like where having with `octoprint daemon`.
  * Use `pip` instead of `python setup.py develop` in `octoprint dev plugin:install` command to avoid issues on Windows.
  * Docs: Fixed a wrong command in the plugin tutorial (see also [#1860](https://github.com/foosel/OctoPrint/pull/1860)).

### More information

- [Commits](https://github.com/foosel/OctoPrint/compare/1.3.2...1.3.3)
- Release Candidates:
  - [1.3.3rc1](https://github.com/foosel/OctoPrint/releases/tag/1.3.3rc1)
  - [1.3.3rc2](https://github.com/foosel/OctoPrint/releases/tag/1.3.3rc2)
  - [1.3.3rc3](https://github.com/foosel/OctoPrint/releases/tag/1.3.3rc3)

## 1.3.2 (2017-03-16)

### Note for plugin authors

**If you maintain a plugin that extends OctoPrint's [JavaScript Client Library](http://docs.octoprint.org/en/master/jsclientlib/index.html)** like demonstrated in e.g. the bundled Software Update Plugin you'll need to update the way you register your plugin to depend on `OctoPrintClient` and registering your extension as shown [here](https://github.com/foosel/OctoPrint/blob/6e793c2/src/octoprint/plugins/softwareupdate/static/js/softwareupdate.js#L1-L84) instead of directly writing to `OctoPrint.plugins` (like it was still done [here](https://github.com/foosel/OctoPrint/blob/23744cd/src/octoprint/plugins/softwareupdate/static/js/softwareupdate.js#L1-L81)). That way your extensions will be available on all instances of `OctoPrintClient`, not just the global instance `OctoPrint` that gets created on startup of the core web interface.

If all you plugin does with regards to JavaScript is registering a custom view model and you have no idea what I'm talking about regarding extending the client library, no action is necessary. This heads-up is really only relevant if you extended the JavaScript Client Library.

### Improvements

- [#732](https://github.com/foosel/OctoPrint/pull/732) - Have OctoPrint's `python setup.py clean` build on stock
`python setup.py clean` for better compatibility with packaging systems
- [#1506](https://github.com/foosel/OctoPrint/issues/1506) - Better handle really long "dwell"/`G4` commands on Repetier firmware (as for example apparently recommended to use with Wanhao D6 and similar printers for nozzle cooling) by actively stalling communication from OctoPrint's side as well. That way we no longer run into a communication timeout produced by a 5min dwell immediately happily acknowledged by the printer with an `ok`.
- [#1542](https://github.com/foosel/OctoPrint/issues/1542) - Support for multi-extruder setups with a shared single nozzle and heater (e.g. E3D Cyclops, Diamond hotend, etc).
- [#1676](https://github.com/foosel/OctoPrint/issues/1676) - Trigger line number reset when connected to printer and seeing `start` message. This should fix issues with printer communication when printer resets but reset goes otherwise undetected.
- [#1681](https://github.com/foosel/OctoPrint/issues/1681) - Support for connecting to multiple OctoPrint instances via the [JavaScript Client Library](http://docs.octoprint.org/en/master/jsclientlib/index.html).
- [#1712](https://github.com/foosel/OctoPrint/issues/1712) - Display current folder name in file list if in sub folder.
- [#1723](https://github.com/foosel/OctoPrint/issues/1723) - Ignore leading `v` or `V` on plugin version numbers for version checks in plugin manager and software updater (see also [#1724](https://github.com/foosel/OctoPrint/pull/1724))
- [#1770](https://github.com/foosel/OctoPrint/issues/1770) - Better resilience against null bytes received from the printer for whatever reason.
- [#1770](https://github.com/foosel/OctoPrint/issues/1770) - Detect printer as connected even when only receiving a `wait` instead of `ok`. Should solve issues with initial connect where printer sends garbage over the line that eats/covers the `ok` if printer also sends regular `wait` messages when idle.
- [#1780](https://github.com/foosel/OctoPrint/issues/1780) - Work around for Safari re-opening one copy of the webcam stream after the other and eating up bandwidth unnecessarily (see also [#1786](https://github.com/foosel/OctoPrint/issues/1786))
- [#1790](https://github.com/foosel/OctoPrint/issues/1790) - Removed unused "color" property from printer profile editor.
- [#1805](https://github.com/foosel/OctoPrint/issues/1805) - Better error resilience against invalid print history data from plugins that replace the printer communication.
- Better error resilience in Plugin Manager against wonky version data in repository file.
- Added a "Restart in safe mode" system menu entry that will always be available if the restart command is configured
- CLI: Only offer `daemon` sub command on Linux (since that it's the only OS it works on)
- Less throttling of analysis of GCODE files from the analysis backlog. Should still leave Pi and friends air to breathe but allow a slightly faster processing of the backlog.
- Added an explanation of safe mode to the docs.
- Log OctoPrint version & plugin list when detecting log rollover.
- Allow `UiPlugin`s to define additional fields for ETag generation.
- Allow `UiPlugin`s utilizing OctoPrint's stock templates to filter out what they don't need.
- Locales contained in `translations` of plugins will now be registered with the system. That way it's possible to provide translations for the full application through plugins.
- Abort file analysis if file is about to be overwritten
- Software Update Plugin: Refresh cache on startup, prevent concurrent refresh
- More solid parsing of request line number for resend requests. Should improve compatibility with Teacup firmwares. Based on issue reported via PR [#300](https://github.com/foosel/OctoPrint/pull/300)

### Bug fixes

- [#733](https://github.com/foosel/OctoPrint/issues/733) - Fixed multiple event handler commands running concurrently. Now they run one after the other, as expected.
- [#1317](https://github.com/foosel/OctoPrint/issues/1317) - Fixed a color distortion issue when rendering timelapses from higher resolution source snapshots that also need to be rotated by adjusting `ffmpeg` parameters to avoid an unexpected behaviour when a pixel format and a filter chain are required for processing.
- [#1560](https://github.com/foosel/OctoPrint/issues/1560) - Make sure we don't try to use an empty `logging.yaml`
- [#1631](https://github.com/foosel/OctoPrint/issues/1631) - Disable "Slice" button in slice dialog if a print is ongoing and a slicer is selected that runs on the same device as OctoPrint. The server would already deny such requests (simply due to performance reasons), but the UI didn't properly reflect that yet.
- [#1671](https://github.com/foosel/OctoPrint/issues/1671) - Removed "Hide empty folders" option from file list. Didn't really add value and caused usability issues.
- [#1771](https://github.com/foosel/OctoPrint/issues/1771) - Fixed `_config_version` in plugin settings not being properly updated.
- [#1732](https://github.com/foosel/OctoPrint/issues/1732) - Fixed a bug in the documentation for the printer profile API
- [#1760](https://github.com/foosel/OctoPrint/issues/1760) - Fixed missing reselect of selected file when updating via the watched folder, causing wrong progress percentages to be reported.
- [#1765](https://github.com/foosel/OctoPrint/issues/1765) - Fixed watched folder not waiting with file move until file stopped growing, causing wrong progress percentages to be reported.
- [#1777](https://github.com/foosel/OctoPrint/issues/1777) - Fixed z-change based timelapses with Slic3r generated z-hops not properly triggering snapshots.
- [#1792](https://github.com/foosel/OctoPrint/issues/1792) - Don't tell Safari we are "web-app-capable" because that means it will throw away all cookies and the user will have to constantly log in again when using a desktop shortcut for the OctoPrint instance.
- [#1812](https://github.com/foosel/OctoPrint/issues/1812) - Don't scroll up navigation in settings when switching between settings screens, very annoying on smaller resolutions (see also [#1814](https://github.com/foosel/OctoPrint/pull/1814))
- Fix settings helper not allowing to delete values for keys that are present in the local config but not in the defaults.
- Fix wrong replacement value for `__progress` in registered command line or GCODE [event handlers](http://docs.octoprint.org/en/master/events/index.html).
- Various fixes in the Software Update Plugin:
  - Don't remove manual software update configurations on settings migration.
  - Properly delete old restart/reboot commands that are now defined globally since config version 4. An issue with the settings helper prevented us from properly deleting them during migration to version 4.
  - Fixed `python_checker` version check method and `python_updater` update method.
  - Fixed update configs without a restart of any kind causing an issue due to an undefined variable.
  - Fixed broken doctests.
- Upgrade LESS.min.js from 2.7.1 to 2.7.2 to fix the broken contrast function
- Always create a new user session for requests with an API key
- Fixed an error when reading all user settings via the API
- Fixed a bunch of caching issues for the page, was not properly updated on change of snapshot URL presence, system menu entry presence, gcode viewer enabled/disabled, changes in access control availability.
- Fixed wrong bundling of core and plugin assets
- Software Update Plugin: Fixed wrong ETag calculation
- Disable external heatup detection until firmware is detected
- Fixed login dropdown not closing on click outside of it
- Fixed new user settings getting lost until restart
- Don't call `onUserLoggedIn`/`onUserLoggedOut` on user reload

### More information

- [Commits](https://github.com/foosel/OctoPrint/compare/1.3.1...1.3.2)
- Release Candidates:
  - [1.3.2rc1](https://github.com/foosel/OctoPrint/releases/tag/1.3.2rc1)

## 1.3.1 (2017-01-25)

### Note for upgraders

#### If you installed OctoPrint manually and used the included init script, you need to update that

The init script so far shipped with OctoPrint contained a [bug](https://github.com/foosel/OctoPrint/issues/1657) that causes issues with OctoPrint 1.3.0 and higher. Please update your init script to the fixed version OctoPrint now ships under `scripts`:

```
sudo cp /path/to/OctoPrint/scripts/octoprint.init /etc/init.d/octoprint
```

If you are running OctoPi, this does **not** apply to you and you do not need to do anything here!

#### Change in stock terminal filter configuration

1.3.1 fixes an issue with the two terminal filters for suppressing temperature and SD status messages and adds a new filter for filtering out firmware `wait` messages. These changes will only be active automatically though for stock terminal filter configurations. If you have customized your terminal filters, you'll need to apply these changes manually under "Settings > Terminal filters":
- Changed "Suppress temperature messages" filter, new regex is `(Send: (N\d+\s+)?M105)|(Recv: ok (B|T\d*):)`
- Changed "Suppress SD status messages" filter, new regex is `(Send: (N\d+\s+)?M27)|(Recv: SD printing byte)`
- New "Suppress wait responses" filter, regex is `Recv: wait`

### Improvements
- [#1607](https://github.com/foosel/OctoPrint/issues/1607) - Way better support for password managers (e.g. browser built-in, 1Password, Lastpass, Dashlane)
- [#1638](https://github.com/foosel/OctoPrint/issues/1638) - Make confirmation dialog when cancelling a print optional.
- [#1656](https://github.com/foosel/OctoPrint/issues/1656) - Make wording of buttons on print cancel dialog less confusing.
- [#1705](https://github.com/foosel/OctoPrint/pull/1705) - Simplified install process on Mac by removing dependency on pyobjc.
- [#1706](https://github.com/foosel/OctoPrint/pull/1706) - Added a mask icon for Safari pinned tab and touchbar.
- Support extraction of filament diameter for volume calculation from GCODE files sliced through Simplify3D.
- Abort low priority jobs in the file analysis queue when a high priority job comes in - should make file analysis and hence time estimates show up faster for newly uploaded files.
- Added a terminal filter for firmware `wait` messages to the stock terminal filters. If you did modify your terminal filter configuration, you might want to add this manually:
  - New "Suppress wait responses" filter: `Recv: wait`

### Bug fixes

- [#1344](https://github.com/foosel/OctoPrint/issues/1344) - Fix ProgressBarPlugins to not correctly be triggered for 0% (second try, this time hopefully for good).
- [#1637](https://github.com/foosel/OctoPrint/issues/1637) - Fix issue preventing a folder to be deleted that has a name which is a common prefix of the file currently being printed.
- [#1641](https://github.com/foosel/OctoPrint/issues/1641) - Fix issue with `octoprint --daemon` not working.
- [#1647](https://github.com/foosel/OctoPrint/issues/1647) - Fix issue with `octoprint` command throwing an error if an environment variable `OCTOPRINT_VERSION` was set to its version number.
- [#1648](https://github.com/foosel/OctoPrint/issues/1648) - Added missing `websocket-client` dependency of `octoprint client` to install script.
- [#1653](https://github.com/foosel/OctoPrint/issues/1653) - Fix for an issue with the included init script on the BBB (see also [#1654](https://github.com/foosel/OctoPrint/issues/1654))
- [#1657](https://github.com/foosel/OctoPrint/issues/1657) - Fix init script regarding check for configured `CONFIGFILE` variable.
- [#1657](https://github.com/foosel/OctoPrint/issues/1657) - Don't care about ordering of common parameters (like `--basedir`, `--config`) on CLI.
- [#1660](https://github.com/foosel/OctoPrint/issues/1660) - Do not show hint regarding keyboard controls beneath webcam stream if keyboard control feature is disabled.
- [#1667](https://github.com/foosel/OctoPrint/issues/1667) - Fix for matching folders not getting listed in the results when performing a search in the file list.
- [#1675](https://github.com/foosel/OctoPrint/issues/1675) - Fix model size calculation in GCODE analysis, produced wrong values in some cases. Also adjusted calculation to match implementation in GCODE viewer, now both produce identical results.
- [#1685](https://github.com/foosel/OctoPrint/issues/1685) - Cura Plugin: Fix filament extraction from CuraEngine slicing output
- [#1692](https://github.com/foosel/OctoPrint/issues/1692) - Cura Plugin: Fix solid layer calculation (backport from [Ultimaker/CuraEngine#140](https://github.com/Ultimaker/CuraEngine/issues/140))
- [#1693](https://github.com/foosel/OctoPrint/issues/1693) - Cura Plugin: Support `perimeter_before_infill` profile setting. Additionally added support for `solidarea_speed`, `raft_airgap_all`, `raft_surface_thickness`, `raft_surface_linewidth` profile settings and adjusted mapping for engine settings `raftAirGapLayer0`, `raftFanSpeed`, `raftSurfaceThickness`and `raftSurfaceLinewidth` according to current mapping in Cura Legacy and adjusted Mach3 GCODE flavor to substitute `S` with `P` in temperature commands of generated start code, also like in Cura Legacy.
- [#1697](https://github.com/foosel/OctoPrint/issues/1697) - Pin Jinja to versions <2.9 for now due to a backwards compatibility issue with templates for versions newer than that. Also pushed as a hotfix to 1.3.0 (as 1.3.0post1).
- [#1708](https://github.com/foosel/OctoPrint/issues/1708) - Cura Plugin: Fixed selection of `start.gcode` for sliced file
- Allow a retraction z-hop of 0 in timelapse configuration.
- Fix files in sub folders to not be processed by the initial analysis backlog check during startup of the server.
- Various fixes in the file analysis queue:
  - High priority items are now really high priority
  - Abort analysis for items that are to be deleted/moved to get around an issue with file access under Windows systems.
- Fix stock terminal filters for suppressing temperature messages and SD status messages to also be able to deal with line number prefixes. If you have added additional terminal filters, you will have to apply this fix manually:
  - Changed "Suppress temperature messages" filter: `(Send: (N\d+\s+)?M105)|(Recv: ok (B|T\d*):)`
  - Changed "Suppress SD status messages" filter: `(Send: (N\d+\s+)?M27)|(Recv: SD printing byte)`
- Fix issue in german translation.

### More information

- [Commits](https://github.com/foosel/OctoPrint/compare/1.3.0...1.3.1)
- Release Candidates:
  - [1.3.1rc1](https://github.com/foosel/OctoPrint/releases/tag/1.3.1rc1)
  - [1.3.1rc2](https://github.com/foosel/OctoPrint/releases/tag/1.3.1rc2)

## 1.3.0 (2016-12-08)

### Features

  * You can now create folders in the file list, upload files into said folders and thus better manage your projects' files.
  * New wizard dialog for system setups that can also be extended by plugins. Replaces the first run dialog for setting up access control and can also be triggered in other cases than only the first run, e.g. if plugins necessitate user input to function properly. Added wizards to help configuring the following components in OctoPrint on first run: access control, webcam URLs & ffmpeg path, server commands (restart, shutdown, reboot), printer profile. Also extended the bundled Cura plugin to add a wizard for its first setup to adjust path and import a slicing profile, and the bundled Software Update plugin to ask the user for details regarding the OctoPrint update configuration. Also see below.
  * New command line interface (CLI). Offers the same functionality as the old one plus:
    * a built-in API client (``octoprint client --help``)
    * built-in development tools (``octoprint dev --help``)
    * extendable through plugins implementing the ``octoprint.cli.commands`` hook (``octoprint plugins --help``)
  * New features within the plugin system:
    * Plugins may now give hints in which order various hooks or mixin methods should be called by optionally providing an integer value that will be used for sorting the callbacks prior to execution.
    * Plugins may now define configuration overlays to be applied on top of the default configuration but before ``config.yaml``.
    * New mixin `UiPlugin` for plugins that want to provide an alternative web interface delivered by the     server.
    * New mixin ``WizardPlugin`` for plugins that want to provide wizard components to OctoPrint's new wizard dialog.
    * New hook ``octoprint.cli.commands`` for registering a command with the new OctoPrint CLI
    * New hook ``octoprint.comm.protocol.gcode.received`` for receiving messages from the printer
    * New hook ``octoprint.printer.factory`` for providing a custom factory to contruct the global ``PrinterInterface`` implementation.
    * New ``TemplatePlugin`` template type: ``wizard``
  * New Javascript client library for utilizing the server's API, can be reused by `UiPlugin`s.
  * OctoPrint will now track the current print head position on pause and cancel and provide it as new template variables ``pause_position``/``cancel_position`` for the relevant GCODE scripts. This will allow more intelligent pause codes that park the print head at a rest position during pause and move it back to the exact position it was before the pause on resume ([Example](https://gist.github.com/foosel/1c09e269b1c0bb7a471c20eef50c8d3e)). Note that this is NOT enabled by default and for now will necessitate adjusting the pause and resume GCODE scripts yourself since position tracking with multiple extruders or when printing from SD is currently not fool proof thanks to firmware limitations regarding reliable tracking of the various ``E`` values and the currently selected tool ``T``. In order to fully implement this feature, the following improvements were also done:
    * New ``PositionUpdated`` event when OctoPrint receives a response to an ``M114`` position query.
    * Extended ``PrintPaused`` and ``PrintCancelled`` events with position data from ``M114`` position query on print interruption/end.
  * Added (optional) firmware auto detection. If enabled (which it is by default), OctoPrint will now send an ``M115`` to the printer on initial connection in order to try to figure out what kind of firmware it is. For FIRMWARE_NAME values containing "repetier" (case insensitive), all Repetier-specific flags will be set on the comm layer. For FIRMWARE_NAME values containing "reprapfirmware" (also case insensitive), all RepRapFirmware-specific flags will be set on the comm layer. For now no other handling will be performed.
  * Added safe mode flag ``--safe`` and config setting ``startOnceInSafeMode`` that disables all third party plugins when active. The config setting will automatically be removed from `config.yaml` after the server has started through successfully.
  * Added ``octoprint config`` CLI that allows easier manipulation of config.yaml entries from the command line. Example: ``octoprint config set --bool server.startOnceInSafeMode true``

### Improvements

  * [#1048](https://github.com/foosel/OctoPrint/issues/1048) - Added "Last print time" to extended file information (see also [#1522](https://github.com/foosel/OctoPrint/pull/1522))
  * [#1422](https://github.com/foosel/OctoPrint/issues/1422) - Added option for post roll for timed timelapse to duplicate last frame instead of capturing new frames. That makes for a faster render at the cost of a still frame at the end of the rendered video. See also [#1553](https://github.com/foosel/OctoPrint/pull/1553).
  * [#1551](https://github.com/foosel/OctoPrint/issues/1551) - Allow to define a custom bounding box for valid printer head movements in the printer profile, to make print dimension check more flexible.
  * [#1583](https://github.com/foosel/OctoPrint/pull/1583) - Strip invalid `pip` arguments from `pip uninstall` commands, if provided by the user as additional pip arguments.
  * [#1593](https://github.com/foosel/OctoPrint/issues/1593) - Automatically migrate old manual system commands for restarting OctoPrint and rebooting or shutting down the server to the new system wide configuration settings. Make a backup copy of the old `config.yaml` before doing so in case a manual rollback is required.
  * New central configuration option for commands to restart OctoPrint and to restart and shut down the system OctoPrint is running on. This allows plugins (like the Software Update Plugin or the Plugin Manager) and core functionality to perform these common administrative tasks without the user needing to define everything redundantly.
  * `pip` helper now adjusts `pip install` parameters corresponding to detected `pip` version:
    * Removes `--process-dependency-links` when it's not needed
    * Adds `--no-use-wheel` when it's needed
    * Detects and reports on completely broken versions
  * Better tracking of printer connection state for plugins and scripts:
    * Introduced three new Events `Connecting`, `Disconnecting` and `PrinterStateChanged`.
    * Introduced new GCODE script `beforePrinterDisconnected` which will get sent before a (controlled) disconnect from the printer. This can be used to send some final commands to the printer before the connection goes down, e.g. `M117 Bye from OctoPrint`.
    * The communication layer will now wait for the send queue to be fully processed before disconnecting from the printer for good. This way it is ensured that the `beforePrinterDisconnected` script or any further GCODE injected into it will actually get sent.
  * Additional baud rates to allow for connecting can now be specified along side additional serial ports via the settings dialog and the configuration file.
  * Option to never send checksums (e.g. if the printer firmware doesn't support it), see [#949](https://github.com/foosel/OctoPrint/issues/949).
  * Added secondary temperature polling interval to use when printer is not printing but a target temperature is set - this way the graph should be more responsive while monitoring a manual heatup.
  * Test buttons for webcam snapshot & stream URL, ffmpeg path and some other settings (see also [#183](https://github.com/foosel/OctoPrint/issues/183)).
  * Temperature graph automatically adjusts its Y axis range if necessary to accomodate the plotted data (see also [#632](https://github.com/foosel/OctoPrint/issues/632)).
  * "Fan on" command now always sends `S255` parameter for better compatibility across firmwares.
  * Warn users with a notification if a file is selected for printing that exceeds the current print volume (if the corresponding model data is available, see also [#1254](https://github.com/foosel/OctoPrint/pull/1254))
  * Added option to also display temperatures in Fahrenheit (see also [#1258] (https://github.com/foosel/OctoPrint/pull/1258))
  * Better error message when the ``config.yaml`` file is invalid during startup
  * API now also allows issuing absolute jogging commands to the printer
  * Printer profile editor dialog refactored to better structure fields and explain where they are used
  * Option to detect z-hops during z-based timelapses and not trigger a snapshot (see also [1148](https://github.com/foosel/OctoPrint/pull/1148))
  * File rename, move and copy functionality exposed via API, not yet utilized in stock frontend but available in [file manager plugin](https://github.com/Salandora/OctoPrint-FileManager).
  * Try to assure a sound SSL environment for the process at all times
  * Improved caching:
    * Main page and asset files now carry proper ``ETag`` and ``Last-Modified`` headers to allow for sensible browser-side caching
    * API sets ``Etag`` and/or ``Last-Modified`` headers on responses to GET requests where possible and feasible to allow for sensible browser-side caching
  * Renamed ``GcodeFilesViewModel`` to ``FilesViewModel`` - plugin authors should accordingly update their dependencies from ``gcodeFilesViewModel`` to ``filesViewModel``. Using the old name still works, but will log a warning and stop working with 1.4.x.
  * Make sure ``volume.depth`` for circular beds is forced to ``volume.width`` in printer profiles
  * Support for `M116`
  * Support ``M114`` responses without whitespace between coordinates (protocol consistency - who needs it?).
  * `M600` is now marked as a long running command by default.
  * Don't focus files in the file list after deleting a file - made the list too jumpy.
  * Cura plugin: "Test" button to check if path to cura engine is valid.
  * Cura plugin: Wizard component for configuring the path to the CuraEngine binary and for importing the first slicing profile
  * GCODE viewer: Added Layer Up/Down buttons (see also [#1306] (https://github.com/foosel/OctoPrint/pull/1306))
  * GCODE viewer: Allow cycling through layer via keyboard (up, down, pgup, pgdown)
  * GCODE viewer: Allow changing size thresholds via settings menu (see also [#1308](https://github.com/foosel/OctoPrint/pull/1308))
  * GCODE viewer: Added support for GCODE arc commands (see also [#1382](https://github.com/foosel/OctoPrint/pull/1382))
  * Language packs: Limit upload dialog for language pack archives to .zip, .tar.gz, .tgz and .tar extensions.
  * Plugin Manager: Adjusted to utilize new `pip` helper
  * Plugin Manager: Show restart button on install/uninstall notification if restart command is configured and a restart is required
  * Plugin Manager: Track managable vs not managable plugins
  * Plugin Manager: Allow hiding plugins from Plugin Manager via ``config.yaml``.
  * Plugin Manager: Limit upload dialog for plugin archives to .zip, .tar.gz, .tgz and .tar extensions.
  * Plugin Manager: Allow closing of all notifications and close them automatically on detected server disconnect. No need to keep a "Restart needed" message around if a restart is in progress.
  * Software Update plugin: More verbose output for logged in administrators. Will now log the update commands and their output similar to the Plugin Manager install and uninstall dialog.
  * Software Update plugin: CLI for checking for and applying updates
  * Software Update plugin: Wizard component for configuring OctoPrint's update mechanism
  * Software Update plugin: "busy" spinner on check buttons while already checking for updates.
  * Software Update plugin: Prevent update notification when wizard is open.
  * Plugin Manager / Software Update plugin: The "There's a new version of pip" message during plugin installs and software updates is no longer displayed like an error.
  * Plugin Manager / Software Update plugin: The "busy" dialog can no longer be closed accidentally.
  * Timelapse: Better (& earlier) reporting to the user when something's up with the snapshot URL causing issues with capturing timelapse frames and hence making it impossible to render a timelapse movie on print completion.
  * Virtual printer: Usage screen for the ``!!DEBUG`` commands on ``!!DEBUG``, ``!!DEBUG:help`` or ``!!DEBUG:?``
  * Updated frontend dependencies (possibly relevant for plugin authors):
    * Bootstrap to 2.3.2
    * JQuery to 2.2.4
    * Lodash to 3.10.1
    * SockJS to 1.1.1
  * Better error resilience against errors in UI components.
  * Various improvements in the GCODE interpreter which performs the GCODE analysis
  * Various adjustments towards Python 3 compatibility (still a work in progress though, see also [#1411](https://github.com/foosel/OctoPrint/pull/1411), [#1412](https://github.com/foosel/OctoPrint/pull/1412), [#1413](https://github.com/foosel/OctoPrint/pull/1413), [#1414](https://github.com/foosel/OctoPrint/pull/1414))
  * Various code refactorings
  * Various small UI improvements
  * Various documentation improvements

### Bug fixes

  * [#1047](https://github.com/foosel/OctoPrint/issues/1047) - Fixed 90 degree webcam rotation for iOS Safari.
  * [#1148](https://github.com/foosel/OctoPrint/issues/1148) - Fixed retraction z hop setting for Z-triggered timelapses. Was not correctly propagated to the backend and hence not taking effect.
  * [#1567](https://github.com/foosel/OctoPrint/issues/1567) - Invalidate ``/api/settings`` cache on change of the user's login state (include user roles into ETag calculation).
  * [#1586](https://github.com/foosel/OctoPrint/issues/1586) - Fixed incompatibility of update script and command line helper with non-ASCII output from called commands.
  * [#1588](https://github.com/foosel/OctoPrint/issues/1588) - Fixed feedback controls again.
  * [#1599](https://github.com/foosel/OctoPrint/issues/1599) - Properly handle exceptions that arise within the update script during runtime.
  * It's not possible anymore to select files that are not machinecode files (e.g. GCODE) for printing on the file API.
  * Changes to a user's personal settings via the UI now propagate across sessions.
  * Improved compatibility of webcam rotation CSS across newer browsers (see also [#1436](https://github.com/foosel/OctoPrint/pull/1436))
  * Fix for system menu not getting properly reloaded after entries changed
  * Invalidate ``/api/settings`` cache on change of the currently enabled plugins (by including plugin names into ETag calculation) and/or on change of the current effective config.
  * Fix for `/api/settings` not being properly invalidated for plugin settings that do not have a representation in `config.yaml` but are only added at runtime (and hence are not captured by `config.effective`).
  * Invalidate ``/api/timelapse`` cache on change of the current timelapse configuration.
  * Fixed an issue causing the version number not to be properly extracted from ``sdist`` tarballs generated under Windows.
  * Get rid of double scroll bar in printer profile editor.
  * Fixed tracking of current byte position in file being streamed from disk. Turns out that ``self._handle.tell`` lied to us thanks to line buffering.
  * Fixed select & print not working anymore for SD files thanks to a timing issue.
  * Fixed ``PrintFailed`` event payload (was still missing new folder relevant data).
  * Fixed premature parse stop on ``M114`` and ``M115`` responses with ``ok``-prefix.
  * Make sure `?l10n` request parameter gets also propagated to API calls as `X-Locale` header in case of locale sensitive API responses.
  * Fix language mixture due to cached template configs including localized strings; cache per locale.
  * Only insert divider in system menu after core commands if there are custom commands.
  * Fix update of webcam stream URL not being applied due to caching.
  * Fixed a rare race condition causing the new "The settings changed, reload?" popup to show up even when the settings change originated in the same client instance.
  * Fixed a bunch of missing translations.
  * Pinned Tornado version to 4.0.2. Former version requirement was able to pull in a beta version causing issues with websockets due to a bug in `permessage-deflate` handling. The Tornado requirement needs an update, but we'll leave it at 4.0.2 for 1.3.0 since we'll need to do some migration work for compatibility with anything newer. Potentially related to [#1523](https://github.com/foosel/OctoPrint/issues/1523).
  * Fix a rare race condition in the command line helper and the update script that could cause the code to hang due to waiting on an event that would never be set.
  * Fix issue with handling new settings substructures when they are compared to existing settings data in order to find the structural diff.
  * Fix for the temperature graph not displaying the data history on site reload.

### More information

  * [Commits](https://github.com/foosel/OctoPrint/compare/1.2.18...1.3.0)
  * Release Candidates:
    * [1.3.0rc1](https://github.com/foosel/OctoPrint/releases/tag/1.3.0rc1)
    * [1.3.0rc2](https://github.com/foosel/OctoPrint/releases/tag/1.3.0rc2)
    * [1.3.0rc3](https://github.com/foosel/OctoPrint/releases/tag/1.3.0rc3)

---

For even older changes, please refer to [the Github releases page](https://github.com/foosel/OctoPrint/releases).
