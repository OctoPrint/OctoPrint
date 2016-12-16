.. sec-jsclientlib-settings:

:mod:`OctoPrint.settings`
-------------------------

.. js:function:: OctoPrint.settings.get(opts)

   Retrieves the current settings.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrint.settings.save(settings, opts)

   Saves the provided ``settings``.

   :param object settings: The settings to save
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrint.settings.getPluginSettings(plugin, opts)

   Retrieves the settings of the specified ``plugin``.

   :param string plugin: The plugin for which to retrieve the settings
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrint.settings.savePluginSettings(plugin, settings, opts)

   Saves the ``settings`` for the specified ``plugin``.

   :param string plugin: The plugin for which to save settings
   :param object settings: The settings to save
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. seealso::

   :ref:`Settings API <sec-api-settings>`
       The documentation of the underlying settings API.
