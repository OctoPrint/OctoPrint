.. sec-jsclientlib-users:

:mod:`OctoPrint.users`
----------------------

.. note::

   Most methods here require that the used API token or a the existing browser session
   has admin rights *or* corresponds to the user to be modified. Some methods
   definitely require admin rights.

.. js:function:: OctoPrint.users.list(opts)

   Get a list of all registered users.

   Requires admin rights.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrint.users.get(name, opts)

   Get information about a specific user.

   :param string name: The user's name
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrint.users.add(user, opts)

   Add a new user.

   Requires admin rights.

   :param object user: The new user
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrint.users.update(name, active, admin, opts)

   Update an existing user.

   Requires admin rights.

   :param string name: The user's name
   :param bool active: The new ``active`` state of the user
   :param bool admin: The new ``admin`` state of the user
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrint.users.delete(name, opts)

   Delete an existing user.

   Requires admin rights.

   :param string name: The user's name
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrint.users.changePassword(name, password, opts)

   Change the password for a user.

   :param string name: The user's name
   :param string password: The new password
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrint.users.generateApiKey(name, opts)

   Generate a new API key for a user.

   :param string name: The user's name
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrint.users.resetApiKey(name, opts)

   Reset the API key for a user to being unset.

   :param string name: The user's name
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrint.users.getSettings(name, opts)

   Get the settings for a user.

   :param string name: The user's name
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrint.users.saveSettings(name, settings, opts)

   Save the settings for a user.

   :param string name: The user's name
   :param object settings: The new settings, may be a partial set of settings which will be merged unto the current ones
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. seealso::

   :ref:`User API <sec-api-user>`
       The documentation of the underlying user API.
