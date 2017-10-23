.. _sec-jsclientlib-slicing:

:mod:`OctoPrintClient.slicing`
------------------------------

.. js:function:: OctoPrintClient.slicing.listAllSlicersAndProfiles(opts)

   Retrieves a list of all slicers and their available slicing profiles.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.slicing.listProfilesForSlicer(slicer, opts)

   Retrieves of all slicing profiles for the specified ``slicer``.

   :param string slicer: The identifier of the slicer for which to retrieve the profiles
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.slicing.getProfileForSlicer(slicer, profileId, opts)

   Retrieves the slicing profile with ``profileId`` for the specified ``slicer``.

   :param string slicer: The slicer for which to retrieve the profile
   :param string profileId: The identifier of the profile to retrieve
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.slicing.addProfileForSlicer(slicer, profileId, profile, opts)

   Adds the profile with identifier ``profileId`` to the specified ``slicer``, using the provided ``profile`` data.

   :param string slicer: The slicer for which to add the profile
   :param string profileId: The identifier for the profile to add
   :param object profile: The data of the profile to add
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.slicing.updateProfileForSlicer(slicer, profileId, profile, opts)

   Updates the profile ``profileId`` for ``slicer`` with the provided ``profile`` data.

   :param string slicer: The slicer for which to update the profile
   :param string profileId: The identifier for the profile to update
   :param object profile: The updated data of the profile
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.slicing.deleteProfileForSlicer(slicer, profileId, opts)

   Deletes the profile ``profileId`` for ``slicer``.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. seealso::

   :ref:`Slicing API <sec-api-slicing>`
       The documentation of the underlying slicing API.
