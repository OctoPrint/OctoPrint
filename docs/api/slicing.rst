.. _sec-api-slicing:

*******
Slicing
*******

.. warning::

   The interface documented here is the status quo that might be changed while the interfaces are streamlined for
   a more general consumption. If you happen to want to develop against it, you should drop me an email to make sure I can give you a heads-up when
   something changes.

.. contents::

The Slicing API on one hand offers methods for managing slicing profiles stored within OctoPrint, on the other hand
it will be extended in the future to also allow for multi extruder slicing (which currently is not possible with the
``slice`` command of the :ref:`File operations API <sec-api-fileops-filecommand>` and other things.

.. _sec-api-slicing-listall:

List All Slicers and Slicing Profiles
=====================================

.. http:get:: /api/slicing

   Returns a list of all available slicing profiles for all registered slicers in the system.

   Returns a :http:statuscode:`200` response with a :ref:`Slicer list <sec-api-slicing-datamodel-slicerlist>`
   as the body upon successful completion.

   **Example**

   .. sourcecode:: http

      GET /api/slicing HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "cura": {
          "key": "cura",
          "displayName": "CuraEngine",
          "default": true,
          "profiles": {
            "high_quality": {
              "key": "high_quality",
              "displayName": "High Quality",
              "default": false,
              "resource": "http://example.com/api/slicing/cura/profiles/high_quality"
            },
            "medium_quality": {
              "key": "medium_quality",
              "displayName": "Medium Quality",
              "default": true,
              "resource": "http://example.com/api/slicing/cura/profiles/medium_quality"
            }
          }
        }
      }

   :statuscode 200: No error

.. _sec-api-slicing-list:

List Slicing Profiles of a Specific Slicer
==========================================

.. http:get:: /api/slicing/(string:slicer)/profiles

   Returns a list of all available slicing profiles for the requested slicer.

   Returns a :http:statuscode:`200` response with a :ref:`Profile list <sec-api-slicing-datamodel-profilelist>`
   as the body upon successful completion.

   **Example**

   .. sourcecode:: http

      GET /api/slicing/cura/profiles HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "high_quality": {
          "key": "high_quality",
          "displayName": "High Quality",
          "default": false,
          "resource": "http://example.com/api/slicing/cura/profiles/high_quality"
        },
        "medium_quality": {
          "key": "medium_quality",
          "displayName": "Medium Quality",
          "default": true,
          "resource": "http://example.com/api/slicing/cura/profiles/medium_quality"
        }
      }

   :param slicer:   The identifying key of the slicer for which to list the available profiles.
   :statuscode 200: No error
   :statuscode 404: If the ``slicer`` was unknown to the system or not yet configured.

.. _sec-api-slicing-listspecific:

Retrieve Specific Profile
=========================

.. http:get:: /api/slicing/(string:slicer)/profiles/(string:key)

   Retrieves the specified profile from the system.

   Returns a :http:statuscode:`200` response with a :ref:`full Profile <sec-api-slicing-datamodel-profile>`
   as the body upon successful completion.

   **Example**

   .. sourcecode:: http

      GET /api/slicing/cura/profiles/quick_test HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "displayName": "Just a test",
        "description": "This is just a test",
        "resource": "http://example.com/api/slicing/cura/profiles/quick_test",
        "data": {
          "bottom_layer_speed": 20.0,
          "bottom_thickness": 0.3,
          "brim_line_count": 20,
          "cool_head_lift": false,
          "cool_min_feedrate": 10.0,
          "cool_min_layer_time": 5.0
        }
      }

   :param slicer:   The identifying key of the slicer for which to list the available profiles.
   :param name:     The identifying key of the profile to retrieve
   :statuscode 200: No error
   :statuscode 404: If the ``slicer`` or the profile ``key`` was unknown to the system.

.. _sec-api-slicing-add:

Add Slicing Profile
===================

