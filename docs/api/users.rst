.. _sec-api-user:

****
User
****

.. contents::

.. _sec-api-users-list:

Retrieve a list of users
========================

.. http:get:: /api/users

   Retrieves a list of all registered users in OctoPrint.

   Will return a :http:statuscode:`200` with a :ref:`user list response <sec-api-users-datamodel-userlistresponse>`
   as body.

   Requires admin rights.

   :status 200: No error

.. _sec-api-users-retrieve:

Retrieve a user
===============

.. http:get:: /api/users/(string:username)

   Retrieves information about a user.

   Will return a :http:statuscode:`200` with a :ref:`user record <sec-api-users-datamodel-userrecord>`
   as body.

   Requires either admin rights or to be logged in as the user.

   :param username: Name of the user which to retrieve
   :status 200:     No error
   :status 404:     Unknown user

.. _sec-api-users-add:

Add a user
==========

.. http:post:: /api/users

   Adds a user to OctoPrint.

   Expects a :ref:`user registration request <sec-api-users-datamodel-adduserrequest>`
   as request body.

   Returns a list of registered users on success, see :ref:`Retrieve a list of users <sec-api-users-list>`.

   Requires admin rights.

   :json name:     The user's name
   :json password: The user's password
   :json active:   Whether to activate the account (true) or not (false)
   :json admin:    Whether to give the account admin rights (true) or not (false)
   :status 200:    No error
   :status 400:    If any of the mandatory fields is missing or the request is otherwise
                   invalid
   :status 409:    A user with the provided name does already exist

.. _sec-api-users-update:

Update a user
=============

.. http:put:: /api/users/(string:username)

   Updates a user record.

   Expects a :ref:`user update request <sec-api-users-datamodel-updateuserrequest>`
   as request body.

   Returns a list of registered users on success, see :ref:`Retrieve a list of users <sec-api-users-list>`.

   Requires admin rights.

   :param username: Name of the user to update
   :json admin:     Whether to mark the user as admin (true) or not (false), can be left out (no change)
   :json active:    Whether to mark the account as activated (true) or deactivated (false), can be left out (no change)
   :status 200:     No error
   :status 404:     Unknown user

.. _sec-api-users-delete:

Delete a user
=============

.. http:delete:: /api/users/(string:username)

   Delete a user record.

   Returns a list of registered users on success, see :ref:`Retrieve a list of users <sec-api-users-list>`.

   Requires admin rights.

   :param username: Name of the user to delete
   :status 200:     No error
   :status 404:     Unknown user

.. _sec-api-users-resetpassword:

Reset a user's password
=======================

.. http:put:: /api/users/(string:username)/password

   Changes the password of a user.

   Expects a JSON object with a single property ``password`` as request body.

   Requires admin rights or to be logged in as the user.

   :param username: Name of the user to change the password for
   :json password:  The new password to set
   :status 200:     No error
   :status 400:     If the request doesn't contain a ``password`` property or the request
                    is otherwise invalid
   :status 403:     No admin rights and not logged in as the user
   :status 404:     The user is unknown

.. _sec-api-users-getsettings:

Retrieve a user's settings
==========================

.. http:get:: /api/users/(string:username)/settings

   Retrieves a user's settings.

   Will return a :http:statuscode:`200` with a JSON object representing the user's
   personal settings (if any) as body.

   Requires admin rights or to be logged in as the user.

   :param username: Name of the user to retrieve the settings for
   :status 200:     No error
   :status 403:     No admin rights and not logged in as the user
   :status 404:     The user is unknown

.. _sec-api-users-updatesettings:

Update a user's settings
========================

.. http:patch:: /api/users/(string:username)/settings

   Updates a user's settings.

   Expects a new settings JSON object to merge with the current settings as
   request body.

   Requires admin rights or to be logged in as the user.

   :param username: Name of the user to retrieve the settings for
   :status 204:     No error
   :status 403:     No admin rights and not logged in as the user
   :status 404:     The user is unknown

.. _sec-api-users-generateapikey:

Regenerate a user's personal API key
====================================

.. http:post:: /api/users/(string:username)/apikey

   Generates a new API key for the user.

   Does not expect a body. Will return the generated API key as ``apikey``
   property in the JSON object contained in the response body.

   Requires admin rights or to be logged in as the user.

   :param username: Name of the user to retrieve the settings for
   :status 200:     No error
   :status 403:     No admin rights and not logged in as the user
   :status 404:     The user is unknown

.. _sec-api-users-deleteapikey:

Delete a user's personal API key
================================

.. http:delete:: /api/users/(string:username)/apikey

   Deletes a user's personal API key.

   Requires admin rights or to be logged in as the user.

   :param username: Name of the user to retrieve the settings for
   :status 204:     No error
   :status 403:     No admin rights and not logged in as the user
   :status 404:     The user is unknown

.. _sec-api-users-datamodel:

Data model
==========

.. _sec-api-users-datamodel-userlistresponse:

User list response
------------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``users``
     - 0..n
     - List of :ref:`user records <sec-api-users-datamodel-userrecord>`
     - The list of registered users

.. _sec-api-users-datamodel-userrecord:

User record
-----------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``name``
     - 1
     - string
     - The user's name
   * - ``active``
     - 1
     - bool
     - Whether the user's account is active (true) or not (false)
   * - ``user``
     - 1
     - bool
     - Whether the user has user rights. Should always be true.
   * - ``admin``
     - 1
     - bool
     - Whether the user has admin rights (true) or not (false)
   * - ``apikey``
     - 0..1
     - string
     - The user's personal API key
   * - ``settings``
     - 1
     - object
     - The user's personal settings, might be an empty object.

.. _sec-api-users-datamodel-adduserrequest:

User registration request
-------------------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``name``
     - 1
     - string
     - The user's name
   * - ``password``
     - 1
     - string
     - The user's password
   * - ``active``
     - 1
     - bool
     - Whether to activate the account (true) or not (false)
   * - ``admin``
     - 0..1
     - bool
     - Whether to give the user admin rights (true) or not (false or not present)

.. _sec-api-users-datamodel-updateuserrequest:

User update request
-------------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``active``
     - 0..1
     - bool
     - If present will set the user's active flag to the provided value. True for
       activating the account, false for deactivating it.
   * - ``admin``
     - 0..1
     - bool
     - If present will set the user's admin flag to the provided value. True for
       admin rights, false for no admin rights.
