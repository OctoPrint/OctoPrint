.. _sec-plugins-viewmodels:

Viewmodels
==========

.. contents::
   :local:

When implementing frontend components, you'll sooner or later want to define your own `KnockoutJS view models <http://knockoutjs.com/>`_
in order to provide custom functionality.

.. _sec-plugins-viewmodels-registering:

Registering custom viewmodels
-----------------------------

Register your view model with OctoPrint's web app by pushing a config object unto the global array ``OCTOPRINT_VIEWMODELS``.

Possible properties in this config object are:

construct
    Function to use for constructing the view model instance. Usually that will be the view model class, which acts as
    a constructor. This property is mandatory.
name
    Name to register the view model under. If not provided, the name of the ``construct`` function will
    be used, turning the first letter lower case. If a view model under the same name already exists at time
    of construction, an error will be logged and the view model will not be instantiated.
additionalNames
    A list of additional names to also register the view model under. Only those that do not already exist will be
    registered.
dependencies
    List of dependencies the view model needs injected. If any of the view models in this list cannot be found,
    initialization of the view model will fail.  The parameters injected on instantiation will consist of first
    the ``dependencies``, then the ``optional`` list concatenated.
optional
    A list of optional dependencies the view model needs injected. If any of the view models in this list cannot be found,
    they will be ``null`` in the parameter list injected to the constructor on instantiation. The parameters injected on
    instantiation will consist of first the ``dependencies``, then the ``optional`` list concatenated.
elements
    A list of UI elements to bind to. Each binding target can be either a string which will then be passed to jQuery's
    ``$(...)`` method to resolve the target, or alternatively directly a jQuery element

Example:

.. code-block:: javascript
   :emphasize-lines: 12-22

   $(function() {
       function MyCustomViewModel(parameters) {
           var self = this;

           self.loginState = parameters[0]; // requested as first dependency below
           self.settings = parameters[1]; // requested as second dependency below
           self.someOtherViewModel = parameters[2]; // requested as first optional dependency below

           // more of your view model's implementation
       }

       // we don't explicitely declare a name property here
       // our view model will be registered under "myCustomViewModel" (implicit
       // name derived from contructor name) and "yourCustomViewModel" (explicitely
       // provided as additional name)
       OCTOPRINT_VIEWMODELS.push({
           construct: MyCustomViewModel,
           additionalNames: ["yourCustomViewModel"],
           dependencies: ["loginStateViewModel", "settingsViewModel"],
           optional: ["someOtherViewModel"],
           elements: ["#some_div", "#some_other_div"]
       });
   })

You might also come across a different approach to view model declaration, providing not a config object but instead
a 3-tuple of constructor, dependencies and elements to bind to. Additional names, different names than the default name
and optional dependencies cannot be specified with this format. It should be considered deprecated. Still, an example
of how that would look in practice is provided here as well:

.. code-block:: javascript
   :caption: Old tuple-based configuration format, consider this deprecated
   :emphasize-lines: 11-16

   $(function() {
       function MyCustomViewModel(parameters) {
           var self = this;

           self.loginState = parameters[0]; // requested as first constructor parameter below
           self.settingsViewModel = parameters[1] // requested as second constructor parameter below

           // more of your view model's implementation
       }

       // construct, dependencies, elements
       OCTOPRINT_VIEWMODELS.push([
           MyCustomViewModel,
           ["loginStateViewModel", "settingsViewModel"],
           ["#some_div", "#some_other_div"]
       ]);
   })

.. _sec-plugins-viewmodels-dependencies:

Dependencies
------------

OctoPrint will try to inject all view model dependencies requested by your view model. In order to do this it will
perform multiple passes iterating over all registered view models and collecting the necessary dependencies prior to
construction. Circular dependencies (A depends on B, B on C, C on A) naturally cannot be resolved and will cause an
error to be logged to the JavaScript console.

OctoPrint's core currently comes with the following view models that your plugin can request for injection:

appearanceViewModel
   View model that holds the appearance settings (name, color and transparency flag).
connectionViewModel
   View model for the connection sidebar entry.
controlViewModel
   View model for the control tab.
filesViewModel
   View model for the files sidebar entry. Also available under the deprecated name ``gcodeFilesViewModel``.
firstRunViewModel
   View model for the first run dialog.
gcodeViewModel
   View model for the gcode viewer tab.
gcodeFilesViewModel
   Deprecated in favor of ``filesViewModel``.
logViewModel
   View model for the logfile settings dialog.
loginStateViewModel
   View model for the current loginstate of the user, very interesting for plugins that need to
   evaluate the current login state or information about the current user, e.g. associated roles.
navigationViewModel
   View model for the navigation bar.
printerProfilesViewModel
   View model for the printer profiles settings dialog.
printerStateViewModel
   View model for the current printer state, very interesting for plugins that need
   to know information about the current print job, if the printer is connected, operational etc.
settingsViewModel
   View model for the settings dialog, also holds all settings to be used by other view models, hence
   very interesting for plugins as well.
slicingViewModel
   View model for the slicing dialog.
temperatureViewModel
   View model for the temperature tab, also holds current temperature information which
   might be interesting for plugins.
terminalViewModel
   View model for the terminal tab, also holds terminal log entries.
timelapseViewModel
   View model for the timelapse tab.
usersViewModel
   View model for the user management in the settings dialog.
userSettingsViewModel
   View model for settings associated with the currently logged in user, used for
   the user settings dialog.
wizardViewModel
   View model for the wizard dialog.

Each plugin's view model will be added to the view model map used for resolving dependencies as well, using
the view model's class name with a lower case first character as identifier (so "MyCustomViewModel" will be registered
for dependency injection as "myCustomViewModel") or an alternative name provided in the ``name`` property of the
config object, plus any configured ``additionalNames``.

.. _sec-plugins-viewmodels-callbacks:

Callbacks
---------

OctoPrint's web application will call several callbacks on all registered view models, provided they implement them.
Those are listed below:

onStartup()
   Called when the first initialization has been done: All view models are constructed and hence their dependencies
   resolved, no bindings have been done yet.

onBeforeBinding()
   Called per view model before attempting to bind it to its binding targets.

onAfterBinding()
   Called per view model after binding it to its binding targets.

onAllBound(allViewModels)
   Called after all view models have been bound, with the list of all view models as the single parameter.

onStartupComplete()
   Called after the startup of the web app has been completed.

onServerDisconnect()
   Called if a disconnect from the server is detected.

onDataUpdaterReconnect()
   Called when the connection to the server has been reestablished after a disconnect.

fromHistoryData(data)
   Called when history data is received from the server. Usually that happens only after initial connect in order to
   transmit the temperature and terminal log history to the connecting client. Called with the ``data`` as single parameter.

fromCurrentData(data)
   Called when current printer status data is received from the server with the ``data`` as single parameter.

onSlicingProgress(slicer, modelPath, machineCodePath, progress)
   Called on slicing progress, call rate is once per percentage point of the progress at maximum.

onEvent<EventName>(payload)
   Called on firing of an event of type ``EventName``, e.g. ``onEventPrintDone``. See :ref:`the list of available events <sec-events-available_events>`
   for the possible events and their payloads.

fromTimelapseData(data)
   Called when timelapse configuration data is received from the server. Usually that happens after initial connect.

onDataUpdaterPluginMessage(plugin, message)
   Called when a plugin message is pushed from the server with the identifier of the calling plugin as first
   and the actual message as the second parameter. Note that the latter might be a full fledged object, depending
   on the plugin sending the message. You can use this method to asynchronously push data from your plugin's server
   component to it's frontend component.

