.. _sec-plugins-hooks:

Available plugin hooks
======================

.. note::

   All of the hooks below take at least two parameters, ``*args`` and ``**kwargs``. Please make sure those are present.
   They will act as placeholders if additional parameters are added to the hooks in the future and will allow
   your plugin to stay compatible to OctoPrint without any necessary adjustments from you in these cases.

.. contents::
   :local:

.. _sec-plugins-hook-accesscontrol-appkey:

octoprint.accesscontrol.appkey
------------------------------

.. py:function:: hook(*args, **kwargs)

   By handling this hook plugins may register additional :ref:`App session key providers <sec-api-apps-sessionkey>`
   within the system.

   Overrides this to return your additional app information to be used for validating app session keys. You'll
   need to return a list of 3-tuples of the format (id, version, public key).

   The ``id`` should be the (unique) identifier of the app. Using a domain prefix might make sense here, e.g.
   ``org.octoprint.example.MyApp``.

   ``version`` should be a string specifying the version of the app for which the public key is valid. You can
   provide the string ``any`` here, in which case the provided public key will be valid for all versions of the
   app for which no specific public key is defined.

   Finally, the public key is expected to be provided as a PKCS1 string without newlines.

   :return: A list of 3-tuples as described above
   :rtype: list

.. _sec-plugins-hook-cli-commands:

octoprint.cli.commands
----------------------

.. py:function:: hook(cli_group, pass_octoprint_ctx, *args, **kwargs)

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
      :linenos:
      :tab-width: 4
      :caption: `custom_cli_command.py <https://github.com/OctoPrint/Plugin-Examples/blob/master/custom_cli_command.py>`_

   Calling ``octoprint --help`` shows the two new commands:

   .. code-block:: none

      $ octoprint --help
      Usage: octoprint [OPTIONS] COMMAND [ARGS]...

      Options:
        -b, --basedir PATH  Specify the basedir to use for uploads, timelapses etc.
        -c, --config PATH   Specify the config file to use.
        -v, --verbose       Increase logging verbosity
        --version           Show the version and exit.
        --help              Show this message and exit.

      Commands:
        daemon                     Starts, stops or restarts in daemon mode.
        dev:plugin                 Helpers for plugin developers
        plugin:custom_cli_command  custom_cli_command commands
        serve                      Starts the OctoPrint server.

      $ octoprint plugin:custom_cli_command --help
      Usage: octoprint plugin:custom_cli_command [OPTIONS] COMMAND [ARGS]...

        custom_cli_command commands

      Options:
        --help  Show this message and exit.

      Commands:
        greet   Greet someone by name, the greeting can be...
        random  Greet someone by name with a random greeting.

   Each also has an individual help output:

   .. code-block:: none

      $ octoprint plugin:custom_cli_command greet --help
      Usage: octoprint plugin:custom_cli_command greet [OPTIONS] [NAME]

        Greet someone by name, the greeting can be customized.

      Options:
        -g, --greeting TEXT  The greeting to use
        --help               Show this message and exit.

      $ octoprint plugin:custom_cli_command random --help
      Usage: octoprint plugin:custom_cli_command random [OPTIONS] [NAME]

        Greet someone by name with a random greeting.

      Options:
        --help  Show this message and exit.

   And of course they work too:

   .. code-block:: none

      $ octoprint plugin:custom_cli_command greet
      Hello World!

      $ octoprint plugin:custom_cli_command greet --greeting "Good morning"
      Good morning World!

      $ octoprint plugin:custom_cli_command random stranger
      Hola stranger!

   .. note::

      If your hook handler is an instance method of a plugin mixin implementation, be aware that the hook will be
      called without OctoPrint initializing your implementation instance. That means that **none** of the
      :ref:`injected properties <sec-plugins-concepts-injectedproperties>` will be available and also the
      :method:`~octoprint.plugin.Plugin.initialize` method will not be called.

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

.. _sec-plugins-hook-comm-protocol-action:

octoprint.comm.protocol.action
------------------------------

