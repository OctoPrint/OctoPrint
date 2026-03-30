.. _sec-api-fileops:

***************
File operations
***************

.. versionchanged:: 2.0.0

   API versioning, ``sdcard`` renamed to ``printer``

.. _sec-api-fileops-retrieveall:

Retrieve all files
==================

.. md-tab-set::

   .. md-tab-item:: API version 2.0.0+

      .. http:get:: /api/files
      
         Retrieve information regarding all files currently available and regarding the disk space still available
         locally in the system. The results are cached for performance reasons. If you
         want to override the cache, supply the query parameter ``force`` and set it to ``true``. Note that
         while printing a refresh/override of the cache for files stored on the printer's internal storage
         is disabled due to bandwidth restrictions on the serial interface.
      
         By default only returns the files and folders in the root directory. If the query parameter ``recursive``
         is provided and set to ``true``, returns all files and folders.
      
         Returns an object mapping storage IDs to :ref:`sec-api-fileops-datamodel-storage-data`.
      
         Requires the ``FILES_LIST`` permission.
      
         **Example 1**:
      
         Fetch only the files and folders from the root folder.
      
         .. sourcecode:: http
      
            GET /api/files HTTP/1.1
            Host: example.com
            Authorization: Bearer abcdef...
            X-OctoPrint-Api-Version: 2.0.0
      
         .. sourcecode:: http
      
            HTTP/1.1 200 OK
            Content-Type: application/json

            {
              "local": {
                "key": "local",
                "name": "Local",
                "capabilities": {
                  "add_folder": true,
                  "concurrent_printing": true,
                  "copy_file": true,
                  "copy_folder": true,
                  "history": true,
                  "metadata": true,
                  "move_file": true,
                  "move_folder": true,
                  "path_on_disk": true,
                  "read_file": true,
                  "remove_file": true,
                  "remove_folder": true,
                  "thumbnails": true,
                  "write_file": true
                },
                "files": [
                  {
                    "name": "whistle_v2.gcode",
                    "path": "whistle_v2.gcode",
                    "type": "machinecode",
                    "typePath": ["machinecode", "gcode"],
                    "hash": "...",
                    "size": 1468987,
                    "date": 1378847754,
                    "origin": "local",
                    "refs": {
                      "resource": "http://example.com/api/files/local/whistle_v2.gcode",
                      "download": "http://example.com/downloads/files/local/whistle_v2.gcode"
                    },
                    "gcodeAnalysis": {
                      "estimatedPrintTime": 1188,
                      "filament": {
                        "length": 810,
                        "volume": 5.36
                      }
                    },
                    "print": {
                      "failure": 4,
                      "success": 23,
                      "last": {
                        "date": 1387144346,
                        "success": true
                      }
                    }
                  },
                  {
                    "name": "folderA",
                    "path": "folderA",
                    "type": "folder",
                    "typePath": ["folder"],
                    "children": []
                  }
                ],
                "usage": {
                  "free": 123000,
                  "total": 123456
                }
              },
              "printer": {
                "key": "printer",
                "name": "Printer",
                "capabilities": {
                  "add_folder": false,
                  "concurrent_printing": false,
                  "copy_file": false,
                  "copy_folder": false,
                  "history": false,
                  "metadata": true,
                  "move_file": false,
                  "move_folder": false,
                  "path_on_disk": false,
                  "read_file": false,
                  "remove_file": true,
                  "remove_folder": false,
                  "thumbnails": false,
                  "write_file": true
                },
                "files": [
                  {
                    "name": "whistle_.gco",
                    "path": "whistle_.gco",
                    "type": "machinecode",
                    "typePath": ["machinecode", "gcode"],
                    "origin": "printer",
                    "refs": {
                      "resource": "http://example.com/api/files/printer/whistle_.gco"
                    }
                  }
                ]
              }
            }
      
         **Example 2**
      
         Recursively fetch all files and folders.
      
         .. sourcecode:: http
      
            GET /api/files?recursive=true HTTP/1.1
            Host: example.com
            Authorization: Bearer abcdef...
            X-OctoPrint-Api-Version: 2.0.0
      
         .. sourcecode:: http
      
            HTTP/1.1 200 OK
            Content-Type: application/json

            {
              "local": {
                "key": "local",
                "name": "Local",
                "capabilities": {
                  "add_folder": true,
                  "concurrent_printing": true,
                  "copy_file": true,
                  "copy_folder": true,
                  "history": true,
                  "metadata": true,
                  "move_file": true,
                  "move_folder": true,
                  "path_on_disk": true,
                  "read_file": true,
                  "remove_file": true,
                  "remove_folder": true,
                  "thumbnails": true,
                  "write_file": true
                },
                "files": [
                  {
                    "name": "whistle_v2.gcode",
                    "path": "whistle_v2.gcode",
                    "type": "machinecode",
                    "typePath": ["machinecode", "gcode"],
                    "hash": "...",
                    "size": 1468987,
                    "date": 1378847754,
                    "origin": "local",
                    "refs": {
                      "resource": "http://example.com/api/files/local/whistle_v2.gcode",
                      "download": "http://example.com/downloads/files/local/whistle_v2.gcode"
                    },
                    "gcodeAnalysis": {
                      "estimatedPrintTime": 1188,
                      "filament": {
                        "length": 810,
                        "volume": 5.36
                      }
                    },
                    "print": {
                      "failure": 4,
                      "success": 23,
                      "last": {
                        "date": 1387144346,
                        "success": true
                      }
                    }
                  },
                  {
                    "name": "folderA",
                    "path": "folderA",
                    "type": "folder",
                    "typePath": ["folder"],
                    "children": [
                      {
                        "name": "whistle_v2_copy.gcode",
                        "path": "whistle_v2_copy.gcode",
                        "type": "machinecode",
                        "typePath": ["machinecode", "gcode"],
                        "hash": "...",
                        "size": 1468987,
                        "date": 1378847754,
                        "origin": "local",
                        "refs": {
                          "resource": "http://example.com/api/files/local/folderA/whistle_v2_copy.gcode",
                          "download": "http://example.com/downloads/files/local/folderA/whistle_v2_copy.gcode"
                        },
                        "gcodeAnalysis": {
                          "estimatedPrintTime": 1188,
                          "filament": {
                            "length": 810,
                            "volume": 5.36
                          }
                        },
                        "print": {
                          "failure": 4,
                          "success": 23,
                          "last": {
                            "date": 1387144346,
                            "success": true
                          }
                        }
                      }
                    ]
                  }
                ],
                "usage": {
                  "free": 123000,
                  "total": 123456
                }
              },
              "printer": {
                "key": "printer",
                "name": "Printer",
                "capabilities": {
                  "add_folder": false,
                  "concurrent_printing": false,
                  "copy_file": false,
                  "copy_folder": false,
                  "history": false,
                  "metadata": true,
                  "move_file": false,
                  "move_folder": false,
                  "path_on_disk": false,
                  "read_file": false,
                  "remove_file": true,
                  "remove_folder": false,
                  "thumbnails": false,
                  "write_file": true
                },
                "files": [
                  {
                    "name": "whistle_.gco",
                    "path": "whistle_.gco",
                    "type": "machinecode",
                    "typePath": ["machinecode", "gcode"],
                    "origin": "printer",
                    "refs": {
                      "resource": "http://example.com/api/files/printer/whistle_.gco"
                    }
                  }
                ]
              }
            }
      
      
         :param force: If set to ``true``, forces a refresh, overriding the cache.
         :param recursive: If set to ``true``, return all files and folders recursively. Otherwise only return items on same level.
         :statuscode 200: No error

   .. md-tab-item:: API version pre 2.0.0

      .. http:get:: /api/files
      
         Retrieve information regarding all files currently available and regarding the disk space still available
         locally in the system. The results are cached for performance reasons. If you
         want to override the cache, supply the query parameter ``force`` and set it to ``true``. Note that
         while printing a refresh/override of the cache for files stored on the printer's internal storage
         is disabled due to bandwidth restrictions on the serial interface.
      
         By default only returns the files and folders in the root directory. If the query parameter ``recursive``
         is provided and set to ``true``, returns all files and folders.
      
         Returns a :ref:`sec-api-fileops-datamodel-readfiles-pre-1_12`.
      
         Requires the ``FILES_LIST`` permission.
      
         **Example 1**:
      
         Fetch only the files and folders from the root folder.
      
         .. sourcecode:: http
      
            GET /api/files HTTP/1.1
            Host: example.com
            Authorization: Bearer abcdef...
      
         .. sourcecode:: http
      
            HTTP/1.1 200 OK
            Content-Type: application/json
      
            {
              "files": [
                {
                  "name": "whistle_v2.gcode",
                  "path": "whistle_v2.gcode",
                  "type": "machinecode",
                  "typePath": ["machinecode", "gcode"],
                  "hash": "...",
                  "size": 1468987,
                  "date": 1378847754,
                  "origin": "local",
                  "refs": {
                    "resource": "http://example.com/api/files/local/whistle_v2.gcode",
                    "download": "http://example.com/downloads/files/local/whistle_v2.gcode"
                  },
                  "gcodeAnalysis": {
                    "estimatedPrintTime": 1188,
                    "filament": {
                      "length": 810,
                      "volume": 5.36
                    }
                  },
                  "print": {
                    "failure": 4,
                    "success": 23,
                    "last": {
                      "date": 1387144346,
                      "success": true
                    }
                  }
                },
                {
                  "name": "whistle_.gco",
                  "path": "whistle_.gco",
                  "type": "machinecode",
                  "typePath": ["machinecode", "gcode"],
                  "origin": "printer",
                  "refs": {
                    "resource": "http://example.com/api/files/printer/whistle_.gco"
                  }
                },
                {
                  "name": "folderA",
                  "path": "folderA",
                  "type": "folder",
                  "typePath": ["folder"],
                  "children": []
                }
              ],
              "free": "3.2GB"
            }
      
         **Example 2**
      
         Recursively fetch all files and folders.
      
         .. sourcecode:: http
      
            GET /api/files?recursive=true HTTP/1.1
            Host: example.com
            Authorization: Bearer abcdef...
      
         .. sourcecode:: http
      
            HTTP/1.1 200 OK
            Content-Type: application/json
      
            {
              "files": [
                {
                  "name": "whistle_v2.gcode",
                  "path": "whistle_v2.gcode",
                  "type": "machinecode",
                  "typePath": ["machinecode", "gcode"],
                  "hash": "...",
                  "size": 1468987,
                  "date": 1378847754,
                  "origin": "local",
                  "refs": {
                    "resource": "http://example.com/api/files/local/whistle_v2.gcode",
                    "download": "http://example.com/downloads/files/local/whistle_v2.gcode"
                  },
                  "gcodeAnalysis": {
                    "estimatedPrintTime": 1188,
                    "filament": {
                      "length": 810,
                      "volume": 5.36
                    }
                  },
                  "print": {
                    "failure": 4,
                    "success": 23,
                    "last": {
                      "date": 1387144346,
                      "success": true
                    }
                  }
                },
                {
                  "name": "whistle_.gco",
                  "path": "whistle_.gco",
                  "type": "machinecode",
                  "typePath": ["machinecode", "gcode"],
                  "origin": "printer",
                  "refs": {
                    "resource": "http://example.com/api/files/printer/whistle_.gco"
                  }
                },
                {
                  "name": "folderA",
                  "path": "folderA",
                  "type": "folder",
                  "typePath": ["folder"],
                  "children": [
                    {
                      "name": "test.gcode",
                      "path": "folderA/test.gcode",
                      "type": "machinecode",
                      "typePath": ["machinecode", "gcode"],
                      "hash": "...",
                      "size": 1234,
                      "date": 1378847754,
                      "origin": "local",
                      "refs": {
                        "resource": "http://example.com/api/files/local/folderA/test.gcode",
                        "download": "http://example.com/downloads/files/local/folderA/test.gcode"
                      }
                    },
                    {
                      "name": "subfolder",
                      "path": "folderA/subfolder",
                      "type": "folder",
                      "typePath": ["folder"],
                      "children": [
                        {
                          "name": "test.gcode",
                          "path": "folderA/subfolder/test2.gcode",
                          "type": "machinecode",
                          "typePath": ["machinecode", "gcode"],
                          "hash": "...",
                          "size": 100,
                          "date": 1378847754,
                          "origin": "local",
                          "refs": {
                            "resource": "http://example.com/api/files/local/folderA/subfolder/test2.gcode",
                            "download": "http://example.com/downloads/files/local/folderA/subfolder/test2.gcode"
                          }
                        },
                      ],
                      "size": 100,
                      "refs": {
                        "resource": "http://example.com/api/files/local/folderA/subfolder",
                      }
                    }
                  ],
                  "size": 1334,
                  "refs": {
                    "resource": "http://example.com/api/files/local/folderA",
                  }
                }
              ],
              "free": "3.2GB"
            }
      
         :param force: If set to ``true``, forces a refresh, overriding the cache.
         :param recursive: If set to ``true``, return all files and folders recursively. Otherwise only return items on same level.
         :statuscode 200: No error

