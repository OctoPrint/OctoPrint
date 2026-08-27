.. _sec-jsclientlib-system:

.. js:module:: OctoPrintClient.system

``OctoPrintClient.system``
--------------------------

.. note::

   All methods here require that the used API token or the existing browser session
   has admin rights.

.. js:function:: getCommands(opts)

   Retrieves a list of configured system commands for both ``core`` and ``custom`` sources.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: getCommandsForSource(source, opts)

   Retrieves a list of system commands, limiting it to the specified ``source``, which might be
   either ``core`` or ``custom``.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: executeCommand(source, action, opts)

   Executes command ``action`` on ``source``.

   :param string source: The source of the command to execute
   :param string action: The action identifier of the command to execute
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. seealso::

   :ref:`System API <sec-api-system>`
       Documentation of the underlying system API.
