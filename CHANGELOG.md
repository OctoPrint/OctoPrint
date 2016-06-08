# OctoPrint Changelog

## 1.2.12 (2016-06-09)

### Improvements

  * [#1338](https://github.com/foosel/OctoPrint/issues/1338): Threshold configuration fields now include information about how to specify the thresholds.
  * Mark unrendered timelapses currently being processed (recording or rendering) in the list and remove action buttons so no accidental double-processing can take place.
  * Removed file extension from "rendering" and "rendered" notifications, was misleading when using the [mp4 wrapper script](https://github.com/guysoft/OctoPi/issues/184).
  * Added some new events for manipulation of slicing profiles.
  * Small fix of the german translation.

### Bug Fixes

  * [#1314](https://github.com/foosel/OctoPrint/issues/1314): Do not change the extension of `.g` files being uploaded to SD (e.g. `auto0.g`)
  * [#1320](https://github.com/foosel/OctoPrint/issues/1320): Allow deletion of *.mp4 timelapse files (see [this wrapper script](https://github.com/guysoft/OctoPi/issues/184)).
  * [#1324](https://github.com/foosel/OctoPrint/issues/1324): Make daemonized OctoPrint properly clean up its pid file again (see also [#1330](https://github.com/foosel/OctoPrint/pull/1330)).
  * [#1326](https://github.com/foosel/OctoPrint/issues/1326): Do not try to clean up an unrendered timelapse while it is already being deleted (and produce way too much logging output in the process).
  * [#1343](https://github.com/foosel/OctoPrint/issues/1343): Events are now processed in the order they are fired in, making e.g. the "timelapse rendering" message always appear before "timelapse failed" and hence not stay on forever in case of a failed timelapse.
  * [#1344](https://github.com/foosel/OctoPrint/issues/1344): `ProgressPlugin`s now get also notified about a progress of 0%.
  * [#1357](https://github.com/foosel/OctoPrint/issues/1357): Fixed wrongly named method call on editing access control options for a user, causing that to not work properly.
  * [#1361](https://github.com/foosel/OctoPrint/issues/1361): Properly reload profile list for currently selected slicer in the slicing dialog on change of profiles.
  * [#1364](https://github.com/foosel/OctoPrint/issues/1364): Fixed a race condition that could cause the UI to not initialize correctly due to 401 errors, leaving it in an unusable state until a reload.
  * Fixed concurrent message pushing to the frontend being able to break push messages for the session by forcing synchronization of SockJS message sending.
  * Do not require admin rights for connecting/disconnecting, like it was in 1.1.x (note that this is supposed to become configurable behaviour once [#1110](https://github.com/foosel/OctoPrint/issues/1110) gets implemented)

([Commits](https://github.com/foosel/OctoPrint/compare/1.2.11...1.2.12))

## 1.2.11 (2016-05-04)

### Important Announcement

Due to a recent change in the financial situation of the project, the funding of OctoPrint is at stake. If you love OctoPrint and want to see its development continue at the pace of the past two years, please read on about its current funding situation and how you can help: ["I need your support"](http://octoprint.org/blog/2016/04/13/i-need-your-support/).

### Improvements

  * Added option to treat resend requests as `ok` for such firmwares that do not send an `ok` after requesting a resend. If you printer communication gets stalled after a resend request from the firmware, try checking this option.
  * Added an "About" dialog to properly inform about OctoPrint's license, contributors and supporters.
  * Added a announcement plugin that utilizes the RSS feeds of the [OctoPrint Blog](http://octoprint.org/blog/) and the [plugin repository](http://plugins.octoprint.org) to display news to the user. By default only the "important announcement" category is enabled. This category will only be used for very rare situations such as making you aware of critical updates or important news. You can enable further categories (with more announcements to be expected) in the plugin's settings dialog.

### Bug Fixes

  * [#1300](https://github.com/foosel/OctoPrint/issues/1300) - Removed possibility to accidentally disabling local file list by first limiting view to files from SD and then disabling SD support.
  * [#1315](https://github.com/foosel/OctoPrint/issues/1315) - Fixed broken post roll on z-based timelapses.
  * Fixed CSS data binding syntax on the download link in the files list
  * Changed control distance from jQuery data into a knockout observerable and observerableArray
  * Allow an unauthorized user to logout from a logedin interface state

([Commits](https://github.com/foosel/OctoPrint/compare/1.2.10...1.2.11))

## 1.2.10 (2016-03-16)

### Improvements

  * Improved performance of console output during plugin installation/deinstallation
  * Slight performance improvements in the communication layer
  * Log small log excerpt to `octoprint.log` upon encountering a communication error.
  * Changed wording in "firmware error" notifications to better reflect that there was an error while communicating with the printer, since the error condition can also be triggered by serial errors while trying to establish a connection to the printer or when already connected.
  * Support downloading ".mp4" timelapse files. You'll need a [custom wrapper script for timelapse rendering](https://github.com/guysoft/OctoPi/issues/184) for this to be relevant to you. See also [#1255](https://github.com/foosel/OctoPrint/pull/1255)
  * The communication layer will now wait up to 10s after clicking disconnect in order to send any left-over lines from its buffers.
  * Moved less commonly used configuration options in Serial settings into "Advanced options" roll-out.

### Bug Fixes

  * [#1224](https://github.com/foosel/OctoPrint/issues/1224) - Fixed an issue introduced by the fix for [#1196](https://github.com/foosel/OctoPrint/issues/1196) that had the "Upload to SD" button stop working correctly.
  * [#1226](https://github.com/foosel/OctoPrint/issues/1226) - Fixed an issue causing an error on disconnect after or cancelling of an SD print, caused by the unsuccessful attempt to record print recovery data for the file on the printer's SD card.
  * [#1268](https://github.com/foosel/OctoPrint/issues/1268) - Only add bed temperature line to temperature management specific start gcode in CuraEngine invocation if a bed temperature is actually set in the slicing profile.
  * [#1271](https://github.com/foosel/OctoPrint/issues/1271) - If a communication timeout occurs during an active resend request, OctoPrint will now not send an `M105` with an increased line number anymore but repeat the last resent command instead.
  * [#1272](https://github.com/foosel/OctoPrint/issues/1272) - Don't add an extra `ok` for `M28` response.
  * [#1273](https://github.com/foosel/OctoPrint/issues/1273) - Add an extra `ok` for `M29` response, but only if configured such in "Settings" > "Serial" > "Advanced options" > "Generate additional ok for M29"
  * [#1274](https://github.com/foosel/OctoPrint/issues/1274) - Trigger `M20` only once after finishing uploading to SD
  * [#1275](https://github.com/foosel/OctoPrint/issues/1275) - Prevent `M105` "cascade" due to communication timeouts
  * Fixed wrong tracking of extruder heating up for `M109 Tn` commands in multi-extruder setups.
  * Fixed start of SD file uploads not sending an `M110`.
  * Fixed job data not being reset when disconnecting while printing.

([Commits](https://github.com/foosel/OctoPrint/compare/1.2.9...1.2.10))

## 1.2.9 (2016-02-10)

### Improvements

  * [#318](https://github.com/foosel/OctoPrint/issues/318) - Snapshots for timelapses are now named in a non-colliding, job-based way, allowing a new timelapse to start while the other is still being rendered (although printing with an active timelapse rendering job is not recommended and will be solved with a proper render job queue in a later version). Timelapses that were not successfully rendered are kept for 7 days (configurable, although not via the UI so far) and can be manually rendered or deleted through a new UI component within the timelapse tab that shows up if unrendered timelapses are detected.
  * [#485](https://github.com/foosel/OctoPrint/issues/485) - "Timelapse rendering" notification is now persistent, even across reloads/client switches. That should make it easier to see that a rendering job is currently in progress.
  * [#939](https://github.com/foosel/OctoPrint/issues/939) - Updated to Knockout 3.4.0
  * [#1204](https://github.com/foosel/OctoPrint/issues/1204) - Display total print time as estimated by GCODE viewer on GCODE viewer tab. That will allow access to an estimate even if the server hadn't yet calculated that when a print started. Note that due to slightly different implementation server and client side the resulting estimate might differ.
  * OctoPrint now serves an intermediary page upon start that informs the user about the server still starting up. Once the server is detected as running, the page automatically switches to the standard interface.
  * OctoPrint now displays a link to the release notes of an updated component in the update notification, the update confirmation and the version overview in the settings dialog. Please always make sure to at least skim over the release notes for new OctoPrint releases, they might contain important information that you need to know before updating.
  * Improved initial page loading speeds by introducing a preemptive cache. OctoPrint will now record how you access it and on server start pre-render the page so it's ideally available in the server-side cache when you try to access it.
  * Initialize login user name and password with an empty string and clear both on successful login (see [#1175](https://github.com/foosel/OctoPrint/pull/1175)).
  * Added a "Refresh" button to the file list for people who modify the stored files externally (doing this is not encouraged however due to reasons of book keeping, e.g. metadata tracking etc).
  * "Save" button on settings dialog is now disabled while background tasks (getting or receiving config data from the backend) are in progress.
  * Improved performance of terminal tab on lower powered clients. Adaptive rate limiting now ensures the server backs off with log updates if the client can't process them fast enough. If the client is really slow, log updates get disabled automatically during printing. This behaviour can be disabled with override buttons in the terminal tab's advanced options if necessary.
  * Added option to ignore any unhandled errors reported by the firmware and another option to only cancel ongoing prints on unhandled errors from the firmware (instead of instant disconnect that so far was the default).
  * Made version compatibility check PEP440 compliant (important for plugin authors).
  * Do not hiccup on manually sent `M28` commands.
  * Persist print recovery data on print failures (origin and name of printed file, position in file when print was aborted, time and date of print failure). Currently this data isn't used anywhere, but it [can be accessed from plugins in order to add recovery functionality](https://github.com/foosel/OctoPrint-PrintRecoveryPoc) to OctoPrint.
  * Small performance improvements in update checks.
  * The file upload dialog will now only display files having an extension that's supported for upload (if the browser supports it, also see [#1196](https://github.com/foosel/OctoPrint/issues/1196)).

### Bug Fixes

  * [#1007](https://github.com/foosel/OctoPrint/issues/1007) - Don't enable the "Print" button if no print job is selected.
  * [#1181](https://github.com/foosel/OctoPrint/issues/1181) - Properly slugify UTF-8 only file names.
  * [#1196](https://github.com/foosel/OctoPrint/issues/1196) - Do not show drag-n-drop overlay if server is offline.
  * [#1208](https://github.com/foosel/OctoPrint/issues/1208) - Fixed `retraction_combing` profile setting being incorrectly used by bundled Cura plugin (see [#1209](https://github.com/foosel/OctoPrint/pull/1209))
  * Fixed OctoPrint compatibility check in the plugin manager, could report `False` for development versions against certain versions of Python's `setuptools` (thanks to @ignaworm who stumbled over this).
  * Fixed a missing parameter in `PluginSettings.remove` call (see [#1177](https://github.com/foosel/OctoPrint/pull/1177)).
  * Docs: Fixed the example for a custom `M114` control to also match negative coordinates.
  * Reset scroll position in settings dialog properly when re-opening it or switching tabs.
  * Fixed an issue that prevented system menu entries that were added to a so far empty system menu make the menu show up.
  * Fixed an issue that made requests to restricted resources fail even though the first run wizard had been completed successfully.
  * Fixed an issue where an unknown command or the suppression of a command could cause the communication to stall until a communication timeout was triggered.
  * Strip [unwanted ANSI characters](https://github.com/pypa/pip/issues/3418) from output produced by pip versions 8.0.0, 8.0.1 and 8.0.3 that prevents our plugin installation detection from working correctly.

([Commits](https://github.com/foosel/OctoPrint/compare/1.2.8...1.2.9))

## 1.2.8 (2015-12-07)

### Notes for Upgraders

#### A bug in 1.2.7 prevents directly updating to 1.2.8, here's what to do

A bug in OctoPrint 1.2.7 (fixed in 1.2.8) prevents updating OctoPrint to version
1.2.8. If you try to perform the update, you will simply be told that "the update
was successful", but the update won't actually have taken place. To solve this
hen-egg-problem, a plugin has been made available that fixes said bug (through
monkey patching).

The plugin is called "Updatefix 1.2.7" and can be found
[in the plugin repository](http://plugins.octoprint.org/plugins/updatefix127/)
and [on Github](https://github.com/OctoPrint/OctoPrint-Updatefix-1.2.7/).

Before attempting to update your installation from version 1.2.7 to version 1.2.8,
please install the plugin via your plugin manager and restart your server. Note that
you will only see it in the Plugin Manager if you need it, since it's only compatible with
OctoPrint version 1.2.7. After you installed the plugin and restarted your server
you can update as usual. The plugin will self-uninstall once it detects that it's
running under OctoPrint 1.2.8. After the self-uninstall another restart of your server
will be triggered (if you have setup your server's restart command, defaults to
`sudo service octoprint restart` on OctoPi) in order to really get rid of any
left-overs, so don't be alarmed when that happens, it is intentional.

**If you cannot or don't want to use the plugin**, alternatively you can switch
OctoPrint to "Commit" based tracking via the settings of the Software Update plugin,
update, then switch back to "Release" based tracking (see [this screenshot](https://i.imgur.com/wvkgiGJ.png)).

#### Bed temperatures are now only displayed if printer profile has a heated bed configured

This release fixes a [bug](https://github.com/foosel/OctoPrint/issues/1125)
that caused bed temperature display and controls to be available even if the
selected printer profile didn't have a heated bed configured.

If your printer does have a heated bed but you are not seeing its temperature
in the "Temperature" tab after updating to 1.2.8, please make sure to check
the "Heated Bed" option in your printer profile (under Settings > Printer Profiles)
as shown [in this short GIF](http://i.imgur.com/wp1j9bs.gif).

### Improvements

  * Version numbering now follows [PEP440](https://www.python.org/dev/peps/pep-0440/).
  * Prepared some things for publishing OctoPrint on [PyPi](https://pypi.python.org/pypi)
    in the future.
  * [BlueprintPlugin mixin](http://docs.octoprint.org/en/master/plugins/mixins.html#blueprintplugin)
    now has an `errorhandler` decorator that serves the same purpose as
    [Flask's](http://flask.pocoo.org/docs/0.10/patterns/errorpages/#error-handlers)
    ([#1059](https://github.com/foosel/OctoPrint/pull/1059))
  * Interpret `M25` in a GCODE file that is being streamed from OctoPrint as
    indication to pause, like `M0` and `M1`.
  * Cache rendered page and translation files indefinitely. That should
    significantly improve performance on reloads of the web interface.
  * Added the string "unknown command" to the list of ignored printer errors.
    This should help with general firmware compatibility in case a firmware
    lacks features.
  * Added the strings "cannot open" and "cannot enter" to the list of ignored
    printer errors. Those are errors that Marlin may report if there is an issue
    with the printer's SD card.
  * The "CuraEngine" plugin now makes it more obvious that it only targets
    CuraEngine versions up to and including 15.04 and also links to the plugin's
    homepage with more information right within the settings dialog.
  * Browser tab visibility is now tracked by the web interface, disabling the
    webcam and the GCODE viewer if the tab containing OctoPrint is not active.
    That should reduce the amount of resource utilized by the web interface on
    the client when it is not actively monitored. Might also help to mitigate
    [#1065](https://github.com/foosel/OctoPrint/issues/1065), the final verdict
    on that one is still out though.
  * The printer log in the terminal tab will now be cut off after 3000 lines
    even if autoscroll is disabled. If the limit is reached, no more log lines
    will be added to the client's buffer. That ensures that the log will not
    scroll and the current log excerpt will stay put while also not causing
    the browser to run into memory errors due to trying to buffer an endless
    amount of log lines.
  * Increased timeout of "waiting for restart" after an update from 20 to 60sec
    (20sec turned out to be too little for OctoPi for whatever reason).
  * Added a couple of unit tests

### Bug Fixes

 * [#1120](https://github.com/foosel/OctoPrint/issues/1120) - Made the watchdog
   that monitors and handles the `watched` folder more resilient towards errors.
 * [#1125](https://github.com/foosel/OctoPrint/issues/1125) - Fixed OctoPrint
   displaying bed temperature and controls and allowing the sending of GCODE
   commands targeting the bed (`M140`, `M190`) if the printer profile doesn't
   have a heated bed configured.
 * Fixed an issue that stopped the software updater working for OctoPrint. The
   updater reports success updating, but no update has actually taken place. A
   fix can be applied for this issue to OctoPrint version 1.2.7 via
   [the Updatefix 1.2.7 plugin](https://github.com/OctoPrint/OctoPrint-Updatefix-1.2.7).
   For more information please refer to the [Important information for people updating from version 1.2.7](#important-information-for-people-updating-from-version-127)
   above.
 * Fix: Current filename in job data should never be prefixed with `/`
 * Only persist plugin settings that differ from the defaults. This way the
   `config.yaml` won't be filled with lots of redundant data. It's the
   responsibility of the plugin authors to responsibly handle changes in default
   settings of their plugins and add data migration where necessary.
 * Fixed a documentation bug ([#1067](https://github.com/foosel/OctoPrint/pull/1067))
 * Fixed a conflict with bootstrap-responsive, e.g. when using the
   [ScreenSquish Plugin](http://plugins.octoprint.org/plugins/screensquish/)
   ([#1103](https://github.com/foosel/OctoPrint/pull/1067))
 * Fixed OctoPrint still sending SD card related commands to the printer even
   if SD card support is disabled (e.g. `M21`).
 * Hidden files are no longer visible to the template engine, neither as (GCODE)
   scripts nor as interface templates.
 * The hostname and URL prefix via which the OctoPrint web interface is accessed
   is now part of the cache key. Without that being the case the cache could
   be created referring to something like `/octoprint/prefix/api/` for its API
   endpoint (if accessed via `http://somehost:someport/octoprint/prefix/` first
   time), which would then cause the interface to not work if accessed later
   via another route (e.g. `http://someotherhost/`).
 * Fixed a JavaScript error on finishing streaming of a file to SD.
 * Fixed version reporting on detached HEADs (when the branch detection
   reported "HEAD" instead of "(detached"
 * Fixed some path checks for systems with symlinked paths
   ([#1051](https://github.com/foosel/OctoPrint/pull/1051))
 * Fixed a bug causing the "Server Offline" overlay to pop _under_ the
   "Please reload" overlay, which could lead to "Connection refused" browser
   messages when clicking "Reload now" in the wrong moment.

([Commits](https://github.com/foosel/OctoPrint/compare/1.2.7...1.2.8))

## 1.2.7 (2015-10-20)

### Improvements

  * [#1062](https://github.com/foosel/OctoPrint/issues/1062) - Plugin Manager
    now has a configuration dialog that among other things allows defining the
    used `pip` command if auto detection proves to be insufficient here.
  * Allow defining additional `pip` parameters in Plugin Manager. That might
    make `sudo`-less installation of plugins possible in situations where it's
    tricky otherwise.
  * Improved timelapse processing (backported from `devel` branch):
    * Individually captured frames cannot "overtake" each other anymore through
      usage of a capture queue.
    * Notifications will now be shown when the capturing of the timelapse's
      post roll happens, including an approximation of how long that will take.
    * Usage of `requests` instead of `urllib` for fetching the snapshot,
      appears to also have [positive effects on webcam compatibility](https://github.com/foosel/OctoPrint/issues/1078).
  * Some more defensive escaping for various settings in the UI (e.g. webcam URL)
  * Switch to more error resilient saving of configuration files and other files
    modified during runtime (save to temporary file & move). Should reduce risk
    of file corruption.
  * Downloading GCODE and STL files should now set more fitting `Content-Type`
    headers (`text/plain` and `application/sla`) for better client side support
    for "Open with" like usage scenarios.
  * Selecting z-triggered timelapse mode will now inform about that not working
    when printing from SD card.
  * Software Update Plugin: Removed "The web interface will now be reloaded"
    notification after successful update since that became obsolete with
    introduction of the "Reload Now" overlay.
  * Updated required version of `psutil` and `netifaces` dependencies.

### Bug Fixes

  * [#1057](https://github.com/foosel/OctoPrint/issues/1057) - Better error
    resilience of the Software Update plugin against broken/incomplete update
    configurations.
  * [#1075](https://github.com/foosel/OctoPrint/issues/1075) - Fixed support
    of `sudo` for installing plugins, but added big visible warning about it
    as it's **not** recommended.
  * [#1077](https://github.com/foosel/OctoPrint/issues/1077) - Do not hiccup
    on [UTF-8 BOMs](https://en.wikipedia.org/wiki/Byte_order_mark) (or other
    BOMs for that matter) at the beginning of GCODE files.
  * Fixed an issue that caused user sessions to not be properly associated,
    leading to Sessions getting duplicated, wrongly saved etc.
  * Fixed internal server error (HTTP 500) response on REST API calls with
    unset `Content-Type` header.
  * Fixed an issue leading to drag-and-drop file uploads to trigger frontend
    processing in various other file upload widgets.
  * Fixed a documentation error.
  * Fixed caching behaviour on GCODE/STL downloads, was setting the `ETag`
    header improperly.
  * Fixed GCODE viewer not properly detecting change of currently visualized
    file on Windows systems.

([Commits](https://github.com/foosel/OctoPrint/compare/1.2.6...1.2.7))

## 1.2.6 (2015-09-02)

### Improvements

  * Added support for version reporting on detached checkouts
    (see [#1041](https://github.com/foosel/OctoPrint/pull/1041))

### Bug Fixes

  * Pinned requirement for [psutil](https://pypi.python.org/pypi/psutil)
    dependency to version 3.1.1 of that library due to an issue when
    installing version 3.2.0 of that library released on 2015-09-02 through
    a `python setup.py install` on OctoPrint. Also pinned all other requirements
    to definitive versions that definitely work while at it to keep that from
    happening again.

([Commits](https://github.com/foosel/OctoPrint/compare/1.2.5...1.2.6))

## 1.2.5 (2015-08-31)

### Improvements

  * [#986](https://github.com/foosel/OctoPrint/issues/986) - Added tooltip for
    "additional data" button in file list.
  * [#1028](https://github.com/foosel/OctoPrint/issues/1028) - Hint about why
    timelapse configuration is disabled.
  * New central configuration option for commands to restart OctoPrint and to
    restart and shut down the system OctoPrint is running on. This allows plugins
    (like the Software Update Plugin or the Plugin Manager) and core functionality
    to perform these common administrative tasks without the user needing to define
    everything redundantly.
  * Settings dialog now visualizes when settings are saving and when they being
    retrieved. Also the Send/Cancel buttons are disabled while settings are saving
    to prevent duplicated requests and concurrent retrieval of the settings by
    multiple viewmodels is disabled as well.
  * Better protection against rendering errors from templates provided by third
    party plugins.
  * Better protection against corrupting the configuration by using a temporary
    file as intermediate buffer.
  * Added warning to UI regarding Z timelapses and spiralized objects.
  * Better compatibility with Repetier firmware:
    * Added "Format Error" to whitelisted recoverable communication errors
      (see also [#1032](https://github.com/foosel/OctoPrint/pull/1032)).
    * Added option to ignore repeated resend requests for the same line (see
      also discussion in [#1015](https://github.com/foosel/OctoPrint/pull/1015)).
  * Software Update Plugin:
    * Adjusted to utilize new centralized restart commands (see above).
    * Allow configuration of checkout folder and version tracking type via
      Plugin Configuration.
    * Display message to user if OctoPrint's checkout folder is not configured
      or a non-release version is running and version tracking against releases
      is enabled.
    * Clear version cache when a change in the check configuration is detected.
    * Mark check configurations for which an update is not possible.
  * Made disk space running low a bit more obvious through visual warning on
    configurable thresholds.

### Bug Fixes

  * [#985](https://github.com/foosel/OctoPrint/issues/985) - Do not hiccup on
    unset `Content-Type` part headers for multipart file uploads.
  * [#1001](https://github.com/foosel/OctoPrint/issues/1001) - Fixed connection
    tab not unfolding properly (see also [#1002](https://github.com/foosel/OctoPrint/pull/1002)).
  * [#1012](https://github.com/foosel/OctoPrint/issues/1012) - All API
    responses now set no-cache headers, making the Edge browser behave a bit better
  * [#1019](https://github.com/foosel/OctoPrint/issues/1019) - Better error
    handling of problems when trying to write the webassets cache.
  * [#1021](https://github.com/foosel/OctoPrint/issues/1021) - Properly handle
    serial close on Macs.
  * [#1031](https://github.com/foosel/OctoPrint/issues/1031) - Special
    handling of `M112` (emergency stop) command:
    * Jump send queue
    * In case the printer's firmware doesn't understand it yet, at least
      shutdown all of the heaters
    * Disconnect
  * Properly reset job progress to 0% when restarting a previously completed
    printjob (see [#998](https://github.com/foosel/OctoPrint/pull/998)).
  * Report an update as failed if the `pip` command returns a return code that
    indicates failure.
  * Fixed sorting of templates: could only be sorted by name, individual
    configurations were ignored (see [#1022](https://github.com/foosel/OctoPrint/pull/1022)).
  * Fixed positioning of custom context menus: were offset due to changes in
    overall positioning settings (see [#1023](https://github.com/foosel/OctoPrint/pull/1023)).
  * Software Update: Don't use display version for comparison of git commit
    hashs.
  * Fixed temperature parsing for multi extruder setups.
  * Fixed nested vertical and horizontal custom control layouts.

([Commits](https://github.com/foosel/OctoPrint/compare/1.2.4...1.2.5))

## 1.2.4 (2015-07-23)

### Improvements

  * `RepeatedTimer` now defaults to `daemon` set to `True`. This makes sure
    plugins using it don't have to remember to set that flag themselves in
    order for the server to properly shut down when timers are still active.
  * Fixed a typo in the docs about `logging.yaml` (top level element is
    `loggers`, not `logger`).
  * Support for plugins with external dependencies (`dependency_links` in
    setuptools), interesting for plugin authors who need to depend on Python
    libraries that are (not yet) available on PyPI.
  * Better resilience against errors within plugins.

### Bug Fixes

  * Do not cache web page when running for the first time, to avoid caching
    the first run dialog popup along side with it. This should solve issues
    people were having when configuring OctoPrint for the first time, then
    reloading the page without clearing the cache, being again prompted with
    the dialog with no chance to clear it.
  * Fix/workaround for occasional white panes in settings dialog on Safari 8,
    which appears to have an issue with fixed positioning.
  * Fixed form field truncation in upload requests that could lead to problems
    when trying to import Cura profiles with names longer than 28 characters.
  * Fixed webcam rotation for timelapse rendering.
  * Fixed user settings not reaching the editor in the frontend.
  * Notifications that are in process of being closed don't open again on
    mouse over (that was actually more of an unwanted feature).

([Commits](https://github.com/foosel/OctoPrint/compare/1.2.3...1.2.4))

## 1.2.3 (2015-07-09)

### Improvements

  * New option to actively poll the watched folder. This should make it work also
    if it is mounted on a filesystem that doesn't allow getting notifications
    about added files through notification by the operating system (e.g.
    network shares).
  * Better resilience against senseless temperature/SD-status-polling intervals
    (such as 0).
  * Log exceptions during writing to the serial port to `octoprint.log`.

### Bug Fixes

  * [#961](https://github.com/foosel/OctoPrint/pull/961) - Fixed a JavaScript error that caused an error to be logged when "enter" was pressed in file or plugin search.
  * [#962](https://github.com/foosel/OctoPrint/pull/962) - ``url(...)``s in packed CSS and LESS files should now be rewritten properly too to refer to correct paths
  * Update notifications were not vanishing properly after updating:
    * Only use version cache for update notifications if the OctoPrint version still is the same to make sure the cache gets invalidated after an external update of OctoPrint.
    * Do not persist version information when saving settings of the Software Update plugin
  * Always delete files from the ``watched`` folder after importing then. Using file preprocessor plugins could lead to the files staying there.
  * Fixed an encoding problem causing OctoPrint's Plugin Manager and Software Update plugins to choke on UTF-8 characters in the update output.
  * Fixed sorting by file size in file list
  * More resilience against missing plugin assets:
    * Asset existence will now be checked before they get included
      in the assets to bundle by webassets, logging a warning if a
      file isn't present.
    * Monkey-patched webassets filter chain to not die when a file
      doesn't exist, but to log an error instead and just return
      an empty file instead.

([Commits](https://github.com/foosel/OctoPrint/compare/1.2.2...1.2.3))

## 1.2.2 (2015-06-30)

### Bug Fixes

* Fixed an admin-only security issue introduced in 1.2.0, updating is strongly advised.

([Commits](https://github.com/foosel/OctoPrint/compare/1.2.1...1.2.2))

## 1.2.1 (2015-06-30)

### Improvements

* More flexibility when interpreting compatibility data from plugin repository. If compatibility information is provided
  only as a version number it's prefixed with `>=` for the check (so stating a compatibility of only
  `1.2.0` will now make the plugin compatible to OctoPrint 1.2.0+, not only 1.2.0). Alternatively the compatibility
  information may now contain stuff like `>=1.2,<1.3` in which case the plugin will only be shown as compatible
  to OctoPrint versions 1.2.0 and up but not 1.3.0 or anything above that. See also
  [the requirement specification format of the `pkg_resources` package](https://pythonhosted.org/setuptools/pkg_resources.html#requirements-parsing).
* Only print the commands of configured event handlers to the log when a new `debug` flag is present in the config
  (see [the docs](http://docs.octoprint.org/en/master/configuration/config_yaml.html#events)). Reduces risk of disclosing sensitive data when sharing log files.

### Bug Fixes

* [#956](https://github.com/foosel/OctoPrint/issues/956) - Fixed server crash when trying to configure a default
  slicing profile for a still unconfigured slicer.
* [#957](https://github.com/foosel/OctoPrint/issues/957) - Increased maximum allowed body size for plugin archive uploads.
* Bugs without tickets:
  * Clean exit on `SIGTERM`, calling the shutdown functions provided by plugins.
  * Don't disconnect on `volume.init` errors from the firmware.
  * `touch` uploaded files on local file storage to ensure proper "uploaded date" even for files that are just moved
    from other locations of the file system (e.g. when being added from the `watched` folder).

([Commits](https://github.com/foosel/OctoPrint/compare/1.2.0...1.2.1))

## 1.2.0 (2015-06-25)

### Note for Upgraders

  * The [Cura integration](https://github.com/daid/Cura) has changed in such a way that OctoPrint now calls the
    [CuraEngine](https://github.com/Ultimaker/CuraEngine) directly instead of depending on the full Cura installation. See
    [the wiki](https://github.com/foosel/OctoPrint/wiki/Plugin:-Cura) for instructions on how to change your setup to
    accommodate the new integration.

### New Features

* OctoPrint now has a [plugin system](http://docs.octoprint.org/en/master/plugins/index.html) which allows extending its
  core functionality.
  * Plugins may be installed through the new and bundled [Plugin Manager Plugin](https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager)
    available in OctoPrint's settings. This Plugin Manager also allows browsing and easy installation of plugins
    registered on the official [OctoPrint Plugin Repository](http://plugins.octoprint.org).
  * For interested developers there is a [tutorial available in the documentation](http://docs.octoprint.org/en/master/plugins/gettingstarted.html)
    and also a [cookiecutter template](https://github.com/OctoPrint/cookiecutter-octoprint-plugin) to quickly bootstrap
    new plugins.
* Added internationalization of UI. Translations of OctoPrint are being crowd sourced via [Transifex](https://www.transifex.com/projects/p/octoprint/).
  Language Packs for both the core application as well as installed plugins can be uploaded through a new management
  dialog in Settings > Appearance > Language Packs. A translation into German is included, further language packs
  will soon be made available.
* Printer Profiles: Printer properties like print volume, extruder offsets etc are now managed via Printer Profiles. A
  connection to a printer will always have a printer profile associated.
* File management now supports STL files as first class citizens (including UI adjustments to allow management of
  uploaded STL files including removal and reslicing) and also allows folders (not yet supported by UI). STL files
  can be downloaded like GCODE files.
* Slicing has been greatly improved:
  * It now allows for a definition of slicing profiles to use for slicing plus overrides which can be defined per slicing
    job (defining overrides is not yet part of the UI but it's on the roadmap).
  * A new slicing dialog has been added which allows (re-)slicing uploaded STL files (which are now displayed in the file list
    as well). The slicing profile and printer profile to use can be specified here as well as the file name to which to
    slice to and the action to take after slicing has been completed (none, selecting the sliced GCODE for printing or
    starting to print it directly)
  * The slicing API allows positioning the model to slice on the print bed (Note: this is not yet available in the UI).
  * Slicers themselves are integrated into the system via ``SlicingPlugins``.
  * Bundled [Cura Plugin](https://github.com/foosel/OctoPrint/wiki/Plugin:-Cura) allows slicing through CuraEngine up
    to and including 15.04. Existing Cura slicing profiles can be imported through the web interface.
* New file list: Pagination is gone, no more (mobile incompatible) pop overs, instead scrollable and with instant
  search
* You can now define a folder (default: `~/.octoprint/watched`) to be watched for newly added GCODE (or -- if slicing
  support is enabled -- STL) files to automatically add.
* New type of API key: [App Session Keys](http://docs.octoprint.org/en/master/api/apps.html) for trusted applications
* OctoPrint now supports `action:...` commands received via debug messages (`// action:...`) from the printer. Currently supported are
  - `action:pause`: Pauses the current job in OctoPrint
  - `action:resume`: Resumes the current job in OctoPrint
  - `action:disconnect`: Disconnects OctoPrint from the printer
  Plugins can add supported commands by [hooking](http://docs.octoprint.org/en/master/plugins/hooks.html) into the
  ``octoprint.comm.protocol.action`` hook
* Mousing over the webcam image in the control tab enables key control mode, allowing you to quickly move the axis of your
  printer with your computer's keyboard ([#610](https://github.com/foosel/OctoPrint/pull/610)):
  - arrow keys: X and Y axes
  - W, S / PageUp, PageDown: Z axes
  - Home: Home X and Y axes
  - End: Home Z axes
  - 1, 2, 3, 4: change step size used (0.1, 1, 10, 100mm)
* Controls for adjusting feed and flow rate factor added to Controls ([#362](https://github.com/foosel/OctoPrint/issues/362))
* Custom controls now also support slider controls
* Custom controls now support a row layout
* Users can now define custom GCODE scripts to run upon starting/pausing/resuming/success/failure of a print or for
  custom controls ([#457](https://github.com/foosel/OctoPrint/issues/457), [#347](https://github.com/foosel/OctoPrint/issues/347))
* Bundled [Discovery Plugin](https://github.com/foosel/OctoPrint/wiki/Plugin:-Discovery) allows discovery of OctoPrint
  instances via SSDP/UPNP and optionally also via ZeroConf/Bonjour/Avahi.
* Bundled [Software Update Plugin](https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update) takes care of notifying
  about new OctoPrint releases and also allows updating if configured as such. Plugins may register themselves with the
  update notification and application process through a new hook ["octoprint.plugin.softwareupdate.check_config"](https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update#octoprintpluginsoftwareupdatecheck_config).

### Improvements

* Logging is now configurable via config file
* Added last print time to additional GCODE file information
* Better error handling for capture issues during timelapse creation & more robust handling of missing images during
  timelapse creation
* Start counting the layers at 1 instead of 0 in the GCODE viewer
* Upgraded [Font Awesome](https://fortawesome.github.io/Font-Awesome/) to version 3.2.1
* Better error reporting for timelapse rendering and system commands
* Custom control can now be defined so that they show a Confirm dialog with configurable text before executing
  ([#532](https://github.com/foosel/OctoPrint/issues/532) and [#590](https://github.com/foosel/OctoPrint/pull/590))
* Serial communication: Also interpret lines starting with "!!" as errors
* Added deletion of pyc files to the `python setup.py clean` command
* Settings now show a QRCode for the API Key ([#637](https://github.com/foosel/OctoPrint/pull/637))
* Username in UI is no longer enclosed in scare quotes ([#595](https://github.com/foosel/OctoPrint/pull/595))
* Username in login dialog is not automatically capitalized on mobile devices anymore ([#639](https://github.com/foosel/OctoPrint/pull/639))
* "Slicing Done" and "Streaming Done" notifications now have a green background ([#558](https://github.com/foosel/OctoPrint/issues/558))
* Files that are currently in use, be it for slicing, printing or whatever, are now tracked and can not be deleted as
  long as they are in use
* Settings in UI get refreshed when opening settings dialog
* New event "SettingsUpdated"
* "Print time left" is now not displayed until it becomes somewhat stable. Display in web interface now also happens
  in a fuzzy way instead of the format hh:mm:ss, to not suggest a high accuracy anymore where the can't be one. Additionally
  OctoPrint will use data from prior prints to enhance the initial print time estimation.
* Added handler for uncaught exceptions to make sure those get logged, should make the logs even more useful for analysing
  bug reports
* The server now tracks the modification date of the configuration file and reloads it prior to saving the config if
  it has been changed during runtime by external editing, hence no config settings added manually while the server
  was running should be overwritten anymore.
* Display a "Please Reload" overlay when a new server version or a change in installed plugins is detected after a
  reconnect to the server.
* Better handling of errors on the websocket - no more logging of the full stack trace to the log, only a warning
  message for now.
* Daemonized OctoPrint now cleans up its pidfile when receiving a TERM signal ([#711](https://github.com/foosel/OctoPrint/issues/711))
* Added serial types for OpenBSD ([#551](https://github.com/foosel/OctoPrint/pull/551))
* Improved behaviour of terminal:
  * Disabling autoscrolling now also stops cutting off the log while it's enabled, effectively preventing log lines from
    being modified at all ([#735](https://github.com/foosel/OctoPrint/issues/735))
  * Applying filters displays ``[...]`` where lines where removed and doesn't cause scrolling on filtered lines
    anymore ([#286](https://github.com/foosel/OctoPrint/issues/286))
  * Added a link to scroll to the end of the terminal log (useful for when autoscroll is disabled)
  * Added a link to select all current contents of the terminal log for easy copy-pasting
  * Added a display of how many lines are displayed, how many are filtered and how many are available in total
* Frame rate for timelapses can now be configured per timelapse ([#782](https://github.com/foosel/OctoPrint/pull/782))
* Added an option to specify the amount of encoding threads for FFMPEG ([#785](https://github.com/foosel/OctoPrint/pull/785))
* "Disconnected" screen now is not shown directly after a close of the socket, instead the client first tries to
  directly reconnect once, and only if that doesn't work displays the dialog. Should reduce short popups of the dialog
  due to shaky network connections and/or weird browser behaviour when downloading things from the UI.
* Development dependencies can now be installed with ``pip -e .[develop]``
* White and transparent colors ;) are supported for the navigation bar ([#789](https://github.com/foosel/OctoPrint/pull/789))
* Drag-n-drop overlay for file uploads now uses the full available screen space, improving usability on high resolution
  displays ([#187](https://github.com/foosel/OctoPrint/issues/187))
* OctoPrint server should no longer hang when big changes in the system time happen, e.g. after first contact to an
  NTP server on a Raspberry Pi image. Achieved through monkey patching Tornado with
  [this PR](https://github.com/tornadoweb/tornado/pull/1290).
* Serial ports matching ``/dev/ttyAMA*`` are not anymore listed by default (this was the reason for a lot of people
  running into problems while attempting to connect to their printer on their Raspberry Pis, on which ``/dev/ttyAMA0``
  is the OS's serial console by default). Added configuration of additional ports to the Serial Connection section in
  the Settings to make it easier for those people who do indeed have their printer connected to ``/dev/ttyAMA0``.
* Better behaviour of the settings dialog on low-width devices, navigation and content also now scroll independently
  from each other (see also [#823](https://github.com/foosel/OctoPrint/pull/823))
* Renamed "Temperature Timeout" and "SD Status Timeout" in Settings to "Temperature Interval" and "SD Status Interval"
  to better reflect what those values are actually used for.
* Added support for rectangular printer beds with the origin in the center ([#682](https://github.com/foosel/OctoPrint/issues/682)
  and [#852](https://github.com/foosel/OctoPrint/pull/852)). Printer profiles now contain a new settings ``volume.origin``
  which can either be ``lowerleft`` or ``center``. For circular beds only ``center`` is supported.
* Made baudrate detection a bit more solid, still can't perform wonders.
* Only show configuration options for additional extruders if more than one is available, and don't include offset
  configuration for first nozzle which acts as reference for the other offsets ([#677](https://github.com/foosel/OctoPrint/issues/677)).
* Cut off of the temperature graph is now not based on the number of data points any more but on the actual time of the
  data points. Anything older than ``n`` minutes will be cut off, with ``n`` defaulting to 30min. This value can be
  changed under "Temperatures" in the Settings ([#343](https://github.com/foosel/OctoPrint/issues/343)).
* High-DPI support for the GCode viewer ([#837](https://github.com/foosel/OctoPrint/issues/837)).
* Stop websocket connections from multiplying ([#888](https://github.com/foosel/OctoPrint/pull/888)).
* New setting to rotate webcam by 90° counter clockwise ([#895](https://github.com/foosel/OctoPrint/issues/895) and
  [#906](https://github.com/foosel/OctoPrint/pull/906))
* System commands now be set to a) run asynchronized by setting their `async` property to `true` and b) to ignore their
  result by setting their `ignore` property to `true`.
* Various improvements of newly introduced features over the course of development:
  * File management: The new implementation will migrate metadata from the old one upon first startup after upgrade from
    version 1.1.x to 1.2.x. That should speed up initial startup.
  * File management: GCODE Analysis backlog processing has been throttled to not take up too many resources on system
    startup. Freshly uploaded files should still be analyzed at full speed.
  * Plugins: SettingsPlugins may track versions of configuration format stored in `config.yaml`, including a custom
    migration method getting called when a mismatch between the currently stored configuration format version and the one
    reported by the plugin as current is detected.
  * Plugins: Plugins may now have a folder for plugin related data whose path can be retrieved from the plugin itself
    via its new method [`get_plugin_data_folder`](http://docs.octoprint.org/en/master/modules/plugin.html#octoprint.plugin.types.OctoPrintPlugin.get_plugin_data_folder).
  * Plugin Manager: Don't allow plugin management actions (like installing/uninstalling or enabling/disabling) while the
    printer is printing (see also unreproduced issue [#936](https://github.com/foosel/OctoPrint/issues/936)).
  * Plugin Manager: More options to try to match up installed plugin packages with discovered plugins.
  * Plugin Manager: Display a more friendly message if after the installation of a plugin it could not be correctly
    identifier.
  * Software Update: Enforce refreshing of available updates after any changes in enabled plugins.

### Bug Fixes

* [#435](https://github.com/foosel/OctoPrint/issues/435) - Always interpret negative duration (e.g. for print time left)
  as 0
* [#516](https://github.com/foosel/OctoPrint/issues/516) - Also require API key even if ACL is disabled.
* [#556](https://github.com/foosel/OctoPrint/issues/556) - Allow login of the same user from multiple browsers without
  side effects
* [#612](https://github.com/foosel/OctoPrint/issues/612) - Fixed GCODE viewer in zoomed out browsers
* [#633](https://github.com/foosel/OctoPrint/issues/633) - Correctly interpret temperature lines from multi extruder
  setups under Smoothieware
* [#680](https://github.com/foosel/OctoPrint/issues/680) - Don't accidentally include a newline from the MIME headers
  in the parsed multipart data from file uploads
* [#709](https://github.com/foosel/OctoPrint/issues/709) - Properly initialize time estimation for SD card transfers too
* [#715](https://github.com/foosel/OctoPrint/issues/715) - Fixed an error where Event Triggers of type command caused
  and exception to be raised due to a misnamed attribute in the code
* [#717](https://github.com/foosel/OctoPrint/issues/717) - Use ``shutil.move`` instead of ``os.rename`` to avoid cross
  device renaming issues
* [#752](https://github.com/foosel/OctoPrint/pull/752) - Fix error in event handlers sending multiple gcode commands.
* [#780](https://github.com/foosel/OctoPrint/issues/780) - Always (re)set file position in SD files to 0 so that reprints
  work correctly
* [#784](https://github.com/foosel/OctoPrint/pull/784) - Also include ``requirements.txt`` in files packed up for
  ``python setup.py sdist``
* [#330](https://github.com/foosel/OctoPrint/issues/330) - Ping pong sending to fix potential acknowledgement errors.
  Also affects [#166](https://github.com/foosel/OctoPrint/issues/166), [#470](https://github.com/foosel/OctoPrint/issues/470)
  and [#490](https://github.com/foosel/OctoPrint/issues/490). A big thank you to all people involved in these tickets
  in getting to the ground of this.
* [#825](https://github.com/foosel/OctoPrint/issues/825) - Fixed "please visualize" button of large GCODE files
* Various fixes of bugs in newly introduced features and improvements:
  * [#625](https://github.com/foosel/OctoPrint/pull/625) - Newly added GCODE files were not being added to the analysis
    queue
  * [#664](https://github.com/foosel/OctoPrint/issues/664) - Fixed jog controls again
  * [#677](https://github.com/foosel/OctoPrint/issues/677) - Fixed extruder offsets not being properly editable in
    printer profiles
  * [#678](https://github.com/foosel/OctoPrint/issues/678) - SockJS endpoints is now referenced by relative URL
    using ``url_for``, should solve any issues with IE11.
  * [#683](https://github.com/foosel/OctoPrint/issues/683) - Fixed heated bed option not being properly displayed in
    printer profiles
  * [#685](https://github.com/foosel/OctoPrint/issues/685) - Quoted file name for Timelapse creation to not make
    command hiccup on ``~`` in file name
  * [#709](https://github.com/foosel/OctoPrint/issues/709) - Fixed file sending to SD card
  * [#714](https://github.com/foosel/OctoPrint/issues/714) - Fixed type validation of printer profiles
  * Heating up the heated bed (if present) was not properly configured in CuraEngine plugin
  * [#720](https://github.com/foosel/OctoPrint/issues/720) - Fixed translation files not being properly copied over
    during install
  * [#724](https://github.com/foosel/OctoPrint/issues/724) - Fixed timelapse deletion for timelapses with non-ascii
    characters in their name
  * [#726](https://github.com/foosel/OctoPrint/issues/726) - Fixed ``babel_refresh`` command
  * [#759](https://github.com/foosel/OctoPrint/pull/759) - Properly initialize counter for template plugins of type
    "generic"
  * [#775](https://github.com/foosel/OctoPrint/pull/775) - Error messages in javascript console show the proper name
    of the objects
  * [#795](https://github.com/foosel/OctoPrint/issues/795) - Allow adding slicing profiles for unconfigured slicers
  * [#809](https://github.com/foosel/OctoPrint/issues/809) - Added proper form validation to printer profile editor
  * [#824](https://github.com/foosel/OctoPrint/issues/824) - Settings getting lost when switching between panes in
    the settings dialog (fix provided by [#879](https://github.com/foosel/OctoPrint/pull/879))
  * [#892](https://github.com/foosel/OctoPrint/issues/892) - Preselected baudrate is now properly used for auto detected
    serial ports
  * [#909](https://github.com/foosel/OctoPrint/issues/909) - Fixed Z-Timelapse for Z changes on ``G1`` moves.
  * Fixed another instance of a missing `branch` field in version dicts generated by versioneer (compare
    [#634](https://github.com/foosel/OctoPrint/pull/634)). Caused an issue when installing from source archive
    downloaded from Github.
  * [#931](https://github.com/foosel/OctoPrint/issues/931) - Adjusted `octoprint_setuptools` to be compatible to older
    versions of setuptools potentially site-wide installed on hosts.
  * [#942](https://github.com/foosel/OctoPrint/issues/942) - Settings can now be saved again after installing a new
    plugin. Plugins must not use `super` anymore to call parent implementation of `SettingsPlugin.on_settings_save` but
    should instead switch to `SettingsPlugin.on_settings_save(self, ...)`. Settings API will capture related
    `TypeErrors` and log a big warning to the log file indicating which plugin caused the problem and needs to be
    updated. Also updated all bundled plugins accordingly.
  * Software Update: Don't persist more check data than necessary in the configuration. Solves an issue where persisted
    information overrode updated check configuration reported by plugins, leading to a "an update is available" loop.
    An auto-migration function was added that should remove the redundant data.
* Various fixes without tickets:
  * GCODE viewer now doesn't stumble over completely extrusionless GCODE files
  * Do not deliver the API key on settings API unless user has admin rights
  * Don't hiccup on slic3r filament_diameter comments in GCODE generated for multi extruder setups
  * Color code successful or failed print results directly in file list, not just after a reload
  * Changing Timelapse post roll activates save button
  * Timelapse post roll is loaded properly from config
  * Handling of files on the printer's SD card contained in folders now works correctly
  * Don't display a "Disconnected" screen when trying to download a timelapse in Firefox
  * Fixed handling of SD card files in folders
  * Fixed refreshing of timelapse file list upon finished rendering of a new one
  * Fixed ``/api/printer`` which wasn't adapter yet to new internal offset data model
  * Made initial connection to printer a bit more responsive: Having to wait for the first serial timeout before sending
    the first ``M105`` even when not waiting for seeing a "start" caused unnecessary wait times for reaching the
    "Operational" state.
  * Log cancelled prints only once (thanks to @imrahil for the headsup)

### More information

  * [Commits](https://github.com/foosel/OctoPrint/compare/1.1.2...1.2.0)
  * Release Candidates:
    * [RC1](https://github.com/foosel/OctoPrint/releases/tag/1.2.0-rc1)
    * [RC2](https://github.com/foosel/OctoPrint/releases/tag/1.2.0-rc2)
    * [RC3](https://github.com/foosel/OctoPrint/releases/tag/1.2.0-rc3)

## 1.1.2 (2015-03-23)

### Improvements

* Added deletion of `*.pyc` files to `python setup.py clean` command, should help tremendously when switching branches (backported
  from [9e014eb](https://github.com/foosel/OctoPrint/commit/9e014eba1feffde11ed0601d9c911b8cac9f3fb0))
* Increased default communication and connection timeouts
* [#706](https://github.com/foosel/OctoPrint/issues/706) - Do not truncate error reported from printer

### Bug Fixes

* [#539](https://github.com/foosel/OctoPrint/issues/539) - Limit maximum number of tools, sanity check tool numbers in
  GCODE files against upper limit and refuse to create 10000 tools due to weird slicers. (backported from `devel`)
* [#634](https://github.com/foosel/OctoPrint/pull/634) - Fixed missing `branch` fields in version dicts generated
  by versioneer
* [#679](https://github.com/foosel/OctoPrint/issues/679) - Fix error where API state is requested and printer is offline
  (backport of [619fe9a](https://github.com/foosel/OctoPrint/commit/619fe9a0e78826bd1524b235a910156439bcb6d7)).
* [#719](https://github.com/foosel/OctoPrint/issues/719) - Properly center print bed in GCODE viewer
* [#780](https://github.com/foosel/OctoPrint/issues/780) - Always (re)set file position in SD files to 0 so that reprints
  work correctly (backported from ``devel``)
* [#801](https://github.com/foosel/OctoPrint/issues/801) - Fixed setting of bed temperature offset
* [IRC] - Don't hiccup on slic3r ``filament_diameter`` comments generated for multi extruder setups
* [ML] - Fixed relative URL to SockJS endpoint, wasn't yet using the proper base url
* [unreported] & [#698](https://github.com/foosel/OctoPrint/issues/698) - Generated URLs now take X-Forwarded-Host header
  sent by proxies into account for included host and port, also fixed [#698](https://github.com/foosel/OctoPrint/issues/698)
  introduced by this
* [unreported] Fixed a bug causing gcodeInterpreter to hiccup on GCODES containing invalid coordinates such as Xnan or
  Yinf (backported from `devel`)
* Small fixes for timelapse creation:
  - [#344](https://github.com/foosel/OctoPrint/issues/344) - Made timelapses capable of coping with missing captures in between by decrementing the image counter again if there
    was an error fetching the latest image from the snapshot URL (backport of [1a7a468](https://github.com/foosel/OctoPrint/commit/1a7a468eb65fdf2a13b4c7a7723280e822c9c34b)
    and [bf9d5ef](https://github.com/foosel/OctoPrint/commit/bf9d5efe43a1e57aacd8512125082ddca06b4efc))
  - [#693](https://github.com/foosel/OctoPrint/issues/693) -  Try not to capture an image if image counter is still unset
  - [unreported] Synchronize image counter decrementing as well as incrementing to prevent rare race conditions when generating the
    image file names

([Commits](https://github.com/foosel/OctoPrint/compare/1.1.1...1.1.2))

## 1.1.1 (2014-10-27)

### Improvements

* The API is now enabled by default and the API key -- if not yet set -- will be automatically generated on first
  server start and written back into ``config.yaml``
* Event subscriptions are now enabled by default (it was an accident that they weren't)
* Generate the key used for session hashing individually for each server instance
* Generate the salt used for hashing user passwords individually for each server instance

### Bug Fixes

* [#580](https://github.com/foosel/OctoPrint/issues/580) - Properly unset job data when instructed so by callers
* [#604](https://github.com/foosel/OctoPrint/issues/604) - Properly initialize settings basedir on server startup
* [IRC] Also allow downloading .g files via Tornado

([Commits](https://github.com/foosel/OctoPrint/compare/1.1.0...1.1.1))

## 1.1.0 (2014-09-03)

### New Features

* New REST API, including User API Keys additionally to the global API key. Please note that **this will break existing
  API clients** as it replaces the old API (same endpoint). You can find the documentation of the new API at
  [docs.octoprint.org](http://docs.octoprint.org/en/1.1.0/api/index.html).
* New Event structure allows more flexibility regarding payload data, configuration files will be migrated automatically.
  You can find the documentation of the new event format and its usage at [docs.octoprint.org](http://docs.octoprint.org/en/1.1.0/events/index.html).
* Support for multi extruder setups. With this OctoPrint now in theory supports an unlimited amount of extruders, however
  for now it's artificially limited to 9.
* Log files can be accessed from within the browser via the Settings dialog ([#361](https://github.com/foosel/OctoPrint/pull/361))
* Timelapses can now have a post-roll duration configured which will be rendered into the video too to not let it
  end so abruptly ([#384](https://github.com/foosel/OctoPrint/issues/384))
* The terminal tab now has a command history ([#388](https://github.com/foosel/OctoPrint/pull/388))

### Improvements

* Stopping the application via Ctrl-C produces a less scary message ([#277](https://github.com/foosel/OctoPrint/pull/277))
* Webcam stream is disabled when control tab is not in focus, reduces bandwidth ([#316](https://github.com/foosel/OctoPrint/issues/316))
* M and G commands entered in Terminal tab are automatically converted to uppercase
* GCODE viewer now only loads automatically if GCODE file size is beneath certain threshold (different ones for desktop
  and mobile devices), only actually loads file if user acknowledges that this might be too much for his browser
* Added time needed for printing file to PrintDone event's payload ([#333](https://github.com/foosel/OctoPrint/issues/333))
* Also provide the filename (basename without the path) in print events
* Support for circular beds in the GCODE viewer ([#407](https://github.com/foosel/OctoPrint/pull/407))
* The dimensions of the print bed can now be configured via the Settings ([#396](https://github.com/foosel/OctoPrint/pull/396))
* Target temperature reporting format of Repetier Firmware is now supported as well ([360](https://github.com/foosel/OctoPrint/issues/360))
* Version tracking now based on git tagging and [versioneer](https://github.com/warner/python-versioneer/). Version number,
  git commit and branch get reported in the format `<version tag>-<commits since then>-g<commit hash> (<branch> branch)`,
  e.g. `1.2.0-dev-172-ga48b5de (devel branch)`.
* Made "Center viewport on model" and "Zoom in on model" in the GCODE viewer automatically deselect and de-apply if
  viewport gets manipulated by the user ([#398](https://github.com/foosel/OctoPrint/issues/398))
* GCODE viewer now interprets inverted axes for printer control and mirrors print bed accordingly ([#431](https://github.com/foosel/OctoPrint/issues/431))
* Added `clean` command to `setup.py`, removes old build artifacts (mostly interesting for developers)
* Added version resource on API which reports application and API version
* Made the navbar static instead of fixed to improve usability on mobile devices ([#257](https://github.com/foosel/OctoPrint/issues/257))
* Switch to password field upon enter in username field, submit login form upon enter in password field
* Changed default path to OctoPrint executable in included init-script to `/usr/local/bin/octoprint` (the default when
  installing via `python setup.py install`)

### Bug Fixes

* Properly calculate time deltas (forgot to factor in days)
* [#35](https://github.com/foosel/OctoPrint/issues/35) - GCODE viewer has been modularized, options are now functional
* [#337](https://github.com/foosel/OctoPrint/issues/337) - Also recognize `--iknowwhatimdoing` when running as daemon
* [#357](https://github.com/foosel/OctoPrint/issues/357) - Do not run GCODE analyzer when a print is ongoing
* [#381](https://github.com/foosel/OctoPrint/issues/381) - Only list those SD files that have an ASCII filename
* Fixed a race condition that could occur when pressing "Print" (File not opened yet, but attempt to read from it)
* [#398](https://github.com/foosel/OctoPrint/issues/398) - Fixed interfering options in GCODE viewer
* [#399](https://github.com/foosel/OctoPrint/issues/399) & [360](https://github.com/foosel/OctoPrint/issues/360) - Leave
  bed temperature unset when not detected (instead of dying a horrible death)
* [#492](https://github.com/foosel/OctoPrint/issues/492) - Fixed a race condition which could lead to an attempt to read
  from an already closed serial port, causing an error to be displayed to the user
* [#257](https://github.com/foosel/OctoPrint/issues/257) - Logging in on mobile devices should now work
* [#476](https://github.com/foosel/OctoPrint/issues/476) - Also update the metadata correctly when an analysis finishes
* Various fixes of bugs in newly introduced features and improvements:
  - [#314](https://github.com/foosel/OctoPrint/issues/314) - Use G28 for homing (G1 was copy and paste error)
  - [#317](https://github.com/foosel/OctoPrint/issues/317) - Fixed "load and print" function
  - [#326](https://github.com/foosel/OctoPrint/issues/326) - Fixed refresh of SD file list
  - [#338](https://github.com/foosel/OctoPrint/issues/338) - Refetch file list when deleting a file
  - [#339](https://github.com/foosel/OctoPrint/issues/339) - More error resilience when handling temperature offset data from the backend
  - [#345](https://github.com/foosel/OctoPrint/issues/345) - Also recognize such temperature reports that do not contain a `T:` but a `T0:`
  - [#377](https://github.com/foosel/OctoPrint/pull/377) - URLs in API examples fixed
  - [#378](https://github.com/foosel/OctoPrint/pull/378) - Fixed crash of API call when `getStartTime()` returns None
  - [#379](https://github.com/foosel/OctoPrint/pull/379) - Corrected response code for connection success
  - [#414](https://github.com/foosel/OctoPrint/pull/414) - Fix style attribute for Actual column header

([Commits](https://github.com/foosel/OctoPrint/compare/1.0.0...1.1.0))

## 1.0.0 (2014-06-22)

First release with new versioning scheme.
