.. sec-jsclientlib-job:

:mod:`OctoPrint.job`
--------------------

.. js:function:: OctoPrint.job.get(opts)

   Retrieves information about the current job.

.. js:function:: OctoPrint.job.start(opts)

.. js:function:: OctoPrint.job.cancel(opts)

   Cancels the current job.

.. js:function:: OctoPrint.job.restart(opts)

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

.. js:function:: OctoPrint.job.pause(opts)

   Pauses the current job if it's running, does nothing if it's already paused.

.. js:function:: OctoPrint.job.resume(opts)

   Resumes the current job if it's currently pause, does nothing if it's running.

.. js:function:: OctoPrint.job.togglePause(opts)

   Resumes a paused job and pauses a running a print.

