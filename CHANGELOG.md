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
  uploaded STL files including removal and reslicing) and also allows folders (not yet supported by UI)
* Also interpret lines starting with "!!" as errors
* Added deletion of pyc files to the `python setup.py clean` command
* Settings now show a QRCode for the API Key ([#637](https://github.com/foosel/OctoPrint/pull/637))
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

### Bug Fixes

* [#435](https://github.com/foosel/OctoPrint/issues/435) - Always interpret negative duration (e.g. for print time left)
  as 0
* [#633](https://github.com/foosel/OctoPrint/issues/633) - Correctly interpret temperature lines from multi extruder 
  setups under Smoothieware
* [#556](https://github.com/foosel/OctoPrint/issues/556) - Allow login of the same user from multiple browsers without
  side effects
* [#680](https://github.com/foosel/OctoPrint/issues/680) - Don't accidentally include a newline from the MIME headers
  in the parsed multipart data from file uploads
* Various fixes of bugs in newly introduced features and improvements:
  * [#625](https://github.com/foosel/OctoPrint/pull/625) - Newly added GCODE files were not being added to the analysis
    queue
  * [#664](https://github.com/foosel/OctoPrint/issues/664) - Fixed jog controls again
  * [#677](https://github.com/foosel/OctoPrint/issues/677) - Fixed extruder offsets not being properly editable in
    printer profiles
  * [#683](https://github.com/foosel/OctoPrint/issues/683) - Fixed heated bed option not being properly displayed in
    printer profiles
* Various fixes without tickets:
  * GCODE viewer now doesn't stumble over completely extrusionless GCODE files
  * Do not deliver the API key on settings API unless user has admin rights
  * Don't hiccup on slic3r filament_diameter comments in GCODE generated for multi extruder setups

## 1.1.2 (Unreleased)

### Bug Fixes

* [#634](https://github.com/foosel/OctoPrint/pull/634) - Fixed missing `branch` fields in version dicts generated
  by versioneer
* [IRC] Don't hiccup on slic3r filament_diameter comments generated for multi extruder setups

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
