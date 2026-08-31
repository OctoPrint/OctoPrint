.. _sec-jsclientlib-control:

.. js:module:: OctoPrintClient.control

``OctoPrintClient.control``
---------------------------

.. js:function:: getCustomControls(opts)

   Retrieves the defined custom controls from the server.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: sendGcode(commands, opts)

   Sends the provided ``commands`` to the printer.

   Corresponds to the :ref:`Send an arbitrary command to the printer <sec-api-printer-arbcommand>` API,
   see there for details.

   :param commands: One or more commands to send to the printer as either an array or a string.
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: sendGcodeWithParameters(commands, parameters, opts)

   Sends the provided ``commands`` to the printer, replacing contained placeholders with
   the provided ``parameters`` first.

   Corresponds to the :ref:`Send an arbitrary command to the printer <sec-api-printer-arbcommand>` API,
   see there for details.

   :param commands: One or more commands to send to the printer (list or string)
   :param object parameters: Parameters (key-value-pairs) to replace placeholders in ``commands`` with
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: sendGcodeScript(script, context, opts)

   Sends the provided ``script`` to the printer, enhancing the template with the
   specified ``context``.

   :param string script: Name of the script to send to the printer
   :param object context: Template context
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: sendGcodeScriptWithParameters(script, context, parameters, opts)

   Sends the provided ``script`` to the printer, enhancing the template with the
   specified ``context`` and ``parameters``.

   :param string script: Name of the script to send to the printer
   :param object context: Template context
   :param object parameters: Template parameters
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response
