.. _sec-bundledplugins-errortracking:

Error Tracking Plugin
=====================

.. versionadded:: 1.3.11

The Error Tracking plugin will cause any logged exceptions in the server and the browser interface to be sent to
OctoPrint's `Sentry instance <https://sentry.io/>`_.

By enabling it you help to gather detailed information on the cause of bugs or other issues. This is especially
valuable on release candidates, which is why this plugin will also prompt you to enable error tracking if it detects
that you are subscribed to an RC release channel.

By default, even when enabled it will only be active if you are running a released OctoPrint version, so either a stable
release or a release candidate.

The Error Tracking plugin is using a Sentry instance kindly provided by `sentry.io <https://sentry.io/>`_. For information on their service
please refer to their `Security & Compliance documentation <https://sentry.io/security/>`_
and their `Privacy Policy <https://sentry.io/privacy/>`_.

The Error Tracking plugin has been bundled with OctoPrint since version 1.3.11.

.. _sec-bundledplugins-errortracking-configuration:

Configuring the plugin
----------------------

The plugin supports the following configuration keys:

  * ``enabled``:  Whether to enable error tracking. Defaults to ``false``.
  * ``enabled_unreleased``: Whether to also enable tracking on unreleased OctoPrint versions (anything not stable releases
    or release candidates). Defaults to ``false``.
  * ``unique_id``: Unique instance identifier, auto generated on first activation

.. _sec-bundledplugins-errortracking-sourcecode:

Source Code
-----------

The source of the Error Tracking plugin is bundled with OctoPrint and can be
found in its source repository under ``src/octoprint/plugins/errortracking``.
