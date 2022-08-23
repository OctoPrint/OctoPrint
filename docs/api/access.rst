.. _sec-api-access:

**************
Access control
**************

.. contents::

.. _sec-api-access-permissions:

Permissions
===========

.. _sec-api-access-permissions-list:

List all permissions
--------------------

.. http:get:: /api/access/permissions

   Retrieves all permissions available in the system.

   Will return a :http:statuscode:`200` with a :ref:`permission list <sec-api-access-datamodel-permissions-list>`
   as body.

   :status 200: No error

.. _sec-api-access-groups:

Groups
======

.. _sec-api-access-groups-list:

Get group list
--------------

.. http:get:: /api/access/groups

   Retrieves all groups registered in the system.

   Will return a :http:statuscode:`200` with a :ref:`group list <sec-api-access-datamodel-groups-list>`
   as body.

   Requires the ``SETTINGS`` permission.

   :status 200: No error

.. _sec-api-access-groups-add:

Add a new group
---------------

.. http:post:: /api/access/groups

   Adds a new group to the system.

   Expects a :ref:`group registration request <sec-api-access-datamodel-groups-addgrouprequest>` as request body.

   Will return a :ref:`group list response <sec-api-access-datamodel-groups-list>` on success.

   Requires the ``SETTINGS`` permission.

   :json key:         The group's identifier
   :json name:        The user's name
   :json description: A human readable description of the group
   :json permissions: The permissions to assign to the group
   :json subgroups:   Subgroups assigned to the group
   :json default:     Whether the group should be assigned to new users by default or not
   :status 200:       No error
   :status 400:       If any of the mandatory fields is missing or the request is otherwise
                      invalid
   :status 409:       A group with the provided key does already exist

.. _sec-api-access-groups-retrieve:

Retrieve a group
----------------

.. http:get:: /api/access/groups/(string:key)

   Retrieves an individual group record.

   Will return a :http:statuscode:`200` with a :ref:`group record <sec-api-access-datamodel-groups-list>`
   as body.

   Requires the ``SETTINGS`` permission.

   :status 200: No error

.. _sec-api-access-groups-modify:

Update a group
--------------

.. http:put:: /api/access/groups/(string:key)

   Updates an existing group.

   Expects a :ref:`group update request <sec-api-access-datamodel-groups-updategrouprequest>` as request body.

   Will return a :ref:`group list response <sec-api-access-datamodel-groups-list>` on success.

   Requires the ``SETTINGS`` permission.

   :json description: A human readable description of the group
   :json permissions: The permissions to assign to the group
   :json subgroups:   Subgroups assigned to the group
   :json default:     Whether the group should be assigned to new users by default or not
   :status 200:       No error
   :status 400:       If any of the mandatory fields is missing or the request is otherwise
                      invalid

.. _sec-api-access-groups-delete:

Delete a group
--------------

.. http:delete:: /api/access/groups/(string:key)

   Deletes a group.

   Will return a :ref:`group list response <sec-api-access-datamodel-groups-list>` on success.

   Requires the ``SETTINGS`` permission.

   :status 200:       No error

.. _sec-api-access-users:

Users
=====

.. _sec-api-access-users-list:

Retrieve a list of users
========================

.. http:get:: /api/access/users

   Retrieves a list of all registered users in OctoPrint.

   Will return a :http:statuscode:`200` with a :ref:`user list response <sec-api-access-datamodel-users-userlistresponse>`
   as body.

   Requires the ``SETTINGS`` permission.

   :status 200: No error

.. _sec-api-access-users-retrieve:

Retrieve a user
---------------

.. http:get:: /api/access/users/(string:username)

   Retrieves information about a user.

   Will return a :http:statuscode:`200` with a :ref:`user record <sec-api-datamodel-access>`
   as body.

   Requires either the ``SETTINGS`` permission or to be logged in as the user.

   :param username: Name of the user which to retrieve
   :status 200:     No error
   :status 404:     Unknown user

.. _sec-api-access-users-add:

Add a new user
--------------

.. http:post:: /api/access/users

   Adds a user to OctoPrint.

   Expects a :ref:`user registration request <sec-api-access-datamodel-users-adduserrequest>`
   as request body.

   Returns a list of registered users on success, see :ref:`Retrieve a list of users <sec-api-access-users-list>`.

   Requires the ``SETTINGS`` permission.

   :json name:     The user's name
   :json password: The user's password
   :json active:   Whether to activate the account (true) or not (false)
   :json admin:    Whether to give the account admin rights (true) or not (false)
   :status 200:    No error
   :status 400:    If any of the mandatory fields is missing or the request is otherwise
                   invalid
   :status 409:    A user with the provided name does already exist

.. _sec-api-access-users-modify:

Update a user
-------------

.. http:put:: /api/access/users/(string:username)

   Updates a user record.

   Expects a :ref:`user update request <sec-api-access-datamodel-users-updateuserrequest>`
   as request body.

   Returns a list of registered users on success, see :ref:`Retrieve a list of users <sec-api-access-users-list>`.

   Requires the ``SETTINGS`` permission.

   :param username: Name of the user to update
   :json admin:     Whether to mark the user as admin (true) or not (false), can be left out (no change)
   :json active:    Whether to mark the account as activated (true) or deactivated (false), can be left out (no change)
   :status 200:     No error
   :status 404:     Unknown user

.. _sec-api-access-users-delete:

Delete a user
-------------

.. http:delete:: /api/access/users/(string:username)

   Delete a user record.

   Returns a list of registered users on success, see :ref:`Retrieve a list of users <sec-api-access-users-list>`.

   Requires the ``SETTINGS`` permission.

   :param username: Name of the user to delete
   :status 200:     No error
   :status 404:     Unknown user

