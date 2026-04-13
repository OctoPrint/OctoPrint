(sec-plugins-octo_2_0_0)=
# Migrating to OctoPrint 2.0.0

With OctoPrint 2.0.0 quite a number of compatibility layers in place for most of the past decade are finally getting removed, causing potential breakage for existing plugins still relying on these compatilibity layers after having ignored the related deprecation warnings for years.

It's time to finally migrate, and this guide is in place to show you how to quickly get your plugin up and running under OctoPrint 2.0.0 again as all but 1 of the removed deprecated endpoints and functions have had replacements available for a long time already!

:::{note}
This looks like an incredibly long list. But please don't get discouraged by this. Most plugins won't have to do anything but maybe one or two points, some note even anything at all.

This migration guide lists *all* changes in OctoPrint 2.0.0 that might require changes in any plugin (or client) implementations. Whether your plugin is affected by any of them relies heavily on the implementation and complexity of your plugin.

However, even if you are not affected by any of the necessary changes, please take note of the section on [migrating your plugin to the use of pyproject.toml](sec-plugins-octo_2_0_0-project) and also the section on [upcoming removals that already have active deprecation warnings](sec-plugins-octo_2_0_0-upcoming).
:::

(sec-plugins-octo_2_0_0-server)=
## Server side

(sec-plugins-octo_2_0_0-server-access)=
### Access control

(sec-plugins-octo_2_0_0-server-access-octoprint_access_users)=
#### Changes in `octoprint.access.users.*`

Various long deprecated (and replaced) methods have been removed from `octoprint.access.users.UserManager`, `octoprint.access.users.FilebasedUserManager`, `octoprint.access.users.User` and `octoprint.access.users.SessionUser`. If your code utilizes any of them,  you'll need to migrate.

What follows is a list of all methods and their corresponding replacements:

  - `octoprint.access.users.UserManager`:
    - `checkPassword` -> `check_password`
    - `addUser` -> `add_user`
    - `changeUserActivation` -> `change_user_activation`
    - `changeUserPassword` -> `change_user_password`
    - `getUserSetting` -> `get_user_setting`
    - `getAllUserSettings` -> `get_all_user_settings`
    - `changeUserSetting` -> `change_user_setting`
    - `changeUserSettings` -> `change_user_settings`
    - `removeUser` -> `remove_user`
    - `findUser` -> `find_user`
    - `getAllUsers` -> `get_all_users`
    - `hasBeenCustomized` -> `has_been_customized`
    - `changeUserRoles` -> `change_user_permissions`
    - `addRolesToUser` -> `add_permissions_to_user`
    - `removeRolesFromUser` -> `remove_permissions_from_user`
  - `octoprint.access.users.FilebasedUserManager`:
    - `generateApiKey` -> `generate_api_key`
    - `deleteApiKey` -> `delete_api_key`
    - `addUser` -> `add_user`
    - `changeUserActivation` -> `change_user_activation`
    - `changeUserPassword` -> `change_user_password`
    - `getUserSetting` -> `get_user_setting`
    - `getAllUserSettings` -> `get_all_user_settings`
    - `changeUserSetting` -> `change_user_setting`
    - `changeUserSettings` -> `change_user_settings`
    - `removeUser` -> `remove_user`
    - `findUser` -> `find_user`
    - `getAllUsers` -> `get_all_users`
    - `hasBeenCustomized` -> `has_been_customized`
  - `octoprint.access.users.User`
    - `asDict` -> `as_dict`
    - `is_admin`, `is_user`, `roles` -> check specific permissions instead, e.g.:

      ``` python
      from octoprint.access.permissions import Permissions

      # instead of user.is_admin:
      is_admin = user.has_permission(Permissions.ADMIN)  # preferred!
      is_admin = "admin" in user.groups

      # instead of user.is_user:
      is_user = not user.is_anonymous  # preferred!
      is_user = "user" in user.groups
      ```
  - `octoprint.access.users.SessionUser`
    - `get_session` -> `session`

(sec-plugins-octo_2_0_0-server-access-octoprint_users)=
#### Removed `octoprint.users`

