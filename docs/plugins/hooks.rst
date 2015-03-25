.. _sec-plugins-hooks:

Available plugin hooks
======================

.. _sec-plugins-hook-comm-protocol-gcode:

octoprint.comm.protocol.gcode
-----------------------------

.. _sec-plugins-hook-comm-protocol-action:

octoprint.comm.protocol.action
------------------------------

.. py:function:: hook(comm_instance, line, action)

   React to a :ref:`action command <>` received from the printer.

   Hook handlers may use this to react to react to custom firmware messages. OctoPrint parses the received action
   command ``line`` and provides the parsed ``action`` (so anything after ``// action:``) to the hook handler.

   No returned value is expected.

   :param object comm_instance: The :class:`~octoprint.util.comm.MachineCom` instance which triggered the hook.
   :param str line: The complete line as received from the printer, format ``// action:<command>``
   :param str action: The parsed out action command, so for a ``line`` like ``// action:some_command`` this will be
       ``some_command``

.. _sec-plugins-hook-comm-protocol-scripts:

octoprint.comm.protocol.scripts
-------------------------------

.. py:function:: hook(comm_instance, script_type, script_name)

   Return a prefix to prepend and a postfix to append to the script ``script_name`` of type ``type``. Handlers should
   make sure to only proceed with returning additional scripts if the ``script_type`` and ``script_name`` match
   handled scripts. If not, None should be returned directly.

   If the hook handler has something to add to the specified script, it may return a 2-tuple, with the first entry
   defining the prefix (what to *prepend* to the script in question) and the last entry defining the postfix (what to
   *append* to the script in question). Both prefix and postfix can be None to signify that nothing should be prepended
   respectively appended.

   The returned entries may be either iterables of script lines or a string including newlines of the script lines (which
   will be split by the caller if necessary).

   Example:

   .. code-block:: python

      def hook(comm_instance, script_type, script_name):
          if not script_type == "gcode" or not script_name == "afterPrinterConnected":
              return None

          prefix = "M117 Hello\nM117 Hello World"
          postfix = ["M117 Connected", "M117 to OctoPrint"]
          return prefix, postfix

      __plugin_hooks__ = {"octoprint.comm.protocol.scripts": hook}

   :param MachineCom comm_instance: The :class:`~octoprint.util.comm.MachineCom` instance which triggered the hook.
   :param str script_type: The type of the script for which the hook was called, currently only "gcode" is supported here.
   :param str script_name: The name of the script for which the hook was called.
   :return: A 2-tuple in the form ``(prefix, postfix)`` or None
   :rtype: tuple or None