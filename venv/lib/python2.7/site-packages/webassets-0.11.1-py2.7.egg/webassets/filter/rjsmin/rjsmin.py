#!/usr/bin/env python
# -*- coding: ascii -*-
#
# Copyright 2011
# Andr\xe9 Malo or his licensors, as applicable
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
r"""
=====================
 Javascript Minifier
=====================

Javascript Minifier based on `jsmin.c by Douglas Crockford`_\.

This module is a re-implementation based on the semantics of jsmin.c. Usually
it produces the same results. It differs in the following ways:

- there is no error detection: unterminated string, regex and comment
  literals are treated as regular javascript code and minified as such.
- Control characters inside string and regex literals are left untouched; they
  are not converted to spaces (nor to \n)
- Newline characters are not allowed inside string and regex literals, except
  for line continuations in string literals (ECMA-5).
- rjsmin does not handle streams, but only complete strings. (However, the
  module provides a "streamy" interface).

Besides the list above it differs from direct python ports of jsmin.c in
speed. Since most parts of the logic are handled by the regex engine it's way
faster than the original python port by Baruch Even. The speed factor varies
between about 6 and 55 depending on input and python version (it gets faster
the more compressed the input already is). Compared to the speed-refactored
python port by Dave St.Germain the performance gain is less dramatic but still
between 1.2 and 7. See the docs/BENCHMARKS file for details.

rjsmin.c is a reimplementation of rjsmin.py in C and speeds it up even more.

Both python 2 and python 3 are supported.

.. _jsmin.c by Douglas Crockford:
   http://www.crockford.com/javascript/jsmin.c
"""
__author__ = "Andr\xe9 Malo"
__author__ = getattr(__author__, 'decode', lambda x: __author__)('latin-1')
__docformat__ = "restructuredtext en"
__license__ = "Apache License, Version 2.0"
__version__ = '1.0.1'
__all__ = ['jsmin', 'jsmin_for_posers']

import re as _re
from webassets.six.moves import map
from webassets.six.moves import zip


