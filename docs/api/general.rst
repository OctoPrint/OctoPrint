.. _sec-api-general:

*******************
General information
*******************

.. _sec-api-general-authorization:

Authorization
=============

OctoPrint's API expects an API key to be supplied with each request. This API key can be either the globally
configured one or a user specific one if "Access Control" is enabled. Users are able to generate and revoke their
custom API key via the "Change password" dialog.

The API key must be supplied in the custom HTTP header ``X-Api-Key``, e.g.

.. sourcecode:: http

   GET /api/files HTTP/1.1
   Host: example.com
   X-Api-Key: abcdef...

If it is missing, OctoPrint will directly return a response with status :http:statuscode:`401`. If it is included in
the request but invalid, OctoPrint will directly return a response with status :http:statuscode:`403`.

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

.. _sec-api-general-contenttype:

Content Type
============

If not otherwise stated OctoPrint's API expects request bodies and issues response bodies as ``Content-Type: application/json``.

.. _sec-api-general-encoding:

Encoding
========

OctoPrint uses UTF-8 as charset.