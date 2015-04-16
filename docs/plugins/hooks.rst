.. _sec-plugins-hooks:

Available plugin hooks
======================

.. contents::
   :local:

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

.. _sec-plugins-hook-comm-protocol-gcode:

octoprint.comm.protocol.gcode
-----------------------------

.. py:function:: hook(comm_instance, cmd, cmd_type=None, with_checksum=None)

   Preprocess and optionally suppress a GCODE command before it is being sent to the printer.

   Hook handlers may use this to rewrite or completely suppress certain commands before they enter the send queue of
   the communication layer. The hook handler will be called with the ``cmd`` to be sent to the printer as well as
   the parameters for sending like ``cmd_type`` and ``with_checksum``.

   If the handler does not wish to handle the command, it should simply perform a ``return cmd`` as early as possible,
   that will ensure that no changes are applied to the command.

   If the handler wishes to suppress sending of the command altogether, it should return None instead. That will tell
   OctoPrint that the ``cmd`` has been scraped altogether and not send anything.

   More granular manipulation of the sending logic is possible by not just returning ``cmd`` (be it the original, a
   rewritten variant or a None value) but a 2-tuple (cmd, cmd_type) or a 3-tuple (cmd, cmd_type, with_checksum). This
   allows to also rewrite the ``cmd_type`` and the ``with_checksum`` parameter used for sending. Note that the latter
   should only be necessary in very rare circumstances, since usually plugins should not need to have to decide whether
   a command should be sent with a checksum or not.

   Defining a ``cmd_type`` other than None will make sure OctoPrint takes care of only having one command of that type
   in its sending queue. Predefined types are ``temperature_poll`` for temperature polling via ``M105`` and
   ``sd_status_poll`` for polling the SD printing status via ``M27``.

   **Example**

   The following hook handler replaces all ``M107`` ("Fan Off", deprecated) with an ``M106 S0`` ("Fan On" with speed
   parameter)

   .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/rewrite_m107.py
      :linenos:
      :tab-width: 4
      :caption: `rewrite_m107.py <https://github.com/OctoPrint/Plugin-Examples/blob/master/rewrite_m107.py>`_

   :param object comm_instance: The :class:`~octoprint.util.comm.MachineCom` instance which triggered the hook.
   :param str cmd: The GCODE command for which the hook was triggered. This is the full command as taken either
       from the currently streamed GCODE file or via other means (e.g. user input our status polling).
   :param str cmd_type: Type of command, ``temperature_poll`` for temperature polling or ``sd_status_poll`` for SD
       printing status polling.
   :param boolean with_checksum: Whether the ``cmd`` was to be sent with a checksum (True) or not (False)
   :return: A rewritten ``cmd``, a tuple of ``cmd`` and ``cmd_type`` or ``cmd``, ``cmd_type`` and ``with_checksum``
       or None to suppress sending of the ``cmd`` to the printer. See above for details.

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
   :param port str: The port for which to construct a serial instance. May be ``None`` or ``AUTO`` in which case port
       auto detection is to be performed.
   :param baudrate int: The baudrate for which to construct a serial instance. May be 0 in which case baudrate auto
       detection is to be performed.
   :param read_timeout int: The read timeout to set on the serial port.
   :return: The constructed serial object ready for use, or ``None`` if the handler could not construct the object.
   :rtype: A serial instance implementing implementing the methods ``readline(...)``, ``write(...)``, ``close()`` and
       optionally ``baudrate`` and ``timeout`` attributes as described above.

.. _sec-plugins-hook-filemanager-extensiontree:

octoprint.filemanager.extension_tree
------------------------------------

.. py:function:: hook()

   Return additional entries for the tree of accepted file extensions for uploading/handling by the file manager.

   Should return a dictionary to merge with the existing extension tree, adding additional extension groups to
   ``machinecode`` or ``model`` types.

   **Example:**

   The following handler would add a new file type "x3g" as accepted ``machinecode`` format, with extensions ``x3g``
   and ``s3g``:

   .. code-block:: python
      :linenos:

      def support_x3g_machinecode():
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