def _make_jsmin(extended=True, python_only=False):
    """
    Generate JS minifier based on `jsmin.c by Douglas Crockford`_

    .. _jsmin.c by Douglas Crockford:
       http://www.crockford.com/javascript/jsmin.c

    :Parameters:
      `extended` : ``bool``
        Extended Regexps? (using lookahead and lookbehind). This is faster,
        because it can be optimized way more. The regexps used with `extended`
        being false are only left here to allow easier porting to platforms
        without extended regex features (and for my own reference...)

      `python_only` : ``bool``
        Use only the python variant. If true, the c extension is not even
        tried to be loaded.

    :Return: Minifier
    :Rtype: ``callable``
    """
    # pylint: disable = R0912, R0914, W0612
    if not python_only:
        try:
            import _rjsmin
        except ImportError:
            pass
        else:
            return _rjsmin.jsmin
    try:
        xrange
    except NameError:
        xrange = range # pylint: disable = W0622

    space_chars = r'[\000-\011\013\014\016-\040]'

    line_comment = r'(?://[^\r\n]*)'
    space_comment = r'(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/)'
    string1 = \
        r'(?:\047[^\047\\\r\n]*(?:\\(?:[^\r\n]|\r?\n|\r)[^\047\\\r\n]*)*\047)'
    string2 = r'(?:"[^"\\\r\n]*(?:\\(?:[^\r\n]|\r?\n|\r)[^"\\\r\n]*)*")'
    strings = r'(?:%s|%s)' % (string1, string2)

    charclass = r'(?:\[[^\\\]\r\n]*(?:\\[^\r\n][^\\\]\r\n]*)*\])'
    nospecial = r'[^/\\\[\r\n]'
    if extended:
        regex = r'(?:/(?![\r\n/*])%s*(?:(?:\\[^\r\n]|%s)%s*)*/)' % (
            nospecial, charclass, nospecial
        )
    else:
        regex = (
            r'(?:/(?:[^*/\\\r\n\[]|%s|\\[^\r\n])%s*(?:(?:\\[^\r\n]|%s)%s*)*/)'
        )
        regex = regex % (charclass, nospecial, charclass, nospecial)
    pre_regex = r'[(,=:\[!&|?{};\r\n]'

    space = r'(?:%s|%s)' % (space_chars, space_comment)
    newline = r'(?:%s?[\r\n])' % line_comment

    def fix_charclass(result):
        """ Fixup string of chars to fit into a regex char class """
        pos = result.find('-')
        if pos >= 0:
            result = r'%s%s-' % (result[:pos], result[pos + 1:])

        def sequentize(string):
            """
            Notate consecutive characters as sequence

            (1-4 instead of 1234)
            """
            first, last, result = None, None, []
            for char in map(ord, string):
                if last is None:
                    first = last = char
                elif last + 1 == char:
                    last = char
                else:
                    result.append((first, last))
                    first = last = char
            if last is not None:
                result.append((first, last))
            return ''.join(['%s%s%s' % (
                chr(first),
                last > first + 1 and '-' or '',
                last != first and chr(last) or ''
            ) for first, last in result])

        return _re.sub(r'([\000-\040\047])', # for better portability
            lambda m: '\\%03o' % ord(m.group(1)), (sequentize(result)
                .replace('\\', '\\\\')
                .replace('[', '\\[')
                .replace(']', '\\]')
            )
        )

    def id_literal_(what):
        """ Make id_literal like char class """
        match = _re.compile(what).match
        result = ''.join([
            chr(c) for c in range(127) if not match(chr(c))
        ])
        return '[^%s]' % fix_charclass(result)

    def not_id_literal_(keep):
        """ Make negated id_literal like char class """
        match = _re.compile(id_literal_(keep)).match
        result = ''.join([
            chr(c) for c in range(127) if not match(chr(c))
        ])
        return r'[%s]' % fix_charclass(result)

    if extended:
        id_literal = id_literal_(r'[a-zA-Z0-9_$]')
        id_literal_open = id_literal_(r'[a-zA-Z0-9_${\[(+-]')
        id_literal_close = id_literal_(r'[a-zA-Z0-9_$}\])"\047+-]')

        space_sub = _re.compile((
            r'([^\047"/\000-\040]+)'
            r'|(%(strings)s[^\047"/\000-\040]*)'
            r'|(?:(?<=%(pre_regex)s)%(space)s*(%(regex)s[^\047"/\000-\040]*))'
            r'|(?<=%(id_literal_close)s)'
                r'%(space)s*(?:(%(newline)s)%(space)s*)+'
                r'(?=%(id_literal_open)s)'
            r'|(?<=%(id_literal)s)(%(space)s)+(?=%(id_literal)s)'
            r'|%(space)s+'
            r'|(?:%(newline)s%(space)s*)+'
        ) % locals()).sub
        def space_subber(match):
            """ Substitution callback """
            # pylint: disable = C0321
            groups = match.groups()
            if groups[0]: return groups[0]
            elif groups[1]: return groups[1]
            elif groups[2]: return groups[2]
            elif groups[3]: return '\n'
            elif groups[4]: return ' '
            return ''

        def jsmin(script): # pylint: disable = W0621
            r"""
            Minify javascript based on `jsmin.c by Douglas Crockford`_\.

            Instead of parsing the stream char by char, it uses a regular
            expression approach which minifies the whole script with one big
            substitution regex.

            .. _jsmin.c by Douglas Crockford:
               http://www.crockford.com/javascript/jsmin.c

            :Parameters:
              `script` : ``str``
                Script to minify

            :Return: Minified script
            :Rtype: ``str``
            """
            return space_sub(space_subber, '\n%s\n' % script).strip()

    else:
        not_id_literal = not_id_literal_(r'[a-zA-Z0-9_$]')
        not_id_literal_open = not_id_literal_(r'[a-zA-Z0-9_${\[(+-]')
        not_id_literal_close = not_id_literal_(r'[a-zA-Z0-9_$}\])"\047+-]')

        space_norm_sub = _re.compile((
            r'(%(strings)s)'
            r'|(?:(%(pre_regex)s)%(space)s*(%(regex)s))'
            r'|(%(space)s)+'
            r'|(?:(%(newline)s)%(space)s*)+'
        ) % locals()).sub
        def space_norm_subber(match):
            """ Substitution callback """
            # pylint: disable = C0321
            groups = match.groups()
            if groups[0]: return groups[0]
            elif groups[1]: return groups[1].replace('\r', '\n') + groups[2]
            elif groups[3]: return ' '
            elif groups[4]: return '\n'

        space_sub1 = _re.compile((
            r'[\040\n]?(%(strings)s|%(pre_regex)s%(regex)s)'
            r'|\040(%(not_id_literal)s)'
            r'|\n(%(not_id_literal_open)s)'
        ) % locals()).sub
        def space_subber1(match):
            """ Substitution callback """
            groups = match.groups()
            return groups[0] or groups[1] or groups[2]

        space_sub2 = _re.compile((
            r'(%(strings)s)\040?'
            r'|(%(pre_regex)s%(regex)s)[\040\n]?'
            r'|(%(not_id_literal)s)\040'
            r'|(%(not_id_literal_close)s)\n'
        ) % locals()).sub
        def space_subber2(match):
            """ Substitution callback """
            groups = match.groups()
            return groups[0] or groups[1] or groups[2] or groups[3]

        def jsmin(script):
            r"""
            Minify javascript based on `jsmin.c by Douglas Crockford`_\.

            Instead of parsing the stream char by char, it uses a regular
            expression approach. The script is minified with three passes:

            normalization
                Control character are mapped to spaces, spaces and newlines
                are squeezed and comments are stripped.
            space removal 1
                Spaces before certain tokens are removed
            space removal 2
                Spaces after certain tokens are remove

            .. _jsmin.c by Douglas Crockford:
               http://www.crockford.com/javascript/jsmin.c

            :Parameters:
              `script` : ``str``
                Script to minify

            :Return: Minified script
            :Rtype: ``str``
            """
            return space_sub2(space_subber2,
                space_sub1(space_subber1,
                    space_norm_sub(space_norm_subber, '\n%s\n' % script)
                )
            ).strip()
    return jsmin