.. http:put:: /api/slicing/(string:slicer)/profiles/(string:key)

   Adds a new slicing profile for the given ``slicer`` to the system. If the profile identified by ``key`` already exists,
   it will be overwritten.

   Expects a :ref:`Profile <sec-api-slicing-datamodel-profile>` as body.

   Returns a :http:statuscode:`201` and an :ref:`abridged Profile <sec-api-slicing-datamodel-profile>` in the body
   upon successful completion.

   Requires admin rights.

   **Example**

   .. sourcecode:: http

      PUT /api/slicing/cura/profiles/quick_test HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...
      Content-Type: application/json

      {
        "displayName": "Just a test",
        "description": "This is just a test to show how to create a cura profile with a different layer height and skirt count",
        "data": {
          "layer_height": 0.2,
          "skirt_line_count": 3
        }
      }


   .. sourcecode:: http

      HTTP/1.1 201 Created
      Content-Type: application/json
      Location: http://example.com/api/slicing/cura/profiles/quick_test

      {
        "displayName": "Just a test",
        "description": "This is just a test to show how to create a cura profile with a different layer height and skirt count",
        "resource": "http://example.com/api/slicing/cura/profiles/quick_test"
      }

   :param slicer:   The identifying key of the slicer for which to add the profile
   :param key:      The identifying key of the new profile
   :statuscode 201: No error
   :statuscode 404: If the ``slicer`` was unknown to the system.

.. _sec-api-slicing-delete:

Delete Slicing Profile
======================

.. http:delete:: /api/slicing/(string:slicer)/profiles/(string:key)

   Delete the slicing profile identified by ``key`` for the slicer ``slicer``. If the profile doesn't exist, the
   request will succeed anyway.

   Requires admin rights.

   :param slicer:   The identifying key of the slicer for which to delete the profile
   :param key:      The identifying key of the profile to delete
   :statuscode 204: No error
   :statuscode 404: If the ``slicer`` was unknown to the system.

.. _sec-api-slicing-datamodel:

Data model
==========

.. _sec-api-slicing-datamodel-slicerlist:

Slicer list
-----------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``<slicer key>``
     - 0..*
     - :ref:`Slicer <sec-api-slicing-datamodel-slicer>`
     - Information about a slicer registered in the system, incl. stored profiles without ``data``.

.. _sec-api-slicing-datamodel-slicer:

Slicer
------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``key``
     - 1
     - ``string``
     - Identifier of the slicer
   * - ``displayName``
     - 1
     - ``string``
     - Display name of the slicer
   * - ``sameDevice``
     - 1
     - ``boolean``
     - Whether the slicer runs on the same device as OctoPrint (``true``) and hence can't be used while printing,
       or not (``false``)
   * - ``default``
     - 1
     - ``boolean``
     - Whether the slicer is the default slicer to use (``true``) or not (``false``).
   * - ``profiles``
     - 0..*
     - :ref:`Profile list <sec-api-slicing-datamodel-profilelist>`
     - Slicing profiles available for this slicer, mapped by their ``key``

.. _sec-api-slicing-datamodel-profilelist:

Profile list
------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``<profile key>``
     - 0..1
     - :ref:`Profile <sec-api-slicing-datamodel-profile>`
     - Information about a profile stored in the system, ``data`` field will be left out.

.. _sec-api-slicing-datamodel-profile:

Profile
-------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``key``
     - 1
     - ``string``
     - Identifier of the profile
   * - ``displayName``
     - 0..1
     - ``string``
     - Display name of the profile
   * - ``description``
     - 0..1
     - ``string``
     - Description of the profile
   * - ``default``
     - 0..1
     - ``boolean``
     - Whether this is the default profile to be used with this slicer (``true``) or not (``false``). Will always be
       returned in responses but can be left out of save/update requests.
   * - ``resource``
     - 0..1
     - ``URL``
     - Resource URL of the profile, will always be returned in responses but can be left out of save/update requests.
   * - ``data``
     - 0..1
     - Object
     - The actual profile data, including any default values if the profile was retrieved from the server. May contain
       only the keys differing from the defaults when saving/updating a profile. The keys to be found in here a slicer
       specific. Will be left out for list responses.