.. _sec-api-fileops-retrievestorage:

Retrieve data of specific storage
=================================

.. md-tab-set::

   .. md-tab-item:: API version 2.0.0+

      .. http:get:: /api/files/(string:storage)

         Retrieve information regarding the files currently available on the selected ``storage``. The results are cached for performance reasons. If you
         want to override the cache, supply the query parameter ``force`` and set it to ``true``.
 
         By default only returns the files and folders in the root directory. If the query parameter ``recursive``
         is provided and set to ``true``, returns all files and folders.
 
         Returns the requested :ref:`sec-api-fileops-datamodel-storage-data`.
 
         Requires the ``FILES_LIST`` permission.
 
         **Example**:
 
         .. sourcecode:: http
 
             GET /api/files/local HTTP/1.1
             Host: example.com
             Authorization: Bearer abcdef...
             X-OctoPrint-Api-Version: 2.0.0
 
         .. sourcecode:: http
 
             HTTP/1.1 200 OK
             Content-Type: application/json
 
             {
               "key": "local",
               "name": "Local",
               "capabilities": {
                 "add_folder": true,
                 "concurrent_printing": true,
                 "copy_file": true,
                 "copy_folder": true,
                 "history": true,
                 "metadata": true,
                 "move_file": true,
                 "move_folder": true,
                 "path_on_disk": true,
                 "read_file": true,
                 "remove_file": true,
                 "remove_folder": true,
                 "thumbnails": true,
                 "write_file": true
               },
               "files": [
                {
                   "name": "whistle_v2.gcode",
                   "path": "whistle_v2.gcode",
                   "type": "machinecode",
                   "typePath": ["machinecode", "gcode"],
                   "hash": "...",
                   "size": 1468987,
                   "date": 1378847754,
                   "origin": "local",
                   "refs": {
                     "resource": "http://example.com/api/files/local/whistle_v2.gcode",
                     "download": "http://example.com/downloads/files/local/whistle_v2.gcode"
                   },
                   "gcodeAnalysis": {
                     "estimatedPrintTime": 1188,
                     "filament": {
                       "length": 810,
                       "volume": 5.36
                     }
                   },
                   "print": {
                     "failure": 4,
                     "success": 23,
                     "last": {
                       "date": 1387144346,
                       "success": true
                     }
                   }
                 },
                 {
                   "name": "folderA",
                   "path": "folderA",
                   "type": "folder",
                   "typePath": ["folder"],
                   "children": []
                 }
               ],
               "usage": {
                 "free": 123000,
                 "total": 123456
               }
             }
 
         :param storage: The storage from which to retrieve the files. Must be one of the currently registered storages.
         :param force: If set to ``true``, forces a refresh, overriding the cache.
         :param recursive: If set to ``true``, return all files and folders recursively. Otherwise only return items on same level.
         :statuscode 200: No error
         :statuscode 404: If `storage` is not one of the registered storages (stock: ``local``, ``printer``)

   .. md-tab-item:: API version pre 2.0.0

      .. http:get:: /api/files/(string:storage)

         Retrieve information regarding the files currently available on the selected ``location`` and -- if targeting
         the ``local`` storage -- regarding the disk space still available locally in the system. The results are cached for performance reasons. If you
         want to override the cache, supply the query parameter ``force`` and set it to ``true``.
         Note that while printing a refresh/override of the cache for files stored on the printer's internal storage
         is disabled due to bandwidth restrictions on the serial interface.
 
         By default only returns the files and folders in the root directory. If the query parameter ``recursive``
         is provided and set to ``true``, returns all files and folders.
 
         Returns a :ref:`sec-api-fileops-datamodel-readstorage-pre-1_12`.
 
         Requires the ``FILES_LIST`` permission.
 
         **Example**:
 
         .. sourcecode:: http
 
             GET /api/files/local HTTP/1.1
             Host: example.com
             Authorization: Bearer abcdef...
 
         .. sourcecode:: http
 
             HTTP/1.1 200 OK
             Content-Type: application/json
 
             {
               "files": [
                 {
                   "name": "whistle_v2.gcode",
                   "path": "whistle_v2.gcode",
                   "type": "machinecode",
                   "typePath": ["machinecode", "gcode"],
                   "size": 1468987,
                   "date": 1378847754,
                   "origin": "local",
                   "refs": {
                     "resource": "http://example.com/api/files/local/whistle_v2.gcode",
                     "download": "http://example.com/downloads/files/local/whistle_v2.gcode"
                   },
                   "gcodeAnalysis": {
                     "estimatedPrintTime": 1188,
                     "filament": {
                       "length": 810,
                       "volume": 5.36
                     }
                   },
                   "print": {
                     "failure": 4,
                     "success": 23,
                     "last": {
                       "date": 1387144346,
                       "success": true
                     }
                   }
                 }
               ],
               "free": 123000
             }
 
         :param storage: The storage from which to retrieve the files. Currently only ``local`` and ``printer`` (or the deprecated ``sdcard``) are
                           supported, with ``local`` referring to files stored in OctoPrint's ``uploads`` folder and ``printer``
                           referring to files stored on the printer's internal storage (if available).
         :param force: If set to ``true``, forces a refresh, overriding the cache.
         :param recursive: If set to ``true``, return all files and folders recursively. Otherwise only return items on same level.
         :statuscode 200: No error
         :statuscode 404: If ``storage`` is unknown

