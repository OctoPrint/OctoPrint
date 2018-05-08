.. _sec-api-logs:

*******************
Log file management
*******************

Log file management (and logging configuration) was moved into a bundled plugin in OctoPrint 1.3.7. Refer to
:ref:`the Logging's plugins API <sec-bundledplugins-logging-api>` for the API documentation.

The former endpoints ``/api/logs`` and ``api/logs/<path>`` are marked as deprecated but still work for now. New
client implementations should directly use the new endpoints provided by the bundled plugin. Existing implementations
should adapt their endpoints as soon as possible.
