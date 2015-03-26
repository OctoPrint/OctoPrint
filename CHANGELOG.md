# OctoPrint Changelog

## 1.2.0 (Unreleased)

### New Features

* Added internationalization of UI. Translations of OctoPrint are being crowd sourced via [Transifex](https://www.transifex.com/projects/p/octoprint/).
  The following translations are already available with more in the works:
  - Dutch (nl)
  - German (de)
  - French (fr)
  - Hebrew (he)
  - Norwegian (no)
  - Romanian (ro)
* New file list: Pagination is gone, no more (mobile incompatible) pop overs, instead scrollable and with instant
  search
* You can now define a folder (default: `~/.octoprint/watched`) to be watched for newly added GCODE (or -- if slicing
  support is enabled -- STL) files to automatically add.
* OctoPrint now has a [plugin system](http://docs.octoprint.org/en/devel/plugins/index.html) which allows extending its 
  core functionality.
* New type of API key: [App Session Keys](http://docs.octoprint.org/en/devel/api/apps.html) for trusted applications
* Printer Profiles: Printer properties like print volume, extruder offsets etc are now managed via Printer Profiles. A
  connection to a printer will always have a printer profile associated.
* OctoPrint now supports `action:...` commands received via debug messages (`// action:...`) from the printer. Currently supported are
  - `action:pause`: Pauses the current job in OctoPrint
  - `action:resume`: Resumes the current job in OctoPrint
  - `action:disconnect`: Disconnects OctoPrint from the printer
  Plugins can add supported commands by [hooking](http://docs.octoprint.org/en/devel/plugins/hooks.html) into the
  ``octoprint.comm.protocol.action`` hook
* Mousing over the webcam image in the control tab enables key control mode, allowing you to quickly move the axis of your
  printer with your computer's keyboard ([#610](https://github.com/foosel/OctoPrint/pull/610)):
  - arrow keys: X and Y axes
  - W, S / PageUp, PageDown: Y axes
  - Home: Home X and Y axes
  - End: Home Z axes
  - 1, 2, 3, 4: change step size used (0.1, 1, 10, 100mm)
* Controls for adjusting feed and flow rate factor added to Controls ([#362](https://github.com/foosel/OctoPrint/issues/362))
* Custom controls now also support slider controls
* Custom controls now support a row layout
* Users can now define custom GCODE scripts to run upon starting/pausing/resuming/success/failure of a print

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
* Slicing has been greatly improved:
  * It now allows for a definition of slicing profiles to use for slicing plus overrides which can be defined per slicing 
    job (defining overrides is not yet part of the UI but it's on the roadmap).
  * A new slicing dialog has been added which allows (re-)slicing uploaded STL files (which are now displayed in the file list
    as well). This dialog also allows specifying which action to take after slicing has been completed (none, selecting the
    sliced GCODE for printing or starting to print it directly)
  * Slicers themselves are integrated into the system via ``SlicingPlugins``. 
  * The [Cura integration](https://github.com/daid/Cura) has changed in such a way that OctoPrint now calls the 
    [CuraEngine](https://github.com/Ultimaker/CuraEngine) directly instead of depending on the full Cura installation. See 
    [the wiki](https://github.com/foosel/OctoPrint/wiki/Plugin:-Cura) for instructions on how to change your setup to 
    accommodate the new integration.
  * The "Slicing done" notification is now colored green ([#558](https://github.com/foosel/OctoPrint/issues/558)).
  * The slicing API allows positioning the model to slice on the print bed (Note: this is not yet available in the UI).
* File management now supports STL files as first class citizens (including UI adjustments to allow management of
  uploaded STL files including removal and reslicing) and also allows folders (not yet supported by UI). STL files
  can be downloaded like GCODE files.
* Also interpret lines starting with "!!" as errors
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
* Automatically hard-reload the UI if upon reconnecting to the server a new version is detected.
* Better handling of errors on the websocket - no more logging of the full stack trace to the log, only a warning
  message for now.
* Daemonized OctoPrint now cleans up its pidfile when receiving a TERM signal ([#711](https://github.com/foosel/OctoPrint/issues/711))
* Added serial types for OpenBSD ([#551](https://github.com/foosel/OctoPrint/pull/551))
* Improved behaviour of terminal:
  * Disabling autoscrolling now also stops cutting of the log while it's enabled, effectively preventing log lines from
    being modified at all ([#735](https://github.com/foosel/OctoPrint/issues/735))
  * Applying filters displays ``[...]`` where lines where removed
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
  attempting to connect to their printer on their Raspberry Pis, on which ``/dev/ttyAMA0`` is the OS's serial console
  by default). Added configuration of additional ports to the Serial Connection section in the Settings to make it easier
  for those people who do indeed have their printer connected to ``/dev/ttyAMA0``.

### Bug Fixes

* [#435](https://github.com/foosel/OctoPrint/issues/435) - Always interpret negative duration (e.g. for print time left)
  as 0
* [#633](https://github.com/foosel/OctoPrint/issues/633) - Correctly interpret temperature lines from multi extruder 
  setups under Smoothieware
* [#556](https://github.com/foosel/OctoPrint/issues/556) - Allow login of the same user from multiple browsers without
  side effects
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
  and [#490](https://github.com/foosel/OctoPrint/issues/490).
* Various fixes of bugs in newly introduced features and improvements:
  * [#625](https://github.com/foosel/OctoPrint/pull/625) - Newly added GCODE files were not being added to the analysis
    queue
  * [#664](https://github.com/foosel/OctoPrint/issues/664) - Fixed jog controls again
  * [#677](https://github.com/foosel/OctoPrint/issues/677) - Fixed extruder offsets not being properly editable in
    printer profiles
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

([Commits](https://github.com/foosel/OctoPrint/compare/master...devel))

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
