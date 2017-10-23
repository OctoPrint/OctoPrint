.. _sec-jsclientlib-wizard:

:mod:`OctoPrintClient.wizard`
-----------------------------

.. note::

   All methods here require that the used API token or a the existing browser session
   has admin rights.

.. js:function:: OctoPrintClient.wizard.get(opts)

   Retrieve additional data about registered wizards.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.wizard.finish(handled, opts)

   Inform wizards that the wizard dialog has been finished.

   :param list handled: List of identifiers of handled wizards
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. seealso::

   :ref:`Wizard API <sec-api-wizard>`
       The documentation of the underlying wizard API.
