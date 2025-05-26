.. _sec-api-settings:

********
Settings
********

.. _sec-api-settings-retrieve:

Retrieve current settings
=========================

.. http:get:: /api/settings

   Retrieves the current configuration of OctoPrint.

   Returns a :http:statuscode:`200` with the current settings as a JSON object in the
   response body.

   The :ref:`data model <sec-api-settings-datamodel>` is similar to what can be found in
   :ref:`config.yaml <sec-configuration-config_yaml>`, see below for details.

   Requires the ``SETTINGS_READ`` permission.

.. _sec-api-settings-save:

Save settings
=============

.. http:post:: /api/settings

   Saves the provided settings in OctoPrint.

   Expects a JSON object with the settings to change as request body. This can be either a
   full settings tree, or only a partial tree containing only those fields that should
   be updated.

   Returns the currently active settings on success, as part of a :http:statuscode:`200` response.

   Requires the ``SETTINGS`` permission.

   **Example**

   Only change the UI color to black.

   .. sourcecode:: http

      POST /api/settings HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...
      Content-Type: application/json

      {
        "appearance": {
          "color": "black"
        }
      }

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "api": {
          "enabled": true
        },
        "appearance": {
          "color": "black"
        }
      }

.. _sec-api-settings-generateapikey:

Regenerate the system wide API key
==================================

.. http:post:: /api/settings/apikey

   Generates a new system wide API key.

   Does not expect a body. Will return the generated API key as ``apikey``
   property in the JSON object contained in the response body.

   Requires admin rights.

   :status 200:     No error
   :status 403:     No admin rights

.. _sec-api-settings-fetchtemplaatedata:

Fetch template data
===================

.. http:get:: /api/settings/templates

   Fetch data (currently only the sorting order) of all registered template components in the system.

   Use this to get a full list of the identifiers of all UI components provided either by core OctoPrint or any
   currently active plugins.

   Example:

   .. sourcecode:: http

      GET /api/settings/templates HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "order": {
          "about": [
            {
              "id": "about",
              "name": "About OctoPrint"
            },
            {
              "id": "supporters",
              "name": "Supporters"
            },
            {
              "id": "authors",
              "name": "Authors"
            },
            {
              "id": "changelog",
              "name": "Changelog"
            },
            {
              "id": "license",
              "name": "OctoPrint License"
            },
            {
              "id": "thirdparty",
              "name": "Third Party Licenses"
            },
            {
              "id": "plugin_pluginmanager",
              "name": "Plugin Licenses",
              "plugin_id": "pluginmanager",
              "plugin_name": "Plugin Manager"
            }
          ],
          "generic": [
            {
              "id": "plugin_announcements",
              "name": "plugin_announcements",
              "plugin_id": "announcements",
              "plugin_name": "Announcement Plugin"
            }
          ],
          "navbar": [
            {
              "id": "settings",
              "name": "settings"
            },
            {
              "id": "systemmenu",
              "name": "systemmenu"
            },
            {
              "id": "plugin_announcements",
              "name": "plugin_announcements",
              "plugin_id": "announcements",
              "plugin_name": "Announcement Plugin"
            },
            {
              "id": "login",
              "name": "login"
            }
          ],
          "plugin_pluginmanager_about_thirdparty": [],
          "settings": [
            {
              "id": "section_printer",
              "name": "Printer"
            },
            {
              "id": "serial",
              "name": "Serial Connection"
            },
            {
              "id": "printerprofiles",
              "name": "Printer Profiles"
            },
            {
              "id": "temperatures",
              "name": "Temperatures"
            },
            {
              "id": "terminalfilters",
              "name": "Terminal Filters"
            },
            {
              "id": "gcodescripts",
              "name": "GCODE Scripts"
            },
            {
              "id": "section_features",
              "name": "Features"
            },
            {
              "id": "features",
              "name": "Features"
            },
            {
              "id": "webcam",
              "name": "Webcam & Timelapse"
            },
            {
              "id": "accesscontrol",
              "name": "Access Control"
            },
            {
              "id": "gcodevisualizer",
              "name": "GCODE Visualizer"
            },
            {
              "id": "api",
              "name": "API"
            },
            {
              "id": "section_octoprint",
              "name": "OctoPrint"
            },
            {
              "id": "server",
              "name": "Server"
            },
            {
              "id": "folders",
              "name": "Folders"
            },
            {
              "id": "appearance",
              "name": "Appearance"
            },
            {
              "id": "plugin_logging",
              "name": "Logging",
              "plugin_id": "logging",
              "plugin_name": "Logging"
            },
            {
              "id": "plugin_pluginmanager",
              "name": "Plugin Manager",
              "plugin_id": "pluginmanager",
              "plugin_name": "Plugin Manager"
            },
            {
              "id": "plugin_softwareupdate",
              "name": "Software Update",
              "plugin_id": "softwareupdate",
              "plugin_name": "Software Update"
            },
            {
              "id": "plugin_announcements",
              "name": "Announcements",
              "plugin_id": "announcements",
              "plugin_name": "Announcement Plugin"
            },
            {
              "id": "section_plugins",
              "name": "Plugins"
            },
            {
              "id": "plugin_action_command_prompt",
              "name": "Action Command Prompt",
              "plugin_id": "action_command_prompt",
              "plugin_name": "Action Command Prompt Support"
            },
            {
              "id": "plugin_curalegacy",
              "name": "Cura Legacy",
              "plugin_id": "curalegacy",
              "plugin_name": "Cura Legacy"
            }
          ],
          "sidebar": [
            {
              "id": "plugin_printer_safety_check",
              "name": "Printer Safety Warning",
              "plugin_id": "printer_safety_check",
              "plugin_name": "Printer Safety Check"
            },
            {
              "id": "connection",
              "name": "Connection"
            },
            {
              "id": "state",
              "name": "State"
            },
            {
              "id": "files",
              "name": "Files"
            }
          ],
          "tab": [
            {
              "id": "temperature",
              "name": "Temperature"
            },
            {
              "id": "control",
              "name": "Control"
            },
            {
              "id": "gcodeviewer",
              "name": "GCode Viewer"
            },
            {
              "id": "terminal",
              "name": "Terminal"
            },
            {
              "id": "timelapse",
              "name": "Timelapse"
            }
          ],
          "usersettings": [
            {
              "id": "access",
              "name": "Access"
            },
            {
              "id": "interface",
              "name": "Interface"
            }
          ],
          "wizard": []
        }
      }

   Requires admin rights.

   .. warning::

      This API endpoint is in beta. Things might change. If you happen to want to develop against it, you should drop
      me an email to make sure I can give you a heads-up when something changes in an backwards incompatible way.

   :status 200: No error
   :status 403: No admin rights

