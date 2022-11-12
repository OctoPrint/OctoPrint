.. _sec-plugins-hooks:

Hooks
=====

.. contents::
   :local:

.. _sec-plugins-hooks-general:

General Concepts
----------------

Hooks are the smaller siblings of :ref:`mixins <sec-plugins-mixins>`, allowing to extend functionality or data processing where a custom mixin type
would be too much overhead. Where mixins are based on classes, hooks are based on methods. Like with the mixin
implementations, plugins inform OctoPrint about hook handlers using a control property, ``__plugin_hooks__``.

This control property is a dictionary consisting of the implemented hooks' names as keys and either the hook callback
or a 2-tuple of hook callback and order value as value.

Each hook defines a contract detailing the call parameters for the hook handler method and the expected return type.
OctoPrint will call the hook with the define parameters and process the result depending on the hook.

An example for a hook within OctoPrint is ``octoprint.comm.protocol.scripts``, which allows adding additional
lines to OctoPrint's :ref:`GCODE scripts <sec-features-gcode_scripts>`, either as ``prefix`` (before the existing lines)
or as ``postfix`` (after the existing lines).

.. code-block:: python

   self._gcode_hooks = self._pluginManager.get_hooks("octoprint.comm.protocol.scripts")

   # ...

   for hook in self._gcodescript_hooks:
       try:
           retval = self._gcodescript_hooks[hook](self, "gcode", scriptName)
       except Exception:
           self._logger.exception("Error while processing gcodescript hook %s" % hook)
       else:
           if retval is None:
               continue
           if not isinstance(retval, (list, tuple)) or not len(retval) == 2:
               continue

           def to_list(data):
               if isinstance(data, str):
                   data = map(x.strip() for x in data.split("\n"))

               if isinstance(data, (list, tuple)):
                   return list(data)
               else:
                   return None

           prefix, suffix = map(to_list, retval)
           if prefix:
               scriptLines = list(prefix) + scriptLines
           if suffix:
               scriptLines += list(suffix)

As you can see, the hook's method signature is defined to take the current ``self`` (as in, the current comm layer instance),
the general type of script for which to look for additions ("gcode") and the script name for which to look (e.g.
``beforePrintStarted`` for the GCODE script executed before the beginning of a print job). The hook is expected to
return a 2-tuple of prefix and postfix if has something for either of those, otherwise ``None``. OctoPrint will then take
care to add prefix and suffix as necessary after a small round of preprocessing.

Plugins can easily add their own hooks too. For example, the `Software Update Plugin <https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html>`_
declares a custom hook "octoprint.plugin.softwareupdate.check_config" which other plugins can add handlers for in order
to register themselves with the Software Update Plugin by returning their own update check configuration.

If you want your hook handler to be an instance method of a mixin implementation of your plugin (for example since you
need access to instance variables handed to your implementation via mixin invocations), you can get this work
by using a small trick. Instead of defining it directly via ``__plugin_hooks__`` utilize the ``__plugin_load__``
property instead, manually instantiate your implementation instance and then add its hook handler method to the
``__plugin_hooks__`` property and itself to the ``__plugin_implementation__`` property. See the following example.

.. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/custom_action_command.py
   :tab-width: 4
   :caption: `custom_action_command.py <https://github.com/OctoPrint/Plugin-Examples/blob/master/custom_action_command.py>`__
   :name: sec-plugin-concepts-hooks-example

.. _sec-plugins-hooks-ordering:

Execution Order
---------------

Hooks may also define an order number to allow influencing the execution order of the registered hook handlers. Instead
of registering only a callback as hook handler, it is also possible to register a 2-tuple consisting of a callback and
an integer value used for ordering handlers. They way this works is that OctoPrint will first sort all registered
hook handlers with a order number, taking their identifier as the second sorting criteria, then after that append
all hook handlers without a order number sorted only by their identifier.

An example should help clear this up. Let's assume we have the following plugin ``ordertest`` which defines a new
hook called ``octoprint.plugin.ordertest.callback``:

.. code-block:: python
   :caption: ordertest.py

   import octoprint.plugin

   class OrderTestPlugin(octoprint.plugin.StartupPlugin):
       def get_sorting_key(self, sorting_context):
           return 10

       def on_startup(self, *args, **kwargs):
           self._logger.info("############### Order Test Plugin: StartupPlugin.on_startup called")
           hooks = self._plugin_manager.get_hooks("octoprint.plugin.ordertest.callback")
           for name, hook in hooks.items():
               hook()

       def on_after_startup(self):
           self._logger.info("############### Order Test Plugin: StartupPlugin.on_after_startup called")

   __plugin_name__ = "Order Test"
   __plugin_version__ = "0.1.0"
   __plugin_implementation__ = OrderTestPlugin()

And these three plugins defining handlers for that hook:

.. code-block:: python
   :caption: oneorderedhook.py

   import logging

    def callback(*args, **kwargs):
        logging.getLogger("octoprint.plugins." + __name__).info("Callback called in oneorderedhook")

    __plugin_name__ = "One Ordered Hook"
    __plugin_version__ = "0.1.0"
    __plugin_hooks__ = {
        "octoprint.plugin.ordertest.callback": (callback, 1)
    }

.. code-block:: python
   :caption: anotherorderedhook.py

   import logging

   def callback(*args, **kwargs):
       logging.getLogger("octoprint.plugins." + __name__).info("Callback called in anotherorderedhook")

   __plugin_name__ = "Another Ordered Hook"
   __plugin_version__ = "0.1.0"
   __plugin_hooks__ = {
       "octoprint.plugin.ordertest.callback": (callback, 2)
   }

.. code-block:: python
   :caption: yetanotherhook.py

   import logging

   def callback(*args, **kwargs):
       logging.getLogger("octoprint.plugins." + __name__).info("Callback called in yetanotherhook")

   __plugin_name__ = "Yet Another Hook"
   __plugin_version__ = "0.1.0"
   __plugin_hooks__ = {
       "octoprint.plugin.ordertest.callback": callback
   }

Both ``orderedhook.py`` and ``anotherorderedhook.py`` not only define a handler callback in the hook registration,
but actually a 2-tuple consisting of a callback and an order number. ``yetanotherhook.py`` only defines a callback.

OctoPrint will sort these hooks so that ``orderedhook`` will be called first, then ``anotherorderedhook``, then
``yetanotherhook``. Just going by the identifiers, the expected order would be ``anotherorderedhook``, ``orderedhook``,
``yetanotherhook``, but since ``orderedhook`` defines a lower order number (``1``) than ``anotherorderedhook`` (``2``),
it will be sorted before ``anotherorderedhook``. If you copy those files into your ``~/.octoprint/plugins`` folder
and start up OctoPrint, you'll see output like this:

.. code-block:: none

   [...]
   2016-03-24 09:29:21,342 - octoprint.plugins.ordertest - INFO - ############### Order Test Plugin: StartupPlugin.on_startup called
   2016-03-24 09:29:21,355 - octoprint.plugins.oneorderedhook - INFO - Callback called in oneorderedhook
   2016-03-24 09:29:21,357 - octoprint.plugins.anotherorderedhook - INFO - Callback called in anotherorderedhook
   2016-03-24 09:29:21,358 - octoprint.plugins.yetanotherhook - INFO - Callback called in yetanotherhook
   [...]
   2016-03-24 09:29:21,861 - octoprint.plugins.ordertest - INFO - ############### Order Test Plugin: StartupPlugin.on_after_startup called
   [...]

.. _sec-plugins-hooks-available:

Available plugin hooks
----------------------

.. note::

   All of the hooks below take at least two parameters, ``*args`` and ``**kwargs``. Make sure those are
   **always** present in your hook handler declaration.
   They will act as placeholders if additional parameters are added to the hooks in the future and will allow
   your plugin to stay compatible to OctoPrint without any necessary adjustments from you in these cases.

.. contents::
   :local:

.. _sec-plugins-hook-permissions:

octoprint.access.permissions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: additional_permissions_hook(*args, **kwargs)

   .. versionadded:: 1.4.0

   Return a list of additional permissions to register in the system on behalf of the plugin. Use this
   to add granular permissions to your plugin which can be configured for users and user groups in the general
   access control settings of OctoPrint.

   Additional permissions must be modelled as ``dict``s with at least a ``key`` and ``name`` field. Possible
   fields are as follows:

     * ``key``: A key for the permission to be used for referring to it from source code. This will turned uppercase
       and prefixed with ``PLUGIN_<PLUGIN IDENTIFIER>_`` before being made available on ``octoprint.access.permissions.Permissions``,
       e.g. ``my_permission`` on the plugin with identifier ``example`` turns into ``PLUGIN_EXAMPLE_MY_PERMISSION`` and
       can be accessed as ``octoprint.access.permissions.Permissions.PLUGIN_EXAMPLE_MY_PERMISSION`` on the server and
       ``permissions.PLUGIN_EXAMPLE_MY_PERMISSION`` on the ``AccessViewModel`` on the client. Must only contain a-z, A-Z, 0-9 and _.
     * ``name``: A human readable name for the permission.
     * ``description``: A human readable description of the permission.
     * ``permissions``: A list of permissions this permission includes, by key.
     * ``roles``: A list of roles this permission includes. Roles are simple strings you define. Usually one role will
       suffice.
     * ``dangerous``: Whether this permission should be considered dangerous (``True``) or not (``False``)
     * ``default_groups``: A list of standard groups this permission should be apply to by default. Standard groups
       are ``octoprint.access.ADMIN_GROUP``, ``octoprint.access.USER_GROUP``, ``octoprint.access.READONLY_GROUP`` and ``octoprint.access.GUEST_GROUP``

   The following example is based on some actual code included in the bundled Application Keys plugin and defines
   one additional permission called ``ADMIN`` with a role ``admin`` which is marked as dangerous (since it gives
   access to the management to other user's application keys) and by default will only be given to the standard admin
   group:

   .. code-block:: python

      from octoprint.access import ADMIN_GROUP

      def get_additional_permissions(*args, **kwargs):
          return [
              dict(key="ADMIN",
                   name="Admin access",
                   description=gettext("Allows administrating all application keys"),
                   roles=["admin"],
                   dangerous=True,
                   default_groups=[ADMIN_GROUP])
          ]

      __plugin_hooks__ = {
          "octoprint.access.permissions": get_additional_permissions
      }

   Once registered it can be referenced under the key ``PLUGIN_APPKEYS_ADMIN``.

   :return: A list of additional permissions to register in the system.
   :rtype: A list of dicts.

.. _sec-plugins-hook-users-factory:

octoprint.access.users.factory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: user_manager_factory_hook(components, settings, *args, **kwargs)

   .. versionadded:: 1.4.0

   Return a :class:`~octoprint.access.users.UserManager` instance to use as global user manager object. This will
   be called only once during initial server startup.

   The provided ``components`` is a dictionary containing the already initialized system components:

     * ``plugin_manager``: The :class:`~octoprint.plugin.core.PluginManager`
     * ``printer_profile_manager``: The :class:`~octoprint.printer.profile.PrinterProfileManager`
     * ``event_bus``: The :class:`~octoprint.events.EventManager`
     * ``analysis_queue``: The :class:`~octoprint.filemanager.analysis.AnalysisQueue`
     * ``slicing_manager``: The :class:`~octoprint.slicing.SlicingManager`
     * ``file_manager``: The :class:`~octoprint.filemanager.FileManager`
     * ``plugin_lifecycle_manager``: The :class:`~octoprint.server.LifecycleManager`
     * ``preemptive_cache``: The :class:`~octoprint.server.util.flask.PreemptiveCache`

   If the factory returns anything but ``None``, it will be assigned to the global ``userManager`` instance.

   If none of the registered factories return a user manager instance, the class referenced by the ``config.yaml``
   entry ``accessControl.userManager`` will be initialized if possible, otherwise a stock
   :class:`~octoprint.access.users.FilebasedUserManager` will be instantiated, linked to the default user storage
   file ``~/.octoprint/users.yaml``.

   :param dict components: System components to use for user manager instance initialization
   :param SettingsManager settings: The global settings manager instance to fetch configuration values from if necessary
   :return: The ``userManager`` instance to use globally.
   :rtype: UserManager subclass or None


.. _sec-plugins-hook-accesscontrol-keyvalidator:

octoprint.accesscontrol.keyvalidator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: acl_keyvalidator_hook(apikey, *args, **kwargs)

   .. versionadded:: 1.3.6

   Via this hook plugins may validate their own customized API keys to be used to access OctoPrint's API.

   ``apikey`` will be the API key as read from the request headers.

   Hook handlers are expected to return a :class:`~octoprint.access.users.User` instance here that will then be considered that
   user making the request. By returning ``None`` or nothing at all, hook handlers signal that they do not handle the
   provided key.

   **Example:**

   Allows using a user's id as their API key (for obvious reasons this is NOT recommended in production environments
   and merely provided for educational purposes):

   .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/custom_keyvalidator.py
      :tab-width: 4
      :caption: `custom_keyvalidator.py <https://github.com/OctoPrint/Plugin-Examples/blob/master/custom_keyvalidator.py>`_

   .. versionadded:: 1.3.6

   :param str apikey: The API key to validate
   :return: The user in whose name the request will be processed further
   :rtype: :class:`~octoprint.access.users.User`

.. _sec-plugins-hook-cli-commands:

octoprint.cli.commands
~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: cli_commands_hook(cli_group, pass_octoprint_ctx, *args, **kwargs)

   .. versionadded:: 1.3.0

   By providing a handler for this hook plugins may register commands on OctoPrint's command line interface (CLI).

   Handlers are expected to return a list of callables annotated as `Click commands <http://click.pocoo.org/5/>`_ to register with the
   CLI.

   The custom ``MultiCommand`` instance :class:`~octoprint.cli.plugins.OctoPrintPluginCommands` is provided
   as parameter. Via that object handlers may access the *global* :class:`~octoprint.settings.Settings`
   and the :class:`~octoprint.plugin.core.PluginManager` instance as ``cli_group.settings`` and ``cli_group.plugin_manager``.

   **Example:**

   Registers two new commands, ``custom_cli_command:greet`` and ``custom_cli_command:random`` with
   OctoPrint:

   .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/custom_cli_command.py
      :tab-width: 4
      :caption: `custom_cli_command.py <https://github.com/OctoPrint/Plugin-Examples/blob/master/custom_cli_command.py>`_

   Calling ``octoprint plugins --help`` shows the two new commands:

   .. code-block:: none

      $ octoprint plugins --help
      Usage: octoprint plugins [OPTIONS] COMMAND [ARGS]...

        Additional commands provided by plugins.

      Options:
        --help  Show this message and exit.

      Commands:
        custom_cli_command:greet   Greet someone by name, the greeting can be...
        custom_cli_command:random  Greet someone by name with a random greeting.
        softwareupdate:check       Check for updates.
        softwareupdate:update      Apply updates.

   Each also has an individual help output:

   .. code-block:: none

      $ octoprint plugins custom_cli_command:greet --help
      Usage: octoprint plugins custom_cli_command:greet [OPTIONS] [NAME]

        Greet someone by name, the greeting can be customized.

      Options:
        -g, --greeting TEXT  The greeting to use
        --help               Show this message and exit.

      $ octoprint plugins custom_cli_command:random --help
      Usage: octoprint plugins custom_cli_command:random [OPTIONS] [NAME]

        Greet someone by name with a random greeting.

      Options:
        --help  Show this message and exit.

   And of course they work too:

   .. code-block:: none

      $ octoprint plugins custom_cli_command:greet
      Hello World!

      $ octoprint plugins custom_cli_command:greet --greeting "Good morning"
      Good morning World!

      $ octoprint plugins custom_cli_command:random stranger
      Hola stranger!

   .. note::

      If your hook handler is an instance method of a plugin mixin implementation, be aware that the hook will be
      called without OctoPrint initializing your implementation instance. That means that **none** of the
      :ref:`injected properties <sec-plugins-mixins-injectedproperties>` will be available and also the
      :meth:`~octoprint.plugin.Plugin.initialize` method will not be called.

      Your hook handler will have access to the plugin manager as ``cli_group.plugin_manager`` and to the
      *global* settings as ``cli_group.settings``. You can have your handler turn the latter into a
      :class:`~octoprint.plugin.PluginSettings` instance by using :func:`octoprint.plugin.plugin_settings_from_settings_plugin`
      if your plugin's implementation implements the :class:`~octoprint.plugin.SettingsPlugin` mixin and inject
      that and the plugin manager instance yourself:

      .. code-block:: python

         import octoprint.plugin

         class MyPlugin(octoprint.plugin.SettingsPlugin):

             def get_cli_commands(self, cli_group, pass_octoprint_ctx, *args, **kwargs):
                 import logging

                 settings = cli_group._settings
                 plugin_settings = octoprint.plugin.plugin_settings_for_settings_plugin("myplugin", self)
                 if plugin_settings is None:
                     # this can happen if anything goes wrong with preparing the PluginSettings instance
                     return dict()

                 self._settings = plugin_settings
                 self._plugin_manager = cli_group._plugin_manager
                 self._logger = logging.getLogger(__name__)

                 ### command definition starts here

                 # ...


      No other platform components will be available - the CLI runs outside of a running, fully initialized
      OctoPrint server context, so there is absolutely no way to access a printer connection, the event bus or
      anything else like that. The only things available are the settings and the plugin manager.

   :return: A list of `Click commands or groups <http://click.pocoo.org/5/commands/>`_ to provide on
            OctoPrint's CLI.
   :rtype: list

.. _sec-plugins-hook-comm-protocol-firmware-info:

octoprint.comm.protocol.firmware.info
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: firmware_info_hook(comm_instance, firmware_name, firmware_data, *args, **kwargs)

   .. versionadded:: 1.3.9

   Be notified of firmware information received from the printer following an ``M115``.

   Hook handlers may use this to react/adjust behaviour based on reported firmware data. OctoPrint parses the received
   report line and provides the parsed ``firmware_name`` and additional ``firmware_data`` contained therein. A
   response line ``FIRMWARE_NAME:Some Firmware Name FIRMWARE_VERSION:1.2.3 PROTOCOL_VERSION:1.0`` for example will
   be turned into a ``dict`` looking like this:

   .. code-block:: python

      dict(FIRMWARE_NAME="Some Firmware Name",
           FIRMWARE_VERSION="1.2.3",
           PROTOCOL_VERSION="1.0")

   ``firmware_name`` will be ``Some Firmware Name`` in this case.

   .. warning::

      Make sure to not perform any computationally expensive or otherwise long running actions within these handlers as
      you will effectively block the receive loop, causing the communication with the printer to stall.

      This includes I/O of any kind.

   :param object comm_instance: The :class:`~octoprint.util.comm.MachineCom` instance which triggered the hook.
   :param str firmware_name: The parsed name of the firmware
   :param dict firmware_data: All data contained in the ``M115`` report

.. _sec-plugins-hook-comm-protocol-firmware-capabilities:

octoprint.comm.protocol.firmware.capabilities
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: firmware_capability_hook(comm_instance, capability, enabled, already_defined, *args, **kwargs)

   .. versionadded:: 1.3.9

   Be notified of capability report entries received from the printer.

   Hook handlers may use this to react to custom firmware capabilities. OctoPrint parses the received capability
   line and provides the parsed ``capability`` and whether it's ``enabled`` to the handler. Additionally all already
   parsed capabilities will also be provided.

   Note that hook handlers will be called once per received capability line.

   .. warning::

      Make sure to not perform any computationally expensive or otherwise long running actions within these handlers as
      you will effectively block the receive loop, causing the communication with the printer to stall.

      This includes I/O of any kind.

   :param object comm_instance: The :class:`~octoprint.util.comm.MachineCom` instance which triggered the hook.
   :param str capability: The name of the parsed capability
   :param bool enabled: Whether the capability is reported as enabled or disabled
   :param dict already_defined: Already defined capabilities (capability name mapped to enabled flag)

.. _sec-plugins-hook-comm-protocol-action:

octoprint.comm.protocol.firmware.capability_report
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: firmware_capability_report_hook(comm_instance, firmware_capabilities, *args, **kwargs)

   .. versionadded:: 1.9.0

   Be notified when all capability report entries are received from the printer.

   Hook handlers may use this to react to the end of the custom firmware capability report. OctoPrint parses the received
   capability lines and provides a dictionary of all reported capabilities and whether they're enabled to the handler.

   .. warning::

      Make sure to not perform any computationally expensive or otherwise long running actions within these handlers as
      you will effectively block the receive loop, causing the communication with the printer to stall.

      This includes I/O of any kind.

   :param object comm_instance: The :class:`~octoprint.util.comm.MachineCom` instance which triggered the hook.
   :param dict firmware_capabilities: Reported capabilities (capability name mapped to enabled flag)

.. _sec-plugins-hook-comm-protocol-action:

octoprint.comm.protocol.action
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: protocol_action_hook(comm_instance, line, action, name='', params='', *args, **kwargs)

   .. versionadded:: 1.2.0

   React to a :ref:`action command <sec-features-action_commands>` received from the printer.

   Hook handlers may use this to react to custom firmware messages. OctoPrint parses the received action
   command ``line`` and provides the parsed ``action`` (so anything after ``// action:``) to the hook handler.

   No returned value is expected.

   .. warning::

      Make sure to not perform any computationally expensive or otherwise long running actions within your handlers as
      you will effectively block the receive loop, causing the communication with the printer to stall.

      This includes I/O of any kind.

   **Example:**

   Logs if the ``custom`` action (``// action:custom``) is received from the printer's firmware.

   .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/custom_action_command.py
      :tab-width: 4
      :caption: `custom_action_command.py <https://github.com/OctoPrint/Plugin-Examples/blob/master/custom_action_command.py>`__

   :param object comm_instance: The :class:`~octoprint.util.comm.MachineCom` instance which triggered the hook.
   :param str line: The complete line as received from the printer, format ``// action:<command>``
   :param str action: The parsed out action command incl. parameters, so for a ``line`` like ``// action:some_command key value`` this will be
       ``some_command key value``
   :param str name: The action command name, for a ``line`` like ``// action:some_command key value`` this will be
       ``some_command``
   :param str params: The action command's parameter, for a ``line`` like ``// action:some_command key value`` this will
       be ``key value``

.. _sec-plugins-hook-comm-protocol-atcommand-phase:

octoprint.comm.protocol.atcommand.<phase>
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This describes actually two hooks:

  * ``octoprint.comm.protocol.atcommand.queuing``
  * ``octoprint.comm.protocol.atcommand.sending``

.. py:function:: protocol_atcommandphase_hook(comm_instance, phase, command, parameters, tags=None, *args, **kwargs)

   .. versionadded:: 1.3.7

   Trigger on :ref:`@ commands <sec-features-atcommands>` as they progress through the ``queuing`` and ``sending``
   phases of the comm layer. See :ref:`the gcode phase hook <sec-plugins-hook-comm-protocol-gcode-phase>` for a
   detailed description of each of these phases.

   Hook handlers may use this to react to arbitrary :ref:`@ commands <sec-features-atcommands>` included in GCODE files
   streamed to the printer or sent as part of GCODE scripts, through the API or plugins.

   Please note that these hooks do not allow to rewrite, suppress or expand @ commands, they are merely callbacks to
   trigger the *actual execution* of whatever functionality lies behind a given @ command, similar to
   :ref:`the action command hook <sec-plugins-hook-comm-protocol-action>`.

   .. warning::

      Make sure to not perform any computationally expensive or otherwise long running actions within your handlers as
      you will effectively block the send/receive loops, causing the communication with the printer to stall.

      This includes I/O of any kind.

   **Example**

   Pause the print on ``@wait`` (this mirrors the implementation of the built-in ``@pause`` command, just with a
   different name).

   .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/custom_atcommand.py
      :tab-width: 4
      :caption: `custom_action_command.py <https://github.com/OctoPrint/Plugin-Examples/blob/master/custom_atcommand.py>`__

   :param object comm_instance: The :class:`~octoprint.util.comm.MachineCom` instance which triggered the hook.
   :param str phase: The current phase in the command progression, either ``queuing`` or ``sending``. Will always
       match the ``<phase>`` of the hook.
   :param str cmd: The @ command without the leading @
   :param str parameters: Any parameters provided to the @ command. If none were provided this will be an empty string.

.. _sec-plugins-hook-comm-protocol-gcode-phase:

octoprint.comm.protocol.gcode.<phase>
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This actually describes four hooks:

  * ``octoprint.comm.protocol.gcode.queuing``
  * ``octoprint.comm.protocol.gcode.queued``
  * ``octoprint.comm.protocol.gcode.sending``
  * ``octoprint.comm.protocol.gcode.sent``

.. py:function:: protocol_gcodephase_hook(comm_instance, phase, cmd, cmd_type, gcode, subcode=None, tags=None, *args, **kwargs)

   .. versionadded:: 1.2.0

   Pre- and postprocess commands as they progress through the various phases of being sent to the printer. The phases
   are the following:

     * ``queuing``: This phase is triggered just before the command is added to the send queue of the communication layer. This
       corresponds to the moment a command is being read from a file that is currently being printed. Handlers
       may suppress or change commands or their command type here. This is the only phase that supports multi command
       expansion by having the handler return a list, see below for details.
     * ``queued``: This phase is triggered just after the command was added to the send queue of the communication layer.
       No manipulation is possible here anymore (returned values will be ignored).
     * ``sending``: This phase is triggered just before the command is actually being sent to the printer. Right afterwards
       a line number will be assigned and the command will be sent. Handlers may suppress or change commands here. The
       command type is not taken into account anymore.
     * ``sent``: This phase is triggered just after the command was handed over to the serial connection to the printer.
       No manipulation is possible here anymore (returned values will be ignored). A command that reaches the sent phase
       must not necessarily have reached the printer yet and it might also still run into communication problems and a
       resend might be triggered for it.

   Hook handlers may use this to rewrite or completely suppress certain commands before they enter the send queue of
   the communication layer or before they are actually sent over the serial port, or to react to the queuing or sending
   of commands after the fact. The hook handler will be called with the processing ``phase``, the ``cmd`` to be sent to
   the printer as well as the ``cmd_type`` parameter used for enqueuing (OctoPrint will make sure that the send queue
   will never contain more than one line with the same ``cmd_type``) and the detected ``gcode`` command (if it is one)
   as well as its ``subcode`` (if it has one). OctoPrint will also provide any ``tags`` attached to the command throughout
   its lifecycle.

   Tags are arbitrary strings that can be attached to a command as it moves through the various phases and can be used to e.g.
   distinguish between commands that originated in a printed file (``source:file``) vs. a configured GCODE script
   (``source:script``) vs. an API call (``source:api``) vs. a plugin (``source:plugin`` or ``source:rewrite`` and
   ``plugin:<plugin identifier>``). If during development you want to get an idea of the various possible tags, set
   the logger ``octoprint.util.comm.command_phases``  to ``DEBUG``, connect to a printer (real or virtual) and take a
   look at your ``octoprint.log`` during serial traffic:

   .. code-block:: none

      2018-02-16 18:20:31,213 - octoprint.util.comm.command_phases - DEBUG - phase: queuing | command: T0 | gcode: T | tags: [ api:printer.command, source:api, trigger:printer.commands ]
      2018-02-16 18:20:31,216 - octoprint.util.comm.command_phases - DEBUG - phase: queued | command: M117 Before T! | gcode: M117 | tags: [ api:printer.command, phase:queuing, plugin:multi_gcode_test, source:api, source:rewrite, trigger:printer.commands ]
      2018-02-16 18:20:31,217 - octoprint.util.comm.command_phases - DEBUG - phase: sending | command: M117 Before T! | gcode: M117 | tags: [ api:printer.command, phase:queuing, plugin:multi_gcode_test, source:api, source:rewrite, trigger:printer.commands ]
      2018-02-16 18:20:31,217 - octoprint.util.comm.command_phases - DEBUG - phase: queued | command: T0 | gcode: T | tags: [ api:printer.command, source:api, trigger:printer.commands ]
      2018-02-16 18:20:31,219 - octoprint.util.comm.command_phases - DEBUG - phase: queued | command: M117 After T! | gcode: M117 | tags: [ api:printer.command, phase:queuing, plugin:multi_gcode_test, source:api, source:rewrite, trigger:printer.commands ]
      2018-02-16 18:20:31,220 - octoprint.util.comm.command_phases - DEBUG - phase: sent | command: M117 Before T! | gcode: M117 | tags: [ api:printer.command, phase:queuing, plugin:multi_gcode_test, source:api, source:rewrite, trigger:printer.commands ]
      2018-02-16 18:20:31,230 - tornado.access - INFO - 204 POST /api/printer/command (127.0.0.1) 23.00ms
      2018-02-16 18:20:31,232 - tornado.access - INFO - 200 POST /api/printer/command (127.0.0.1) 25.00ms
      2018-02-16 18:20:31,232 - octoprint.util.comm.command_phases - DEBUG - phase: sending | command: T0 | gcode: T | tags: [ api:printer.command, source:api, trigger:printer.commands ]
      2018-02-16 18:20:31,234 - octoprint.util.comm.command_phases - DEBUG - phase: sent | command: T0 | gcode: T | tags: [ api:printer.command, source:api, trigger:printer.commands ]
      2018-02-16 18:20:31,242 - octoprint.util.comm.command_phases - DEBUG - phase: sending | command: M117 After T! | gcode: M117 | tags: [ api:printer.command, phase:queuing, plugin:multi_gcode_test, source:api, source:rewrite, trigger:printer.commands ]
      2018-02-16 18:20:31,243 - octoprint.util.comm.command_phases - DEBUG - phase: sent | command: M117 After T! | gcode: M117 | tags: [ api:printer.command, phase:queuing, plugin:multi_gcode_test, source:api, source:rewrite, trigger:printer.commands ]
      2018-02-16 18:20:38,552 - octoprint.util.comm.command_phases - DEBUG - phase: queuing | command: G91 | gcode: G91 | tags: [ api:printer.printhead, source:api, trigger:printer.commands, trigger:printer.jog ]
      2018-02-16 18:20:38,552 - octoprint.util.comm.command_phases - DEBUG - phase: queued | command: G91 | gcode: G91 | tags: [ api:printer.printhead, source:api, trigger:printer.commands, trigger:printer.jog ]
      2018-02-16 18:20:38,553 - octoprint.util.comm.command_phases - DEBUG - phase: sending | command: G91 | gcode: G91 | tags: [ api:printer.printhead, source:api, trigger:printer.commands, trigger:printer.jog ]
      2018-02-16 18:20:38,553 - octoprint.util.comm.command_phases - DEBUG - phase: queuing | command: G1 X10 F6000 | gcode: G1 | tags: [ api:printer.printhead, source:api, trigger:printer.commands, trigger:printer.jog ]
      2018-02-16 18:20:38,555 - octoprint.util.comm.command_phases - DEBUG - phase: queued | command: G1 X10 F6000 | gcode: G1 | tags: [ api:printer.printhead, source:api, trigger:printer.commands, trigger:printer.jog ]
      2018-02-16 18:20:38,556 - octoprint.util.comm.command_phases - DEBUG - phase: sent | command: G91 | gcode: G91 | tags: [ api:printer.printhead, source:api, trigger:printer.commands, trigger:printer.jog ]
      2018-02-16 18:20:38,556 - octoprint.util.comm.command_phases - DEBUG - phase: queuing | command: G90 | gcode: G90 | tags: [ api:printer.printhead, source:api, trigger:printer.commands, trigger:printer.jog ]
      2018-02-16 18:20:38,558 - octoprint.util.comm.command_phases - DEBUG - phase: queued | command: G90 | gcode: G90 | tags: [ api:printer.printhead, source:api, trigger:printer.commands, trigger:printer.jog ]

   Defining a ``cmd_type`` other than None will make sure OctoPrint takes care of only having one command of that type
   in its sending queue. Predefined types are ``temperature_poll`` for temperature polling via ``M105`` and
   ``sd_status_poll`` for polling the SD printing status via ``M27``.

   ``phase`` will always match the ``<phase>`` part of the implemented hook (e.g. ``octoprint.comm.protocol.gcode.queued``
   handlers will always be called with ``phase`` set to ``queued``). This parameter is provided so that plugins may
   utilize the same hook for multiple phases if required.

   Handlers are expected to return one of the following result variants:

     * ``None``: Don't change anything. Note that Python functions will also automatically return ``None`` if
       an empty ``return`` statement is used or just nothing is returned explicitly from the handler. Hence, the following
       examples are all falling into this category and equivalent:

       .. code-block:: python

          def one(*args, **kwargs):
              print("I return None explicitly")
              return None

          def two(*args, **kwargs):
              print("I just return without any values")
              return

          def three(*args, **kwargs):
              print("I don't explicitly return anything at all")

       Handlers which do not wish to modify (or suppress) ``cmd`` or ``cmd_type`` at all should use this option.
     * A string with the rewritten version of the ``cmd``, e.g. ``return "M110"``. To avoid situations which will be
       difficult to debug should the returned command be later changed to ``None`` (with the intent to suppress the
       command instead but actually causing ``cmd`` and ``cmd_type`` to just staying as-is), this variant should be
       entirely avoided by handlers.
     * A 1-tuple consisting of a rewritten version of the ``cmd``, e.g. ``return "M110",``, or ``None`` in order to
       suppress the command, e.g. ``return None,``. Handlers which wish to rewrite the command or to suppress it completely
       should use this option.
     * A 2-tuple consisting of a rewritten version of the ``cmd`` and the ``cmd_type``, e.g. ``return "M105", "temperature_poll"``.
       Handlers which wish to rewrite both the command and the command type should use this option.
     * A 3-tuple consisting of a rewritten version of the ``cmd``, the ``cmd_type`` and any additional ``tags`` you might
       want to attach to the lifecycle of the command in a set, e.g. ``return "M105", "temperature_poll", {"my_custom_tag"}``
     * **"queuing" phase only**: A list of any of the above to allow for expanding one command into
       many. The following example shows how any queued command could be turned into a sequence of a temperature query,
       line number reset, display of the ``gcode`` on the printer's display and finally the actual command (this example
       does not make a lot of sense to be quite honest):

       .. code-block:: python

          def rewrite_foo(self, comm_instance, phase, cmd, cmd_type, gcode, subcode=None, tags=None *args, **kwargs):
              if gcode or not cmd.startswith("@foo"):
                  return

              return [("M105", "temperature_poll"),    # 2-tuple, command & command type
                      ("M110",),                       # 1-tuple, just the command
                      "M117 echo foo: {}".format(cmd)] # string, just the command

          __plugin_hooks__ = {
              "octoprint.comm.protocol.gcode.queuing": rewrite_foo
          }

     Note: Only one command of a given ``cmd_type`` (other than None) may be queued at a time. Trying to rewrite the ``cmd_type``
     to one already in the queue will give an error.

   .. warning::

      Make sure to not perform any computationally expensive or otherwise long running actions within these handlers as
      you will effectively block the send loop, causing the communication with the printer to stall.

      This includes I/O of any kind.

   **Example**

   The following hook handler replaces all ``M107`` ("Fan Off", deprecated) with an ``M106 S0`` ("Fan On" with speed
   parameter) upon queuing and logs all sent ``M106``.

   .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/rewrite_m107.py
      :tab-width: 4
      :caption: `rewrite_m107.py <https://github.com/OctoPrint/Plugin-Examples/blob/master/rewrite_m107.py>`_

   :param object comm_instance: The :class:`~octoprint.util.comm.MachineCom` instance which triggered the hook.
   :param str phase: The current phase in the command progression, either ``queuing``, ``queued``, ``sending`` or
       ``sent``. Will always match the ``<phase>`` of the hook.
   :param str cmd: The GCODE command for which the hook was triggered. This is the full command as taken either
       from the currently streamed GCODE file or via other means (e.g. user input our status polling).
   :param str cmd_type: Type of command, e.g. ``temperature_poll`` for temperature polling or ``sd_status_poll`` for SD
       printing status polling.
   :param str gcode: Parsed GCODE command, e.g. ``G0`` or ``M110``, may also be None if no known command could be parsed
   :param str subcode: Parsed subcode of the GCODE command, e.g. ``1`` for ``M80.1``. Will be None if no subcode was provided
       or no command could be parsed.
   :param tags: Tags attached to the command
   :return: None, 1-tuple, 2-tuple or string, see the description above for details.

.. _sec-plugins-hook-comm-protocol-gcode-received:

octoprint.comm.protocol.gcode.received
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: gcode_received_hook(comm_instance, line, *args, **kwargs)

   .. versionadded:: 1.3.0

   Get the returned lines sent by the printer. Handlers should return the received line or in any case, the modified
   version of it. If the handler returns None, processing will be aborted and the communication layer will get an
   empty string as the received line. Note that Python functions will also automatically return ``None`` if an empty
   ``return`` statement is used or just nothing is returned explicitly from the handler.

   .. warning::

      Make sure to not perform any computationally expensive or otherwise long running actions within these handlers as
      you will effectively block the receive loop, causing the communication with the printer to stall.

      This includes I/O of any kind.

   **Example:**

   Looks for the response of an ``M115``, which contains information about the ``MACHINE_TYPE``, among other things.

   .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/read_m115_response.py
      :tab-width: 4
      :caption: `read_m115_response.py <https://github.com/OctoPrint/Plugin-Examples/blob/master/read_m115_response.py>`_

   :param MachineCom comm_instance: The :class:`~octoprint.util.comm.MachineCom` instance which triggered the hook.
   :param str line: The line received from the printer.
   :return: The received line or in any case, a modified version of it.
   :rtype: str

.. _sec-plugins-hook-comm-protocol-gcode-error:

octoprint.comm.protocol.gcode.error
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: gcode_error_hook(comm_instance, error_message, *args, **kwargs)

   .. versionadded:: 1.3.7

   Get the messages of any errors messages sent by the printer, with the leading ``Error:`` or ``!!`` already
   stripped. Handlers should return True if they handled that error internally and it should not be processed by
   the system further. Normal processing of these kinds of errors - depending on the configuration of error
   handling - involves canceling the ongoing print and possibly also disconnecting.

   Plugins might utilize this hook to handle errors generated by the printer that are recoverable in one way or
   the other and should not trigger the normal handling that assumes the worst.

   .. warning::

      Make sure to not perform any computationally expensive or otherwise long running actions within these handlers as
      you will effectively block the receive loop, causing the communication with the printer to stall.

      This includes I/O of any kind.

   **Example:**

   Looks for error messages containing "fan error" or "bed missing" (ignoring case) and marks them as handled by the
   plugin.

   .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/comm_error_handler_test.py
      :tab-width: 4
      :caption: `comm_error_handler_test.py <https://github.com/OctoPrint/Plugin-Examples/blob/master/comm_error_handler_test.py>`_

   :param MachineCom comm_instance: The :class:`~octoprint.util.comm.MachineCom` instance which triggered the hook.
   :param str error_message: The error message received from the printer.
   :return: True if the error was handled in the plugin and should not be processed further, False (or None) otherwise.
   :rtype: bool

.. _sec-plugins-hook-comm-protocol-scripts:

octoprint.comm.protocol.scripts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: protocol_scripts_hook(comm_instance, script_type, script_name, *args, **kwargs)

   .. versionadded:: 1.2.0
   .. versionchanged:: 1.3.7

   Return a prefix to prepend, postfix to append, and optionally a dictionary of variables to provide to the script ``script_name`` of type ``type``. Handlers should
   make sure to only proceed with returning additional scripts if the ``script_type`` and ``script_name`` match
   handled scripts. If not, None should be returned directly.

   If the hook handler has something to add to the specified script, it may return a 2-tuple, a 3-tuple or a 4-tuple with the first entry
   defining the prefix (what to *prepend* to the script in question), the second entry defining the postfix (what to
   *append* to the script in question), and finally if desired a dictionary of variables to be made available to the script on third and additional tags to set on the
   commands on fourth position. Both prefix and postfix can be None to signify that nothing should be prepended
   respectively appended.

   The returned prefix and postfix entries may be either iterables of script lines or a string including newlines of the script lines (which
   will be split by the caller if necessary).

   **Example 1:**

   Appends an ``M117 OctoPrint connected`` to the configured ``afterPrinterConnected`` GCODE script.

   .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/message_on_connect.py
      :tab-width: 4
      :caption: `message_on_connect.py <https://github.com/OctoPrint/Plugin-Examples/blob/master/message_on_connect.py>`_

   **Example 2:**

   Provides the variable ``myvariable`` to the configured ``beforePrintStarted`` GCODE script.

   .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/gcode_script_variables.py
      :tab-width: 4
      :caption: `gcode_script_variables.py <https://github.com/OctoPrint/Plugin-Examples/blob/master/gcode_script_variables.py>`_

   :param MachineCom comm_instance: The :class:`~octoprint.util.comm.MachineCom` instance which triggered the hook.
   :param str script_type: The type of the script for which the hook was called, currently only "gcode" is supported here.
   :param str script_name: The name of the script for which the hook was called.
   :return: A 2-tuple in the form ``(prefix, postfix)``, 3-tuple in the form ``(prefix, postfix, variables)``, or None
   :rtype: tuple or None

.. _sec-plugins-hook-comm-protocol-temperatures-received:

octoprint.comm.protocol.temperatures.received
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: protocol_temperatures_received_hook(comm_instance, parsed_temperatures, *args, **kwargs)

   .. versionadded:: 1.3.6

   Get the parsed temperatures returned by the printer, allowing handlers to modify them prior to handing them off
   to the system. Handlers are expected to either return ``parsed_temperatures`` as-is or a modified copy thereof.

   ``parsed_temperatures`` is a dictionary mapping from tool/bed identifier (``B``, ``T0``, ``T1``) to a 2-tuple of
   actual and target temperature, e.g. ``{'B': (45.2, 50.0), 'T0': (178.9, 210.0), 'T1': (21.3, 0.0)}``.

   This hook can be useful in cases where a printer e.g. is prone to returning garbage data from time to time, allowing
   additional sanity checking to be applied and invalid values to be filtered out. If a handler returns an empty
   dictionary or ``None``, no further processing will take place.

   .. warning::

      Make sure to not perform any computationally expensive or otherwise long running actions within these handlers as
      you will effectively block the receive loop, causing the communication with the printer to stall.

      This includes I/O of any kind.

   **Example**

   The following example shows how to filter out actual temperatures that are outside a sane range of 1°C to 300°C.

   .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/sanitize_temperatures.py
      :tab-width: 4
      :caption: `sanitize_temperatures.py <https://github.com/OctoPrint/Plugin-Examples/blob/master/sanitize_temperatures.py>`_

.. _sec-plugins-hook-comm-transport-serial-additonal-port-names:

octoprint.comm.transport.serial.additional_port_names
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: additional_port_names_hook(candidates, *args, **kwargs)

   .. versionadded:: 1.4.1

   Return additional port names (not glob patterns!) to use as a serial connection to the printer. Expected to be
   ``list`` of ``string``.

   Useful in combination with :ref:`octoprint.comm.transport.serial.factory <sec-plugins-hook-comm-transport-serial-factory>`
   to implement custom serial-like ports through plugins.

   For an example of use see the bundled ``virtual_printer`` plugin.

   :param list candidates: The port names already found on the system available for connection.
   :return: Additional port names to offer up for connection.
   :rtype: list

.. _sec-plugins-hook-comm-transport-serial-factory:

octoprint.comm.transport.serial.factory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: serial_factory_hook(comm_instance, port, baudrate, read_timeout, *args, **kwargs)

   .. versionadded:: 1.2.0

   Return a serial object to use as serial connection to the printer. If a handler cannot create a serial object
   for the specified ``port`` (and ``baudrate``), it should just return ``None``.

   If the hook handler needs to perform state switches (e.g. for autodetection) or other operations on the
   :class:`~octoprint.util.comm.MachineCom` instance, it can use the supplied ``comm_instance`` to do so. Plugin
   authors should keep in mind however that due to a pending change in the communication layer of
   OctoPrint, that interface will change in the future. Authors are advised to follow OctoPrint's development
   closely if directly utilizing :class:`~octoprint.util.comm.MachineCom` functionality.

   A valid serial instance is expected to provide the following methods, analogue to PySerial's
   :py:class:`serial.Serial`:

   readline(size=None, eol='\n')
       Reads a line from the serial connection, compare :py:meth:`serial.Serial.readline`.
   write(data)
       Writes data to the serial connection, compare :py:meth:`serial.Serial.write`.
   close()
       Closes the serial connection, compare :py:meth:`serial.Serial.close`.

   Additionally setting the following attributes need to be supported if baudrate detection is supposed to work:

   baudrate
       An integer describing the baudrate to use for the serial connection, compare :py:attr:`serial.Serial.baudrate`.
   timeout
       An integer describing the read timeout on the serial connection, compare :py:attr:`serial.Serial.timeout`.

   **Example:**

   Serial factory similar to the default one which performs auto detection of the serial port if ``port`` is ``None``
   or ``AUTO``.

   .. code-block:: python

      def default(comm_instance, port, baudrate, connection_timeout):
          if port is None or port == 'AUTO':
              # no known port, try auto detection
              comm_instance._changeState(comm_instance.STATE_DETECT_SERIAL)
              serial_obj = comm_instance._detectPort(False)
              if serial_obj is None:
                  comm_instance._log("Failed to autodetect serial port")
                  comm_instance._errorValue = 'Failed to autodetect serial port.'
                  comm_instance._changeState(comm_instance.STATE_ERROR)
                  eventManager().fire(Events.ERROR, {"error": comm_instance.getErrorString()})
                  return None

          else:
              # connect to regular serial port
              comm_instance._log("Connecting to: %s" % port)
              if baudrate == 0:
                  serial_obj = serial.Serial(str(port), 115200, timeout=connection_timeout, writeTimeout=10000, parity=serial.PARITY_ODD)
              else:
                  serial_obj = serial.Serial(str(port), baudrate, timeout=connection_timeout, writeTimeout=10000, parity=serial.PARITY_ODD)
              serial_obj.close()
              serial_obj.parity = serial.PARITY_NONE
              serial_obj.open()

          return serial_obj

   :param MachineCom comm_instance: The :class:`~octoprint.util.comm.MachineCom` instance which triggered the hook.
   :param str port: The port for which to construct a serial instance. May be ``None`` or ``AUTO`` in which case port
       auto detection is to be performed.
   :param int baudrate: The baudrate for which to construct a serial instance. May be 0 in which case baudrate auto
       detection is to be performed.
   :param int read_timeout: The read timeout to set on the serial port.
   :return: The constructed serial object ready for use, or ``None`` if the handler could not construct the object.
   :rtype: A serial instance implementing implementing the methods ``readline(...)``, ``write(...)``, ``close()`` and
       optionally ``baudrate`` and ``timeout`` attributes as described above.

.. _sec-plugins-hook-events-register_custom_events:

octoprint.events.register_custom_events
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: register_custom_events_hook(*args, **kwargs)

   .. versionadded:: 1.3.11

   Return a list of custom :ref:`events <sec-events>` to register in the system for your plugin.

   Should return a list of strings which represent the custom events. Their name on the `octoprint.events.Events` object
   will be the returned value transformed into upper case ``CAMEL_CASE`` and prefixed with ``PLUGIN_<IDENTIFIER>``. Their
   value will be prefixed with ``plugin_<identifier>_``.

   Example:

   Consider the following hook part of a plugin with the identifier ``myplugin``. It will register two custom events
   in the system, ``octoprint.events.Events.PLUGIN_MYPLUGIN_MY_CUSTOM_EVENT`` with value ``plugin_myplugin_my_custom_event``
   and ``octoprint.events.Events.PLUGIN_MYPLUGIN_MY_OTHER_CUSTOM_EVENT`` with value ``plugin_myplugin_my_other_custom_event``.

   .. code-block:: python

      def register_custom_events(*args, **kwargs):
          return ["my_custom_event", "my_other_custom_event"]

   :return: A list of custom events to register
   :rtype: list

.. _sec-plugins-hook-filemanager-analysis-factory:

octoprint.filemanager.analysis.factory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: analysis_queue_factory_hook(*args, **kwargs)

   .. versionadded:: 1.3.9

   Return additional (or replacement) analysis queue factories used for analysing uploaded files.

   Should return a dictionary to merge with the existing dictionary of factories, mapping from extension tree leaf
   to analysis queue factory. Analysis queue factories are expected to be :class:`~octoprint.filemanager.analysis.AbstractAnalysisQueue`
   subclasses or factory methods taking one argument (the finish callback to be used by the queue implementation
   to signal that an analysis has been finished to the system). See the source of :class:`~octoprint.filemanager.analysis.GcodeAnalysisQueue`
   for an example.

   By default, only one analysis queue factory is registered in the system, for file type ``gcode``: :class:`~octoprint.filemanager.analysis.GcodeAnalysisQueue`.
   This can be replaced by plugins using this hook, allowing other approaches to file analysis.

   This is useful for plugins wishing to provide (alternative) methods of metadata analysis for printable files.

   **Example:**

   The following handler would replace the existing analysis queue for ``gcode`` files with a custom implementation:

   .. code-block:: python

      from octoprint.filemanager.analysis import AbstractAnalysisQueue

      class MyCustomGcodeAnalysisQueue(AbstractAnalysisQueue):
          # ... custom implementation here ...

      def custom_gcode_analysis_queue(*args, **kwargs):
          return dict(gcode=MyCustomGcodeAnalysisQueue)

   :return: A dictionary of analysis queue factories, mapped by their targeted file type.
   :rtype: dict

.. _sec-plugins-hook-filemanager-extensiontree:

octoprint.filemanager.extension_tree
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: file_extension_hook(*args, **kwargs)

   .. versionadded:: 1.2.0

   Return additional entries for the tree of accepted file extensions for uploading/handling by the file manager.

   Should return a dictionary to merge with the existing extension tree, adding additional extension groups to
   ``machinecode`` or ``model`` types.

   **Example:**

   The following handler would add a new file type "x3g" as accepted ``machinecode`` format, with extensions ``x3g``
   and ``s3g``:

   .. code-block:: python

      def support_x3g_machinecode(*args, **kwargs):
          return dict(
              machinecode=dict(
                  x3g=["x3g", "s3g"]
              )
          )

   .. note::

      This will only add the supplied extensions to the extension tree, allowing the files to be uploaded and managed
      through the file manager. Plugins will need to add further steps to ensure that the files will be processable
      in the rest of the system (e.g. handling/preprocessing new machine code file types for printing etc)!

   :return: The partial extension tree to merge with the full extension tree.
   :rtype: dict

.. _sec-plugins-hook-filemanager-preprocessor:

octoprint.filemanager.preprocessor
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: file_preprocessor_hook(path, file_object, links=None, printer_profile=None, allow_overwrite=False, *args, **kwargs)

   .. versionadded:: 1.2.0

   Replace the ``file_object`` used for saving added files to storage by calling :func:`~octoprint.filemanager.util.AbstractFileWrapper.save`.

   ``path`` will be the future path of the file on the storage. The file's name is accessible via
   :attr:`~octoprint.filemanager.util.AbstractFileWrapper.filename`.

   ``file_object`` will be a subclass of :class:`~octoprint.filemanager.util.AbstractFileWrapper`. Handlers may
   access the raw data of the file via :func:`~octoprint.filemanager.util.AbstractFileWrapper.stream`, e.g.
   to wrap it further. Handlers which do not wish to handle the `file_object` should just return it untouched.

   **Example**

   The following plugin example strips all comments from uploaded/generated GCODE files ending on the name postfix ``_strip``.

   .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/strip_all_comments.py
      :tab-width: 4
      :caption: `strip_all_comments.py <https://github.com/OctoPrint/Plugin-Examples/blob/master/strip_all_comments.py>`_

   :param str path: The path on storage the `file_object` is to be stored
   :param AbstractFileWrapper file_object: The :class:`~octoprint.filemanager.util.AbstractFileWrapper` instance
       representing the file object to store.
   :param dict links: The links that are going to be stored with the file.
   :param dict printer_profile: The printer profile associated with the file.
   :param boolean allow_overwrite: Whether to allow overwriting an existing file named the same or not.
   :return: The `file_object` as passed in or None, or a replaced version to use instead for further processing.
   :rtype: AbstractFileWrapper or None

.. _sec-plugins-hook-plugin-backup-excludes:

octoprint.plugin.backup.additional_excludes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. versionadded:: 1.5.0

See :ref:`here <sec-bundledplugins-backup-hooks-excludes>`.

.. _sec-plugins-hook-plugin-pluginmanager-reconnect:

octoprint.plugin.pluginmanager.reconnect_hooks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. versionadded:: 1.4.0

See :ref:`here <sec-bundledplugins-pluginmanager-hooks-reconnect_hooks>`.

.. _sec-plugins-hook-plugin-softwareupdate-check_config:

octoprint.plugin.softwareupdate.check_config
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. versionadded:: 1.2.0

See :ref:`here <sec-bundledplugins-softwareupdate-hooks-check_config>`.

.. _sec-plugins-hooks-plugin-printer-additional_state_data:

octoprint.printer.additional_state_data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: additional_state_data_hook(initial=False, *args, **kwargs)

   .. versionadded:: 1.5.0

   Use this to inject additional data into the data structure returned from the printer backend to the frontend
   on the push socket or other registered :class:`octoprint.printer.PrinterCallback`. Anything you return here
   will be located beneath ``plugins.<your plugin id>`` in the resulting initial and current data push structure.

   The ``initial`` parameter will be ``True`` if this the additional update sent to the callback. Your handler should
   return a ``dict``, or ``None`` if nothing should be included.

   .. warning::

      Make sure to not perform any computationally expensive or otherwise long running actions within these handlers as
      you could stall the whole state monitor and thus updates being pushed to the frontend.

      This includes I/O of any kind.

      Cache your data!

   :param boolean initial: True if this is the initial update, False otherwise
   :return: Additional data to include
   :rtype: dict

.. _sec-plugins-hook-printer-factory:

octoprint.printer.factory
~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: printer_factory_hook(components, *args, **kwargs)

   .. versionadded:: 1.3.0

   Return a :class:`~octoprint.printer.PrinterInstance` instance to use as global printer object. This will
   be called only once during initial server startup.

   The provided ``components`` is a dictionary containing the already initialized system components:

     * ``plugin_manager``: The :class:`~octoprint.plugin.core.PluginManager`
     * ``printer_profile_manager``: The :class:`~octoprint.printer.profile.PrinterProfileManager`
     * ``event_bus``: The :class:`~octoprint.events.EventManager`
     * ``analysis_queue``: The :class:`~octoprint.filemanager.analysis.AnalysisQueue`
     * ``slicing_manager``: The :class:`~octoprint.slicing.SlicingManager`
     * ``file_manager``: The :class:`~octoprint.filemanager.FileManager`
     * ``plugin_lifecycle_manager``: The :class:`~octoprint.server.LifecycleManager`
     * ``user_manager``: The :class:`~octoprint.access.users.UserManager`
     * ``preemptive_cache``: The :class:`~octoprint.server.util.flask.PreemptiveCache`

   If the factory returns anything but ``None``, it will be assigned to the global ``printer`` instance.

   If none of the registered factories return a printer instance, the default :class:`~octoprint.printer.standard.Printer`
   class will be instantiated.

   :param dict components: System components to use for printer instance initialization
   :return: The ``printer`` instance to use globally.
   :rtype: PrinterInterface subclass or None

.. _sec-plugins-hook-printer-handle_connect:

octoprint.printer.handle_connect
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: handle_connect(*args, **kwargs):

   .. versionadded:: 1.6.0

   Allows plugins to perform actions upon connecting to a printer. By returning ``True``,
   plugins may also prevent further processing of the connect command. This hook is of
   special interest if your plugin needs a connect from going through under certain
   circumstances or if you need to do something before a connection to the printer is
   established (e.g. switching on power to the printer).

   :param kwargs: All connection parameters supplied to the ``connect`` call. Currently
                  this also includes ``port``, ``baudrate`` and ``profile``.
   :return: ``True`` if OctoPrint should not proceed with the connect
   :rtype: boolean or None

.. _sec-plugins-hook-printer-estimation-factory:

octoprint.printer.estimation.factory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: print_time_estimator_factory(*args, **kwargs)

   .. versionadded:: 1.3.9

   Return a :class:`~octoprint.printer.estimation.PrintTimeEstimator` subclass (or factory) to use for print time
   estimation. This will be called on each start of a print or streaming job with a single parameter ``job_type``
   denoting the type of job that was just started: ``local`` meaning a print of a local file through the serial connection,
   ``sdcard`` a print of a file stored on the printer's SD card, ``stream`` the streaming of a local file to the
   printer's SD card.

   This is useful for plugins wishing to provide alternative methods of live print time estimation.

   If none of the registered factories return a ``PrintTimeEstimator`` subclass, the default :class:`~octoprint.printer.estimation.PrintTimeEstimator`
   will be used.

   **Example:**

   The following example would replace the stock print time estimator with (a nonsensical) one that always estimates
   two hours of print time left:

   .. code-block:: python

      from octoprint.printer.estimation import PrintTimeEstimator

      class CustomPrintTimeEstimator(PrintTimeEstimator):
          def __init__(self, job_type):
              pass

          def estimate(self, progress, printTime, cleanedPrintTime, statisticalTotalPrintTime, statisticalTotalPrintTimeType):
              # always reports 2h as printTimeLeft
              return 2 * 60 * 60, "estimate"

      def create_estimator_factory(*args, **kwargs):
          return CustomPrintTimeEstimator

      __plugin_hooks__ = {
      	"octoprint.printer.estimation.factory": create_estimator_factory
      }


   :return: The :class:`~octoprint.printer.estimation.PrintTimeEstimator` class to use, or a factory method
   :rtype: class or function

.. _sec-plugins-hook-octoprint-printer-sdcardupload:

octoprint.printer.sdcardupload
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: sd_card_upload_hook(printer, filename, path, start_callback, success_callback, failure_callback, *args, **kwargs)

   .. versionadded:: 1.3.11

   Via this hook plugins can change the way files are being uploaded to the sd card of the printer.

   Implementations **must** call the provided ``start_callback`` on start of the file transfer and either the ``success_callback``
   or ``failure_callback`` on the end of the file transfer, depending on whether it was successful or not.

   The ``start_callback`` has the following signature:

   .. code-block:: python

      def start_callback(local_filename, remote_filename):
          # ...

   ``local_filename`` must be the name of the file on the ``local`` storage, ``remote_filename`` the name of the file
   to be created on the ``sdcard`` storage.

   ``success_callback`` and ``failure_callback`` both have the following signature:

   .. code-block:: python

      def success_or_failure_callback(local_filename, remote_filename, elapsed):
          # ...

   ``local_filename`` must be the name of the file on the ``local`` storage, ``remote_filename`` the name of the file
   to be created on the ``sdcard`` storage. ``elapsed`` is the elapsed time in seconds.

   If the hook is going to handle the upload, it must return the (future) remote filename of the file on the ``sdcard``
   storage. If it returns ``None`` (or an otherwise falsy value), OctoPrint will interpret this as the hook not going to
   handle the file upload, in which case the next hook or - if no other hook is registered - the default implementation
   will be called.

   **Example**

   The following example creates a dummy SD card uploader that does nothing but sleep for ten seconds when a file
   is supposed to be uploaded. Note that the long running process of sleeping for ten seconds is extracted into its
   own thread, which is important in order to not block the main application!

   .. code-block:: python

      import threading
      import logging
      import time

      def nop_upload_to_sd(printer, filename, path, sd_upload_started, sd_upload_succeeded, sd_upload_failed, *args, **kwargs):
          logger = logging.getLogger(__name__)

          remote_name = printer._get_free_remote_name(filename)
          logger.info("Starting dummy SDCard upload from {} to {}".format(filename, remote_name))

          sd_upload_started(filename, remote_name)

          def process():
              logger.info("Sleeping 10s...")
              time.sleep(10)
              logger.info("And done!")
              sd_upload_succeeded(filename, remote_name, 10)

          thread = threading.Thread(target=process)
          thread.daemon = True
          thread.start()

          return remote_name

      __plugin_name__ = "No-op SDCard Upload Test"
      __plugin_hooks__ = {
          "octoprint.printer.sdcardupload": nop_upload_to_sd
      }

   .. versionadded:: 1.3.11

   :param object printer: the :py:class:`~octoprint.printer.PrinterInterface` instance the hook was called from
   :param str filename: filename on the ``local`` storage
   :param str path: path of the file in the local file system
   :param function sd_upload_started: callback for when the upload started
   :param function sd_upload_success: callback for successful finish of upload
   :param function sd_upload_failure: callback for failure of upload
   :return: the name of the file on the ``sdcard`` storage or ``None``
   :rtype: string or ``None``

.. _sec-plugins-hook-server-http-after_request:

octoprint.server.api.after_request
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: after_request_handlers_hook(*args, **kwargs)

   .. versionadded:: 1.3.10

   Allows adding additional after-request-handlers to API endpoints defined by OctoPrint itself and installed plugins.

   Your plugin might need this to further restrict access to API methods.

   .. important::

      Implementing this hook will make your plugin require a restart of OctoPrint for enabling/disabling it fully.

.. _sec-plugins-hook-server-http-before_request:

octoprint.server.api.before_request
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: before_request_handlers_hook(*args, **kwargs)

   .. versionadded:: 1.3.10

   Allows adding additional before-request-handlers to API endpoints defined by OctoPrint itself and installed plugins.

   Your plugin might need this to further restrict access to API methods.

   .. important::

      Implementing this hook will make your plugin require a restart of OctoPrint for enabling/disabling it fully.

.. _sec-plugins-hook-server-http-access_validator:

octoprint.server.http.access_validator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: access_validator_hook(request, *args, **kwargs)

   .. versionadded:: 1.3.10

   Allows adding additional access validators to the default tornado routers.

   Your plugin might need to this to restrict access to downloads and webcam snapshots further.

   .. important::

      Implementing this hook will make your plugin require a restart of OctoPrint for enabling/disabling it fully.

.. _sec-plugins-hook-server-http-bodysize:

octoprint.server.http.bodysize
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: server_bodysize_hook(current_max_body_sizes, *args, **kwargs)

   .. versionadded:: 1.2.0

   Allows extending the list of custom maximum body sizes on the web server per path and HTTP method with custom entries
   from plugins.

   Your plugin might need this if you want to allow uploading files larger than 100KB (the default maximum upload size
   for anything but the ``/api/files`` endpoint).

   ``current_max_body_sizes`` will be a (read-only) list of the currently configured maximum body sizes, in case you
   want to check from your plugin if you need to even add a new entry.

   The hook must return a list of 3-tuples (the list's length can be 0). Each 3-tuple should have the HTTP method
   against which to match as first, a regular expression for the path to match against and the maximum body size as
   an integer as the third entry.

   The path of the route will be prefixed by OctoPrint with ``/plugin/<plugin identifier>/`` (if the path already begins
   with a ``/`` that will be stripped first).

   .. important::

      Implementing this hook will make your plugin require a restart of OctoPrint for enabling/disabling it fully.

   **Example**

   The following plugin example sets the maximum body size for ``POST`` requests against four custom URLs to 100, 200,
   500 and 1024KB. To test its functionality try uploading files larger or smaller than an endpoint's configured maximum
   size (as multipart request with the file upload residing in request parameter ``file``) and observe the behaviour.

   .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/increase_bodysize.py
      :tab-width: 4
      :caption: `increase_bodysize.py <https://github.com/OctoPrint/Plugin-Examples/blob/master/increase_bodysize.py>`_

   :param list current_max_body_sizes: read-only list of the currently configured maximum body sizes
   :return: A list of 3-tuples with additional request specific maximum body sizes as defined above
   :rtype: list

.. _sec-plugins-hook-server-http-routes:

octoprint.server.http.routes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: server_route_hook(server_routes, *args, **kwargs)

   .. versionadded:: 1.2.0

   Allows extending the list of routes registered on the web server.

   This is interesting for plugins which want to provide their own download URLs which will then be delivered statically
   following the same path structure as regular downloads.

   ``server_routes`` will be a (read-only) list of the currently defined server routes, in case you want to check from
   your plugin against that.

   The hook must return a list of 3-tuples (the list's length can be 0). Each 3-tuple should have the path of the route
   (a string defining its regular expression) as the first, the `RequestHandler <http://tornado.readthedocs.org/en/branch4.0/web.html#request-handlers>`_
   class to use for the route as the second and a dictionary with keywords parameters for the defined request handler as
   the third entry.

   The path of the route will be prefixed by OctoPrint with ``/plugin/<plugin identifier>/`` (if the path already begins
   with a ``/`` that will be stripped first).

   .. note::

      Static routes provided through this hook take precedence over routes defined through blueprints.

      If your plugin also implements the :class:`~octoprint.plugin.BlueprintPlugin` mixin and has defined a route for a
      view on that which matches one of the paths provided via its ``octoprint.server.http.routes`` hook handler, the
      view of the blueprint will thus not be reachable since processing of the request will directly be handed over
      to your defined handler class.

   .. important::

      If you want your route to support CORS if it's enabled in OctoPrint, your `RequestHandler <http://tornado.readthedocs.org/en/branch4.0/web.html#request-handlers>`_
      needs to implement the :class:`~octoprint.server.util.tornado.CorsSupportMixin` for this to work. Note that all of
      :class:`~octoprint.server.util.tornado.LargeResponseHandler`, :class:`~octoprint.server.util.tornado.UrlProxyHandler`,
      :class:`~octoprint.server.util.tornado.StaticDataHandler` and :class:`~octoprint.server.util.tornado.DeprecatedEndpointHandler`
      already implement this mixin.

   .. important::

      Implementing this hook will make your plugin require a restart of OctoPrint for enabling/disabling it fully.

   **Example**

   The following example registers two new routes ``/plugin/add_tornado_route/download`` and ``/plugin/add_tornado_route/forward``
   in the webserver which roughly replicate the functionality of ``/downloads/files/local`` and ``/downloads/camera/current``.

   .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/add_tornado_route.py
      :tab-width: 4
      :caption: `add_tornado_route.py <https://github.com/OctoPrint/Plugin-Examples/blob/master/add_tornado_route.py>`_

   .. seealso::

      :class:`~octoprint.server.util.tornado.LargeResponseHandler`
         Customized `tornado.web.StaticFileHandler <http://tornado.readthedocs.org/en/branch4.0/web.html#tornado.web.StaticFileHandler>`_
         that allows delivery of the requested resource as attachment and access validation through an optional callback.
      :class:`~octoprint.server.util.tornado.UrlForwardHandler`
         `tornado.web.RequestHandler <http://tornado.readthedocs.org/en/branch4.0/web.html#request-handlers>`_ that proxies
         requests to a preconfigured URL and returns the response.

   :param list server_routes: read-only list of the currently configured server routes
   :return: a list of 3-tuples with additional routes as defined above
   :rtype: list

.. _sec-plugins-hook-server-sockjs-authed:

octoprint.server.sockjs.authed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: socket_authed_hook(socket, user, *args, **kwargs):

   .. versionadded:: 1.3.10

   Allows plugins to be notified that a user got authenticated or deauthenticated on the socket (e.g. due to logout).

   :param object socket: the socket object which is about to be registered
   :param object user: the user that got authenticated on the socket, or None if the user got deauthenticated

.. _sec-plugins-hook-server-sockjs-register:

octoprint.server.sockjs.register
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: socket_registration_hook(socket, user, *args, **kwargs):

   .. versionadded:: 1.3.10

   Allows plugins to prevent a new :ref:`push socket client <sec-api-push>` to be registered to the system.

   Handlers should return either ``True`` or ``False``. ``True`` signals to proceed with normal registration. ``False``
   signals to not register the client.

   :param object socket: the socket object which is about to be registered
   :param object user: the user currently authenticated on the socket - might be None
   :return: whether to proceed with registration (``True``) or not (``False``)
   :rtype: boolean

.. _sec-plugins-hook-server-sockjs-emit:

octoprint.server.sockjs.emit
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: socket_emit_hook(socket, user, message, payload, *args, **kwargs):

   .. versionadded:: 1.3.10

   Allows plugins to prevent any messages to be emitted on an existing :ref:`push connection <sec-api-push>`.

   Handlers should return either ``True`` to allow the message to be emitted, or ``False`` to prevent it.

   :param object socket: the socket object on which a message is about to be emitted
   :param object user: the user currently authenticated on the socket - might be None
   :param string message: the message type about to be emitted
   :param dict payload: the payload of the message about to be emitted (may be None)
   :return: whether to proceed with sending the message (``True``) or not (``False``)
   :rtype: boolean

.. _sec-plugins-hook-system-additional_commands:

octoprint.system.additional_commands
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: additional_commands_hook(*args, **kwargs)

   .. versionadded:: 1.7.0

   Allows adding additional system commands into the system menu. Handlers must return
   a list of system command definitions, each definition matching the following data
   structure:

   .. list-table::
      :widths: 15 5 10 30
      :header-rows: 1

      * - Name
        - Multiplicity
        - Type
        - Description
      * - ``name``
        - 1
        - String
        - The name to display in the menu.
      * - ``action``
        - 1
        - String
        - An identifier for the action, must only consist of lower case a-z, numbers, ``-`` and ``_`` (``[a-z0-9-_]``).
      * - ``command``
        - 1
        - String
        - The system command to execute.
      * - ``confirm``
        - 0..1
        - String
        - An optional message to show as a confirmation dialog before executing the command.
      * - ``async``
        - 0..1
        - bool
        - If ``True``, the command will be run asynchronously and the API call will return immediately after enqueuing it for execution.
      * - ``ignore``
        - 0..1
        - bool
        - If ``True``, OctoPrint will ignore the result of the command's (and ``before``'s, if set) execution and return a successful result regardless. Defaults to ``False``.
      * - ``debug``
        - 0..1
        - bool
        - If ``True``, the command will generate debug output in the log including the command line that's run. Use with care. Defaults to ``False``
      * - ``before``
        - 0..1
        - callable
        - Optional callable to execute before the actual ``command`` is run. If ``ignore`` is false and this fails in any way, the command will not run and an error returned.

   .. code-block:: python

      def get_additional_commands(*args, **kwargs):
          return [
              {
                  "name": "Just a test",
                  "action": "test",
                  "command": "logger This is just a test of an OctoPrint system command from a plugin",
                  "before": lambda: print("Hello World!")
              }
          ]

      __plugin_hooks__ = {
          "octoprint.system.additional_commands": get_additional_commands
      }

   :return: a list of command specifications
   :rtype: list

.. _sec-plugins-hook-systeminfo-additional_bundle_files:

octoprint.systeminfo.additional_bundle_files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: additional_bundle_files_hook(*args, **kwargs)

   .. versionadded:: 1.7.0

   Allows bundled plugins to extend the list of files to include in the systeminfo bundle.
   Note that this hook will ignore third party plugins. Handlers must return a dictionary
   mapping file names in the bundle to either local log paths on disk or a ``callable``
   that will be called to generate the file's content inside the bundle.

   **Example**

   Add a plugin's ``console`` log file to the systeminfo bundle:

   .. code-block:: python

      def get_additional_bundle_files(*args, **kwargs):
        console_log = self._settings.get_plugin_logfile_path(postfix="console")
        return {os.path.basename(console_log): console_log}

      __plugin_hooks__ = {
          "octoprint.systeminfo.additional_bundle_files": get_additional_bundle_files
      }

   :return: a dictionary mapping bundle file names to bundle file content
   :rtype: dict

.. _sec-plugins-hook-timelapse-extensions:

octoprint.timelapse.extensions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: timelapse_extension_hook(*args, **kwargs)

   .. versionadded:: 1.3.10

   Allows extending the set of supported file extensions for timelapse files. Handlers must return a list of
   additional file extensions.

   **Example**

   Allow the management of timelapse GIFs with extension ``gif``.

   .. code-block:: python

      def get_timelapse_extensions(*args, **kwargs):
          return ["gif"]

      __plugin_hooks__ = {
          "octoprint.timelapse.extensions": get_timelapse_extensions
      }

   :return: a list of additional file extensions
   :rtype: list

.. _sec-plugins-hook-ui-web-templatetypes:

octoprint.ui.web.templatetypes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: templatetype_hook(template_sorting, template_rules, *args, **kwargs)

   .. versionadded:: 1.2.0

   Allows extending the set of supported template types in the web interface. This is interesting for plugins which want
   to offer other plugins to hook into their own offered UIs. Handlers must return a list of additional template
   specifications in form of 3-tuples.

   The first entry of the tuple must be the name of the template type and will be automatically prefixed with
   ``plugin_<identifier>_``.

   The second entry must be a sorting specification that defines how OctoPrint should sort multiple templates injected
   through plugins of this template type. The sorting specification should be a dict with the following possible
   entries:

   .. list-table::
      :widths: 5 95

      * - **Key**
        - **Description**
      * - key
        - The sorting key within the template config to use for sorting the list of template injections. This may be
          ``None`` in which case no sorting will be taking place. Defaults to ``name``.
      * - add
        - Usually irrelevant for custom template types, only listed for the sake of completeness. The method of adding
          the sorted list of template injections from plugins to the template injections from the
          core. May be ``append`` to append the list, ``prepend`` to prepend the list, or ``custom_append`` or
          ``custom_prepend`` to append respectively prepend but going so after preprocessing the entries and order data
          with custom functions (e.g. to inject additional entries such as the "Plugins" section header in the settings
          dialog). For custom template types this defaults to ``append``.
      * - custom_add_entries
        - Usually irrelevant for custom template types, only listed for the sake of completeness. Custom preprocessor
          for the entries provided through plugins, before they are added to the general template entries
          context variable for the current template type.
      * - custom_add_order
        - Usually irrelevant for custom template types, only listed for the sake of completeness. Custom preprocessor
          for the template order provided through plugins, before they are added to the general template order
          context variable for the current template type.

   The third entry must be a rule specification in form of a dict which tells OctoPrint how to process the template
   configuration entries provided by :func:`~octoprint.plugin.TemplatePlugin.get_template_configs` by providing
   transformation functions of various kinds:

   .. list-table::
      :widths: 5 95

      * - **Key**
        - **Description**
      * - div
        - Function that returns the id of the container for template content if not explicitly provided by the template
          config, input parameter is the name of the plugin providing the currently processed template config. If not
          provided this defaults to a lambda function of the form ``lambda x: "<plugin identifier>_<template type>_plugin_" + x``
          with ``plugin identifier`` being the identifier of the plugin providing the additional template type.
      * - template
        - Function that returns the default template filename for a template type to attempt to include in case no
          template name is explicitly provided by the template config, input parameter is the name of the plugin providing
          the current processed template config. If not provided this defaults to a lambda function of the form
          ``lambda x: x + "_plugin_<plugin identifier>_<template type>.jinja2"`` with ``plugin identifier`` being the
          identifier of the plugin providing the additional template type.
      * - to_entry
        - Function to transform a template config to the data structure stored in the Jinja context for the injected
          template. If not provided this defaults to a lambda function returning a 2-tuple of the ``name`` value of
          the template config and the template config itself (``lambda data: (data["name"], data)``)
      * - mandatory
        - A list of keys that must be included in the template config for this template type. Template configs not containing
          all of the keys in this list will be ignored. Defaults to an empty list.

   OctoPrint will provide all template configs for custom template types in the Jinja rendering context in the same way
   as it provides the template configs for core template types, through the ``templates`` context variable which is a
   dict mapping from the template type name (``plugin_<plugin identifier>_<template type>`` for custom ones) to a dict
   with ``entries`` and ``order`` values, the first containing a dict of all registered template configs, the latter
   an ordered list of all registered template keys of the type in the order they should be rendered. Plugins should
   iterate over the ``order`` list and then render each entry utilizing the template entry as provided for the key in
   the ``entries`` dict (note that this entry will have the format specified through the ``to_entry`` section in the
   template rule).

   **Example**

   The example consists of two plugins, one providing a custom template type and the other consuming it.

   First the provider:

   .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/custom_template_provider/__init__.py
      :tab-width: 4
      :caption: `custom_template_provider/__init__.py <https://github.com/OctoPrint/Plugin-Examples/blob/master/custom_template_provider/__init__.py>`_

   .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/custom_template_provider/templates/custom_template_provider_settings.jinja2
      :tab-width: 4
      :caption: `custom_template_provider/templates/custom_template_provider_settings.jinja2 <https://github.com/OctoPrint/Plugin-Examples/blob/master/custom_template_provider/templates/custom_template_provider_settings.jinja2>`_

   Then the consumer:

   .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/custom_template_consumer/__init__.py
      :tab-width: 4
      :caption: `custom_template_consumer/__init__.py <https://github.com/OctoPrint/Plugin-Examples/blob/master/custom_template_consumer/__init__.py>`_

   .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/custom_template_consumer/templates/custom_template_consumer_awesometemplate.jinja2
      :tab-width: 4
      :caption: `custom_template_consumer/templates/custom_template_consumer_awesometemplate.jinja2 <https://github.com/OctoPrint/Plugin-Examples/blob/master/custom_template_consumer/templates/custom_template_consumer_awesometemplate.jinja2>`_


   :param dict template_rules: read-only dictionary of currently configured template rules
   :param dict template_sorting: read-only dictionary of currently configured template sorting specifications
   :return: a list of 3-tuples (template type, rule, sorting spec)
   :rtype: list

.. _sec-plugins-hook-theming-dialog:

octoprint.theming.<dialog>
~~~~~~~~~~~~~~~~~~~~~~~~~~

This actually describes two hooks:

  * ``octoprint.theming.login``
  * ``octoprint.theming.recovery``

.. py:function:: ui_theming_hook(*args, **kwargs)

   .. versionadded:: 1.5.0

   Support theming of the login or recovery dialog, just in case the core UI is themed as well. Use to return a list of additional
   CSS file URLs to inject into the dialog HTML.

   Example usage by a plugin:

   .. code-block:: python

      def loginui_theming():
          from flask import url_for
          return [url_for("plugin.myplugin.static", filename="css/loginui_theme.css")]

      __plugin_hooks__ = {
          "octoprint.theming.login": loginui_theming
      }

   Only a list of ready-made URLs to CSS files is supported, neither LESS nor JS. Best use
   ``url_for`` like in the example above to be prepared for any configured prefix URLs.

   :return: A list of additional CSS URLs to inject into the login or recovery dialog.
   :rtype: A list of strings.


.. _sec-plugins-hook-timelapse-capture-pre:

octoprint.timelapse.capture.pre
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: capture_pre_hook(filename)

   .. versionadded:: 1.4.0

   Perform specific actions prior to capturing a timelapse frame.

   ``filename`` will be the future path of the frame to be saved.

   :param str filename: The future path of the frame to be saved.
   :return: None
   :rtype: None

.. _sec-plugins-hook-timelapse-capture-post:

octoprint.timelapse.capture.post
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: capture_post_hook(filename, success)

   .. versionadded:: 1.4.0

   Perform specific actions after capturing a timelapse frame.

   ``filename`` will be the path of the frame that should have been saved.
   ``success`` indicates whether the capture was successful or not.

   :param str filename: The path of the frame that should have been saved.
   :param boolean success: Indicates whether the capture was successful or not.
   :return: None
   :rtype: None
