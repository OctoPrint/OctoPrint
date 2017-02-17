.. _sec-jsclientlib-control:

:mod:`OctoPrintClient.control`
------------------------------

.. js:function:: OctoPrintClient.control.getCustomControls(opts)

   Retrieves the defined custom controls from the server.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.control.sendGcode(commands, opts)

   Sends the provided ``commands`` to the printer.

   Corresponds to the :ref:`Send an arbitrary command to the printer <sec-api-printer-arbcommand>` API,
   see there for details.

   :param list or string commands: One or more commands to send to the printer.
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.control.sendGcodeWithParameters(commands, parameters, opts)

   Sends the provided ``commands`` to the printer, replacing contained placeholders with
   the provided ``parameters`` first.

   Corresponds to the :ref:`Send an arbitrary command to the printer <sec-api-printer-arbcommand>` API,
   see there for details.

   :param list or string commands: One or more commands to send to the printer
   :param object parameters: Parameters (key-value-pairs) to replace placeholders in ``commands`` with
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.control.sendGcodeScript(script, context, opts)

   Sends the provided ``script`` to the printer, enhancing the template with the
   specified ``context``.

   :param string script: Name of the script to send to the printer
   :param object context: Template context
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.control.sendGcodeScriptWithParameters(script, context, parameters, opts)

   Sends the provided ``script`` to the printer, enhancing the template with the
   specified ``context`` and ``parameters``.

   :param string script: Name of the script to send to the printer
   :param object context: Template context
   :param object parameters: Template parameters
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