.. _sec-api-fileops-uploadfile:

Upload file or create folder
============================

.. md-tab-set::

   .. md-tab-item:: API version 2.0.0+

      .. http:post:: /api/files/(string:storage)

         Upload a file to the selected ``storage`` or create a new empty folder on it.
 
         Other than most of the other requests on OctoPrint's API which are expected as JSON, this request is expected as
         ``Content-Type: multipart/form-data`` due to the included file upload. A ``Content-Length`` header specifying
         the full length of the request body is required as well.
 
         To upload a file, the request body must at least contain the ``file`` form field with the
         contents and file name of the file to upload.
 
         To create a new folder, the request body must at least contain the ``foldername`` form field,
         specifying the name of the new folder. Note that folder creation support depends on the selected
         ``storage``, see ``capabilities.add_folder`` in the response of :ref:`sec-api-fileops-retrievestorage`.
 
         Returns a :http:statuscode:`201` response with a ``Location`` header set to the management URL of the uploaded
         file and an :ref:`sec-api-fileops-datamodel-uploadresponse` as the body upon successful completion.
 
         Requires the ``FILES_UPLOAD`` permission.
 
         **Example for uploading a file**
 
         .. sourcecode:: http
 
             POST /api/files/printer HTTP/1.1
             Host: example.com
             Authorization: Bearer abcdef...
             Content-Type: multipart/form-data; boundary=----WebKitFormBoundaryDeC2E3iWbTv1PwMC
             Content-Length: 430
 
             ------WebKitFormBoundaryDeC2E3iWbTv1PwMC
             Content-Disposition: form-data; name="file"; filename="whistle_v2.gcode"
             Content-Type: application/octet-stream
 
             M109 T0 S220.000000
             T0
             G21
             G90
 
             ------WebKitFormBoundaryDeC2E3iWbTv1PwMC
             Content-Disposition: form-data; name="select"
 
             true
             ------WebKitFormBoundaryDeC2E3iWbTv1PwMC
             Content-Disposition: form-data; name="print"
 
             true
             ------WebKitFormBoundaryDeC2E3iWbTv1PwMC--
 
         .. sourcecode:: http
 
             HTTP/1.1 200 OK
             Content-Type: application/json
             Location: http://example.com/api/files/printer/whistle_.gcode
 
             {
               "file": {
                 "name": "whistle_.gco",
                 "path": "whistle_.gco",
                 "origin": "printer",
                 "refs": {
                   "resource": "http://example.com/api/files/printer/whistle_.gco"
                 }
               },
               "done": false,
               "effectiveSelect": true,
               "effectivePrint": true
             }
 
         **Example with UTF-8 encoded filename following RFC 5987**
 
         .. sourcecode:: http
 
             POST /api/files/local HTTP/1.1
             Host: example.com
             Authorization: Bearer abcdef...
             Content-Type: multipart/form-data; boundary=----WebKitFormBoundaryDeC2E3iWbTv1PwMC
             Content-Length: 263
 
             ------WebKitFormBoundaryDeC2E3iWbTv1PwMC
             Content-Disposition: form-data; name="file"; filename*=utf-8''20mm-%C3%BCml%C3%A4ut-b%C3%B6x.gcode
             Content-Type: application/octet-stream
 
             M109 T0 S220.000000
             T0
             G21
             G90
 
             ------WebKitFormBoundaryDeC2E3iWbTv1PwMC--
 
         .. sourcecode:: http
 
             HTTP/1.1 200 OK
             Content-Type: application/json
             Location: http://example.com/api/files/local/20mm-umlaut-box.gcode
 
             {
               "file": {
                 "name": "20mm-umlaut-box",
                 "origin": "local",
                 "refs": {
                   "resource": "http://example.com/api/files/local/whistle_v2.gcode",
                   "download": "http://example.com/downloads/files/local/whistle_v2.gcode"
                 }
               },
               "done": true,
               "effectiveSelect": false,
               "effectivePrint": false
             }
 
         **Example for creating a folder**
 
         .. sourcecode:: http
 
             POST /api/files/local HTTP/1.1
             Host: example.com
             Authorization: Bearer abcdef...
             Content-Type: multipart/form-data; boundary=----WebKitFormBoundaryDeC2E3iWbTv1PwMD
             Content-Length: 246
 
             ------WebKitFormBoundaryDeC2E3iWbTv1PwMD
             Content-Disposition: form-data; name="foldername"
 
             subfolder
             ------WebKitFormBoundaryDeC2E3iWbTv1PwMD
             Content-Disposition: form-data; name="path"
 
             folder/
             ------WebKitFormBoundaryDeC2E3iWbTv1PwMD--
 
         .. sourcecode:: http
 
             HTTP/1.1 200 OK
             Content-Type: application/json
             Location: http://example.com/api/files/local/folder/subfolder
 
             {
               "folder": {
                 "name": "subfolder",
                 "path": "folder/subfolder",
                 "origin": "local",
                 "refs": {
                   "resource": "http://example.com/api/files/local/folder/subfolder"
                 }
               },
               "done": true
             }
 
         :param storage:  The target location to which to upload the file. By default only ``local`` and ``printer`` are supported
                           here, with ``local`` referring to OctoPrint's ``uploads`` folder and ``printer`` referring to
                           the printer's internal storage.
         :form file:       The file to upload, including a valid ``filename``.
         :form path:       The path within the ``location`` to upload the file to or create the folder in (without the future
                           filename or ``foldername`` - basically the parent folder). If unset will be taken from the provided
                           ``file``'s name or ``foldername`` and default to the root folder of the ``location``.
         :form select:     Whether to select the file directly after upload (``true``) or not (``false``). Optional, defaults
                           to ``false``. If the printer is not operational, this will have no
                           effect and the ``effectiveSelect`` field in the response will be set to ``false``. Ignored when creating a folder.
         :form print:      Whether to start printing the file directly after upload (``true``) or not (``false``). If set, ``select``
                           is implicitly ``true`` as well. Optional, defaults to ``false``. If the
                           printer is not operational, this will have no effect and the ``effectivePrint`` field in the response will be set
                           to ``false``. Ignored when creating a folder.
         :form userdata:   [Optional] An optional string that if specified will be interpreted as JSON and then saved along
                           with the file as metadata (metadata key ``userdata``). Ignored when creating a folder.
         :form foldername: The name of the folder to create. Ignored when uploading a file.
         :statuscode 201:  No error
         :statuscode 400:  If no ``file`` or ``foldername`` are included in the request, ``userdata`` was provided but could
                           not be parsed as JSON or the request is otherwise invalid.
         :statuscode 404:  If ``location`` is not among the registered storages (e.g. ``local``, ``printer``)
         :statuscode 409:  If the upload of the file would override the file that is currently being printed or if an upload
                           to SD card was requested and the printer is either not operational or currently busy with a print job.
         :statuscode 415:  If the file is neither a ``gcode`` nor an ``stl`` file (or it is an ``stl`` file but slicing support
                           is disabled)
         :statuscode 500:  If the upload failed internally

   .. md-tab-item:: API version pre 2.0.0

      .. http:post:: /api/files/(string:storage)

         Upload a file to the selected ``storage`` or create a new empty folder on it.
 
         Other than most of the other requests on OctoPrint's API which are expected as JSON, this request is expected as
         ``Content-Type: multipart/form-data`` due to the included file upload. A ``Content-Length`` header specifying
         the full length of the request body is required as well.
 
         To upload a file, the request body must at least contain the ``file`` form field with the
         contents and file name of the file to upload.
 
         To create a new folder, the request body must at least contain the ``foldername`` form field,
         specifying the name of the new folder. Note that folder creation support depends on the selected
         ``storage``, see ``capabilities.add_folder`` in the response of :ref:`sec-api-fileops-retrievestorage`.
 
         Returns a :http:statuscode:`201` response with a ``Location`` header set to the management URL of the uploaded
         file and an :ref:`sec-api-fileops-datamodel-uploadresponse-pre-1_12` as the body upon successful completion.
 
         Requires the ``FILES_UPLOAD`` permission.
 
         **Example for uploading a file**
 
         .. sourcecode:: http
 
             POST /api/files/printer HTTP/1.1
             Host: example.com
             Authorization: Bearer abcdef...
             Content-Type: multipart/form-data; boundary=----WebKitFormBoundaryDeC2E3iWbTv1PwMC
             Content-Length: 430
 
             ------WebKitFormBoundaryDeC2E3iWbTv1PwMC
             Content-Disposition: form-data; name="file"; filename="whistle_v2.gcode"
             Content-Type: application/octet-stream
 
             M109 T0 S220.000000
             T0
             G21
             G90
 
             ------WebKitFormBoundaryDeC2E3iWbTv1PwMC
             Content-Disposition: form-data; name="select"
 
             true
             ------WebKitFormBoundaryDeC2E3iWbTv1PwMC
             Content-Disposition: form-data; name="print"
 
             true
             ------WebKitFormBoundaryDeC2E3iWbTv1PwMC--
 
         .. sourcecode:: http
 
             HTTP/1.1 200 OK
             Content-Type: application/json
             Location: http://example.com/api/files/printer/whistle_.gcode
 
             {
               "files": {
                 "printer": {
                   "name": "whistle_.gco",
                   "path": "whistle_.gco",
                   "origin": "sdcard",
                   "refs": {
                     "resource": "http://example.com/api/files/printer/whistle_.gco"
                   }
                 }
               },
               "done": false,
               "effectiveSelect": true,
               "effectivePrint": true
             }
 
         **Example with UTF-8 encoded filename following RFC 5987**
 
         .. sourcecode:: http
 
             POST /api/files/local HTTP/1.1
             Host: example.com
             Authorization: Bearer abcdef...
             Content-Type: multipart/form-data; boundary=----WebKitFormBoundaryDeC2E3iWbTv1PwMC
             Content-Length: 263
 
             ------WebKitFormBoundaryDeC2E3iWbTv1PwMC
             Content-Disposition: form-data; name="file"; filename*=utf-8''20mm-%C3%BCml%C3%A4ut-b%C3%B6x.gcode
             Content-Type: application/octet-stream
 
             M109 T0 S220.000000
             T0
             G21
             G90
 
             ------WebKitFormBoundaryDeC2E3iWbTv1PwMC--
 
         .. sourcecode:: http
 
             HTTP/1.1 200 OK
             Content-Type: application/json
             Location: http://example.com/api/files/local/20mm-umlaut-box.gcode
 
             {
               "files": {
                 "local": {
                   "name": "20mm-umlaut-box",
                   "origin": "local",
                   "refs": {
                     "resource": "http://example.com/api/files/local/whistle_v2.gcode",
                     "download": "http://example.com/downloads/files/local/whistle_v2.gcode"
                   }
                 }
               },
               "done": true,
               "effectiveSelect": false,
               "effectivePrint": false
             }
 
         **Example for creating a folder**
 
         .. sourcecode:: http
 
             POST /api/files/local HTTP/1.1
             Host: example.com
             Authorization: Bearer abcdef...
             Content-Type: multipart/form-data; boundary=----WebKitFormBoundaryDeC2E3iWbTv1PwMD
             Content-Length: 246
 
             ------WebKitFormBoundaryDeC2E3iWbTv1PwMD
             Content-Disposition: form-data; name="foldername"
 
             subfolder
             ------WebKitFormBoundaryDeC2E3iWbTv1PwMD
             Content-Disposition: form-data; name="path"
 
             folder/
             ------WebKitFormBoundaryDeC2E3iWbTv1PwMD--
 
         .. sourcecode:: http
 
             HTTP/1.1 200 OK
             Content-Type: application/json
             Location: http://example.com/api/files/local/folder/subfolder
 
             {
               "folder": {
                 "name": "subfolder",
                 "path": "folder/subfolder",
                 "origin": "local",
                 "refs": {
                   "resource": "http://example.com/api/files/local/folder/subfolder"
                 }
               },
               "done": true
             }
 
         :param storage:  The target location to which to upload the file. By default only ``local`` and ``printer`` (and its deprecated alias ``sdcard``) are supported
                           here, with ``local`` referring to OctoPrint's ``uploads`` folder and ``printer`` referring to
                           the printer's internal storage.
         :form file:       The file to upload, including a valid ``filename``.
         :form path:       The path within the ``location`` to upload the file to or create the folder in (without the future
                           filename or ``foldername`` - basically the parent folder). If unset will be taken from the provided
                           ``file``'s name or ``foldername`` and default to the root folder of the ``location``.
         :form select:     Whether to select the file directly after upload (``true``) or not (``false``). Optional, defaults
                           to ``false``. If the printer is not operational, this will have no
                           effect and the ``effectiveSelect`` field in the response will be set to ``false``. Ignored when creating a folder.
         :form print:      Whether to start printing the file directly after upload (``true``) or not (``false``). If set, ``select``
                           is implicitly ``true`` as well. Optional, defaults to ``false``. If the
                           printer is not operational, this will have no effect and the ``effectivePrint`` field in the response will be set
                           to ``false``. Ignored when creating a folder.
         :form userdata:   [Optional] An optional string that if specified will be interpreted as JSON and then saved along
                           with the file as metadata (metadata key ``userdata``). Ignored when creating a folder.
         :form foldername: The name of the folder to create. Ignored when uploading a file.
         :statuscode 201:  No error
         :statuscode 400:  If no ``file`` or ``foldername`` are included in the request, ``userdata`` was provided but could
                           not be parsed as JSON or the request is otherwise invalid.
         :statuscode 404:  If ``location`` is not among the registered storages (e.g. ``local``, ``printer`` or its deprecated alias ``sdcard``)
         :statuscode 409:  If the upload of the file would override the file that is currently being printed or if an upload
                           to SD card was requested and the printer is either not operational or currently busy with a print job.
         :statuscode 415:  If the file is neither a ``gcode`` nor an ``stl`` file (or it is an ``stl`` file but slicing support
                           is disabled)
         :statuscode 500:  If the upload failed internally

