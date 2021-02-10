
from .main import Slugify, UniqueSlugify
from .alt_translates import *


slugify = Slugify()
unique_slugify = UniqueSlugify()
slugify_unicode = Slugify(translate=None)

slugify_url = Slugify()
slugify_url.to_lower = True
slugify_url.stop_words = ('a', 'an', 'the')
slugify_url.max_length = 200

slugify_filename = Slugify()
slugify_filename.separator = '_'
slugify_filename.safe_chars = '-.'
slugify_filename.max_length = 255

slugify_ru = Slugify(pretranslate=CYRILLIC)
slugify_de = Slugify(pretranslate=GERMAN)
slugify_el = Slugify(pretranslate=GREEK)


# Legacy code
def deprecate_init(Klass):
    class NewKlass(Klass):
        def __init__(self, *args, **kwargs):
            import warnings
            warnings.simplefilter('once')
            warnings.warn("'slugify.get_slugify' is deprecated; use 'slugify.Slugify' instead.",
                          DeprecationWarning, stacklevel=2)
            super(NewKlass, self).__init__(*args, **kwargs)
    return NewKlass

# get_slugify was deprecated in 2014, march 31
get_slugify = deprecate_init(Slugify)
