.. _sec-bundledplugins-forcelogin:

ForceLogin Plugin
=================

The ForceLogin Plugin comes bundled with OctoPrint (starting with version 1.3.10). It removes the anonymous
read-only access that up until 1.3.10 was standard when accessing OctoPrint instances without being logged in and
instead forces users to log in if they want to get any kind of information from OctoPrint.

.. _fig-bundledplugins-forcelogin:
.. figure:: ../images/bundledplugins-forcelogin-dialog.png
   :align: center
   :alt: Forced login dialog

   OctoPrint's new forced login dialog.

.. warning::

   Keep in mind that **OctoPrint does not manage your webcam**, it merely embeds it. If you have a webcam,
   it will still be accessible to users who are not logged in under its (guessable) URL. If you need to restrict
   access to your webcam, you'll need to find a way to do so directly on the webcam server which - again -
   is not OctoPrint itself.

.. note::

   If you want back the old behaviour of allowing anonymous read-only access to your OctoPrint instance, disable
   the ForceLogin Plugin in OctoPrint's plugin manager.

.. _sec-bundledplugins-forcelogin-sourcecode:

Source code
-----------

The source of the ForceLogin plugin is bundled with OctoPrint and can be found in
its source repository under ``src/octoprint/plugins/forcelogin``.
