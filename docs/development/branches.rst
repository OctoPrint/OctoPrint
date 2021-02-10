.. _sec-development-branches:

OctoPrint's branching model
===========================

There are three main branches in OctoPrint:

``master``
    The master branch always contains the current stable release plus any changes
    since made to *documentation*, *CI related tests* or *Github meta files*. OctoPrint's actual
    code will only be modified on new releases. Will have a version number following
    the scheme ``<x>.<y>.<z>`` (e.g. ``1.5.1``).
``maintenance``
    Improvements and fixes of the current release that make up
    the next release go here. More or less continuously updated. You can consider
    this a preview of the next release version. It should be very stable at all
    times. Anything you spot in here helps tremendously with getting a rock solid
    next stable release, so if you want to help out development, running the
    ``maintenance`` branch and reporting back anything you find is a very good way
    to do that. Will usually have a version number following the scheme
    ``<x>.<y+1>.<0>.dev<commits since increase of y>`` for an OctoPrint version of ``<x>.<y>.<z>``
    (e.g. ``1.5.0.dev114``).
``devel``
    Ongoing development of what will go into the next big
    release (MAJOR version number increases) will happen on this branch. Usually
    kept stable, sometimes stuff can break though. Backwards incompatible changes will
    be encountered here. Can be considered the "bleeding edge". Will usually have a version
    number following the scheme ``<x+1>.<0>.0.dev<commits since increase of y>`` for a current
    OctoPrint version of ``<x>.<y>.<z>`` (e.g. ``2.0.0.dev123``).

There are couple more RC and staging branches that see regular use:

``staging/bugfix``
    Any preparation for potential bugfix releases takes place here.
    Version number follows the scheme ``<x>.<y>.<z+1>`` (e.g. ``1.5.1``) for a current release
    of ``<x>.<y>.<z>``.
``rc/maintenance``
    This branch is reserved for future releases that have graduated from
    the ``maintenance`` branch and are now being pushed on the "Maintenance"
    pre release channel for further testing. Version number follows the scheme
    ``<x>.<y>.<z>rc<n>`` (e.g. ``1.5.0rc1``).
``staging/maintenance``
    Any preparation for potential follow-up RCs takes place here.
    Version number follows the scheme ``<x>.<y>.<z>rc<n+1>.dev<commits since increase of n>`` (e.g.
    ``1.5.0rc2.dev3``) for a current Maintenance RC of ``<x>.<y>.<z>``.
``rc/devel``
    This branch is reserved for future releases that have graduated from
    the ``devel`` branch and are now being pushed on the "Devel" pre release channel
    for further testing. Version number follows the scheme ``<x+1>.0.0rc<n>`` (e.g. ``2.0.0rc1``)
    for a current stable OctoPrint version of ``<x>.<y>.<z>``.
``staging/devel``
    Any preparation for potential follow-up Devel RCs takes place
    here. Version number follows the scheme ``<x>.0.0rc<n+1>.dev<commits since increase of n>`` (e.g.
    ``2.0.0rc2.dev12``) for a current Devel RC of ``<x>.0.0rc<n>``.

Additionally, from time to time you might see other branches pop up in the repository.
Those usually have one of the following prefixes:

``bug/...``
    Fixes under development that are to be merged into the ``staging/bugfix``
    and later the ``master`` branch.
``fix/...``
    Fixes under development that are to be merged into the ``maintenance``
    and ``devel`` branches.
``improve/...``
    Improvements under development that are to be merged into the
    ``maintenance`` and ``devel`` branches.
``dev/...`` or ``feature/...``
    New functionality under development that is to be merged
    into the ``devel`` branch.

There are also a few older development branches that are slowly being migrated or deleted.

All these branches and branch patterns are set up to automatically get a correct :ref:`version number <sec-development-versions>`
generated through versioneer and thus should also be adhered to during development.
