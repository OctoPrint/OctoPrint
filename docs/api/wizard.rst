.. _sec-api-wizard:

******
Wizard
******

.. note::

   All wizard operations require either admin rights or the ``firstRun`` flag to be ``true``.

.. contents::

.. _sec-api-wizard-retrieve:

Retrieve additional data about registered wizards
=================================================

.. http:get:: /setup/wizard

   Retrieves additional data about the registered wizards.

   Returns a :http:statuscode:`200` with an object mapping wizard identifiers to :ref:`wizard data entries <sec-api-wizard-datamodel-wizarddata>`.

.. _sec-api-wizard-finish:

Finish wizards
==============

.. http:post:: /setup/wizard

   Inform wizards that the wizard dialog has been finished.

   Expects a JSON request body containing a property ``handled`` which holds a list of wizard identifiers
   which were handled (not skipped) in the wizard dialog.

   Will call :func:`octoprint.plugin.WizardPlugin.on_wizard_finish` for all registered wizard plugins,
   supplying the information whether the wizard plugin's identifier was within the list of ``handled``
   wizards or not.

   :json handled: A list of handled wizards

.. _sec-api-wizard-datamodel:

Data model
==========

.. _sec-api-wizard-datamodel-wizarddata:

Wizard data entry
-----------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``required``
     - 1
     - bool
     - Whether the wizard needs to be run (true) or not (false)
   * - ``details``
     - 1
     - object
     - Details for the wizard's UI provided by the wizard plugin
   * - ``version``
     - 1
     - int or null
     - Version of the wizard
   * - ``ignored``
     - 1
     - bool
     - Whether the wizard has already been seen/is ignored (true) or not (false)