.. py:function:: hook(comm_instance, line, action, *args, **kwargs)

   React to a :ref:`action command <sec-features-action_commands>` received from the printer.

   Hook handlers may use this to react to react to custom firmware messages. OctoPrint parses the received action
   command ``line`` and provides the parsed ``action`` (so anything after ``// action:``) to the hook handler.

   No returned value is expected.

   **Example:**

   Logs if the ``custom`` action (``// action:custom``) is received from the printer's firmware.

   .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/custom_action_command.py
      :linenos:
      :tab-width: 4
      :caption: `custom_action_command.py <https://github.com/OctoPrint/Plugin-Examples/blob/master/custom_action_command.py>`_

   :param object comm_instance: The :class:`~octoprint.util.comm.MachineCom` instance which triggered the hook.
   :param str line: The complete line as received from the printer, format ``// action:<command>``
   :param str action: The parsed out action command, so for a ``line`` like ``// action:some_command`` this will be
       ``some_command``

.. _sec-plugins-hook-comm-protocol-gcode-phase:

octoprint.comm.protocol.gcode.<phase>
-------------------------------------

This describes actually four hooks:

  * ``octoprint.comm.protocol.gcode.queuing``
  * ``octoprint.comm.protocol.gcode.queued``
  * ``octoprint.comm.protocol.gcode.sending``
  * ``octoprint.comm.protocol.gcode.sent``

.. py:function:: hook(comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs)

   Pre- and postprocess commands as they progress through the various phases of being sent to the printer. The phases
   are the following:

     * ``queuing``: This phase is triggered just before the command is added to the send queue of the communication layer. This
       corresponds to the moment a command is being read from a file that is currently being printed. Handlers
       may suppress or change commands or their command type here.
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
   will never contain more than one line with the same ``cmd_type``) and the detected gcode command (if it is one).

   Defining a ``cmd_type`` other than None will make sure OctoPrint takes care of only having one command of that type
   in its sending queue. Predefined types are ``temperature_poll`` for temperature polling via ``M105`` and
   ``sd_status_poll`` for polling the SD printing status via ``M27``.

   ``phase`` will always match the ``<phase>`` part of the implemented hook (e.g. ``octoprint.comm.protocol.gcode.queued``
   handlers will always be called with ``phase`` set to ``queued``). This parameter is provided so that plugins may
   utilize the same hook for multiple phases if required.

   Handlers are expected to return one of the following result variants:

     * ``None``: Don't change anything. Note that Python functions will also automatically return ``None`` if
       an empty ``return`` statement is used or just nothing is returned explicitly from the handler. Hence, the following
       examples are all falling into this category:

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

   **Example**

   The following hook handler replaces all ``M107`` ("Fan Off", deprecated) with an ``M106 S0`` ("Fan On" with speed
   parameter) upon queuing and logs all sent ``M106``.

   .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/rewrite_m107.py
      :linenos:
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
   :return: None, 1-tuple, 2-tuple or string, see the description above for details.

.. _sec-plugins-hook-comm-protocol-gcode-received:

octoprint.comm.protocol.gcode.received
--------------------------------------

.. py:function:: hook(comm_instance, line, *args, **kwargs)

   Get the returned lines sent by the printer. Handlers should return the received line or in any case, the modified
   version of it. If the the handler returns None, processing will be aborted and the communication layer will get an
   empty string as the received line. Note that Python functions will also automatically return ``None`` if an empty
   ``return`` statement is used or just nothing is returned explicitely from the handler.

   **Example:**

   Looks for the response of a M115, which contains information about the MACHINE_TYPE, among other things.

   .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/read_m115_response.py
      :linenos:
      :tab-width: 4
      :caption: `read_m115_response.py <https://github.com/OctoPrint/Plugin-Examples/blob/master/read_m115_response.py>`_

   :param MachineCom comm_instance: The :class:`~octoprint.util.comm.MachineCom` instance which triggered the hook.
   :param str line: The line received from the printer.
   :return: The received line or in any case, a modified version of it.
   :rtype: str

.. _sec-plugins-hook-comm-protocol-scripts:

octoprint.comm.protocol.scripts
-------------------------------

.. py:function:: hook(comm_instance, script_type, script_name, *args, **kwargs)

   Return a prefix to prepend and a postfix to append to the script ``script_name`` of type ``type``. Handlers should
   make sure to only proceed with returning additional scripts if the ``script_type`` and ``script_name`` match
   handled scripts. If not, None should be returned directly.

   If the hook handler has something to add to the specified script, it may return a 2-tuple, with the first entry
   defining the prefix (what to *prepend* to the script in question) and the last entry defining the postfix (what to
   *append* to the script in question). Both prefix and postfix can be None to signify that nothing should be prepended
   respectively appended.

   The returned entries may be either iterables of script lines or a string including newlines of the script lines (which
   will be split by the caller if necessary).

   **Example:**

   Appends an ``M117 OctoPrint connected`` to the configured ``afterPrinterConnected`` GCODE script.

   .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/message_on_connect.py
      :linenos:
      :tab-width: 4
      :caption: `message_on_connect.py <https://github.com/OctoPrint/Plugin-Examples/blob/master/message_on_connect.py>`_

   :param MachineCom comm_instance: The :class:`~octoprint.util.comm.MachineCom` instance which triggered the hook.
   :param str script_type: The type of the script for which the hook was called, currently only "gcode" is supported here.
   :param str script_name: The name of the script for which the hook was called.
   :return: A 2-tuple in the form ``(prefix, postfix)`` or None
   :rtype: tuple or None

.. _sec-plugins-hook-comm-transport-serial-factory:

octoprint.comm.transport.serial.factory
---------------------------------------

.. py:function:: hook(comm_instance, port, baudrate, read_timeout, *args, **kwargs)

   Return a serial object to use as serial connection to the printer. If a handler cannot create a serial object
   for the specified ``port`` (and ``baudrate``), it should just return ``None``.

   If the hook handler needs to perform state switches (e.g. for autodetection) or other operations on the
   :class:`~octoprint.util.comm.MachineCom` instance, it can use the supplied ``comm_instance`` to do so. Plugin
   authors should keep in mind however that due to a pending change in the communication layer of
   OctoPrint, that interface will change in the future. Authors are advised to follow OctoPrint's development
   closely if directly utilizing :class:`~octoprint.util.comm.MachineCom` functionality.

   A valid serial instance is expected to provide the following methods, analogue to PySerial's
   `serial.Serial <https://pythonhosted.org//pyserial/pyserial_api.html#serial.Serial>`_:

   readline(size=None, eol='\n')
       Reads a line from the serial connection, compare `serial.Filelike.readline <https://pythonhosted.org//pyserial/pyserial_api.html#serial.FileLike.readline>`_.
   write(data)
       Writes data to the serial connection, compare `serial.Filelike.write <https://pythonhosted.org//pyserial/pyserial_api.html#serial.FileLike.write>`_.
   close()
       Closes the serial connection, compare `serial.Serial.close <https://pythonhosted.org//pyserial/pyserial_api.html#serial.Serial.close>`_.

   Additionally setting the following attributes need to be supported if baudrate detection is supposed to work:

   baudrate
       An integer describing the baudrate to use for the serial connection, compare `serial.Serial.baudrate <https://pythonhosted.org//pyserial/pyserial_api.html#serial.Serial.baudrate>`_.
   timeout
       An integer describing the read timeout on the serial connection, compare `serial.Serial.timeout <https://pythonhosted.org//pyserial/pyserial_api.html#serial.Serial.timeout>`_.

   **Example:**

   Serial factory similar to the default one which performs auto detection of the serial port if ``port`` is ``None``
   or ``AUTO``.

   .. code-block:: python
      :linenos:

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

.. _sec-plugins-hook-filemanager-extensiontree:

octoprint.filemanager.extension_tree
------------------------------------

.. py:function:: hook(*args, **kwargs)

   Return additional entries for the tree of accepted file extensions for uploading/handling by the file manager.

   Should return a dictionary to merge with the existing extension tree, adding additional extension groups to
   ``machinecode`` or ``model`` types.

   **Example:**

   The following handler would add a new file type "x3g" as accepted ``machinecode`` format, with extensions ``x3g``
   and ``s3g``:

   .. code-block:: python
      :linenos:

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
----------------------------------

.. py:function:: hook(path, file_object, links=None, printer_profile=None, allow_overwrite=False, *args, **kwargs)

   Replace the ``file_object`` used for saving added files to storage by calling :func:`~octoprint.filemanager.util.AbstractFileWrapper.save`.

   ``path`` will be the future path of the file on the storage. The file's name is accessible via
   :attr:`~octoprint.filemanager.util.AbstractFileWrapper.filename`.

   ``file_object`` will be a subclass of :class:`~octoprint.filemanager.util.AbstractFileWrapper`. Handlers may
   access the raw data of the file via :func:`~octoprint.filemanager.util.AbstractFileWrapper.stream`, e.g.
   to wrap it further. Handlers which do not wish to handle the `file_object`

   **Example**

   The following plugin example strips all comments from uploaded/generated GCODE files ending on the name postfix ``_strip``.

   .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/strip_all_comments.py
      :linenos:
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

.. _sec-plugins-hook-server-http-bodysize:

octoprint.server.http.bodysize
------------------------------

.. py:function:: hook(current_max_body_sizes, *args, **kwargs)

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

   **Example**

   The following plugin example sets the maximum body size for ``POST`` requests against four custom URLs to 100, 200,
   500 and 1024KB. To test its functionality try uploading files larger or smaller than an endpoint's configured maximum
   size (as multipart request with the file upload residing in request parameter ``file``) and observe the behaviour.

   .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/increase_bodysize.py
      :linenos:
      :tab-width: 4
      :caption: `increase_bodysize.py <https://github.com/OctoPrint/Plugin-Examples/blob/master/increase_bodysize.py>`_

   :param list current_max_body_sizes: read-only list of the currently configured maximum body sizes
   :return: A list of 3-tuples with additional request specific maximum body sizes as defined above
   :rtype: list

.. _sec-plugins-hook-server-http-routes:

octoprint.server.http.routes
----------------------------

.. py:function:: hook(server_routes, *args, **kwargs)

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

   **Example**

   The following example registers two new routes ``/plugin/add_tornado_route/download`` and ``/plugin/add_tornado_route/forward``
   in the webserver which roughly replicate the functionality of ``/downloads/files/local`` and ``/downloads/camera/current``.

   .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/add_tornado_route.py
      :linenos:
      :tab-width: 4
      :caption: `add_tornado_route.py <https://github.com/OctoPrint/Plugin-Examples/blob/master/add_tornado_route.py>`_

   .. seealso::

      :class:`~octoprint.server.util.tornado.LargeResponseHandler`
         Customized `tornado.web.StaticFileHandler <http://tornado.readthedocs.org/en/branch4.0/web.html#tornado.web.StaticFileHandler>`_
         that allows delivery of the requested resource as attachment and access validation through an optional callback.
      :class:`~octoprint.server.util.tornado.UrlForwardHandler`
         `tornado.web.RequestHandler <http://tornado.readthedocs.org/en/branch4.0/web.html#request-handlers>`_ that proxies
         requests to a preconfigured url and returns the response.

   :param list server_routes: read-only list of the currently configured server routes
   :return: a list of 3-tuples with additional routes as defined above
   :rtype: list

.. _sec-plugins-hook-ui-web-templatetypes:

octoprint.ui.web.templatetypes
------------------------------

.. py:function:: hook(template_sorting, template_rules, *args, **kwargs)

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
      :linenos:
      :tab-width: 4
      :caption: `custom_template_provider/__init__.py <https://github.com/OctoPrint/Plugin-Examples/blob/master/custom_template_provider/__init__.py>`_

   .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/custom_template_provider/templates/custom_template_provider_settings.jinja2
      :linenos:
      :tab-width: 4
      :caption: `custom_template_provider/templates/custom_template_provider_settings.jinja2 <https://github.com/OctoPrint/Plugin-Examples/blob/master/custom_template_provider/templates/custom_template_provider_settings.jinja2>`_

   Then the consumer:

   .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/custom_template_consumer/__init__.py
      :linenos:
      :tab-width: 4
      :caption: `custom_template_consumer/__init__.py <https://github.com/OctoPrint/Plugin-Examples/blob/master/custom_template_consumer/__init__.py>`_

   .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/custom_template_consumer/templates/custom_template_consumer_awesometemplate.jinja2
      :linenos:
      :tab-width: 4
      :caption: `custom_template_consumer/templates/custom_template_consumer_awesometemplate.jinja2 <https://github.com/OctoPrint/Plugin-Examples/blob/master/custom_template_consumer/templates/custom_template_consumer_awesometemplate.jinja2>`_


   :param dict template_rules: read-only dictionary of currently configured template rules
   :param dict template_sorting: read-only dictionary of currently configured template sorting specifications
   :return: a list of 3-tuples (template type, rule, sorting spec)
   :rtype: list