`octoprint.users` has long been deprecated and has finally been removed in 2.0.0. Change your imports to `octoprint.access.users`.

(sec-plugins-octo_2_0_0-server-admin_permission)=
#### Removed `octoprint.server.admin_permission` & `octoprint.server.user_permission`

Both of these permission helpers have long been deprecated and have finally been removed in 
2.0.0. Use individual and *specific* permissions instead. Easy drop-in replacements follow:

``` python
from octoprint.access import groups

admin_permission = groups.GroupPermission(groups.ADMIN_GROUP)
user_permission = groups.GroupPermission(groups.USER_GROUP)
```

However, it is *strongly* recommend to think whether some more granular (and possibly [custom](#sec-plugins-hook-permissions)) permissions aren't better suited for your specific usecase!

(sec-plugins-octo_2_0_0-server-storage)=
### File storage, printable files

(sec-plugins-octo_2_0_0-server-storage-sdcard_value)=
#### Changed value of `octoprint.filemanager.FileDestinations.SDCARD`

The value of `FileDestinations.SDCARD` has changed from `printer` to `sdcard`. Any plugins that compared it against the hardcoded string will fail the comparison. Switch your code to using `FileDestinations.PRINTER` for all required checks! Example:

``` python
from octoprint.storage import FileDestinations

if storage == FileDestinations.PRINTER:  # preferred!
    # do something

if storage == FileDestinations.SDCARD:
    # do something
```
(sec-plugins-octo_2_0_0-server-storage-updated_files)=
#### Dropped event type `gcode` for `UpdatedFiles` event

The [`UpdatedFiles` event](#sec-events-available_events-file_handling) generated inside the storage subsystemis no longer generated for the file type `gcode` but only for the file type `printables` now.

If you still rely `UpdatedFiles` to be fired with `type: gcode`, you need
to switch over to `type: printables` now.

(sec-plugins-octo_2_0_0-server-plugin)=
### Plugin system

#### `octoprint.plugin.PluginSettings.get_plugin_data_folder` removed

The long-deprecated `octoprint.plugin.PluginSettings.get_plugin_data_folder` has finally been removed in favor of its established replacement [`octoprint.plugin.OctoPrintPlugin.get_plugin_data_folder`](#octoprint.plugin.types.OctoPrintPlugin.get_plugin_data_folder).

In practice for plugins that means relacing any calls to `self._settings.get_plugin_data_folder` with `self.get_plugin_data_folder`. Note that if the only reason for your plugin to implement [the `SettingsPlugin` mixin](#octoprint.plugin.SettingsPlugin) was to be able to access your plugin's data folder, you can then also remove that mixin from your plugin.

(sec-plugins-octo_2_0_0-server-printer)=
### Printer interaction

(sec-plugins-octo_2_0_0-server-printer-get_transport)=
#### `Printer.get_transport` no longer functional

`get_transport` is no longer functional. There is no alternative implementation. Plugins 
relying on it should please get in touch so we can figure out how to achieve what they so
far have been doing by utilizing this method.

(sec-plugins-octo_2_0_0-server-printer-internal)=
#### Internal attributes of `Printer` class renamed

Some internal attributes of the `octoprint.printer.Printer` class (injected as `self.
_printer into plugin implementations) have been renamed. Plugins that accessed the 
following (**private**) attributes will need to update the names. Please note that these 
are *not* drop-in replacements, and if at all possible your plugin should rather not use 
them at all but rather reply on the public documented API!

The affected names are:

  - `_comm` -> `_connection`
  - `_selectedFile` -> `_selected_job`
  - `_currentZ` -> `_last_z`
  - `_printerProfileManager` -> `_printer_profile_manager`
  - `_fileManager` -> `_file_manager`

(sec-plugins-octo_2_0_0-server-printer-log_format)=
#### Format of terminal log lines changed

Terminal log lines as generated by the serial connection no longer have the prefixes `Recv:` and `Send:` but rather `<<<` and `>>>`. 

Any consumers of these logs must updated their parsers. 

The terminal filters have already been updated accordingly.

(sec-plugins-octo_2_0_0-server-printer-bedtypes)=
#### `octoprint.printer.profile.BedTypes` removed

The long deprecated `octoprint.printer.profile.BedTypes` type has been removed. Its drop-in replacement is the more aptly named `octoprint.printer.profile.BedFormFactor`.

(sec-plugins-octo_2_0_0-server-settings)=
### Settings

(sec-plugins-octo_2_0_0-server-settings-serial)=
#### The `serial.*` block has moved

The `serial` block in the settings schema has moved to `plugins.serial_connector` as its now managed by that bundled plugin.

If you are accessing any `serial` related settings in your plugin, you'll need to adapt your accessing code. In most cases you can just replace all settings paths referring to `serial.*` with `plugins.serial_connector.*`, **with the following exceptions**:

  - `serial.port` -> `printerConnection.preferred.parameters.port`
  - `serial.baudrate` -> `printerConnection.preferred.parameters.baudrate`
  - `serial.autoconnect` -> `printerConnection.autoconnect`
  - `serial.autorefresh` -> `printerConnection.autorefresh`
  - `serial.autorefreshInterval` -> `printerConnection.autorefreshInterval`
  - `serial.notifySuppressedCommands` -> `feature.notifySuppressedCommands`
  - `serial.alwaysSendChecksum`, `serial.neverSendChecksum` -> `plugins.serial_connector.sendChecksum`, set to `always` or `never`
  - `serial.disconnectOnErrors`, `serial.ignoreErrorsFromFirmware` -> `plugins.serial_connector.errorHandling`, set to `disconnect` or `ignore`
  - `serial.blacklistedPorts` -> `plugins.serial_connector.blacklistedPorts` (see also [below](#sec-plugins-octo_2_0_0-server-settings-blocklist))
  - `serial.blacklistedBaudrates` -> `plugins.serial_connector.blacklistedBaudrates` (see also [below](#sec-plugins-octo_2_0_0-server-settings-blocklist))

:::{info}
A compatibility layer is in place performing these mappings for you, however please 
migrate your plugin ASAP if it does access any of these settings to not be hit by the next
removal cycle of deprecated features!
:::

(sec-plugins-octo_2_0_0-server-settings-blocklist)=
#### More inclusive language with regards to "blacklist" and "whitelist"

The following path names containing the words "blacklist" or "whitelist" have been moved to the more inclusive phrasing "blocklist" and "allowlist" and calling code should adapt:

  - `feature.autoUppercaseBlacklist` -> `feature.autoUppercaseBlocklist`
  - `server.pluginBlacklist` -> `server.pluginBlocklist`
  - `serial.blacklistedPorts` -> `plugins.serial_connector.blocklistedPorts` (see also [above](#sec-plugins-octo_2_0_0-server-settings-serial))
  - `serial.blacklistedBaudrates` -> `plugins.serial_connector.blocklistedBoardrates` (see also [above](#sec-plugins-octo_2_0_0-server-settings-serial))

:::{info}
A compatibility layer is in place performing these mappings for you, however please 
migrate your plugin ASAP if it does access any of these settings to not be hit by the next
removal cycle of deprecated features!
:::

(sec-plugins-octo_2_0_0-server-settings-_config)=
#### `octoprint.settings.SettingsManager._config` removed

The long deprecated `octoprint.settings.SettingsManager._config` field has been removed. If you need read access to its old value, use the `config` property instead.

Write access should be avoided at all costs, but if absolutely necessary can be achieved through `_map.topmap`.

(sec-plugins-octo_2_0_0-server-util)=
### Util

There have been changes to the following long-deprecated methods from `octoprint.util`:

- `octoprint.util.bom_aware_open` removed, use the `-sig` suffixed encoding to handle BOM automatically, e.g.

  ``` python
  with open(filename, encoding="utf-8-sig", mode="r") as f:
      # do something
  ```
- `octoprint.util.dict_clean` removed, use [`octoprint.util.dict_sanitize`](#octoprint.util.dict_sanitize) instead
- `octoprint.util.to_str` removed, use [`octoprint.util.to_bytes`](#octoprint.util.to_bytes) instead
- `octoprint.util.to_native_str` removed, use [`octoprint.util.to_unicode`](#octoprint.util.to_unicode) instead
- [`octoprint.util.commandline.clean_ansi`](#octoprint.util.commandline.clean_ansi) no longer accepts `bytes` as input, convert to `str` before calling
- `octoprint.util.json.dump` removed, use [`octoprint.util.json.dumps`](#octoprint.util.json.dumps) instead

(sec-plugins-octo_2_0_0-client)=
## Client side

(sec-plugins-octo_2_0_0-client-viewmodels)=
### Viewmodels

(sec-plugins-octo_2_0_0-client-viewmodels-users_vm)=
#### Removed `usersViewModel`

The `usersViewModel` has long been deprecated and was only a redirect to `accessViewModel.users`. Use that instead as a direct drop-in replacement.

(sec-plugins-octo_2_0_0-client-viewmodels-files_vm_request_data)=
#### Removed support for deprecated method calling signature on `FilesViewModel.requestData`

Calling `FilesViewModel.requestData` with a parameter list of `(focus, switchToPath, force)` is no longer supported. Instead use the single `params` parameter:

``` js
const params = {
    focus: undefined,
    switchToPath: undefined,
    force: false
}
self.filesViewModel.requestData(params);
```

(sec-plugins-octo_2_0_0-client-viewmodels-settings_vm_request_data)=
#### Removed support for deprecated method calling signature on `SettingsViewModel.requestData`

Calling `SettingsViewModel.requestData` with a `callback` parameter is no longer supported.
Instead, use the returned promise:

``` js
self.settingsViewModel.requestData()
    .done((response) => {
        // do something
    });
```

(sec-plugins-octo_2_0_0-client-viewmodels-on_wizard_tab_change)=
#### `onWizardTabChanged` removed

This has long been replaced by `onBeforeWizardTabChange`, so if your plugin still relies on the old name, please just switch to the new.

(sec-plugins-octo_2_0_0-client-jsclient)=
### JS Client

(sec-plugins-octo_2_0_0-client-jsclient-removed_endpoints)=
#### Removed clients for removed API endpoints

The following JS Client components have been removed, with established replacements documented next to them:

  - `OctoPrintClient.logs` -> `OctoPrintClient.plugin.logging`
  - `OctoPrintClient.users` -> `OctoPrintClient.access.users`

(sec-plugins-octo_2_0_0-client-jsclient-get_request_headers)=
#### Removed support for deprecated method calling signature on `OctoPrintClient.getRequestHeaders`

Calling `OctoPrintClient.getRequestHeaders` with additional headers as the first argument
is no longer supported, instead callers need to add additional headers via the `additional`
parameter. Example:

``` js
const headers = OctoPrintClient.getRequestHeaders(
    "POST", 
    {"Some-Header": "Some Value"}
)
```

(sec-plugins-octo_2_0_0-client-jsclient-deprecated_method)=
#### Removed `OctoPrintClient.deprecatedMethod`

If your plugin was using this, use [`OctoPrintClient.deprecated`](#OctoPrintClient.deprecated) instead.

(sec-plugins-octo_2_0_0-client-jsclient-deprecated_variable)=
#### Changed signature on `OctoPrintClient.deprecatedVariable`

If your plugin was using this, make sure to adjust the calling parameters to the the 
new signature. Refer to the documentation of [`OctoPrintClient.deprecatedVariable`](#OctoPrintClient.deprecatedVariable) for details.

(sec-plugins-octo_2_0_0-api)=
## API

(sec-plugins-octo_2_0_0-api-global_api_key)=
### Global API Key

The Global API Key has been deprecated for a while, with 2.0.0 is no longer automatically generated at startup and may thus be empty! [It will be removed entirely in 2.1.0](#sec-plugins-octo_2_0_0-upcoming-global_apikey).

Instead of utilizing this key to talk to OctoPrint's API endpoints from plugin code, plugins
should instead use [`self.plugin_apikey`](#octoprint.plugin.types.OctoPrintPlugin.plugin_apikey). Example:

``` python
import octoprint.plugin

import requests

class MyPlugin(octoprint.plugin.StartupPlugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._port = 5000

    def on_startup(self, host, port, *args, **kwargs):
        self._port = port

    def fetch_api_version(self, **kwargs):
        url = f"https://localhost:{self._port}/api/version"
        headers = {
            "X-Api-Key": self.plugin_apikey
        }

        return requests.get(url, headers=headers, timeout=5)
```

(sec-plugins-octo_2_0_0-api-endpoints)=
### `/api/logs/*`, `/api/users/*` and `/api/plugin/pluginmanager` removed

The following long deprecated API endpoints have been removed, with their established replacements shown next to them:

  - `/api/logs/*` -> `/api/plugin/logging/*`
  - `/api/users/*` -> `/api/access/users/*`
  - `/api/pluginmanager` -> `/plugin/pluginmanager/(plugins|orphan|repository)

Clients still relying on the old endpoints need to switch to the new ones.

(sec-plugins-octo_2_0_0-project)=
## Project organisation

(sec-plugins-octo_2_0_0-project-dependencies)=
### Dependencies

The `netifaces` and `passlib` libraries are no longer part of the dependencies of OctoPrint. Any plugins that import them without listing them as additional requirements will no longer be usable. If your plugin relies on functionality provided by either of these third party libraries, make sure to also make them part of your plugin's requirements by explicitly declaring them in `setup.py` or `pyproject.toml`.

(sec-plugins-octo_2_0_0-project-pyproject_toml)=
### `pyproject.toml` and build isolation

Now is a good as time as any to also [migrate your plugin to use pyproject.toml and build isolation](#sec-plugins-pyproject_toml), should you still be on the old `setup.py` based build approach.

(sec-plugins-octo_2_0_0-upcoming)=
## Prepare for upcoming removals too!

While you are it, please also take care of some upcoming removals that already have 
deprecation warnings going on.

(sec-plugins-octo_2_0_0-upcoming-global_apikey)=
### Global API key will get removed in 2.1.0

The global API key will get removed for good in OctoPrint 2.1.0. If your plugin is still relying on it in any shape or form, you need to migrate off of it **now**.

If you utilize it access APIs provided by other plugins installed in OctoPrint, use the [one-time use `plugin_apikey`](#octoprint.plugin.types.OctoPrintPlugin.plugin_apikey) instead. See also [above](#sec-plugins-octo_2_0_0-api-global_api_key).

(sec-plugins-octo_2_0_0-upcoming-settings_getter_and_setter)=
### `PluginSettings.(get|set)(Int|Float|Boolean)` will get removed in 3.0.0

The methods `getInt`, `getFloat`, `getBoolean`, `setInt`, `setFloat` and `setBoolean` of the [`PluginSettings`](#octoprint.plugin.PluginSettings) instance injected into plugin implementations as `self._settings` have been deprecated and logging deprecation warnings for 10 years. Yet they are still in heavy use by plenty third party plugins out there.

**This is the final warning for plugin authors to finally switch their plugins over to the long standing replacements `get_(int|float|boolean)` and `set_(int|float|boolean)`!**

In practice, that means these simple drop-in replacements in your plugin code:

- `self._settings.getInt` -> `self._settings.get_int`
- `self._settings.getFloat` -> `self._settings.get_float`
- `self._settings.getBoolean` -> `self._settings.get_boolean`
- `self._settings.setInt` -> `self._settings.set_int`
- `self._settings.setFloat` -> `self._settings.set_float`
- `self._settings.setBoolean` -> `self._settings.set_boolean`

OctoPrint 3.0.0 will remove the deprecated versions for good!

(sec-plugins-octo_2_0_0-upcoming-user_factory_hook)=
### Support for the `octoprint.users.factory` hook will be removed in 3.0.0

The plugin hook `octoprint.users.factory` has been declared deprecated in OctoPrint 2.0.0 and will be removed in OctoPrint 3.0.0. It has long been replaced by `octoprint.access.users.factory`. 

If your plugin still implements `octoprint.users.factory`, switch its registration over to the drop-in replacement `octoprint.access.users.factory`.