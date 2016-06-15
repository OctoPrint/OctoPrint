.. sec-jsclientlib-browser:

:mod:`OctoPrint.browser`
------------------------

.. js:function:: OctoPrint.browser.login(username, password, remember, opts)

   Logs the browser into OctoPrint, using the provided ``username`` and
   ``password`` as credentials. If ``remember`` is set to ``true``, the session
   will also persist across browser restarts.

   :param string username: Username to log in with
   :param string password: Password to log in with
   :param bool remember: "Remember me"
   :param object opts: Additional request options
   :returns Promise: A promise for the performed login request

.. js:function:: OctoPrint.browser.passiveLogin(opts)

   Tries to perform a passive login into OctoPrint, using existing session data
   stored in the browser's cookies.

   :param object opts: Additional request options
   :returns Promise: A promise for the performed login request

.. js:function:: OctoPrint.browser.logout(opts)

   Logs the browser out of OctoPrint.

   :param object opts: Additional request options
   :returns Promise: A promise for the performed logout request