onUserLoggedIn(user)
   Called when a user gets logged into the web app, either passively (upon initial load of the page due to a valid
   "Remember Me" cookie) or due to an active completion of the login dialog. The user data of the just logged in user
   will be provided as only parameter.

onUserLoggedOut()
   Called when a user gets logged out of the web app.

onTabChange(next, current)
   Called before the main tab view switches to a new tab, so `before` the new tab becomes visible. Called with the
   next (changed to) and current (still visible) tab's hash (e.g. ``#control``). Note that ``current`` might be undefined
   on the very first call.

onAfterTabChange(current, previous)
   Called after the main tab view switches to a new tab, so `after` the new tab becomes visible. Called with the
   current and previous tab's hash (e.g. ``#control``).

getAdditionalControls()
   Your view model may return additional custom control definitions for inclusion on the "Control" tab of OctoPrint's
   interface. See :ref:`the custom control feature<sec-features-custom_controls>`.

onSettingsShown()
   Called when the settings dialog is shown.

onSettingsHidden()
   Called when the settings dialog is hidden.

onSettingsBeforeSave()
   Called just before the settings view model is sent to the server. This is useful, for example, if your plugin
   needs to compute persisted settings from a custom view model.

onUserSettingsShown()
   Called when the user settings dialog is shown.

onUserSettingsHidden()
   Called when the user settings dialog is hidden.

onWizardDetails(response)
   Called with the response from the wizard detail API call initiated before opening the wizard dialog. Will contain
   the data from all :class:`~octoprint.plugin.WizardPlugin` implementations returned by their :meth:`~octoprint.plugin.WizardPlugin.get_wizard_details`
   method, mapped by the plugin identifier.

onBeforeWizardTabChange(next, current)
   Called before the wizard tab/step is changed, with the ids of the next (changed to) and the current (still visible) tab
   as parameters. Return false in order to prevent the tab change, e.g. if the wizard step is mandatory and not yet
   completed by the user. Take a look at the "Core Wizard" plugin bundled with OctoPrint and the ACL wizard step in
   particular for an example on how to use this.

onAfterWizardTabChange(current)
   Called after the wizard tab/step is changed, with the id of the current tab as parameter. The id of the previous
   tab is sadly not available currently.

onBeforeWizardFinish()
   Called before executing the finishing of the wizard. Return false here to stop the actual finish, e.g. if some step is
   still incomplete.

onWizardFinish()
   Called after executing the finishing of the wizard and before closing the dialog. Return ``reload`` here in order to
   instruct OctoPrint to reload the UI after the wizard closes.

In order to hook into any of those callbacks, just have your view model define a function named accordingly, e.g.
to get called after all view models have been bound during application startup, implement a function ``onAllBound``
on your view model, taking a list of all bound view models:

.. code-block:: javascript
   :emphasize-lines: 7-8

   $(function() {
       function MyCustomViewModel(parameters) {
           var self = this;

           // ...

           self.onAllBound = function(allViewModels) {
               // do something with them
           }

           // ...
       }

       OCTOPRINT_VIEWMODELS.push({
           construct: MyCustomViewModel,
           dependencies: ["loginStateViewModel"],
           elements: ["#some_div", "#some_other_div"]
       });
   })

.. _sec-plugins-viewmodels-livecycle:

Lifecycle diagrams
------------------

.. _sec-plugins-viewmodels-startup:

Web interface startup
~~~~~~~~~~~~~~~~~~~~~

