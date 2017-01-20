.. _sec-jsclientlib-logs:

:mod:`OctoPrintClient.logs`
---------------------------

.. note::

   All methods here require that the used API token or a the existing browser session
   has admin rights.

.. js:function:: OctoPrintClient.logs.list(opts)

   Retrieves a list of log files.

   See :ref:`Retrieve a list of available log files <sec-api-logs-list>` for details.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.logs.delete(path, opts)

   Deletes the specified log ``path``.

   See :ref:`Delete a specific log file <sec-api-logs-delete>` for details.

   :param string path: The path to the log file to delete
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.logs.download(path, opts)

   Downloads the specified log ``file``.

   See :js:func:`OctoPrint.download` for more details on the underlying library download mechanism.

   :param string path: The path to the log file to download
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

