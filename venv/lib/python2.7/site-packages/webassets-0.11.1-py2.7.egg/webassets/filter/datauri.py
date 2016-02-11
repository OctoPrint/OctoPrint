from base64 import b64encode
import mimetypes
import os
from webassets.utils import urlparse

from webassets.filter.cssrewrite.base import CSSUrlRewriter


__all__ = ('CSSDataUri',)


class CSSDataUri(CSSUrlRewriter):
    """Will replace CSS url() references to external files with internal
    `data: URIs <http://en.wikipedia.org/wiki/Data_URI_scheme>`_.

    The external file is now included inside your CSS, which minimizes HTTP
    requests.

    .. note::

       Data Uris have `clear disadvantages <http://stackoverflow.com/questions/5258057/images-in-css-or-html-as-data-base64>`_,
       so put some thought into if and how you would like to use them. Have
       a look at some `performance measurements <http://www.ravelrumba.com/blog/data-uris-for-css-images-more-tests-more-questions/>`_.

    The filter respects a ``DATAURI_MAX_SIZE`` option, which is the maximum
    size (in bytes) of external files to include. The default limit is what
    I think should be a reasonably conservative number, 2048 bytes.
    """

    name = 'datauri'
    options = {
        'max_size': 'DATAURI_MAX_SIZE',
    }

    def replace_url(self, url):
        if url.startswith('data:'):
            # Don't even both sending data: through urlparse(),
            # who knows how well it'll deal with a lot of data.
            return

        # Ignore any urls which are not relative
        parsed = urlparse.urlparse(url)
        if parsed.scheme or parsed.netloc or parsed.path.startswith('/'):
            return

        # Since this runs BEFORE cssrewrite, we can thus assume that urls
        # will be relative to the file location.
        #
        # Notes:
        #  - Django might need to override this filter for staticfiles if it
        #    it should be possible to resolve cross-references between
        #    different directories.
        #  - For Flask-Assets blueprints, the logic might need to be:
        #    1) Take source_path, convert into correct url via absurl().
        #    2) Join with the URL be be replaced.
        #    3) Convert url back to the filesystem path to which the url
        #       would map (the hard part?).
        #

        filename = os.path.join(os.path.dirname(self.source_path), url)

        try:
            if os.stat(filename).st_size <= (self.max_size or 2048):
                with open(filename, 'rb') as f:
                    data = b64encode(f.read())
                return 'data:%s;base64,%s' % (
                    mimetypes.guess_type(filename)[0], data.decode())
        except (OSError, IOError):
            # Ignore the file not existing.
            # TODO: When we have a logging system, this could produce a warning
            return
