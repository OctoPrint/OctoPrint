# coding=utf8

import sys

from unidecode import unidecode
import regex as re


# Don't set regex.DEFAULT_VERSION to regex.VERSION1 cause
# this option will influence on 3rd party libs. E.g. `mailgun` and `flanker`.
# Use regex.VERSION1 regex flag.

# re.VERSION1 - New enhanced behaviour with nested sets and set operations


if sys.version_info[0] == 2:
    str_type = unicode  # Python 2
else:
    str_type = str  # Python 3


def join_words(words, separator, max_length=None):
    """
    words - iterator or list
    """

    if not max_length:
        return separator.join(words)

    words = iter(words)   # List to Generator
    try:
        text = next(words)
    except StopIteration:
        return u''

    for word in words:
        if len(text + separator + word) <= max_length:
            text += separator + word

    return text[:max_length]

# uppercase letters to translate to uppercase letters, NOT camelcase
UPPER_TO_UPPER_LETTERS_RE = \
    u'''
    (
            \p{Uppercase_Letter} {2,}                          # 2 or more adjacent letters - UP always
        |
            \p{Uppercase_Letter}                               # target one uppercase letter, then
                (?=
                    [^\p{Lowercase_Letter}…\p{Term}--,،﹐，]+    # not chars breaks possible UP (…abc.?!:;)
                    \p{Uppercase_Letter} {2}                   # and 2 uppercase letters
                )
        |
            (?<=
                \p{Uppercase_Letter} {2}                       # 2 uppercase letters
                [^\p{Lowercase_Letter}…\p{Term}--,،﹐，]+       # not chars breaks possible UP (…abc.?!:;), then
            )
            \p{Uppercase_Letter}                               # target one uppercase letter, then
            (?!
                    \p{Lowercase_Letter}                       # not lowercase letter
                |
                    […\p{Term}--,،﹐，]\p{Uppercase_Letter}      # and not dot (.?…!:;) with uppercase letter
            )
    )
    '''


class Slugify(object):

    upper_to_upper_letters_re = re.compile(UPPER_TO_UPPER_LETTERS_RE, re.VERBOSE | re.VERSION1)
    _safe_chars = ''
    _stop_words = ()

    def __init__(self, pretranslate=None, translate=unidecode, safe_chars='', stop_words=(),
                 to_lower=False, max_length=None, separator=u'-', capitalize=False,
                 fold_abbrs=False):

        self.pretranslate = pretranslate
        self.translate = translate
        self.safe_chars = safe_chars
        self.stop_words = stop_words

        self.to_lower = to_lower
        self.max_length = max_length
        self.separator = separator
        self.capitalize = capitalize
        self.fold_abbrs = fold_abbrs

    def pretranslate_dict_to_function(self, convert_dict):

        # add uppercase letters
        for letter, translation in list(convert_dict.items()):
            letter_upper = letter.upper()
            if letter_upper != letter and letter_upper not in convert_dict:
                convert_dict[letter_upper] = translation.capitalize()

        self.convert_dict = convert_dict
        PRETRANSLATE = re.compile(u'(\L<options>)', options=convert_dict)

        # translate some letters before translating
        return lambda text: PRETRANSLATE.sub(lambda m: convert_dict[m.group(1)], text)

    def set_pretranslate(self, pretranslate):
        if isinstance(pretranslate, dict):
            pretranslate = self.pretranslate_dict_to_function(pretranslate)

        elif pretranslate is None:
            pretranslate = lambda text: text

        elif not callable(pretranslate):
            error_message = u"Keyword argument 'pretranslate' must be dict, None or callable. Not {0.__class__.__name__}".format(pretranslate)
            raise ValueError(error_message)

        self._pretranslate = pretranslate

    pretranslate = property(fset=set_pretranslate)

    def set_translate(self, func):
        if func:
            self._translate = func
        else:
            self._translate = lambda text: text

    translate = property(fset=set_translate)

    def set_safe_chars(self, safe_chars):
        self._safe_chars = safe_chars
        self.apostrophe_is_not_safe = "'" not in safe_chars
        self.calc_unwanted_chars_re()

    safe_chars = property(fset=set_safe_chars)

    def set_stop_words(self, stop_words):
        self._stop_words = tuple(stop_words)
        self.calc_unwanted_chars_re()

    stop_words = property(fset=set_stop_words)

    def calc_unwanted_chars_re(self):
        unwanted_chars_re = u'[^\p{{AlNum}}{safe_chars}]+'.format(safe_chars=re.escape(self._safe_chars or ''))
        self.unwanted_chars_re = re.compile(unwanted_chars_re, re.IGNORECASE)

        if self._stop_words:
            unwanted_chars_and_words_re = unwanted_chars_re + u'|(?<!\p{AlNum})(?:\L<stop_words>)(?!\p{AlNum})'
            self.unwanted_chars_and_words_re = re.compile(unwanted_chars_and_words_re, re.IGNORECASE, stop_words=self._stop_words)
        else:
            self.unwanted_chars_and_words_re = None

    def sanitize(self, text):
        if self.apostrophe_is_not_safe:
            text = text.replace("'", '').strip()  # remove '

        if self.unwanted_chars_and_words_re:
            words = [word for word in self.unwanted_chars_and_words_re.split(text) if word]
            if words:
                return words

        words = filter(None, self.unwanted_chars_re.split(text))
        return words

    def __call__(self, text, **kwargs):

        max_length = kwargs.get('max_length', self.max_length)
        separator = kwargs.get('separator', self.separator)

        if not isinstance(text, str_type):
            text = text.decode('utf8', 'ignore')

        if kwargs.get('fold_abbrs', self.fold_abbrs):
            text = re.sub(r'(?<![\p{Letter}.])((?:\p{Letter}\.){2,})', lambda x: x.group(0).replace('.', ''), text)

        if kwargs.get('to_lower', self.to_lower):
            text = self._pretranslate(text)
            text = self._translate(text)
            text = text.lower()
        else:
            text_parts = self.upper_to_upper_letters_re.split(text)

            for position, text_part in enumerate(text_parts):
                text_part = self._pretranslate(text_part)
                text_part = self._translate(text_part)
                if position % 2:
                    text_part = text_part.upper()

                text_parts[position] = text_part

            text = u''.join(text_parts)

        words = self.sanitize(text)
        text = join_words(words, separator, max_length)

        if text and kwargs.get('capitalize', self.capitalize):
            text = text[0].upper() + text[1:]

        return text


