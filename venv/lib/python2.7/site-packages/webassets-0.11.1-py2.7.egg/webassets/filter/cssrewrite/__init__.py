import os
from os.path import join
from webassets.utils import common_path_prefix
from webassets.utils import urlparse
from . import urlpath
try:
    from collections import OrderedDict
except ImportError:
    # Use an ordered dict when available, otherwise we simply don't
    # support ordering - it's just a nice bonus.
    OrderedDict = dict

from .base import CSSUrlRewriter, addsep, path2url


__all__ = ('CSSRewrite',)


class CSSRewrite(CSSUrlRewriter):
    """Source filter that rewrites relative urls in CSS files.

    CSS allows you to specify urls relative to the location of the CSS file.
    However, you may want to store your compressed assets in a different place
    than source files, or merge source files from different locations. This
    would then break these relative CSS references, since the base URL changed.

    This filter transparently rewrites CSS ``url()`` instructions in the source
    files to make them relative to the location of the output path. It works as
    a *source filter*, i.e. it is applied individually to each source file
    before they are merged.

    No configuration is necessary.

    The filter also supports a manual mode::

        get_filter('cssrewrite', replace={'old_directory':'/custom/path/'})

    This will rewrite all urls that point to files within ``old_directory`` to
    use ``/custom/path`` as a prefix instead.

    You may plug in your own replace function::

        get_filter('cssrewrite', replace=lambda url: re.sub(r'^/?images/', '/images/', url))
        get_filter('cssrewrite', replace=lambda url: '/images/'+url[7:] if url.startswith('images/') else url)
    """

    # TODO: If we want to support inline assets, this needs to be
    # updated to optionally convert URLs to absolute ones based on
    # MEDIA_URL.

    name = 'cssrewrite'
    max_debug_level = 'merge'

    def __init__(self, replace=False):
        super(CSSRewrite, self).__init__()
        self.replace = replace

    def unique(self):
        # Allow mixing the standard version of this filter, and replace mode.
        return self.replace

    def input(self, _in, out, **kw):
        if self.replace not in (False, None) and not callable(self.replace):
            # For replace mode, make sure we have all the directories to be
            # rewritten in form of a url, so we can later easily match it
            # against the urls encountered in the CSS.
            replace_dict = False
            root = addsep(self.ctx.directory)
            replace_dict = OrderedDict()
            for repldir, sub in self.replace.items():
                repldir = addsep(os.path.normpath(join(root, repldir)))
                replurl = path2url(repldir[len(common_path_prefix([root, repldir])):])
                replace_dict[replurl] = sub
            self.replace_dict = replace_dict

        return super(CSSRewrite, self).input(_in, out, **kw)

    def replace_url(self, url):
        # Replace mode: manually adjust the location of files
        if callable(self.replace):
            return self.replace(url)
        elif self.replace is not False:
            for to_replace, sub in self.replace_dict.items():
                targeturl = urlparse.urljoin(self.source_url, url)
                if targeturl.startswith(to_replace):
                    url = "%s%s" % (sub, targeturl[len(to_replace):])
                    # Only apply the first match
                    break

        # Default mode: auto correct relative urls
        else:
            # If path is an absolute one, keep it
            parsed = urlparse.urlparse(url)
            if not parsed.scheme and not parsed.path.startswith('/'):
                abs_source_url = urlparse.urljoin(self.source_url, url)

                # relpath() will not detect this case
                if urlparse.urlparse(abs_source_url).scheme:
                    return abs_source_url

                # rewritten url: relative path from new location (output)
                # to location of referenced file (source + current url)
                url = urlpath.relpath(self.output_url, abs_source_url)

        return url

    def get_additional_cache_keys(self, **kw):
        if 'output_path' in kw:
            return [os.path.dirname(kw['output_path'])]
        return []
