.. _sec-jsclientlib-access:

:mod:`OctoPrintClient.access`
----------------------------

.. note::

   Most methods here require that the used API token or the existing browser session
   has admin rights *or* corresponds to the user to be modified. Some methods
   definitely require admin rights.

.. _sec-jsclientlib-access-permissions:

:mod:`OctoPrintClient.access.permissions`
.........................................

.. js:function:: OctoPrintClient.access.permissions.list(opts)

   Get a list of all registered permissions.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. seealso::

   :ref:`sec-api-access-permissions`
       The documentation of the underlying user API.

.. _sec-jsclientlib-access-users:

:mod:`OctoPrintClient.access.users`
...................................

.. js:function:: OctoPrintClient.access.users.list(opts)

   Get a list of all registered users.

   Requires admin rights.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.access.users.get(name, opts)

   Get information about a specific user.

   :param string name: The user's name
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.access.users.add(user, opts)

   Add a new user.

   Requires admin rights.

   :param object user: The new user
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.access.users.update(name, active, admin, opts)

   Update an existing user.

   Requires admin rights.

   :param string name: The user's name
   :param bool active: The new ``active`` state of the user
   :param permissions: The list of permissions of the user
   :param groups: The list of groups of the user
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.access.users.delete(name, opts)

   Delete an existing user.

   Requires admin rights.

   :param string name: The user's name
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.access.users.changePassword(name, password, oldpw, opts)

   Change the password for a user.

   :param string name: The user's name
   :param string password: The new password
   :param string oldpw: The old password, optional (but required in most cases)
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.access.users.generateApiKey(name, opts)

   Generate a new API key for a user.

   :param string name: The user's name
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.access.users.resetApiKey(name, opts)

   Reset the API key for a user to being unset.

   :param string name: The user's name
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.access.users.getSettings(name, opts)

   Get the settings for a user.

   :param string name: The user's name
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.access.users.saveSettings(name, settings, opts)

   Save the settings for a user.

   :param string name: The user's name
   :param object settings: The new settings, may be a partial set of settings which will be merged unto the current ones
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. seealso::

   :ref:`sec-api-access-users`
       The documentation of the underlying user API.

.. _sec-jsclientlib-access-groups:

:mod:`OctoPrint.access.groups`
..............................

.. js:function:: OctoPrintClient.access.groups.list(opts)

   Get a list of registered groups.
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.access.groups.get(key, opts)

   Get information about a specific group.

   :param string key: The group's ID
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.access.groups.add(group, opts)

   Add a new group.

   ``group`` is expected to be the new group with at least ``key`` and ``name`` defined. Futher
   supported parameters are ``description``, ``permissions``, ``subgroup`` and the ``default`` flag.

   :param object group: The updated group
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.access.groups.update(group, opts)

   Update an existing group, identified by the ``key`` field in the ``group``. 
   Only ``description``, ``permissions``, ``subgroups`` and ``default`` flag will
   be updated.

   :param object group: The updated group
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.access.groups.delete(key, opts)

   Delete a group.

   :param string key: The group's ID
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. seealso::

   :ref:`sec-api-access-groups`
       The documentation of the underlying user API.