.. mermaid::

   sequenceDiagram
      participant Main
      participant onServerConnect
      participant fetchSettings
      participant bindViewModels
      participant DataUpdater
      participant LoginStateViewModel

      Note right of DataUpdater: connectCallback = undefined

      activate Main

      Main->>+DataUpdater: connect
      Note right of DataUpdater: initialized = false
      DataUpdater-->>Main: ok
      deactivate Main
      DataUpdater->>DataUpdater: asynchronous connect to server...
      activate DataUpdater
      Note right of DataUpdater: store any callbacks instead of triggering (e.g. onServerConnect, fromHistoryData, fromCurrentData, ...)
      DataUpdater-X+Main: done
      deactivate DataUpdater
      deactivate DataUpdater

      Main->>+DataUpdater: connectCallback = onServerConnect
      Note right of DataUpdater: connectCallback = onServerConnect
      DataUpdater-->>-Main: ok
      Main->>+onServerConnect: call
      onServerConnect->>+LoginStateViewModel: passiveLogin
      LoginStateViewModel-->>onServerConnect: ok
      onServerConnect-->>Main: ok
      deactivate onServerConnect
      deactivate Main

      LoginStateViewModel->>+LoginStateViewModel: asynchronous passive login
      Note over Main,LoginStateViewModel: Session available!
      LoginStateViewModel-X+onServerConnect: done
      deactivate LoginStateViewModel
      deactivate LoginStateViewModel

      onServerConnect->>+DataUpdater: initialized
      Note right of DataUpdater: initialized = true
      DataUpdater->DataUpdater: trigger stored callbacks
      DataUpdater-->>-onServerConnect: ok
      onServerConnect-X+Main: done
      deactivate onServerConnect

      Main->>+fetchSettings: call
      Note right of fetchSettings: trigger onStartup

      fetchSettings-->>Main: ok
      deactivate Main

      fetchSettings->>+fetchSettings: asynchronous settings fetch
      fetchSettings->>+bindViewModels: call

      loop for each view model
          bindViewModels->bindViewModels: trigger onBeforeBinding
          bindViewModels->bindViewModels: trigger onBoundTo
          bindViewModels->bindViewModels: trigger onAfterBinding
      end

      bindViewModels->bindViewModels: trigger onAllBound
      opt User is logged in
         bindViewModels->>+LoginStateViewModel: onAllBound
         LoginStateViewModel->LoginStateViewModel: trigger onUserLoggedIn
         LoginStateViewModel-->>-bindViewModels: ok
      end
      bindViewModels->bindViewModels: trigger onStartupComplete
      bindViewModels-->>-fetchSettings: ok

      deactivate fetchSettings
      deactivate fetchSettings


.. _sec-plugins-viewmodels-reconnect:

Web interface reconnect
~~~~~~~~~~~~~~~~~~~~~~~

.. mermaid::

   sequenceDiagram
      participant onServerConnect
      participant DataUpdater
      participant LoginStateViewModel

      activate DataUpdater
      DataUpdater->>DataUpdater: call connectCallback
      DataUpdater->>+onServerConnect: call
      onServerConnect-->>DataUpdater: ok
      deactivate DataUpdater

      onServerConnect->>+LoginStateViewModel: passiveLogin
      LoginStateViewModel-->>onServerConnect: ok
      deactivate onServerConnect
      LoginStateViewModel->>+LoginStateViewModel: asynchronous passive login
      Note over onServerConnect,LoginStateViewModel: Session available!
      opt User is logged in
         LoginStateViewModel->LoginStateViewModel: trigger onUserLoggedIn
      end

      activate onServerConnect
      LoginStateViewModel-XonServerConnect: done
      deactivate LoginStateViewModel
      deactivate LoginStateViewModel

      onServerConnect->>+DataUpdater: initialized
      DataUpdater->DataUpdater: trigger stored callbacks
      DataUpdater-->>onServerConnect: ok
      deactivate DataUpdater
      deactivate onServerConnect

.. seealso::

   `OctoPrint's core viewmodels <https://github.com/foosel/OctoPrint/tree/devel/src/octoprint/static/js/app/viewmodels>`_
      OctoPrint's own view models use the same mechanisms for interacting with each other and the web application as
      plugins. Their source code is therefore a good point of reference on how to achieve certain things.
   `KnockoutJS documentation <http://knockoutjs.com/documentation/introduction.html>`_
      OctoPrint makes heavy use of KnockoutJS for building up its web app.