jsmin = _make_jsmin()


def jsmin_for_posers(script):
    r"""
    Minify javascript based on `jsmin.c by Douglas Crockford`_\.

    Instead of parsing the stream char by char, it uses a regular
    expression approach which minifies the whole script with one big
    substitution regex.

    .. _jsmin.c by Douglas Crockford:
       http://www.crockford.com/javascript/jsmin.c

    :Warning: This function is the digest of a _make_jsmin() call. It just
              utilizes the resulting regex. It's just for fun here and may
              vanish any time. Use the `jsmin` function instead.

    :Parameters:
      `script` : ``str``
        Script to minify

    :Return: Minified script
    :Rtype: ``str``
    """
    def subber(match):
        """ Substitution callback """
        groups = match.groups()
        return (
            groups[0] or
            groups[1] or
            groups[2] or
            (groups[3] and '\n') or
            (groups[4] and ' ') or
            ''
        )

    return _re.sub(
        r'([^\047"/\000-\040]+)|((?:(?:\047[^\047\\\r\n]*(?:\\(?:[^\r\n]|\r?'
        r'\n|\r)[^\047\\\r\n]*)*\047)|(?:"[^"\\\r\n]*(?:\\(?:[^\r\n]|\r?\n|'
        r'\r)[^"\\\r\n]*)*"))[^\047"/\000-\040]*)|(?:(?<=[(,=:\[!&|?{};\r\n]'
        r')(?:[\000-\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/'
        r'))*((?:/(?![\r\n/*])[^/\\\[\r\n]*(?:(?:\\[^\r\n]|(?:\[[^\\\]\r\n]*'
        r'(?:\\[^\r\n][^\\\]\r\n]*)*\]))[^/\\\[\r\n]*)*/)[^\047"/\000-\040]*'
        r'))|(?<=[^\000-!#%&(*,./:-@\[\\^`{|~])(?:[\000-\011\013\014\016-\04'
        r'0]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/))*(?:((?:(?://[^\r\n]*)?[\r\n'
        r']))(?:[\000-\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)'
        r'*/))*)+(?=[^\000-#%-\047)*,./:-@\\-^`|-~])|(?<=[^\000-#%-,./:-@\[-'
        r'^`{-~-])((?:[\000-\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*'
        r']*\*+)*/)))+(?=[^\000-#%-,./:-@\[-^`{-~-])|(?:[\000-\011\013\014\0'
        r'16-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/))+|(?:(?:(?://[^\r\n]*)'
        r'?[\r\n])(?:[\000-\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]'
        r'*\*+)*/))*)+', subber, '\n%s\n' % script
    ).strip()


if __name__ == '__main__':
    import sys as _sys
    _sys.stdout.write(jsmin(_sys.stdin.read()))
