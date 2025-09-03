.. _sec-development-branches:

OctoPrint's branching model
===========================

There are two main branches in OctoPrint:

``main``
    The main branch always contains the current stable release plus any changes
    since made to *documentation*, *CI related tests* or *Github meta files*. OctoPrint's actual
    code will only be modified on new releases. Will have a version number following
    the scheme ``<x>.<y>.<z>`` (e.g. ``1.11.2``).
``dev``
    Ongoing development of what will become the next non-bugfix release.
    More or less continuously updated. You can consider this a preview of the next
    release version. It should be very stable at all times. Anything you spot in here
    helps tremendously with getting a rock solid next stable release, so if you want
    to help out development, running the ``dev`` branch and reporting back anything you
    find is a very good way to do that. Will usually have a version number following the scheme
    ``<x>.<y+1>.<0>.dev<commits since increase of y>`` for an OctoPrint version of ``<x>.<y>.<z>``
    (e.g. ``1.12.0.dev114`` for a stable ``1.11.2``). On a backwards incompatible release, it
    will be ``<x+1>.0.0.dev<commits since increase of x>`` (e.g. ``2.0.0.dev38`` for a stable ``1.11.2``).

There are couple more bugfix and RC related branches that see regular use:

``bugfix``
    Any preparation for potential bugfix releases takes place here.
    Version number follows the scheme ``<x>.<y>.<z+1>.dev<commits since increase of z>`` for a current release
    of ``<x>.<y>.<z>`` (e.g. ``1.11.3.dev4`` for a stable ``1.11.2``).
``next``
    This branch is reserved for future releases that have graduated from
    the ``dev`` branch and are now being pushed on the "Maintenance"
    pre release channel for further testing. Version number usually follows the scheme
    ``<x>.<y+1>.0rc<n>`` for a current release of ``<x>.<y>.<z>`` (e.g. ``1.12.0rc1`` for a stable ``1.11.2``).
    On a backwards incompatible release, it will be ``<x+1>.0.0rc<n>`` (e.g. ``2.0.0rc1`` for a stable ``1.11.2``).

Additionally, from time to time you might see other branches pop up in the repository.
Those usually have one of the following prefixes:

``bug/...``
    Fixes under development that are to be merged into the ``bugfix``
    and later the ``main`` branch.
``regression/...``
    Fixes for regressions discovered in the current RC that are to be merged into the ``next``
    branch.
``wip/...``
    Changes under development that are to be merged into the ``dev`` branch.

There are also a few older development branches that are slowly being migrated or deleted.

All these branches and branch patterns are set up to automatically get a correct :ref:`version number <sec-development-versions>`
generated through a custom versioning tool and thus should also be adhered to during development.

.. note::

   The branching model was changed in September of 2025. To summarize the changes:

   ``master``
       Renamed to ``main``
   ``maintenance``
       Renamed to ``dev``
   ``staging/bugfix``
       Renamed to ``bugfix``
   ``staging/rc``, ``rc/maintenance``
       Roles merged into one now named ``next``
   ``devel``, ``staging/devel``, ``rc/devel``
       Removed
