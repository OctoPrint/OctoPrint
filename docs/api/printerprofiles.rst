.. _sec-api-printerprofiles:

**************************
Printer profile operations
**************************

.. contents::

OctoPrint allows the management of Printer profiles that define a printer's physical properties (such as print volume,
whether a heated bed is available, maximum speeds on its axes etc). The data stored within these profiles is used
for both slicing and gcode visualization.

.. _sec-api-printerprofiles-retrieve:

Retrieve all printer profiles
=============================

.. http:get:: /api/printerprofiles

   Retrieves an object representing all configured printer profiles.

   Returns a :http:statuscode:`200` with a :ref:`profile list <sec-api-printerprofiles-datamodel-profilelist>`.

   Requires the ``CONNECTION`` permission.

   **Example**

   .. sourcecode:: http

      GET /api/printerprofiles HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "profiles": {
          "_default": {
            "id": "_default",
            "name": "Default",
            "color": "default",
            "model": "Generic RepRap Printer",
            "default": true,
            "current": true,
            "resource": "http://example.com/api/printerprofiles/_default",
            "volume": {
              "formFactor": "rectangular",
              "origin": "lowerleft",
              "width": 200,
              "depth": 200,
              "height": 200
            },
            "heatedBed": true,
            "heatedChamber": false,
            "axes": {
              "x": {
                "speed": 6000,
                "inverted": false
              },
              "y": {
                "speed": 6000,
                "inverted": false
              },
              "z": {
                "speed": 200,
                "inverted": false
              },
              "e": {
                "speed": 300,
                "inverted": false
              }
            },
            "extruder": {
              "count": 1,
              "offsets": [
                {"x": 0.0, "y": 0.0}
              ]
            }
          },
          "my_profile": {
            "id": "my_profile",
            "name": "My Profile",
            "color": "default",
            "model": "My Custom Printer",
            "default": false,
            "current": false,
            "resource": "http://example.com/api/printerprofiles/my_profile",
            "volume": {
              "formFactor": "rectangular",
              "origin": "lowerleft",
              "width": 200,
              "depth": 200,
              "height": 200
            },
            "heatedBed": true,
            "heatedChamber": true,
            "axes": {
              "x": {
                "speed": 6000,
                "inverted": false
              },
              "y": {
                "speed": 6000,
                "inverted": false
              },
              "z": {
                "speed": 200,
                "inverted": false
              },
              "e": {
                "speed": 300,
                "inverted": false
              }
            },
            "extruder": {
              "count": 1,
              "offsets": [
                {"x": 0.0, "y": 0.0}
              ]
            }
          },
        }
      }


.. _sec-api-printerprofiles-get:

Retrieve a single printer profile
=================================

.. http:get:: /api/printerprofiles/(string:identifier)

   Retrieves an existing single printer profile.

   Returns a :http:statuscode:`200` with a :ref:`profile <sec-api-printerprofiles-datamodel-profile>`.

   Requires the ``CONNECTION`` permission.

   :statuscode 200: No error
   :statuscode 404: The profile does not exist

.. _sec-api-printerprofiles-add:

Add a new printer profile
=========================

.. http:post:: /api/printerprofiles

   Adds a new printer profile based on either the current default profile
   or the profile identified in ``basedOn``.

   The provided profile data will be merged with the profile data from the
   base profile.

   If a profile with the same ``id`` does already exist, a :http:statuscode:`400`
   will be returned.

   Returns a :http:statuscode:`200` with the saved profile as property ``profile``
   in the JSON body upon success.

   Requires the ``SETTINGS`` permission.

   **Example 1**

   Creating a new profile ``some_profile`` based on the current default profile.

   .. sourcecode:: http

      POST /api/printerprofiles HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...
      Content-Type: application/json

      {
        "profile": {
          "id": "some_profile",
          "name": "Some profile",
          "model": "Some cool model"
        }
      }

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "profile": {
          "id": "some_profile",
          "name": "Some profile",
          "color": "default",
          "model": "Some cool model",
          "default": false,
          "current": false,
          "resource": "http://example.com/api/printerprofiles/some_profile",
          "volume": {
            "formFactor": "rectangular",
            "origin": "lowerleft",
            "width": 200,
            "depth": 200,
            "height": 200
          },
          "heatedBed": true,
          "heatedChamber": false,
          "axes": {
            "x": {
              "speed": 6000,
              "inverted": false
            },
            "y": {
              "speed": 6000,
              "inverted": false
            },
            "z": {
              "speed": 200,
              "inverted": false
            },
            "e": {
              "speed": 300,
              "inverted": false
            }
          },
          "extruder": {
            "count": 1,
            "offsets": [
              {"x": 0.0, "y": 0.0}
            ]
          }
        }
      }

   **Example 2**

   Creating a new profile ``some_other_profile`` based on existing profile
   ``some_profile``.

   .. sourcecode:: http

      POST /api/printerprofiles HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...
      Content-Type: application/json

      {
        "profile": {
          "id": "some_other_profile",
          "name": "Some other profile",
          "heatedBed": false,
          "volume": {
            "formFactor": "circular",
            "origin": "center",
            "width": "150",
            "height": "300"
          },
          "extruder": {
            "count": 2,
            "offsets": [
              {"x": 0.0, "y": 0.0},
              {"x": 21.6, "y": 0.0}
            ]
          }
        },
        "basedOn": "some_profile"
      }

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "profile": {
          "id": "some_other_profile",
          "name": "Some other profile",
          "color": "default",
          "model": "Some cool model",
          "default": false,
          "current": false,
          "resource": "http://example.com/api/printerprofiles/some_other_profile",
          "volume": {
            "formFactor": "circular",
            "origin": "center",
            "width": 150,
            "depth": 150,
            "height": 300
          },
          "heatedBed": false,
          "heatedChamber": false,
          "axes": {
            "x": {
              "speed": 6000,
              "inverted": false
            },
            "y": {
              "speed": 6000,
              "inverted": false
            },
            "z": {
              "speed": 200,
              "inverted": false
            },
            "e": {
              "speed": 300,
              "inverted": false
            }
          },
          "extruder": {
            "count": 2,
            "offsets": [
              {"x": 0.0, "y": 0.0},
              {"x": 21.6, "y": 0.0}
            ]
          }
        }
      }

