.. _sec-jsclientlib-logs:

:mod:`OctoPrintClient.logs`
---------------------------

Log file management (and logging configuration) was moved into a bundled plugin in OctoPrint 1.3.7. Refer to
:ref:`the Logging's plugins JS Client Library <sec-bundledplugins-logging-jsclientlib>` for the JS Client documentation.

The former module ``OctoPrintClient.logs`` and its methods are marked as deprecated but still work for now. New
client implementations should directly use the new module provided by the bundled plugin. Existing implementations
should adapt their used module as soon as possible.
