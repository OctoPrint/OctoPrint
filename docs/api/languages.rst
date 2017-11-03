.. _sec-api-languages:

*********
Languages
*********

.. note::

   All language pack management operations require admin rights.

.. contents::

.. _sec-api-languages-list:

Retrieve installed language packs
=================================

.. http:get:: /api/languages

   Retrieves a list of installed language packs.

   The response body will contain a :ref:`list response <sec-api-languages-datamodel-listresponse>`.

   **Example**

   .. sourcecode:: http

      GET /api/languages HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "language_packs": {
          "_core": {
            "identifier": "_core",
            "name": "Core",
            "languages": []
          },
          "some_plugin": {
            "identifier": "some_plugin",
            "name": "Some Plugin",
            "languages": [
              {
                "locale": "de",
                "locale_display": "Deutsch",
                "locale_english": "German",
                "last_update": 1474574597,
                "author": "Gina Häußge"
              },
              {
                "locale": "it",
                "locale_display": "Italiano",
                "locale_english": "Italian",
                "last_update": 1470859680,
                "author": "The italian Transifex Team"
              }
            ]
        }
      }

   :statuscode 200: No error

.. _sec-api-languages-upload:

Upload a language pack
======================

.. http:post:: /api/languages

   Uploads a new language pack to OctoPrint.

   Other than most of the other requests on OctoPrint's API which are expected as JSON, this request is expected as
   ``Content-Type: multipart/form-data`` due to the included file upload.

   To upload a file, the request body must contain the ``file`` form field with the
   contents and file name of the file to upload.

   Only files with one of the extensions ``zip``, ``tar.gz``, ``tgz`` or ``tar`` will be
   processed, for other file extensions a :http:statuscode:`400` will be returned.

   Will return a list of installed language packs upon completion, as described in
   :ref:`Retrieve installed language packs <sec-api-languages-list>`.

   :form file:      The language pack file to upload
   :statuscode 200: The file was uploaded successfully

.. _sec-api-languages-delete:

Delete a language pack
======================

.. http:delete:: /api/languages/(string:locale)/(string:pack)

   Deletes the language pack ``pack`` for locale ``locale``. Can be either
   the ``_core`` pack (containing translations for core OctoPrint) or
   the language pack for a plugin specified by the plugin identifier.

   Returns a list of installed language packs, as described in
   :ref:`Retrieve installed language packs <sec-api-languages-list>`.

   **Example**

   .. sourcecode:: http

      DELETE /api/languages/it/some_plugin HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "language_packs": {
          "_core": {
            "identifier": "_core",
            "name": "Core",
            "languages": []
          },
          "some_plugin": {
            "identifier": "some_plugin",
            "name": "Some Plugin",
            "languages": [
              {
                "locale": "de",
                "locale_display": "Deutsch",
                "locale_english": "German",
                "last_update": 1474574597,
                "author": "Gina Häußge"
              }
            ]
        }
      }

   :param locale:   The locale for which to delete the language pack
   :param pack:     The language pack to delete
   :statuscode 200: The language pack was deleted

.. _sec-api-languages-datamodel:

Data model
==========

.. _sec-api-languages-datamodel-listresponse:

List response
-------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``language_packs``
     - 0..*
     - Map of :ref:`component lists <sec-api-languages-datamodel-componentlist>`
     - Map of component lists, indexed by the component's identifier

.. _sec-api-languages-datamodel-componentlist:

Component list
--------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``identifier``
     - 1
     - string
     - The plugin's identifier, ``_core`` for core OctoPrint, the plugin's identifier for plugins
   * - ``display``
     - 1
     - string
     - Displayable name of the component, ``Core`` for core OctoPrint, the plugin's name for plugins
   * - ``languages``
     - 0..*
     - List of :ref:`language pack meta data <sec-api-languages-datamodel-packmeta>`
     - Language packs for the component

.. _sec-api-languages-datamodel-packmeta:

Language pack metadata
----------------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``locale``
     - 1
     - string
     - Locale of the language pack
   * - ``locale_display``
     - 1
     - string
     - Displayable name of the locale
   * - ``locale_english``
     - 1
     - string
     - English representation of the locale
   * - ``last_update``
     - 0..1
     - int
     - Timestamp of the last update of the language pack
   * - ``author``
     - 0..1
     - string
     - Author of the language pack