class UniqueSlugify(Slugify):
    """
    Manage unique slugified ids
    """

    def __init__(self, *args, **kwargs):
        # don't declare uids in args to avoid problem if someone uses positional arguments on initialization
        self.uids = kwargs.pop('uids', set())
        if isinstance(self.uids, list):
            self.uids = set(self.uids)
        self.unique_check = kwargs.pop(
            "unique_check",
            lambda text, uids: self.default_unique_check(text, uids)
        )
        super(UniqueSlugify, self).__init__(*args, **kwargs)

    def __call__(self, text, **kwargs):
        # get slugified text
        text = super(UniqueSlugify, self).__call__(text, **kwargs)
        count = 0
        newtext = text
        separator = kwargs.get('separator', self.separator)
        while not self.unique_check(newtext, self.uids):
            count += 1
            newtext = "%s%s%d" % (text, separator, count)
        self.uids.add(newtext)
        return newtext

    def default_unique_check(self, text, uids):
        return text not in uids

# \p{SB=AT} = '.․﹒．'
# \p{SB=ST} = '!?՜՞։؟۔܀܁܂߹।॥၊။።፧፨᙮᜵᜶‼‽⁇⁈⁉⸮。꓿꘎꘏꤯﹖﹗！？｡'
# \p{Term}  = '!,.:;?;·։׃،؛؟۔܀܁܂܃܄܅܆܇܈܉܊܌߸߹।॥๚๛༈།༎༏༐༑༒၊။፡።፣፤፥፦፧፨᙭᙮᛫᛬᛭។៕៖៚‼‽⁇⁈⁉⸮、。꓾꓿꘍꘎꘏꤯﹐﹑﹒﹔﹕﹖﹗！，．：；？｡､'
# \p{Sterm} = '! .  ?՜՞։؟܀   ܁     ܂߹।॥၊။               ።፧፨  ᙮᜵᜶        ‼‽⁇⁈⁉⸮ 。 ꓿ ꘎꘏꤯﹒     ﹖﹗！．    ？｡'

# \p{SB=AT} = .
# \p{SB=ST} =   ! ?
# \p{Term}  = . ! ? , : ;
# \p{Sterm} = . ! ?

# \u002c - Latin comma
# \u060c - Arabic comma
# \ufe50 - Small comma
# \uff0c - Fullwidth comma

# […\p{Term}--,،﹐，] - ellipsis + Terms - commas
