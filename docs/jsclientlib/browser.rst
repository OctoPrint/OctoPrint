.. _sec-jsclientlib-browser:

:mod:`OctoPrintClient.browser`
------------------------------

.. js:function:: OctoPrintClient.browser.login(username, password, remember, opts)

   Logs the browser into OctoPrint, using the provided ``username`` and
   ``password`` as credentials. If ``remember`` is set to ``true``, the session
   will also persist across browser restarts.

   **Example:**

   .. code-block:: javascript

      OctoPrint.browser.login("myusername", "mypassword", true)
          .done(function(response) {
              // do something with the response
          });

   :param string username: Username to log in with
   :param string password: Password to log in with
   :param bool remember: "Remember me"
   :param object opts: Additional request options
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.browser.passiveLogin(opts)

   Tries to perform a passive login into OctoPrint, using existing session data
   stored in the browser's cookies.

   :param object opts: Additional request options
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.browser.logout(opts)

   Logs the browser out of OctoPrint.

   :param object opts: Additional request options
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response
