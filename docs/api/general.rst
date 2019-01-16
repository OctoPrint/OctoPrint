.. _sec-api-general:

*******************
General information
*******************

.. contents::

.. _sec-api-general-authorization:

Authorization
=============

OctoPrint's API expects an API key to be supplied with each request. This API key can be either the globally
configured one, a user specific one if "Access Control" is enabled or an app and user specific one as generated
by the authorization workflow implemented by the bundled :ref:`Application Keys Plugin <sec-bundledplugins-appkeys>` (since 1.3.10).

Clients are advised to implement the :ref:`Application Keys Plugin workflow <sec-bundledplugins-appkeys-workflow>` first and
fallback on directing the user to manually supply the the user specific API key. The global key should rarely be used.

The API key must be supplied in the custom HTTP header ``X-Api-Key``, e.g.

.. sourcecode:: http

   GET /api/files HTTP/1.1
   Host: example.com
   X-Api-Key: abcdef...

If it is missing or included but invalid, OctoPrint will directly return a response with status :http:statuscode:`403`.

For testing purposes it is also possible to supply the API key via a query parameter ``apikey``, e.g.

.. sourcecode:: http

   GET /api/files?apikey=abcdef... HTTP/1.1
   Host: example.com

Please be advised that clients should use the header field variant if at all possible.

.. _fig-api-general-globalapikey:
.. figure:: ../images/settings-global-api-key.png
   :align: center
   :alt: Global API key in the API settings

   The global API key can be found in the "API" settings

.. _fig-api-general-userapikey:
.. figure:: ../images/settings-user-api-key.png
   :align: center
   :alt: User specific API key location in user list

   The user list in the "Access Control" settings shows the API key for users (if available)

.. _fig-api-general-changepassword:
.. figure:: ../images/change-password-api-key.png
   :align: center
   :alt: API key options in "Change password" dialog

   The API key options in the "Change password" dialog. Users can generate and revoke their custom API key here.

.. note::
   OctoPrint's web interface uses a custom API key that is freshly generated on every server start. This key is not
   intended to be used by any other client and would not be very useful in any case, since it basically represents
   a completely anonymous client.

.. _sec-api-general-contenttype:

Content Type
============

If not otherwise stated, OctoPrint's API expects request bodies and issues response bodies as ``Content-Type: application/json``.

.. _sec-api-general-encoding:

Encoding
========

OctoPrint uses UTF-8 as charset.

That also includes headers in ``multipart/form-data`` requests, in order to allow the full UTF-8 range of characters
for uploaded filenames. If a ``multipart/form-data`` sub header cannot be decoded as UTF-8, OctoPrint will also attempt
to decode it as ISO-8859-1.

Additionally, OctoPrint supports replacing the ``filename`` field in the ``Content-Disposition`` header of a
multipart field with a ``filename*`` field following `RFC 5987, Section 3.2 <https://tools.ietf.org/html/rfc5987#section-3.2>`_,
which allows defining the charset used for encoding the filename. If both ``filename`` and ``filename*`` fields are
present, following the recommendation of the RFC ``filename*`` will be used.

For an example on how to send a request utilizing RFC 5987 for the ``filename*`` attribute, see the second example
in :ref:`Upload file <sec-api-fileops-uploadfile>`.

.. _sec-api-general-crossorigin:

Cross-origin requests
=====================

To make use of the OctoPrint API from websites other than the OctoPrint web interface,
cross-origin resource sharing (`CORS <http://en.wikipedia.org/wiki/Cross-origin_resource_sharing>`_) must be enabled.
This is the case even when the website in question is served from a different port on the same machine and on localhost.

To enable this feature, set the ``allowCrossOrigin`` key of the ``api`` section in ``config.yml`` to ``true`` or
check the corresponding checkbox in the API settings dialog.

.. code-block:: yaml

   api:
     enabled: true
     key: ...
     allowCrossOrigin: true

.. _fig-api-general-apicors:
.. figure:: ../images/settings-api-cors.png
   :align: center
   :alt: CORS configuration in the API settings

   Support for CORS can be enabled in the "API" settings

.. note::
   This means any browser page can send requests to the OctoPrint API. Authorization is still required however.

If CORS is not enabled you will get errors like the following::

   XMLHttpRequest cannot load http://localhost:8081/api/files. No 'Access-Control-Allow-Origin'
   header is present on the requested resource.

.. _sec-api-general-login:

Login
=====

.. http:post:: /api/login

   Creates a login session or retrieves information about the currently existing session ("passive login").

   Can be used in one of two ways: to login a user via username and password and create a persistent session (usually
   from a UI in the browser), or to retrieve information about the active user (from an existing session or an API key)
   via the ``passive`` flag.

   Will return a :http:statuscode:`200` with a :ref:`login response <sec-api-general-datamodel-login>` on successful
   login, whether active or passive. The active (username/password) login may also return a :http:statuscode:`401` in
   case of a username/password mismatch or unknown user and a :http:statuscode:`403` in case of a deactivated account.

   :json passive:  If present, performs a passive login only, returning information about the current user that's
                   active either through an existing session or the used API key
   :json user:     (active login only) Username
   :json pass:     (active login only) Password
   :json remember: (active login only) Whether to set a "remember me" cookie on the session
   :status 200:    Successful login
   :status 401:    Username/password mismatch or unknown user
   :status 403:    Deactivated account

.. _sec-api-general-logout:

Logout
======

.. http:post:: /api/logout

   Ends the current login session of the current user.

   Only makes sense in the context of browser based workflows.

   Will return a :http:statuscode:`204`.

   :status 204: No error

.. _sec-api-general-datamodel:

Data model
==========

.. _sec-api-general-datamodel-login:

Login response
--------------

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
     - the user's name/id
   * - ``active``
     - 1
     - boolean
     - Whether the user's account is active or not
   * - ``admin``
     - 1
     - boolean
     - Whether the user has admin rights or not
   * - ``user``
     - 1
     - boolean
     - Whether the user has user rights or not (always ``true``)
   * - ``apikey``
     - 1
     - string or None
     - The user's API key, if set
   * - ``settings``
     - 1
     - dict
     - The user's settings, if any
   * - ``session``
     - 1
     - string
     - The session key, can be used to authenticate with the ``auth`` message on the :ref:`push API <sec-api-push>`.
   * - ``_is_external_client``
     - 1
     - boolean
     - Whether the client that made the request got detected as external from the local network or not.
