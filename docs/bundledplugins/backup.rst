.. _sec-bundledplugins-backup:

Backup Plugin
=============

The OctoPrint Backup Plugin comes bundled with OctoPrint (starting with 1.3.10).

It allows the creation and restoration of backups of OctoPrint's settings, data and installed plugins [#]_.

This allows easy migration
to newly setup instances as well as making regular backups to prevent data loss.

.. _fig-bundledplugins-backup-settings:
.. figure:: ../images/bundledplugins-backup-settings.png
   :align: center
   :alt: OctoPrint Backup Plugin

   The plugin's settings panel with existing backups, the backup creation and restore sections.

As long as plugins adhere to the standard of storing their data and settings in OctoPrint's plugin data folders, their
data will be part of the backup. Note that the backups made by the Backup Plugin will *not* be part of any backups -
you'll need to persist the resulting zip files yourself!

.. _sec-bundledplugins-backup-cli:

Command line usage
------------------

The Backup Plugin implements a command line interface that allows creation and restoration of backups.
It adds two new commands, ``backup:backup`` and ``backup_restore``.

.. code-block:: none

   $ octoprint plugins backup:backup --help
     Initializing settings & plugin subsystem...
     Usage: octoprint plugins backup:backup [OPTIONS]

     Creates a new backup.

     Options:
       --exclude TEXT  Identifiers of data folders to exclude, e.g. 'uploads' to
                       exclude uploads or 'timelapse' to exclude timelapses.
       --help          Show this message and exit.

   $ octoprint plugins backup:restore --help
     Initializing settings & plugin subsystem...
     Usage: octoprint plugins backup:restore [OPTIONS] PATH

       Restores an existing backup from the backup zip provided as argument.

       OctoPrint does not need to run for this to proceed.

     Options:
       --help  Show this message and exit.

.. note::

   The ``backup:backup`` command can be useful in combination with a cronjob to create backups in regular intervals.

.. _sec-bundledplugins-backup-sourcecode:

Source code
-----------

The source of the Backup plugin is bundled with OctoPrint and can be found in
its source repository under ``src/octoprint/plugins/backup``.

.. [#] Note that only those plugins that are available on `OctoPrint's official plugin repository <https://plugins.octoprint.org>`_
       can be automatically restored. If you have plugins installed that are not available on there you'll get their
       names and - if available - homepage URL displayed after restore in order to be able to manually reinstall them.
