.. _sec-plugins-viewmodels:

Viewmodels
==========

.. contents::
   :local:

When implementing frontend components, you'll sooner or later want to define your own `KnockoutJS viewmodels <http://knockoutjs.com/>`_
in order to provide custom functionality.

.. _sec-plugins-viewmodels-registering:

Registering custom viewmodels
-----------------------------

Register your viewmodel with OctoPrint's web app by pushing a 3-tuple consisting of your viewmodel's class, a list
of all required dependencies to be injected into the constructor and a list of all elements to bind the viewmodel to.

Example:

.. code-block:: javascript

   $(function() {
       function MyCustomViewModel(parameters) {
           var self = this;

           self.loginState = parameters[0]; // requested as first constructor parameter below

           // more of your viewmodel's implementation
       }

       OCTOPRINT_VIEWMODELS.push([
           MyCustomViewModel,
           ["loginStateViewModel"],
           ["#some_div", "#some_other_div"]
       ]);
   })

.. note::

   Each provided binding target may be either a string which will then be passed to jQuery's ``$(...)`` method to resolve
   the target, or alternatively directly a jQuery element.

.. _sec-plugins-viewmodels-dependencies:

Dependencies
------------

OctoPrint will try to inject all viewmodel dependencies requested by your viewmodel. In order to do this it will
perform multiple passes iterating over all registered viewmodels and collecting the necessary dependencies prior to
construction. Circular dependencies (A depends on B, B on C, C on A) naturally cannot be resolved and will cause an
error to be logged to the JavaScript console.

OctoPrint's core currently comes with the following viewmodels that your plugin can request for injection:

appearanceViewModel
   Viewmodel that holds the appearance settings (name, color and transparency flag).
connectionViewModel
   Viewmodel for the connection sidebar entry.
controlViewModel
   Viewmodel for the control tab.
gcodeFilesViewModel
   Viewmodel for the files sidebar entry.
firstRunViewModel
   Viewmodel for the first run dialog.
gcodeViewModel
   Viewmodel for the gcode viewer tab.
logViewModel
   Viewmodel for the logfile settings dialog.
loginStateViewModel
   Viewmodel for the current loginstate of the user, very interesting for plugins that need to
   evaluate the current login state or information about the current user, e.g. associated roles.
navigationViewModel
   Viewmodel for the navigation bar.
printerProfilesViewModel
   Viewmodel for the printer profiles settings dialog.
printerStateViewModel
   Viewmodel for the current printer state, very interesting for plugins that need
   to know information about the current print job, if the printer is connected, operational etc.
settingsViewModel
   Viewmodel for the settings dialog, also holds all settings to be used by other viewmodels, hence
   very interesting for plugins as well.
slicingViewModel
   Viewmodel for the slicing dialog.
temperatureViewModel
   Viewmodel for the temperature tab, also holds current temperature information which
   might be interesting for plugins.
terminalViewModel
   Viewmodel for the terminal tab, also holds terminal log entries.
timelapseViewModel
   Viewmodel for the timelapse tab.
usersViewModel
   Viewmodel for the user management in the settings dialog.
userSettingsViewModel
   Viewmodel for settings associated with the currently logged in user, used for
   the user settings dialog.

Additionally each plugin's viewmodel will be added to the viewmodel map used for resolving dependencies as well, using
the viewmodel's class name with a lower case first character as identifier (so "MyCustomViewModel" will be registered
for dependency injection as "myCustomViewModel").

.. _sec-plugins-viewmodels-callbacks:

Callbacks
---------

OctoPrint's web application will call several callbacks on all registered viewmodels, provided they implement them.
Those are listed below:

onStartup()
   Called when the first initialization has been done: All viewmodels are constructed and hence their dependencies
   resolved, no bindings have been done yet.

onBeforeBinding()
   Called per viewmodel before attempting to bind it to its binding targets.

onAfterBinding()
   Called per viewmodel after binding it to its binding targets.

onAllBound(allViewModels)
   Called after all viewmodels have been bound, with the list of all viewmodels as the single parameter.

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

onTabChange(current, previous)
   Called before the main tab view switches to a new tab, so `before` the new tab becomes visible. Called with the
   current and previous tab's hash (e.g. ``#control``).

onAfterTabChange
   Called after the main tab view switches to a new tab, so `after` the new tab becomes visible. Called with the
   current and previous tab's hash (e.g. ``#control``).

getAdditionalControls
   Your viewmodel may return additional custom control definitions for inclusion on the "Control" tab of OctoPrint's
   interface. See :ref:`the custom control feature<sec-features-custom_controls>`.

onSettingsShown
   Called when the settings dialog is shown.

onSettingsHidden
   Called when the settings dialog is hidden.

onSettingsBeforeSave
   Called just before the settings viewmodel is sent to the server. This is useful, for example, if your plugin
   needs to compute persisted settings from a custom viewmodel.

onUserSettingsShown
   Called when the user settings dialog is shown.

onUserSettingsHidden
   Called when the user settings dialog is hidden.

onWizardDetails
   Called with the response from the wizard detail API call initiated before opening the wizard dialog. Will contain
   the data from all :class:`~octoprint.plugin.WizardPlugin` implementations returned by their :meth:`~octoprint.plugin.WizardPlugin.get_wizard_details`
   method, mapped by the plugin identifier.

onWizardTabChange
   Called before the wizard tab/step is changed, with the ids of the current and the next tab as parameters. Return false
   in order to prevent the tab change, e.g. if the wizard step is mandatory and not yet completed by the user. Take a look at
   the "Core Wizard" plugin bundled with OctoPrint and the ACL wizard step in particular for an example on how to use this.

onAfterWizardTabChange
   Called after the wizard tab/step is changed, with the id of the current tab as parameter.

onBeforeWizardFinish
   Called before executing the finishing of the wizard. Return false here to stop the actual finish, e.g. if some step is
   still incomplete.

onWizardFinish
   Called after executing the finishing of the wizard and before closing the dialog. Return ``reload`` here in order to
   instruct OctoPrint to reload the UI after the wizard closes.

In order to hook into any of those callbacks, just have your viewmodel define a function named accordingly, e.g.
to get called after all viewmodels have been bound during application startup, implement a function ``onAllBound``
on your viewmodel, taking a list of all bound viewmodels:

.. code-block:: javascript

   $(function() {
       function MyCustomViewModel(parameters) {
           var self = this;

           // ...

           self.onAllBound = function(allViewModels) {
               // do something with them
           }

           // ...
       }

       OCTOPRINT_VIEWMODELS.push([
           MyCustomViewModel,
           ["loginStateViewModel"],
           ["#some_div", "#some_other_div"]
       ]);
   })

.. seealso::

   `OctoPrint's core viewmodels <https://github.com/foosel/OctoPrint/tree/devel/src/octoprint/static/js/app/viewmodels>`_
      OctoPrint's own viewmodels use the same mechanisms for interacting with each other and the web application as
      plugins. Their source code is therefore a good point of reference on how to achieve certain things.
   `KnockoutJS documentation <http://knockoutjs.com/documentation/introduction.html>`_
      OctoPrint makes heavy use of KnockoutJS for building up its web app.
