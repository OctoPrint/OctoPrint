.. _sec-development-versions:

OctoPrint's versioning strategy
===============================

OctoPrint's version numbers follow `PEP440 <https://www.python.org/dev/peps/pep-0440/>`_, with a version format of
**MAJOR.MINOR.PATCH** following the contract of `semantic versioning <http://semver.org/>`_.

The **PATCH** version number will increase in case of hotfix releases [#f1]_.
Releases that only change the patch number indicate that they only contain bug fixes, and usually
only hotfixes at that. Example: ``1.5.0`` to ``1.5.1``.

The **MINOR** version number increases with releases that add new functionality while maintaining
backwards compatibility on the documented APIs (both internal and external). Example: ``1.4.x`` to ``1.5.0``.

Finally, the **MAJOR** version number increases if there are breaking API changes that concern any of the
documented interfaces (REST API, plugin interfaces, ...). Example: ``1.x.y`` to ``2.0.0``.

OctoPrint's version numbers are automatically generated using a custom versioning tool and depend on
the selected git branch, nearest git tag and commits. Unless a git tag is used for version number
determination, the version number will also contain the git hash within the local version identifier to
allow for an exact determination of the active code base (e.g. ``1.2.9.dev68+g46c7a9c``). Additionally,
instances with active uncommitted changes will contain ``.dirty`` in the local version identifier.

.. _sec-development_versions-mapping:

Version mapping
---------------

.. _sec-development-versions-mapping-2_0_0:

Version mapping for 1.12.0+ to 2.0.0+
.....................................

What was originally planned to be released as OctoPrint 1.12.0 turned into 2.0.0. Due to this, some deprecation
warnings and other information about forthcoming versions changed. If you see warnings or other kinds of information 
about changes upcoming for OctoPrint 1.12.0, 1.13.0 and so on, the mapping is the following for now:

* 1.12.0 → 2.0.0
* 1.13.0 → 2.1.0
* ... and so on

.. rubric:: Footnotes

.. [#f1] Up until 1.4.2, the PATCH version segment was the one increasing most often
         due to OctoPrint's maintenance releases but with 1.5.0 this will *fully* adhere
         to the concepts in semantic versioning mandating only bug fixes in patch releases.
         Maintenance releases will henceforth increase the MINOR segment.