.. _sec-api-fileops-retrievefileinfo:

Retrieve a specific file's or folder's information
==================================================

.. http:get:: /api/files/(string:location)/(path:filename)

   Retrieves the selected file's or folder's information.

   If the file is unknown, a :http:statuscode:`404` is returned.

   If the targeted path is a folder, by default only its direct children will be returned. If ``recursive`` is
   provided and set to ``true``, all sub folders and their children will be returned too.

   On success, a :http:statuscode:`200` is returned, with a :ref:`sec-api-fileops-datamodel-file`
   as the response body.

   Requires the ``FILES_LIST`` permission.

   **Example**

   .. sourcecode:: http

      GET /api/files/local/whistle_v2.gcode HTTP/1.1
      Host: example.com
      Authorization: Bearer abcdef...

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "name": "whistle_v2.gcode",
        "size": 1468987,
        "date": 1378847754,
        "origin": "local",
        "refs": {
          "resource": "http://example.com/api/files/local/whistle_v2.gcode",
          "download": "http://example.com/downloads/files/local/whistle_v2.gcode"
        },
        "gcodeAnalysis": {
          "estimatedPrintTime": 1188,
          "filament": {
            "length": 810,
            "volume": 5.36
          }
        },
        "print": {
          "failure": 4,
          "success": 23,
          "last": {
            "date": 1387144346,
            "success": true
          }
        }
      }

   :param location: The location of the file for which to retrieve the information, by default ``local`` (for OctoPrint's ``uploads``
                    folder) or ``printer`` or its deprecated alias ``sdcard`` for the printer's internal storage (if available)
   :param filename: The filename of the file for which to retrieve the information
   :param recursive: If set to ``true``, return all files and folders recursively. Otherwise only return items on same level.
   :statuscode 200: No error
   :statuscode 404: If ``target`` is not among the registered storages (e.g. ``local``, ``printer`` or its deprecated alias ``sdcard``)

