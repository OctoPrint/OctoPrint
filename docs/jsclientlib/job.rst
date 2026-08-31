.. _sec-jsclientlib-job:

.. js:module:: OctoPrintClient.job

``OctoPrintClient.job``
-----------------------

.. js:function:: get(opts)

   Retrieves information about the current job.

   See :ref:`Retrieve information about the current job <sec-api-job-information>` for details.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: start(opts)

   Starts the current job.

   See :ref:`Issue a job command <sec-api-jobs-command>` for details.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: cancel(opts)

   Cancels the current job.

   See :ref:`Issue a job command <sec-api-jobs-command>` for details.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: restart(opts)

   Restarts the current job. This is equivalent to cancelling and immediately restarting
   the job.

   **Example:**

   .. code-block:: javascript

      OctoPrint.job.restart();

      // the above is a shorthand for:

      OctoPrint.job.cancel()
          .done(function(response) {
              OctoPrint.job.start();
          });

   See :ref:`Issue a job command <sec-api-jobs-command>` for details.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: pause(opts)

   Pauses the current job if it's running, does nothing if it's already paused.

   See :ref:`Issue a job command <sec-api-jobs-command>` for details.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: resume(opts)

   Resumes the current job if it's currently paused, does nothing if it's running.

   See :ref:`Issue a job command <sec-api-jobs-command>` for details.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: togglePause(opts)

   Resumes a paused and pauses a running job.

   See :ref:`Issue a job command <sec-api-jobs-command>` for details.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response
