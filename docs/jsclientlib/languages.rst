.. sec-jsclientlib-languages:

:mod:`OctoPrint.languages`
--------------------------

.. js:function:: OctoPrint.languages.list(opts)

   Retrieves a list of available language packs.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrint.languages.upload(file)

   Uploads a language pack.

   :param object or string file: The file to upload, see :js:func:`OctoPrint.upload` for more details
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrint.languages.delete(locale, pack, opts)

   Deletes the language pack ``pack`` for the specified locale ``locale``.

   :param string locale: The locale for which to delete the language pack
   :param string pack: The identifier of the pack to delete
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

