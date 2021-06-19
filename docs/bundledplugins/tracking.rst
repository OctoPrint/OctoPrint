.. _sec-bundledplugins-tracking:

Anonymous Usage Tracking Plugin
===============================

.. versionadded:: 1.3.10

The Anonymous Usage Tracking plugin provides valuable insights into how many instances running what versions of
OctoPrint are out there, whether they are successfully completing print jobs and various other metrics.

By enabling it you help to identify problems with new releases and release candidates early on, and to better tailor
OctoPrint's future development to actual use.

For details on what gets tracked, please refer to `tracking.octoprint.org <https://tracking.octoprint.org>`_
and also the `Privacy Policy at tracking.octoprint.org <https://tracking.octoprint.org/privacy>`_.

The Anonymous Usage Tracking plugin has been bundled with OctoPrint since version 1.3.10.

.. _sec-bundledplugins-tracking-configuration:

Configuring the plugin
----------------------

The plugin supports the following configuration keys:

  * ``enabled``:  Whether to enable usage tracking. Defaults to ``false``.
  * ``unique_id``: Unique instance identifier, auto generated on first activation
  * ``server``: The tracking server to track against. Defaults to a tracking endpoint on ``https://tracking.octoprint.org``.
  * ``ping``: How often to send a ``ping`` tracking event, in seconds. Defaults to a 15min interval.
  * ``events``: Granular configuration of enabled tracking events. All default to ``true``.

    * ``startup``: Whether to track startup/shutdown events
    * ``printjob``: Whether to track print job related events (start, completion, cancel, ...)
    * ``commerror``: Whether to track communication errors with the printer
    * ``plugin``: Whether to track plugin related events (install, uninstall, ...)
    * ``update``: Whether to track update related events (update successful or not, ...)
    * ``printer``: Whether to track printer related events (connected, firmware, ...)
    * ``printer_safety_check``: Whether to track warnings of the Printer Safety Check plugin
    * ``throttled``: Whether to track throttle events detected on the underlying system

.. _sec-bundledplugins-tracking-sourcecode:

Source Code
-----------

The source of the Anonymous Usage Tracking plugin is bundled with OctoPrint and can be
found in its source repository under ``src/octoprint/plugins/tracking``.
