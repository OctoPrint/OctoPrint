.. _sec-jsclientlib-timelapse:

:mod:`OctoPrintClient.timelapse`
--------------------------------

.. js:function:: OctoPrintClient.timelapse.get(unrendered, opts)

   Get a list of all timelapses and the current timelapse config.

   If ``unrendered`` is true, also retrieve the list of unrendered
   timelapses.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.timelapse.list(opts)

   Get the lists of rendered and unrendered timelapses. The returned promis
   will be resolved with an object containing the properties ``rendered``
   which will have the list of rendered timelapses, and ``unrendered`` which
   will have the list of unrendered timelapses.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.timelapse.listRendered(opts)

   Get the list of rendered timelapses.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.timelapse.listUnrendered(opts)

   Get the list of unrendered timelapses.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.timelapse.download(filename, opts)

   Download the rendered timelapse ``filename``.

   :param string filename: The name of the rendered timelapse to download
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.timelapse.delete(filename, opts)

   Delete the rendered timelapse ``filename``.

   :param string filename: The name of the rendered timelapse to delete
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.timelapse.deleteUnrendered(name, opts)

   Delete the unrendered timelapse ``name``.

   :param string name: The name of the unrendered timelapse to delete
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.timelapse.renderUnrendered(name, opts)

   Render the unrendered timelapse ``name``.

   :param string name: The name of the unrendered timelapse to render
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.timelapse.getConfig(opts)

   Get the current timelapse configuration.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.timelapse.saveConfig(config, opts)

   Save the timelapse configuration.

   :param object config: The config to save
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. seealso::

   :ref:`Timelapse API <sec-api-timelapse>`
       The documentation of the underlying timelapse API.
