.. _sec-jsclientlib-printerprofiles:

:mod:`OctoPrintClient.printerprofiles`
--------------------------------------

.. js:function:: OctoPrintClient.printerprofiles.list(opts)

   Retrieves a list of all configured printer profiles.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.printerprofiles.get(id, opts)

   :param string id: The identifier of the profile to retrieve
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.printerprofiles.add(profile, additional, opts)

   Adds a new profile to OctoPrint.

   :param string profile: The data of the profile to add
   :param string basedOn: The identifier of the profile to base this profile on (optional)
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.printerprofiles.update(id, profile, opts)

   Updates an existing profile in OctoPrint.

   :param string id: The identifier of the profile to update
   :param string profile: The data of the profile to update
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.printerprofiles.delete(id, opts)

   Deletes a profile in OctoPrint.

   :param string id: The identifier of the profile to delete
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. seealso::

   :ref:`Printer profile operations <sec-api-printerprofiles>`
       The documentation of the underlying printer profile API.