.. _sec-api-settings-datamodel:

Data model
==========

The data model on the settings API mostly reflects the contents of
:ref:`config.yaml <sec-configuration-config_yaml>`, which are directly
mapped, with the following exceptions:

.. list-table::
   :header-rows: 1

   * - Field
     - Notes
   * - ``accessControl.*``
     - Only ``autologinLocal`` and ``autologinHeadsupAcknowledged`` are mapped, and only for users with the ADMIN permission.
   * - ``api.*``
     - Only ``key`` and ``allowCrossOrigin`` are mapped, and ``key`` only for users with the ADMIN permission and a recent credential check.
   * - ``appearance.components``
     - Not mapped.
   * - ``controls.*``
     - Only returned for users with the CONTROL permission.
   * - ``devel.*``
     - Only ``pluginTimings`` is mapped.
   * - ``estimation``
     - Not mapped.
   * - ``events.*``
     - Not mapped (but ``events.subscriptions`` is mapped by the bundled EventManager plugin on its subtree)
   * - ``feature.gcodeViewer``
     - Maps to ``gcodeViewer.enabled`` in ``config.yaml``
   * - ``feature.sizeThreshold``
     - Maps to ``gcodeViewer.sizeThreshold`` in ``config.yaml``
   * - ``feature.mobileSizeThreshold``
     - Maps to ``gcodeViewer.mobileSizeThreshold`` in ``config.yaml``
   * - ``folder.*``
     - Only ``uploads``, ``timelapse`` and ``watched`` are mapped.
   * - ``gcodeAnalysis.*``
     - Only ``runAt`` and ``bedZ`` are mapped.
   * - ``gcodeViewer.enabled``
     - Mapped to ``feature.gcodeViewer``
   * - ``gcodeViewer.sizeThreshold``
     - Mapped to ``feature.sizeThreshold``
   * - ``gcodeViewer.mobileSizeThreshold``
     - Mapped to ``feature.mobileSizeThreshold``
   * - ``plugins.*``
     - Plugin settings as available from ``config.yaml`` and :class:`~octoprint.plugin.SettingsPlugin` implementations. All of ``plugins._*`` (e.g. ``plugins._disabled``) are not mapped.
   * - ``printerProfiles.*``
     - Not mapped, available on the dedicated :ref:`API endpoints <sec-api-printerprofiles>`.
   * - ``serial.timeout.*``
     - Mapped to ``serial.timeout*``
   * - ``serial.maxCommunicationTimeouts.*``
     - Mapped to ``serial.maxTimeouts*``
   * - ``server.*``
     - Only ``server.commands``, ``server.diskspace``, ``server.onlineCheck``, ``server.pluginBlacklist`` and ``server.allowFraming`` are mapped. Modifying ``server.commands`` requires a recent credentials check.
   * - ``slicing.*``
     - Only ``slicing.defaultslicer`` is mapped.
   * - ``webcam.*``
     - Only returned for users with the WEBCAM permission. Largely mapped to ``webcam.*``
   * - ``webcam.ffmpeg``
     - Mapped to ``webcam.ffmpegPath``
   * - ``webcam.ffmpegThumbnailCommandline``
     - Not mapped.
   * - ``webcam.timelapse``
     - Not mapped, available on the dedicated :ref:`API endpoints <sec-api-timelapse>`.
   * - ``webcam.cleanTmpAfterDays``
     - Not mapped.
   * - Information about available webcam providers
     - Mapped to ``webcam.webcams[]``, fields of each entry are: ``provider``, ``name``, ``displayName``, ``canSnapshot``, ``snapshotDisplay``, ``flipH``, ``flipV``, ``rotate90``, ``extras`` and ``compat.*``
   * - Default webcam's config options ``flipH``, ``flipV``, ``rotate90`` and ``name``
     - Mapped to ``webcam.flipH``, ``webcam.flipV``, ``webcam.rotate90`` and ``webcam.defaultWebcam``
   * - Default webcam's compatibility layer ``stream``, ``streamRatio``, ``streamTimeout``, ``streamWebrtcIceServers``, ``snapshot``, ``snapshotTimeout``, ``snapshotSslValidation``, ``cacheBuster``
     - Mapped to ``webcam.*``
   * - Snapshot webcam's name
     - Mapped to ``webcam.snapshotWebcam``
