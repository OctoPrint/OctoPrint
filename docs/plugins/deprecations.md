(sec-plugins-deprecations)=
# Current deprecations & upcoming behaviour changes

This document lists all active deprecations or possibly disruptive behaviour changes that require actions from plugin authors or third party clients to avoid breaking in forthcoming versions of OctoPrint.

(sec-plugins-deprecations-2_1_0)=
## Upcoming changes for OctoPrint 2.1.0

(sec-plugins-deprecations-2_1_0-global_apikey)=
### Removal of Global API key

The global API key will get removed for good in OctoPrint 2.1.0. If your plugin is still relying on it in any shape or form, you need to migrate off of it **now**.

If you utilize it to access APIs provided by other plugins installed in OctoPrint, use the [one-time use `plugin_apikey`](#octoprint.plugin.types.OctoPrintPlugin.plugin_apikey) instead. See also [above](#sec-plugins-octo_2_0_0-api-global_api_key).

```{deprecated} 1.6.0
```

(sec-plugins-deprecations-2_1_0-prefixed_plugin_templates)=
### Plugin specific prefix required in plugin templates

Including plugin template without a `plugin_<plugin identifier>` prefix has now been deprecated since version 1.8.0. The compatibility layer that is still allowing for this to work will be removed in OctoPrint 2.1.0.

If your plugin is still including `jinja2` templates without using the `plugin_<plugin identifier>` prefix, you need to fix this *now*.

Look for two things in your code:

1. Imports of other plugin templates in your own plugin's templates, e.g.

   ``` jinja
   {% include "snippets/my_snippet.jinja2" %}
   ```

   will only be resolved relatively to the current plugin, and thus need
   to be prefixed referencing the target plugin going forward:

   ``` jinja
   {% include "plugin_some_other_plugin/snippets/my_snippet.jinja2" %}
   ```
2. Templates rendered by your plugin. e.g. in a custom route created through the [`BlueprintPlugin` mixin](#sec-plugins-mixins-blueprintplugin) need to be prefixed as well. Example:

   {emphasize-lines="5"}
   ``` python
   @octoprint.plugin.BlueprintPlugin.route("/foo", methods=["GET"])
   def foo_endpoint(self):
       return flask.make_response(
         flask.render_template(
           "some_template.jinja2"
         )
       )
   ```

   needs to be turned into

   {emphasize-lines="5"}
   ``` python
   @octoprint.plugin.BlueprintPlugin.route("/foo", methods=["GET"])
   def foo_endpoint(self):
       return flask.make_response(
         flask.render_template(
           "plugin_my_plugin/some_template.jinja2"
         )
       )
   ```

   for a plugin with identifier `my_plugin`.

```{deprecated} 1.8.0
```

### `TemplatePlugin` template auto-escaping switches from opt-in to opt-out

Starting with OctoPrint 1.11.0, OctoPrint supports enforcing auto-escaping on all plugin templates. Until OctoPrint 2.1.0, this is on opt-in mode, meaning plugins that want to enable auto-escaping for reasons of improved security have to actively tell OctoPrint about that.

With 2.1.0 that will change, and OctoPrint *by default* will enable auto-escaping on all third party plugins too.

If your plugin implements `TemplatePlugin`, you should check whether your plugin works with enabled auto-escaping by first opting in:

{emphasize-lines="4-5"}
``` python
class MyPlugin(octoprint.plugin.TemplatePlugin):
    # ...

    def is_template_autoescaped(self):
        return True
```

and then testing the plugin fully. If there are any issues, they should ideally be fixed without disabling auto-escaping.

If it is required to be able to include some HTML from a variable in a template, but only in some specific places, the manual escape filter [`|e`](https://jinja.palletsprojects.com/en/stable/templates/#working-with-manual-escaping) may be used. It's also possible to mark certain includes as safe code by adding [`|safe`](https://jinja.palletsprojects.com/en/stable/templates/#working-with-automatic-escaping). It is important to make *extra* sure to only do that in code that you have under control. Don't mark any variables or other output as safe that can be changed by user input!

[Please also refer to OctoPrint's FAQ entry on auto-escaping](https://community.octoprint.org/t/61067).

```{deprecated} 1.11.0
```

### `SimpleApiPlugin` endpoint protection switches from opt-in to opt-out mode

Starting with OctoPrint 1.11.2, OctoPrint supports enforcing of some basic authentication on all `SimpleApiPlugin` endpoints. Until OctoPrint 2.1.0, this is on opt-in mode, meaning that plugins that want to enable endpoint protection for the sake of improved security have to actively tell OctoPrint about that.

With 2.1.0 that will change, and OctoPrint *by default* will enable protection on all endpoints.

Plugin authors should check whether their plugin works with enabled protection by first opting in:

{emphasize-lines="4-5"}
``` python
class MyPlugin(octoprint.plugin.SimpleApiPlugin):
    # ...

    def is_api_protected(self):
        return True
```

and then testing their plugin fully. If there are any issues, they should ideally be fixed without disabling API protection. If this does not work for reasons of implementation or wanted workflow, instead an explicit opt-out should be done here by returning `False` **and manually implementing authentication on endpoints that should not be completely open**.

```{deprecated} 1.11.2
```

(sec-plugins-deprecations-2_1_0-settings_vm_users)=
### Removal of `SettingsViewModel.users`

`SettingsViewModel.users` is no longer needed by OctoPrint core and will be removed in 2.1.0. 

Should your plugin for whatever reason rely on it instead of having `accessViewModel` on its own dependencies (and thus access to `accessViewModel.users`), you should change this:

1. add a dependency to `accessViewModel` in your plugin's view model
2. replace usages of `self.settingsViewModel.users` (or however you called the parameter you keep the injected `SettingsViewModel` instance in) to `self.accessViewModel.users`

```{deprecated} 2.0.0
```

(sec-plugins-deprecations-2_1_0-system_event_shell)=
### Change of default for `shell` argument in system command event subscriptions

System command event subscriptions configured in `events.yaml` that do not explicitly define the `shell` argument currently default to `shell=True` on the resulting command call. As that is a potential security issue, OctoPrint 2.1.0 will change this default to `shell=False`.

If you rely on shell behaviour (e.g. shell expansion, pipes, redirection) in your event subscriptions, you need to add `shell: true` to them explicitly now to avoid breakage in 2.1.0.

```{deprecated} 2.0.0
```

(sec-plugins-deprecations-2_2_0)=
## Upcoming changes for OctoPrint 2.2.0

(sec-plugins-deprecations-2_2_0-settings_vm_webcam)=
### Removal of the webcam compatibility layer in `SettingsViewModel`

The following observables still present in `SettingsViewModel` (with a deprecation warning) are deprecated since OctoPrint 1.9.0 and will be removed for good in 2.2.0. Their replacements are mentioned right next to them:

  - `webcam_streamUrl` -> `settings.webcam.streamUrl`
  - `webcam_streamRatio` -> `settings.webcam.streamRatio`
  - `webcam_streamTimeout` -> `settings.webcam.streamTimeout`
  - `webcam_streamWebrtcIceServers` -> `settings.webcam.webrtcIceServers`
  - `webcam_snapshotUrl` -> `settings.webcam.snapshotUrl`
  - `webcam_flipH` -> `settings.webcam.flipH`
  - `webcam_flipV` -> `settings.webcam.flipV`
  - `webcam_rotate90` -> `settings.webcam.rotate90`
  - `webcam_cacheBuster` -> `settings.webcam.cacheBuster`

```{deprecated} 1.9.0
```

(sec-plugins-deprecations-2_2_0-slicing_vm_gcodefilename)=
### Removal of renamed `SlicingViewModel.gcodeFilename`

`SlicingViewModel.gcodeFilename` has been renamed to `SlicingViewModel.destinationFilename` since 2.0.0.

Support for the old name will be removed in OctoPrint 2.2.0.

If you make use of this observable in your plugin, adjust it accordingly.

```{deprecated} 2.0.0
```

(sec-plugins-deprecations-3_0_0)=
## Upcoming changes for OctoPrint 3.0.0

(sec-plugins-deprecations-3_0_0-settings_getter_and_setter)=
### Removal of renamed `PluginSettings.(get|set)(Int|Float|Boolean)`

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

```{deprecated} 1.2.0
```

(sec-plugins-deprecations-3_0_0-user_factory_hook)=
### Removal of renamed `octoprint.users.factory` hook

The plugin hook `octoprint.users.factory` has been declared deprecated in OctoPrint 2.0.0 and will be removed in OctoPrint 3.0.0. It has long been replaced by `octoprint.access.users.factory`. 

If your plugin still implements `octoprint.users.factory`, switch its registration over to the drop-in replacement `octoprint.access.users.factory`.

```{deprecated} 2.0.0
```

(sec-plugins-deprecations-3_0_0-jsclient_users_update_admin)=
### Removal of `admin` parameter on `OctoPrintClient.access.users.update`

Calling `OctoPrintClient.access.users.update` with the `admin` parameter at the third spot is deprecated since 2.0.0 and will no longer be supported in OctoPrint 3.0.0.

Use `permissions` or `groups` instead to add or remove the admin permissions on a user account.

Please also refer to [the docs of `OctoPrintClient.access.users.update`](#OctoPrintClient.access.users.update) for the correct calling signature.

```{deprecated} 2.0.0
```

(sec-plugins-deprecations-3_0_0-jsclient_printer_sd)=
### Removal of renamed printer storage related methods on `OctoPrintClient.printer` 

The following methods on `OctoPrintClient.printer` have been renamed:

  - `issueSdCommand` -> `issueStorageCommand`
  - `getSdState` -> `getStorageState`
  - `initSd` -> `initStorage`
  - `releaseSd` -> `releaseStorage`
  - `refreshSd` -> not renamed but replaced, use `OctoPrintClient.files.listForLocation`

The old names still work, but will display a deprecation warning in the browser console. If your plugin or other client is using any of these methods, make sure to switch to the new name.

```{deprecated} 2.0.0
```

(sec-plugins-deprecations-3_0_0-access_vm_current_user)=
### Removal of `AccessViewModel.isCurrentUser` in favor of `AccessViewModel.isUserMyself`

`AccessViewModel.isCurrentUser` has been renamed to `AccessViewModel.isUserMyself` to combat some ambiguity of the former name.

Replace usage in your code accordingly.

```{deprecated} 2.0.0
```

(sec-plugins-deprecations-3_0_0-files_vm_sd)=
### Removal of renamed printer storage related methods on `FilesViewModel`

The following methods on `FilesViewModel` have been renamed:

  - `initSdCard` -> `initPrinterStorage`
  - `releaseSdCard` -> `releasePrinterStorage`
  - `refreshSdFiles` -> `refreshPrinterStorage`

The old names still work, but will display a deprecation warning in the browser console. If your plugin or other client is using any of these methods, make sure to switch to the new name.

```{deprecated} 2.0.0
```

### Removal of `local` parameter from events `TransferStarted`, `TransferDone` and `TransferFailed`

The payload of [the `TransferStarted`, `TransferDone` and `TransferFailed` events](#sec-events-available_events-file_handling) currently still contains an attribute `local` which is the same as `path` since 2.0.0 and which will get removed in 3.0.0.

```{deprecated} 2.0.0
```

(sec-plugins-deprecations-3_0_0-jsclient_appkeys_revokekey)=
### Removal of renamed `OctoPrintClient.plugins.appkeys.revokeKey`

`OctoPrintClient.plugins.appkeys.revokeKey` has been renamed to `OctoPrintClient.plugins.appkeys.revokeKeyForApp`.

The old name still works, but will display a deprecation warning in the browser console. If your plugin or other client is using this method, make sure to switch to the new name.

```{deprecated} 1.10.0
```

(sec-plugins-deprecations-3_0_0-api_system)=
### Removal of the `POST /api/system` compatibility wrapper

The legacy `POST /api/system` API endpoint has been replaced by `POST /api/system/commands/custom/<action>` since 1.3.0. The old endpoint is still kept as a compatibility wrapper that internally redirects to the new one while logging a deprecation warning, and will be removed in OctoPrint 3.0.0.

If your plugin or other client is still issuing requests against `POST /api/system`, switch them over to `POST /api/system/commands/custom/<action>` now.

```{deprecated} 1.3.0
```

(sec-plugins-deprecations-undetermined)=
## Deprecations that don't yet have a removal version defined

### Removal of deprecated methods on `octoprint.printer.standard.Printer`, also known as `self._printer`

- `get_connection_options` -> use `ConnectedPrinter.all()` in combination with `connection_options` on the returned `ConnectedPrinter` instances instead
- `select_file` -> `set_job`
- `unselect_file` -> `set_job` with `None`
- `fake_ack` -> `repair_communication`
- `get_transport` -> only functional if the current connector happens to be the bundled serial connector, please get in touch in the shape of a [feature request](https://github.com/OctoPrint/OctoPrint/issues) so we can figure out what you use this for
- `get_current_connection` -> replaced by `connection_state`, the compatibility layer is only functional if the current connector happens to be the bundled serial connector
- `is_sd_ready` -> `is_storage_mounted`
- `init_sd_card` -> `mount_storage`
- `release_sd_card` -> `unmount_storage`
- `get_sd_files` -> use the `printer` storage instead via the file manager
- `add_sd_file` -> use the `printer` storage instead via the file manager
- `delete_sd_file` -> use the `printer` storage instead via the file manager
- `refresh_sd_files` -> use the `printer` storage instead via the file manager
- `can_modify_file` -> directly compare the job parameters against `current_job` and check the current printing state
- `is_current_file` -> directly compare the job parameters against `current_job`

```{deprecated} 2.0.0
```

#### Migration example: `select_file`

``` python
from octoprint.filemanager import FileDestinations
from octoprint.util.version import is_octoprint_compatible

if is_octoprint_compatible(">=2"):
    job = self._file_manager.create_job(storage, path)
    self._printer.set_job(job, print_after_select=False)
else:
    is_sd = storage == FileDestinations.SDCARD
    file_to_select = path if is_sd else self._file_manager.path_on_disk(storage, path)
    self._printer.select_file(file_to_select, sd=is_sd, printAfterSelect=False)
```

#### Migration example: `unselect_file`

``` python
from octoprint.util.version import is_octoprint_compatible

if is_octoprint_compatible(">=2"):
    self._printer.set_job(None)
else:
    self._printer.unselect_file()
```

#### Migration example: `refresh_sd_files` & `get_sd_files`

```python
from octoprint.filemanager import FileDestinations
from octoprint.util.version import is_octoprint_compatible

if is_octoprint_compatible(">=2"):
    self._file_manager.list_storage_entries([FileDestinations.PRINTER], force_refresh=blocking)
else:
    self._printer.get_sd_files(blocking=blocking)
```

#### Migration example: `can_modify_file`

``` python
from octoprint.filemanager import FileDestinations
from octoprint.util.version import is_octoprint_compatible

if is_octoprint_compatible(">=2"):
    current_job = self._printer.current_job
    is_current_job = current_job is not None and current_job.path == path and current_job.storage == storage
    return not (is_current_job and (self._printer.is_printing() or self._printer.is_paused()))
else:
    is_sd = storage == FileDestinations.SDCARD
    storage_path = path if is_sd else self._file_manager.path_on_disk(storage, path)
    return self._printer.can_modify_file(storage_path, is_sd)
```

#### Migration example: `is_current_file`

``` python
from octoprint.filemanager import FileDestinations
from octoprint.util.version import is_octoprint_compatible

if is_octoprint_compatible(">=2"):
    current_job = self._printer.current_job
    return current_job is not None and current_job.path == path and current_job.storage == storage
else:
    is_sd = storage == FileDestinations.SDCARD
    storage_path = path if is_sd else self._file_manager.path_on_disk(storage, path)
    return self._printer.is_current_file(storage_path, is_sd)
```

### Removal of direct access to `octoprint.util.comm`

The `octoprint.util.comm` module has been moved into the bundled plugin `serial_connector` and is now available as `octoprint.plugins.serial_connector.serial_comm`. Direct access to `octoprint.util.comm` is deprecated and only kept as a compatibility layer that re-exports from the new location.

If your plugin imports anything from `octoprint.util.comm`, switch its imports over to `octoprint.plugins.serial_connector.serial_comm`.

```{deprecated} 2.0.0
```

### Removal of deprecated methods on `octoprint.filemanager.FileManager`, also known as `self._filemanager`

- `list_files` -> `list_storage_entries`
- `get_file` -> `get_storage_entry`
- `add_link` -> no alternative
- `remove_link` -> no alternative

```{deprecated} 2.0.0
```

### Removal of deprecated methods on `octoprint.filemanager.storage.StorageInterface` and thus any storages

- `last_modified` -> `get_lastmodified`
- `get_file` -> `get_storage_entry`
- `list_files` -> `list_storage_entries`
- `add_link` -> no alternative
- `remove_link` -> no alternative

```{deprecated} 2.0.0
```

### Removal of `octoprint.server.util.flask.get_remote_address`

Replaced by `flask.request.remote_addr`.

```{deprecated} 1.10.0
```

### `octoprint.plugin.PluginInfo.blacklisted` renamed to `blocklisted`

`octoprint.plugin.PluginInfo.blacklisted` has been renamed to `octoprint.plugin.PluginInfo.blocklisted`. Adjust calling code accordingly.

```{deprecated} 2.0.0
```

### `octoprint.util.thaw_immutabledict` renamed to `thaw_frozendict`

`octoprint.util.thaw_immutabledict` has been renamed to `octoprint.util.thaw_frozendict`. Adjust calling code accordingly.

```{deprecated} 1.8.0
```

### Removal of the `serial.*` settings compatibility overlay

All settings previously located under `serial.*` have been moved with the migration of the serial communication stack to the bundled `serial_connector` plugin. A read-only compatibility overlay exposes the new settings under their old `serial.*` paths: reads return the current value and log a deprecation warning, while writes are silently dropped. The overlay will be removed in a future release.

If your plugin reads or writes settings under `serial.*`, switch it over to the new locations:

- Connection parameters:
  - `serial.port` -> `printerConnection.preferred.parameters.port`
  - `serial.baudrate` -> `printerConnection.preferred.parameters.baudrate`
  - `serial.autoconnect` -> `printerConnection.autoconnect`
  - `serial.autorefresh` -> `printerConnection.autorefresh`
  - `serial.autorefreshInterval` -> `printerConnection.autorefreshInterval`
- Suppressed command notifications:
  - `serial.notifySuppressedCommands` -> `feature.notifySuppressedCommands`
- Checksum and error handling:
  - `serial.alwaysSendChecksum` / `serial.neverSendChecksum` -> `plugins.serial_connector.sendChecksum` (which is now an enum with values: `always`, `never`, `printing`)
  - `serial.disconnectOnErrors` / `serial.ignoreErrorsFromFirmware` -> `plugins.serial_connector.errorHandling` (which is now an enum with values: `disconnect`, `ignore`, `cancel`)
- Blocklisted ports and baudrates:
  - `serial.blacklistedPorts` -> `plugins.serial_connector.blocklistedPorts`
  - `serial.blacklistedBaudrates` -> `plugins.serial_connector.blocklistedBaudrates`
- All other former `serial.*` settings -> `plugins.serial_connector.*` with the same key name

```{deprecated} 2.0.0
```

### Removal of the `Blacklist` settings compatibility overlay

The settings keys containing `Blacklist` have been renamed to `Blocklist`. A read-only compatibility overlay exposes the new settings under their old names: reads return the current value and log a deprecation warning, while writes are silently dropped. The overlay will be removed in a future release.

If your plugin reads or writes one of these settings, switch it over to the new names:

- `feature.autoUppercaseBlacklist` -> `feature.autoUppercaseBlocklist`
- `server.pluginBlacklist` -> `server.pluginBlocklist`

```{deprecated} 2.0.0
```

### Removal of the `webcam.*` settings compatibility overlay

The top-level `webcam.*` settings have been superseded by the new webcam system introduced in OctoPrint 1.9.0, with configuration now provided by plugins implementing the [`WebcamProviderPlugin` mixin](#sec-plugins-mixins-webcamproviderplugin). A read-only compatibility overlay exposes the configuration of the currently configured default webcam under the old `webcam.*` paths: reads return the current value and log a deprecation warning, while writes are silently dropped. The overlay will be removed in a future release.

If your plugin reads or writes webcam configuration via the `webcam.*` global settings paths, switch it over to the methods provided by the [`WebcamProviderPlugin` mixin](#sec-plugins-mixins-webcamproviderplugin).

```{deprecated} 1.9.0
```