.. _sec-api-fileops-filecommand:

Issue a file command
====================

.. http:post:: /api/files/(string:location)/(path:path)

   Issue a file command to an existing file. Currently supported commands are:

   select
     Selects a file for printing. Additional parameters are:

     * ``print``: Optional, if set to ``true`` the file will start printing directly after selection. If the printer
       is not operational when this parameter is present and set to ``true``, the request will fail with a response
       of ``409 Conflict``.

     Upon success, a status code of :http:statuscode:`204` and an empty body is returned. If there already is an
     active print job, a :http:statuscode:`409` is returned.

     Requires the ``FILES_SELECT`` permission.

   unselect
     Unselects the currently selected file for printing.

     Upon success, a status code of :http:statuscode:`204` and an empty body is returned. If no file is selected
     or there already is an active print job, a :http:statuscode:`409` is returned. If path isn't ``current``
     or the filename of the current selection, a :http:statuscode:`400` is returned

     Requires the ``FILES_SELECT`` permission.

   copy
     Copies the file or folder to a new ``destination`` on the same ``location`` or another ``storage``. Additional parameters are:

     * ``destination``: The path of the parent folder to which to copy the file or folder. It must already exist. Mandatory.
     * ``storage``: The optional target storage to copy the file to.

     .. note::

        Whether this command is supported depends on the involved storage's capabilities.

        For an in-storage move, the storage needs to support ``copy_file`` or ``copy_folder`` respectively.

        For a cross-storage file move, the source needs to support ``read_file`` and the target needs 
        to support ``write_file``. Cross-storage folder copies are currently not supported.

     If there already exists a file or folder of the same name at ``destination``, the request will return a :http:statuscode:`409`.
     If the ``destination`` folder does not exist, a :http:statuscode:`404` will be returned.

     A :http:statuscode:`400` will be returned if:

     * the ``destination`` is missing from the request
     * the cross-storage target ``storage`` is not available
     * the cross-storage operation's ``destination`` is a folder
     * the targeted ``path`` is neither a file nor a folder
     * the involved storages lack the necessary capabilities to perform the operation

     Upon success, a status code of :http:statuscode:`201` and a :ref:`sec-api-fileops-datamodel-uploaded-entry` in the response
     body will be returned.

     Requires the ``FILES_UPLOAD`` permission.

     .. versionchanged:: 2.0.0

        cross-storage support

   move
     Moves the file or folder to a new ``destination`` on the same ``location`` or another ``storage``. Additional parameters are:

     * ``destination``: The path of the parent folder to which to move the file or folder.
     * ``storage``: The optional target storage to move the file to.

     .. note::

        Whether this command is supported depends on the involved storage's capabilities.

        For an in-storage move, the storage needs to support ``move_file`` or ``move_folder`` respectively.

        For a cross-storage file move, the source needs to support ``read_file`` and ``remove_file`` and the target needs 
        to support ``write_file``. Cross-storage folder moves are currently not supported.

     If there already exists a file or folder of the same name at ``destination``, the request will return a :http:statuscode:`409`.
     If the ``destination`` folder does not exist, a :http:statuscode:`404` will be returned. If the ``path`` is currently
     in use by OctoPrint (e.g. it is a GCODE file that's currently being printed) a :http:statuscode:`409` will be
     returned.

     A :http:statuscode:`400` will be returned if:

     * the ``destination`` is missing from the request
     * the cross-storage target ``storage`` is not available
     * the cross-storage operation's ``destination`` is a folder
     * the targeted ``path`` is neither a file nor a folder
     * the involved storages lack the necessary capabilities to perform the operation

     Upon success, a status code of :http:statuscode:`201` and a :ref:`sec-api-fileops-datamodel-uploaded-entry` in the response
     body will be returned.

     Requires the ``FILES_UPLOAD`` permission.

     .. versionchanged:: 2.0.0

        cross-storage support

   refresh_thumbnails
     Forces a refresh of the thumbnail of the targeted file, or the files contained in the targeted folder.

     Additional parameters are:

     * ``force``: If ``true``, a thumbnail refresh will be even done if a thumbnail already exists.
     * ``recursive``: If ``true`` and targeting a folder, any contained subfolders will also be fully processed.

     Upon success, a status code of :http:statuscode:`204` and empty body is returned. The request will only return after the
     refresh has been processed - it thus might be long running!

     Requires the ``FILES_UPLOAD`` permission.

     .. versionadded:: 2.0.0

   slice
     Slices an STL file into GCODE. Note that this is an asynchronous operation that will take place in the background
     after the response has been sent back to the client. Additional parameters are:

     * ``slicer``: The slicing engine to use, defaults to ``cura`` if not set, which is also the only supported slicer right now.
     * ``gcode``: Name of the GCODE file to generated, in the same location as the STL file. Defaults to the STL file name
       with extension ``.gco`` if not set.
     * ``position``: Position of the object-to-slice's center on the print bed. A dictionary containing both ``x`` and ``y``
       coordinate in mm is expected
     * ``printerProfile``: Name of the printer profile to use, if not set the default printer profile will be used.
     * ``profile``: Name of the slicing profile to use, if not set the default slicing profile of the slicer will be used.
     * ``profile.*``: Override parameters, the ``profile.`` prefix will be stripped and the matching profile key will
       be overridden with the supplied value. Use this if you want to specify things that change often like a different
       temperature, filament diameter or infill percentage. Profile keys are slicer specific.
     * ``select``: Optional, if set to ``true`` the file be selected for printing right after the slicing has finished. If the
       printer is not operational or already printing when this parameter is present and set to ``true``, the request will
       fail with a response of ``409 Conflict``
     * ``print``: Optional, if set to ``true`` the file be selected and start printing right after the slicing has finished.
       If the printer is not operational or already printing when this parameter is present and set to ``true``, the request
       will fail with a response of ``409 Conflict``. Note that if this parameter is set, the parameter ``select`` does not
       need to be set, it is automatically assumed to be ``true`` too, otherwise no printing would be possible.

     If consecutive slicing calls are made targeting the same GCODE filename (that also holds true if the default is used),
     the slicing job already running in the background will be cancelled before the new one is started. Note that this will
     also mean that if it was supposed to be directly selected and start printing after the slicing finished, this will not
     take place anymore and whether this will happen with the new sliced file depends entirely on the new request!

     Upon success, a status code of :http:statuscode:`202` and a :ref:`sec-api-fileops-datamodel-uploaded-entry` in the response
     body will be returned.

     Requires the ``SLICE`` permission.

   **Example Select Request**

   .. sourcecode:: http

      POST /api/files/local/whistle_v2.gcode HTTP/1.1
      Host: example.com
      Content-Type: application/json
      Authorization: Bearer abcdef...

      {
        "command": "select",
        "print": true
      }

   .. sourcecode:: http

      HTTP/1.1 204 No Content

   **Example Slice Request**

   .. sourcecode:: http

      POST /api/files/local/some_folder/some_model.stl HTTP/1.1
      Host: example.com
      Content-Type: application/json
      Authorization: Bearer abcdef...

      {
        "command": "slice",
        "slicer": "cura",
        "gcode": "some_model.first_try.gcode",
        "printerProfile": "my_custom_reprap",
        "profile": "high_quality",
        "profile.infill": 75,
        "profile.fill_density": 15,
        "position": {"x": 100, "y": 100},
        "print": true
      }

   .. sourcecode:: http

      HTTP/1.1 202 Accepted
      Content-Type: application/json

      {
        "origin": "local",
        "name": "some_model.first_try.gcode",
        "path": "some_folder/some_model.first_try.gcode",
        "refs": {
          "download": "http://example.com/downloads/files/local/some_folder/some_model.first_try.gcode",
          "resource": "http://example.com/api/files/local/some_folder/some_model.first_try.gcode"
        }
      }

   **Example in-storage Copy Request**

   .. sourcecode:: http

      POST /api/files/local/some_folder/some_model.gcode HTTP/1.1
      Host: example.com
      Content-Type: application/json
      Authorization: Bearer abcdef...

      {
        "command": "copy",
        "destination": "some_other_folder/subfolder"
      }

   .. sourcecode:: http

      HTTP/1.1 201 Created
      Content-Type: application/json
      Location: http://example.com/api/files/local/some_other_folder/subfolder/some_model.gcode

      {
        "origin": "local",
        "name": "some_model.gcode",
        "path": "some_other_folder/subfolder/some_model.gcode",
        "refs": {
          "download": "http://example.com/downloads/files/local/some_other_folder/subfolder/some_model.gcode",
          "resource": "http://example.com/api/files/local/some_other_folder/subfolder/some_model.gcode"
        }
      }

   **Example in-storage Move Request**

   .. sourcecode:: http

      POST /api/files/local/some_folder/and_a_subfolder HTTP/1.1
      Host: example.com
      Content-Type: application/json
      Authorization: Bearer abcdef...

      {
        "command": "move",
        "destination": "some_other_folder"
      }

   .. sourcecode:: http

      HTTP/1.1 201 Created
      Content-Type: application/json
      Location: http://example.com/api/files/local/some_other_folder/and_a_subfolder

      {
        "origin": "local",
        "name": "and_a_subfolder",
        "path": "some_other_folder/and_a_subfolder",
        "refs": {
          "resource": "http://example.com/api/files/local/some_other_folder/and_a_subfolder"
        }
      }

   **Example cross-storage Copy Request**

   .. sourcecode:: http

      POST /api/files/local/some_folder/some_model.gcode HTTP/1.1
      Host: example.com
      Content-Type: application/json
      Authorization: Bearer abcdef...

      {
        "command": "copy",
        "destination": "/",
        "storage": "printer"
      }

   .. sourcecode:: http

      HTTP/1.1 201 Created
      Content-Type: application/json
      Location: http://example.com/api/files/printer/some_mo~1.gco

      {
        "origin": "printer",
        "name": "some_mo~1.gco",
        "path": "some_mo~1.gco",
        "refs": {
          "resource": "http://example.com/api/files/printer/some_mo~1.gco"
        }
      }

   :param location:             The target location on which to send the command for is located, by default ``local`` (for OctoPrint's ``uploads``
                                folder) or ``printer`` or its deprecated alias ``sdcard`` for the printer's internal storage (if available)
   :param path:                 The path of the file for which to issue the command
   :json string command:        The command to issue for the file, currently only ``select`` is supported
   :json boolean print:         ``select`` and ``slice`` command: Optional, whether to start printing the file directly after selection
                                or slicing, defaults to ``false``.
   :json string slicer:         ``slice`` command: The slicer to use, defaults to the default slicer.
   :json string gcode:          ``slice`` command: The name of the gcode file to create, defaults to the targeted stl's file name
                                with its extension changed to ``.gco`` (e.g. "test.stl" will be sliced to "test.gco" if not specified
                                otherwise)
   :json string profile:        ``slice`` command: The slicing profile to use, defaults to the selected slicer's default profile.
   :json string profile.*:      ``slice`` command: Overrides for the selected slicing profile, e.g. to specify a different temperature
                                or filament diameter.
   :json string printerProfile: ``slice`` command: The printer profile to use, defaults to the default printer profile.
   :json boolean select:        ``slice`` command: Optional, whether to select the file for printing directly after slicing,
                                defaults to ``false``
   :statuscode 200:             No error for a ``select`` command.
   :statuscode 202:             No error for a ``slice`` command.
   :statuscode 400:             If the ``command`` is unknown or the request is otherwise invalid
   :statuscode 415:             If a ``slice`` command was issued against something other than an STL file.
   :statuscode 404:             If ``location`` is not among the registered storages (e.g. ``local``, ``printer`` or its deprecated alias ``sdcard``) or the requested file was not found
   :statuscode 409:             If a selected file is supposed to start printing directly but the printer is not operational
                                or if a file is to be selected but the printer is already printing or
                                if a file to be sliced is supposed to be selected or start printing directly but the printer
                                is not operational or already printing.

.. _sec-api-fileops-delete:

Delete file
===========

.. http:delete:: /api/files/(string:location)/(path:path)

   Delete the selected ``path`` on the selected ``location``.

   If the file to be deleted is currently being printed, a :http:statuscode:`409` will be returned.

   Returns a :http:statuscode:`204` after successful deletion.

   Requires the ``FILES_DELETE`` permission.

   **Example Request**

   .. sourcecode:: http

      DELETE /api/files/local/whistle_v2.gcode HTTP/1.1
      Host: example.com
      Authorization: Bearer abcdef...

   :param location: The target location on which to delete the file, by default ``local`` (for OctoPrint's ``uploads``
                    folder) or ``printer`` or its deprecated alias ``sdcard`` for the printer's internal storage (if available)
   :param path:     The path of the file to delete
   :statuscode 204: No error
   :statuscode 404: If ``location`` is not among the registered storages (e.g. ``local``, ``printer`` or its deprecated alias ``sdcard``) or the requested file was not found
   :statuscode 409: If the file to be deleted is currently being printed

.. _sec-api-fileops-datamodel:

Data model
==========

.. _sec-api-fileops-datamodel-readfiles-pre-1_12:

Files response (pre 2.0.0)
---------------------------

.. pydantic-table:: octoprint.schema.api.files.ReadGcodeFilesResponse_pre_2_0_0

   octoprint.schema.api.files.ApiStorageFile = File
   octoprint.schema.api.files.ApiStorageFolder = Folder

.. _sec-api-fileops-datamodel-readstorage-pre-1_12:

Files for storage response (pre 2.0.0)
---------------------------------------

.. pydantic-table:: octoprint.schema.api.files.ReadGcodeFilesForOriginResponse_pre_2_0_0

   octoprint.schema.api.files.ApiStorageFile = File
   octoprint.schema.api.files.ApiStorageFolder = Folder

.. _sec-api-fileops-datamodel-uploadresponse:

Upload response
---------------

.. pydantic-table:: octoprint.schema.api.files.UploadResponse

   octoprint.schema.api.files.ApiAddedEntry = AddedEntry
   ApiAddedEntry = AddedEntry

.. _sec-api-fileops-datamodel-uploadresponse-pre-1_12:

Upload response (pre 2.0.0)
----------------------------

.. pydantic-table:: octoprint.schema.api.files.UploadResponse_pre_2_0_0

   octoprint.schema.api.files.ApiAddedEntry = AddedEntry
   ApiAddedEntry = AddedEntry

.. _sec-api-fileops-datamodel-storage-data:

Storage data
------------

.. pydantic-table:: octoprint.schema.api.files.ApiStorageData

    octoprint.schema.api.files.ApiStorageFile = File
    octoprint.schema.api.files.ApiStorageFolder = Folder
    ApiStorageUsage = Usage

.. _sec-api-fileops-datamodel-storage-capabilities:

Storage capabilities
--------------------

.. pydantic-table:: octoprint.filemanager.storage.StorageCapabilities

.. _sec-api-fileops-datamodel-usage-data:

Usage data
----------

.. pydantic-table:: octoprint.schema.api.files.ApiStorageUsage

.. _sec-api-fileops-datamodel-file:

File entry
----------

.. pydantic-table:: octoprint.schema.api.files.ApiStorageFile

   ApiEntryLastPrint = LastPrint
   ApiEntryAnalysis = Analysis
   ApiEntryStatistics = Statistics

.. _sec-api-fileops-datamodel-folder:

Folder entry
------------

.. pydantic-table:: octoprint.schema.api.files.ApiStorageFolder

   octoprint.schema.api.files.ApiStorageFile = File
   octoprint.schema.api.files.ApiStorageFolder = Folder
   ApiEntryPrints = PrintStats

.. _sec-api-fileops-datamodel-uploaded-entry:

Uploaded entry
--------------

.. pydantic-table:: octoprint.schema.api.files.ApiAddedEntry

.. _sec-api-fileops-datamodel-analysis:

Analysis result
---------------

.. pydantic-table:: octoprint.schema.api.files.ApiEntryAnalysis

   ApiAnalysisVolume = Volume
   ApiAnalysisDimensions = Dimensions
   octoprint.schema.api.files.ApiAnalysisFilamentUse = FilamentUse

.. _sec-api-fileops-datamodel-filament:

Filament use
------------

.. pydantic-table:: octoprint.schema.api.files.ApiAnalysisFilamentUse

.. _sec-api-fileops-datamodel-volume:

Volume
------

.. pydantic-table:: octoprint.schema.api.files.ApiAnalysisVolume

.. _sec-api-fileops-datamodel-dimensions:

Dimensions
----------

.. pydantic-table:: octoprint.schema.api.files.ApiAnalysisDimensions