.. _sec-api-access-users-password:

Change a user's password
------------------------

.. http:put:: /api/access/users/(string:username)/password

   Changes the password of a user.

   Expects a JSON object with a property ``password`` containing the new password as
   request body. Without the ``SETTINGS`` permission, an additional property ``current``
   is also required to be set on the request body, containing the user's current password.

   Requires the ``SETTINGS`` permission or to be logged in as the user. Note that ``current``
   will be evaluated even in presence of the ``SETTINGS`` permission, if set.

   :param username: Name of the user to change the password for
   :json password:  The new password to set
   :json current:   The current password
   :status 200:     No error
   :status 400:     If the request doesn't contain a ``password`` property, doesn't
                    contain a ``current`` property even though required, or the request
                    is otherwise invalid
   :status 403:     No admin rights, not logged in as the user or a current password
                    mismatch
   :status 404:     The user is unknown

.. _sec-api-access-users-settings-get:

Get a user's settings
---------------------

.. http:get:: /api/access/users/(string:username)/settings

   Retrieves a user's settings.

   Will return a :http:statuscode:`200` with a JSON object representing the user's
   personal settings (if any) as body.

   Requires the ``SETTINGS`` permission or to be logged in as the user.

   :param username: Name of the user to retrieve the settings for
   :status 200:     No error
   :status 403:     No admin rights and not logged in as the user
   :status 404:     The user is unknown

.. _sec-api-access-users-settings-set:

Update a user's settings
------------------------

.. http:patch:: /api/access/users/(string:username)/settings

   Updates a user's settings.

   Expects a new settings JSON object to merge with the current settings as
   request body.

   Requires the ``SETTINGS`` permission or to be logged in as the user.

   :param username: Name of the user to retrieve the settings for
   :status 204:     No error
   :status 403:     No admin rights and not logged in as the user
   :status 404:     The user is unknown

.. _sec-api-access-users-apikey-generate:

Regenerate a user's api key
---------------------------

.. http:post:: /api/access/users/(string:username)/apikey

   Generates a new API key for the user.

   Does not expect a body. Will return the generated API key as ``apikey``
   property in the JSON object contained in the response body.

   Requires the ``SETTINGS`` permission or to be logged in as the user.

   :param username: Name of the user to retrieve the settings for
   :status 200:     No error
   :status 403:     No admin rights and not logged in as the user
   :status 404:     The user is unknown

.. _sec-api-access-users-apikey-delete:

Delete a user's api key
-----------------------

.. http:delete:: /api/access/users/(string:username)/apikey

   Deletes a user's personal API key.

   Requires the ``SETTINGS`` permission or to be logged in as the user.

   :param username: Name of the user to retrieve the settings for
   :status 204:     No error
   :status 403:     No admin rights and not logged in as the user
   :status 404:     The user is unknown

.. _sec-api-access-datamodel:

Data model
==========

.. _sec-api-access-datamodel-permissions:

Permissions
-----------

.. _sec-api-access-datamodel-permissions-list:

Permission list response
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``permissions``
     - 0..n
     - List of :ref:`permission records <sec-api-datamodel-access-permissions>`
     - The list of permissions


.. _sec-api-access-datamodel-groups:

Groups
------

.. _sec-api-access-datamodel-groups-list:

Group list response
~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``groups``
     - 0..n
     - List of :ref:`group records <sec-api-datamodel-access-groups>`
     - The list of groups

.. _sec-api-access-datamodel-groups-addgrouprequest:

Group registration request
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``key``
     - 1
     - string
     - The group's identifier
   * - ``name``
     - 1
     - string
     - The group's name
   * - ``description``
     - 0..1
     - string
     - The group's description. Set to empty if not provided.
   * - ``permissions``
     - 1..n
     - List of string
     - A list of identifier's of permissions to assign to the group
   * - ``subgroups``
     - 0..n
     - List of string
     - A list of identifier's of groups to assign to the group as subgroups
   * - ``default``
     - 0..1
     - boolean
     - Whether to assign the group to new users by default (true) or not (false, default value)

.. _sec-api-access-datamodel-groups-updategrouprequest:

Group update request
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``description``
     - 0..1
     - string
     - The group's description. Set to empty if not provided.
   * - ``permissions``
     - 1..n
     - List of string
     - A list of identifier's of permissions to assign to the group
   * - ``subgroups``
     - 0..n
     - List of string
     - A list of identifier's of groups to assign to the group as subgroups
   * - ``default``
     - 0..1
     - boolean
     - Whether to assign the group to new users by default (true) or not (false, default value)


.. _sec-api-access-datamodel-users:

Users
-----

.. _sec-api-access-datamodel-users-userlistresponse:

User list response
~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``users``
     - 0..n
     - List of :ref:`user records <sec-api-datamodel-access-users>`
     - The list of users

.. _sec-api-access-datamodel-users-adduserrequest:

User registration request
~~~~~~~~~~~~~~~~~~~~~~~~~

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
   * - ``groups``
     - 0..n
     - List of string
     - A list of identifiers of groups to assign to the user
   * - ``permissions``
     - 0..n
     - List of string
     - A list of identifiers of permissions to assign to the user

.. _sec-api-access-datamodel-users-updateuserrequest:

User update request
~~~~~~~~~~~~~~~~~~~

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
   * - ``groups``
     - 0..n
     - List of string
     - A list of identifiers of groups to assign to the user
   * - ``permissions``
     - 0..n
     - List of string
     - A list of identifiers of permissions to assign to the user