.. _sec-api-printerporfiles-update:

Update an existing printer profile
==================================

.. http:patch:: /api/printerprofiles/(string:profile)

   Updates an existing printer profile by its ``profile`` identifier.

   The updated (potentially partial) profile is expected in the request's body as part of
   an :ref:`Add or update request <sec-api-printerprofiles-datamodel-update>`.

   Returns a :http:statuscode:`200` with the saved profile as property ``profile``
   in the JSON body upon success.

   Requires the ``SETTINGS`` permission.

   **Example**

   .. sourcecode:: http

      PATCH /api/printerprofiles/some_profile HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...
      Content-Type: application/json

      {
        "profile": {
          "name": "Some edited profile",
          "volume": {
            "depth": "300"
          }
        }
      }

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "profile": {
          "id": "some_profile",
          "name": "Some edited profile",
          "color": "default",
          "model": "Some cool model",
          "default": false,
          "current": false,
          "resource": "http://example.com/api/printerprofiles/some_profile",
          "volume": {
            "formFactor": "rectangular",
            "origin": "lowerleft",
            "width": 200,
            "depth": 300,
            "height": 200
          },
          "heatedBed": true,
          "heatedChamber": false,
          "axes": {
            "x": {
              "speed": 6000,
              "inverted": false
            },
            "y": {
              "speed": 6000,
              "inverted": false
            },
            "z": {
              "speed": 200,
              "inverted": false
            },
            "e": {
              "speed": 300,
              "inverted": false
            }
          },
          "extruder": {
            "count": 2,
            "offsets": [
              {"x": 0.0, "y": 0.0},
              {"x": 21.6, "y": 0.0}
            ]
          }
        }
      }


.. _sec-api-printerprofiles-delete:

Remove an existing printer profile
==================================

.. http:delete:: /api/printerprofiles/(string:profile)

   Deletes an existing printer profile by its ``profile`` identifier.

   If the profile to be deleted is the currently selected profile, a :http:statuscode:`409` will be
   returned.

   Returns a :http:statuscode:`204` an empty body upon success.

   Requires the ``SETTINGS`` permission.

   **Example**

   .. sourcecode:: http

      DELETE /api/printerprofiles/some_profile HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...

   .. sourcecode:: http

      HTTP/1.1 204 No Content


.. _sec-api-printerprofiles-datamodel:

Data model
==========

.. _sec-api-printerprofiles-datamodel-profilelist:

Profile list
------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``profiles``
     - 1
     - Object
     - Collection of all printer profiles available in the system
   * - ``profiles.<profile id>``
     - 0..1
     - :ref:`Profile <sec-api-printerprofiles-datamodel-profile>`
     - Information about a profile stored in the system.

.. _sec-api-printerprofiles-datamodel-update:

Add or update request
---------------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``profiles``
     - 1
     - :ref:`Profile <sec-api-printerprofiles-datamodel-profile>`
     - Information about the profile being added/updated. Only the values to be overwritten need to be supplied.
       Unset fields will be taken from the base profile, which for add requests will be the
       current default profile unless a different base is defined in the ``basedOn`` property
       of the request. For update requests the current version of the profile to be updated will
       be used as base.
   * - ``basedOn``
     - 0..1
     - ``string``
     - Only for add requests, ignored on updates: The identifier of the profile to base the
       new profile on, if different than the current default profile.

.. _sec-api-printerprofiles-datamodel-profile:

Profile
-------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``id``
     - 0..1
     - ``string``
     - Identifier of the profile. Will always be
       returned in responses, is mandatory in add requests but
       can be left out of update requests.
   * - ``name``
     - 0..1
     - ``string``
     - Display name of the profile. Will always be
       returned in responses, is mandatory in add requests but
       can be left out of update requests.
   * - ``color``
     - 0..1
     - ``string``
     - The color to associate with this profile (used in the UI's title bar). Valid values are "default", "red", "orange",
       "yellow", "green", "blue", "black". Will always be
       returned in responses but can be left out of save/update requests.
   * - ``model``
     - 0..1
     - ``string``
     - Printer model of the profile. Will always be
       returned in responses but can be left out of save/update requests.
   * - ``default``
     - 0..1
     - ``boolean``
     - Whether this is the default profile to be used with new connections (``true``) or not (``false``). Will always be
       returned in responses but can be left out of save/update requests.
   * - ``current``
     - 0..1
     - ``boolean``
     - Whether this is the profile currently active. Will always be returned in responses but ignored in save/update
       requests.
   * - ``resource``
     - 0..1
     - ``URL``
     - Resource URL of the profile, will always be returned in responses but can be left out of save/update requests.
   * - ``volume``
     - 0..1
     - Object
     - The print volume, will always be returned in responses but can be left out of save/update requests.
   * - ``volume.formFactor``
     - 0..1
     - ``string``
     - The form factor of the printer's bed, valid values are "rectangular" and "circular"
   * - ``volume.origin``
     - 0..1
     - ``string``
     - The location of the origin on the printer's bed, valid values are "lowerleft" and "center"
   * - ``volume.width``
     - 0..1
     - ``float``
     - The width of the print volume. For circular beds, the diameter of the bed.
   * - ``volume.depth``
     - 0..1
     - ``float``
     - The depth of the print volume. For circular beds, this is the diameter of the bed and will be forced to be the same
       as ``volume.width`` upon saving.
   * - ``volume.height``
     - 0..1
     - ``float``
     - The height of the print volume
   * - ``volume.custom_box``
     - 0..1
     - ``boolean`` or ``object``
     - If the printer has a custom bounding box where the print head can be safely moved to, exceeding the defined print
       volume, that bounding box will be defined here. Otherwise (safe area == print volume) this value will be ``false``.
   * - ``volume.custom_box.min_x``
     - 0..1
     - ``float``
     - Minimum X coordinate defining the safe custom bounding box. Smaller value than the minimum X coordinate of the
       print volume.
   * - ``volume.custom_box.max_x``
     - 0..1
     - ``float``
     - Maximum X coordinate defining the safe custom bounding box. Larger value than the maximum X coordinate of the
       print volume.
   * - ``volume.custom_box.min_y``
     - 0..1
     - ``float``
     - Minimum Y coordinate defining the safe custom bounding box. Smaller value than the minimum Y coordinate of the
       print volume.
   * - ``volume.custom_box.max_y``
     - 0..1
     - ``float``
     - Maximum Y coordinate defining the safe custom bounding box. Larger value than the maximum Y coordinate of the
       print volume.
   * - ``volume.custom_box.min_z``
     - 0..1
     - ``float``
     - Minimum Z coordinate defining the safe custom bounding box. Smaller value than the minimum Z coordinate of the
       print volume.
   * - ``volume.custom_box.max_z``
     - 0..1
     - ``float``
     - Maximum Z coordinate defining the safe custom bounding box. Larger value than the maximum Z coordinate of the
       print volume.
   * - ``heatedBed``
     - 0..1
     - ``boolean``
     - Whether the printer has a heated bed (``true``) or not (``false``)
   * - ``heatedChamber``
     - 0..1
     - ``boolean``
     - Whether the printer has a heated chamber (``true``) or not (``false``)
   * - ``axes``
     - 0..1
     - Object
     - Description of the printer's axes properties, one entry each for ``x``, ``y``, ``z`` and ``e`` holding maximum speed
       and whether this axis is inverted or not.
   * - ``axes.{axis}.speed``
     - 0..1
     - ``int``
     - Maximum speed of the axis in mm/min.
   * - ``axes.{axis}.inverted``
     - 0..1
     - ``boolean``
     - Whether the axis is inverted or not.
   * - ``extruder``
     - 0..1
     - Object
     - Information about the printer's extruders
   * - ``extruder.nozzleDiameter``
     - 0..1
     - ``float``
     - The diameter of the printer's nozzle(s) in mm.
   * - ``extruder.sharedNozzle``
     - ``boolean``
     - Whether there's only one nozzle shared among all extruders (true) or one nozzle per extruder (false).
   * - ``extruder.defaultExtrusionLength``
     - ``int``
     - Default extrusion length used in Control tab on initial page load in mm.
   * - ``extruder.count``
     - 0..1
     - ``int``
     - Count of extruders on the printer (defaults to 1)
   * - ``extruder.offsets``
     - 0..1
     - Array of ``float`` tuples
     - Tuple of (x, y) values describing the offsets of the other extruders relative to the first extruder. E.g. for a
       printer with two extruders, if the second extruder is offset by 20mm in the X and 25mm in the Y direction, this
       array will read ``[ [0.0, 0.0], [20.0, 25.0] ]``

