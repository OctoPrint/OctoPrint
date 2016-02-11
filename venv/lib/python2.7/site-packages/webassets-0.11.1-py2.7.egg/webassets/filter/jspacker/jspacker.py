from __future__ import print_function
##  ParseMaster, version 1.0 (pre-release) (2005/05/12) x6
##  Copyright 2005, Dean Edwards
##  Web: http://dean.edwards.name/
##
##  This software is licensed under the CC-GNU LGPL
##  Web: http://creativecommons.org/licenses/LGPL/2.1/
##
##  Ported to Python by Florian Schulze

import os, re
import sys
if sys.version < '3':
    integer_types = (int, long,)
else:
    integer_types = (int,)

# a multi-pattern parser

class Pattern:
    def __init__(self, expression, replacement, length):
        self.expression = expression
        self.replacement = replacement
        self.length = length

    def __str__(self):
        return "(" + self.expression + ")"

class Patterns(list):
    def __str__(self):
        return '|'.join([str(e) for e in self])

class ParseMaster:
    # constants
    EXPRESSION = 0
    REPLACEMENT = 1
    LENGTH = 2
    GROUPS = re.compile(r"""\(""", re.M)#g
    SUB_REPLACE = re.compile(r"""\$\d""", re.M)
    INDEXED = re.compile(r"""^\$\d+$""", re.M)
    TRIM = re.compile(r"""(['"])\1\+(.*)\+\1\1$""", re.M)
    ESCAPE = re.compile(r"""\\.""", re.M)#g
    #QUOTE = re.compile(r"""'""", re.M)
    DELETED = re.compile("""\x01[^\x01]*\x01""", re.M)#g

    def __init__(self):
        # private
        self._patterns = Patterns()   # patterns stored by index
        self._escaped = []
        self.ignoreCase = False
        self.escapeChar = None

    def DELETE(self, match, offset):
        return "\x01" + match.group(offset) + "\x01"

    def _repl(self, a, o, r, i):
        while (i):
            m = a.group(o+i-1)
            if m is None:
                s = ""
            else:
                s = m
            r = r.replace("$" + str(i), s)
            i = i - 1
        r = ParseMaster.TRIM.sub("$1", r)
        return r

    # public
    def add(self, expression="^$", replacement=None):
        if replacement is None:
            replacement = self.DELETE
        # count the number of sub-expressions
        #  - add one because each pattern is itself a sub-expression
        length = len(ParseMaster.GROUPS.findall(self._internalEscape(str(expression)))) + 1
        # does the pattern deal with sub-expressions?
        if (isinstance(replacement, str) and ParseMaster.SUB_REPLACE.match(replacement)):
            # a simple lookup? (e.g. "$2")
            if (ParseMaster.INDEXED.match(replacement)):
                # store the index (used for fast retrieval of matched strings)
                replacement = int(replacement[1:]) - 1
            else: # a complicated lookup (e.g. "Hello $2 $1")
                # build a function to do the lookup
                i = length
                r = replacement
                replacement = lambda a,o: self._repl(a,o,r,i)
        # pass the modified arguments
        self._patterns.append(Pattern(expression, replacement, length))

    # execute the global replacement
    def execute(self, string):
        if self.ignoreCase:
            r = re.compile(str(self._patterns), re.I | re.M)
        else:
            r = re.compile(str(self._patterns), re.M)
        string = self._escape(string, self.escapeChar)
        string = r.sub(self._replacement, string)
        string = self._unescape(string, self.escapeChar)
        string = ParseMaster.DELETED.sub("", string)
        return string

    # clear the patterns collections so that this object may be re-used
    def reset(self):
        self._patterns = Patterns()

    # this is the global replace function (it's quite complicated)
    def _replacement(self, match):
        i = 1
        # loop through the patterns
        for pattern in self._patterns:
            if match.group(i) is not None:
                replacement = pattern.replacement
                if callable(replacement):
                    return replacement(match, i)
                elif isinstance(replacement, integer_types):
                    return match.group(replacement+i)
                else:
                    return replacement
            else:
                i = i+pattern.length

    # encode escaped characters
    def _escape(self, string, escapeChar=None):
        def repl(match):
            char = match.group(1)
            self._escaped.append(char)
            return escapeChar
        if escapeChar is None:
            return string
        r = re.compile("\\"+escapeChar+"(.)", re.M)
        result = r.sub(repl, string)
        return result

    # decode escaped characters
    def _unescape(self, string, escapeChar=None):
        def repl(match):
            try:
                #result = eval("'"+escapeChar + self._escaped.pop(0)+"'")
                result = escapeChar + self._escaped.pop(0)
                return result
            except IndexError:
                return escapeChar
        if escapeChar is None:
            return string
        r = re.compile("\\"+escapeChar, re.M)
        result = r.sub(repl, string)
        return result

    def _internalEscape(self, string):
        return ParseMaster.ESCAPE.sub("", string)


##   packer, version 2.0 (2005/04/20)
##   Copyright 2004-2005, Dean Edwards
##   License: http://creativecommons.org/licenses/LGPL/2.1/

##  Ported to Python by Florian Schulze

## http://dean.edwards.name/packer/

class JavaScriptPacker:
    def __init__(self):
        self._basicCompressionParseMaster = self.getCompressionParseMaster(False)
        self._specialCompressionParseMaster = self.getCompressionParseMaster(True)

    def basicCompression(self, script):
        return self._basicCompressionParseMaster.execute(script)

    def specialCompression(self, script):
        return self._specialCompressionParseMaster.execute(script)

    def getCompressionParseMaster(self, specialChars):
        IGNORE = "$1"
        parser = ParseMaster()
        parser.escapeChar = '\\'
        # protect strings
        parser.add(r"""'[^']*?'""", IGNORE)
        parser.add(r'"[^"]*?"', IGNORE)
        # remove comments
        parser.add(r"""//[^\n\r]*?[\n\r]""")
        parser.add(r"""/\*[^*]*?\*+([^/][^*]*?\*+)*?/""")
        # protect regular expressions
        parser.add(r"""\s+(\/[^\/\n\r\*][^\/\n\r]*\/g?i?)""", "$2")
        parser.add(r"""[^\w\$\/'"*)\?:]\/[^\/\n\r\*][^\/\n\r]*\/g?i?""", IGNORE)
        # remove: ;;; doSomething();
        if specialChars:
            parser.add(""";;;[^\n\r]+[\n\r]""")
        # remove redundant semi-colons
        parser.add(r""";+\s*([};])""", "$2")
        # remove white-space
        parser.add(r"""(\b|\$)\s+(\b|\$)""", "$2 $3")
        parser.add(r"""([+\-])\s+([+\-])""", "$2 $3")
        parser.add(r"""\s+""", "")
        return parser

    def getEncoder(self, ascii):
        mapping = {}
        base = ord('0')
        mapping.update(dict([(i, chr(i+base)) for i in range(10)]))
        base = ord('a')
        mapping.update(dict([(i+10, chr(i+base)) for i in range(26)]))
        base = ord('A')
        mapping.update(dict([(i+36, chr(i+base)) for i in range(26)]))
        base = 161
        mapping.update(dict([(i+62, chr(i+base)) for i in range(95)]))

        # zero encoding
        # characters: 0123456789
        def encode10(charCode):
            return str(charCode)

        # inherent base36 support
        # characters: 0123456789abcdefghijklmnopqrstuvwxyz
        def encode36(charCode):
            l = []
            remainder = charCode
            while 1:
                result, remainder = divmod(remainder, 36)
                l.append(mapping[remainder])
                if not result:
                    break
                remainder = result
            l.reverse()
            return "".join(l)

        # hitch a ride on base36 and add the upper case alpha characters
        # characters: 0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ
        def encode62(charCode):
            l = []
            remainder = charCode
            while 1:
                result, remainder = divmod(remainder, 62)
                l.append(mapping[remainder])
                if not result:
                    break
                remainder = result
            l.reverse()
            return "".join(l)

        # use high-ascii values
        def encode95(charCode):
            l = []
            remainder = charCode
            while 1:
                result, remainder = divmod(remainder, 95)
                l.append(mapping[remainder+62])
                if not result:
                    break
                remainder = result
            l.reverse()
            return "".join(l)

        if ascii <= 10:
            return encode10
        elif ascii <= 36:
            return encode36
        elif ascii <= 62:
            return encode62
        return encode95

    def escape(self, script):
        script = script.replace("\\","\\\\")
        script = script.replace("'","\\'")
        script = script.replace('\n','\\n')
        #return re.sub(r"""([\\'](?!\n))""", "\\$1", script)
        return script

    def escape95(self, script):
        result = []
        for x in script:
            if x>'\xa1':
                x = "\\x%0x" % ord(x)
            result.append(x)
        return "".join(result)

    def encodeKeywords(self, script, encoding, fastDecode):
        # escape high-ascii values already in the script (i.e. in strings)
        if (encoding > 62):
            script = self.escape95(script)
        # create the parser
        parser = ParseMaster()
        encode = self.getEncoder(encoding)
        # for high-ascii, don't encode single character low-ascii
        if encoding > 62:
            regexp = r"""\w\w+"""
        else:
            regexp = r"""\w+"""
        # build the word list
        keywords = self.analyze(script, regexp, encode)
        encoded = keywords['encoded']
        # encode
        def repl(match, offset):
            return encoded.get(match.group(offset), "")
        parser.add(regexp, repl)
        # if encoded, wrap the script in a decoding function
        script = parser.execute(script)
        script = self.bootStrap(script, keywords, encoding, fastDecode)
        return script

    def analyze(self, script, regexp, encode):
        # analyse
        # retreive all words in the script
        regexp = re.compile(regexp, re.M)
        all = regexp.findall(script)
        sorted = [] # list of words sorted by frequency
        encoded = {} # dictionary of word->encoding
        protected = {} # instances of "protected" words
        if all:
            unsorted = []
            _protected = {}
            values = {}
            count = {}
            all.reverse()
            for word in all:
                word = "$"+word
                if word not in count:
                    count[word] = 0
                    j = len(unsorted)
                    unsorted.append(word)
                    # make a dictionary of all of the protected words in this script
                    #  these are words that might be mistaken for encoding
                    values[j] = encode(j)
                    _protected["$"+values[j]] = j
                count[word] = count[word] + 1
            # prepare to sort the word list, first we must protect
            #  words that are also used as codes. we assign them a code
            #  equivalent to the word itself.
            # e.g. if "do" falls within our encoding range
            #      then we store keywords["do"] = "do";
            # this avoids problems when decoding
            sorted = [None] * len(unsorted)
            for word in unsorted:
                if word in _protected and isinstance(_protected[word], int):
                    sorted[_protected[word]] = word[1:]
                    protected[_protected[word]] = True
                    count[word] = 0
            unsorted.sort(key=lambda a: count[a])
            j = 0
            for i in range(len(sorted)):
                if sorted[i] is None:
                    sorted[i]  = unsorted[j][1:]
                    j = j + 1
                encoded[sorted[i]] = values[i]
        return {'sorted': sorted, 'encoded': encoded, 'protected': protected}

    def encodePrivate(self, charCode):
        return "_"+str(charCode)

    def encodeSpecialChars(self, script):
        parser = ParseMaster()
        # replace: $name -> n, $$name -> $$na
        def repl(match, offset):
            #print offset, match.groups()
            length = len(match.group(offset + 2))
            start = length - max(length - len(match.group(offset + 3)), 0)
            return match.group(offset + 1)[start:start+length] + match.group(offset + 4)
        parser.add(r"""((\$+)([a-zA-Z\$_]+))(\d*)""", repl)
        # replace: _name -> _0, double-underscore (__name) is ignored
        regexp = r"""\b_[A-Za-z\d]\w*"""
        # build the word list
        keywords = self.analyze(script, regexp, self.encodePrivate)
        # quick ref
        encoded = keywords['encoded']
        def repl(match, offset):
            return encoded.get(match.group(offset), "")
        parser.add(regexp, repl)
        return parser.execute(script)

    # build the boot function used for loading and decoding
    def bootStrap(self, packed, keywords, encoding, fastDecode):
        ENCODE = re.compile(r"""\$encode\(\$count\)""")
        # $packed: the packed script
        #packed = self.escape(packed)
        #packed = [packed[x*10000:(x+1)*10000] for x in range((len(packed)/10000)+1)]
        #packed = "'" + "'+\n'".join(packed) + "'\n"
        packed = "'" + self.escape(packed) + "'"

        # $count: number of words contained in the script
        count = len(keywords['sorted'])

        # $ascii: base for encoding
        ascii = min(count, encoding) or 1

        # $keywords: list of words contained in the script
        for i in keywords['protected']:
            keywords['sorted'][i] = ""
        # convert from a string to an array
        keywords = "'" + "|".join(keywords['sorted']) + "'.split('|')"

        encoding_functions = {
            10: """ function($charCode) {
                        return $charCode;
                    }""",
            36: """ function($charCode) {
                        return $charCode.toString(36);
                    }""",
            62: """ function($charCode) {
                        return ($charCode < _encoding ? "" : arguments.callee(parseInt($charCode / _encoding))) +
                            (($charCode = $charCode % _encoding) > 35 ? String.fromCharCode($charCode + 29) : $charCode.toString(36));
                    }""",
            95: """ function($charCode) {
                        return ($charCode < _encoding ? "" : arguments.callee($charCode / _encoding)) +
                            String.fromCharCode($charCode % _encoding + 161);
                    }"""
        }

        # $encode: encoding function (used for decoding the script)
        encode = encoding_functions[encoding]
        encode = encode.replace('_encoding',"$ascii")
        encode = encode.replace('arguments.callee', "$encode")
        if ascii > 10:
            inline = "$count.toString($ascii)"
        else:
            inline = "$count"
        # $decode: code snippet to speed up decoding
        if fastDecode:
            # create the decoder
            decode = r"""// does the browser support String.replace where the
                        //  replacement value is a function?
                        if (!''.replace(/^/, String)) {
                            // decode all the values we need
                            while ($count--) $decode[$encode($count)] = $keywords[$count] || $encode($count);
                            // global replacement function
                            $keywords = [function($encoded){return $decode[$encoded]}];
                            // generic match
                            $encode = function(){return'\\w+'};
                            // reset the loop counter -  we are now doing a global replace
                            $count = 1;
                        }"""
            if encoding > 62:
                decode = decode.replace('\\\\w', "[\\xa1-\\xff]")
            else:
                # perform the encoding inline for lower ascii values
                if ascii < 36:
                    decode = ENCODE.sub(inline, decode)
            # special case: when $count==0 there ar no keywords. i want to keep
            #  the basic shape of the unpacking funcion so i'll frig the code...
            if not count:
                raise NotImplemented
                #) $decode = $decode.replace(/(\$count)\s*=\s*1/, "$1=0");


        # boot function
        unpack = r"""function($packed, $ascii, $count, $keywords, $encode, $decode) {
                        while ($count--)
                            if ($keywords[$count])
                                $packed = $packed.replace(new RegExp("\\b" + $encode($count) + "\\b", "g"), $keywords[$count]);
                        return $packed;
                    }"""
        if fastDecode:
            # insert the decoder
            #unpack = re.sub(r"""\{""", "{" + decode + ";", unpack)
            unpack = unpack.replace('{', "{" + decode + ";", 1)

        if encoding > 62: # high-ascii
            # get rid of the word-boundaries for regexp matches
            unpack = re.sub(r"""'\\\\b'\s*\+|\+\s*'\\\\b'""", "", unpack)
        if ascii > 36 or encoding > 62 or fastDecode:
            # insert the encode function
            #unpack = re.sub(r"""\{""", "{$encode=" + encode + ";", unpack)
            unpack = unpack.replace('{', "{$encode=" + encode + ";", 1)
        else:
            # perform the encoding inline
            unpack = ENCODE.sub(inline, unpack)
        # pack the boot function too
        unpack = self.pack(unpack, 0, False, True)

        # arguments
        params = [packed, str(ascii), str(count), keywords]
        if fastDecode:
            # insert placeholders for the decoder
            params.extend(['0', "{}"])

        # the whole thing
        return "eval(" + unpack + "(" + ",".join(params) + "))\n";

    def pack(self, script, encoding=0, fastDecode=False, specialChars=False, compaction=True):
        script = script+"\n"
        self._encoding = encoding
        self._fastDecode = fastDecode
        if specialChars:
            script = self.specialCompression(script)
            script = self.encodeSpecialChars(script)
        else:
            if compaction:
                script = self.basicCompression(script)
        if encoding:
            script = self.encodeKeywords(script, encoding, fastDecode)
        return script

def run():
    p = JavaScriptPacker()
    script = open('test_plone.js').read()
    result = p.pack(script, compaction=False, encoding=62, fastDecode=True)
    open('output.js','w').write(result)

def run1():

    test_scripts = []

    test_scripts.append(("""// -----------------------------------------------------------------------
// public interface
// -----------------------------------------------------------------------

cssQuery.toString = function() {
    return "function cssQuery() {\n  [version " + version + "]\n}";
};""", 0, False, False, """cssQuery.toString=function(){return"function cssQuery() {\n  [version "+version+"]\n}"};"""))

    test_scripts.append(("""function test(_localvar) {
    var $name = 'foo';
    var $$dummy = 2;

    return $name + $$dummy;
}""", 0, False, True, """function test(_0){var n='foo';var du=2;return n+du}"""))

    test_scripts.append(("""function _test($localvar) {
    var $name = 1;
    var _dummy = 2;
    var __foo = 3;

    return $name + _dummy + $localvar + __foo;
}""", 0, False, True, """function _1(l){var n=1;var _0=2;var __foo=3;return n+_0+l+__foo}"""))

    test_scripts.append(("""function _test($localvar) {
    var $name = 1;
    var _dummy = 2;
    var __foo = 3;

    return $name + _dummy + $localvar + __foo;
}

function _bar(_ocalvar) {
    var $name = 1;
    var _dummy = 2;
    var __foo = 3;

    return $name + _dummy + $localvar + __foo;
}""", 0, False, True, """function _3(l){var n=1;var _0=2;var __foo=3;return n+_0+l+__foo}function _2(_1){var n=1;var _0=2;var __foo=3;return n+_0+l+__foo}"""))

    test_scripts.append(("cssQuery1.js", 0, False, False, "cssQuery1-p1.js"))
    test_scripts.append(("cssQuery.js", 0, False, False, "cssQuery-p1.js"))
    test_scripts.append(("pack.js", 0, False, False, "pack-p1.js"))
    test_scripts.append(("cssQuery.js", 0, False, True, "cssQuery-p2.js"))
    # the following ones are different, because javascript might use an
    # unstable sort algorithm while python uses an stable sort algorithm
    test_scripts.append(("pack.js", 0, False, True, "pack-p2.js"))
    test_scripts.append(("test.js", 0, False, True, """function _4(l){var n=1;var _0=2;var __foo=3;return n+_0+l+__foo}function _3(_1){var n=1;var _2=2;var __foo=3;return n+_2+l+__foo}"""))
    test_scripts.append(("test.js", 10, False, False, """eval(function(p,a,c,k,e,d){while(c--){if(k[c]){p=p.replace(new RegExp("\\b"+e(c)+"\\b","g"),k[c])}}return p}('8 13($6){0 $4=1;0 7=2;0 5=3;9 $4+7+$6+5}8 11(12){0 $4=1;0 10=2;0 5=3;9 $4+10+$6+5}',10,14,'var||||name|__foo|localvar|_dummy|function|return|_2|_bar|_ocalvar|_test'.split('|')))
"""))
    test_scripts.append(("test.js", 62, False, False, """eval(function(p,a,c,k,e,d){while(c--){if(k[c]){p=p.replace(new RegExp("\\b"+e(c)+"\\b","g"),k[c])}}return p}('8 d($6){0 $4=1;0 7=2;0 5=3;9 $4+7+$6+5}8 b(c){0 $4=1;0 a=2;0 5=3;9 $4+a+$6+5}',14,14,'var||||name|__foo|localvar|_dummy|function|return|_2|_bar|_ocalvar|_test'.split('|')))
"""))
    test_scripts.append(("test.js", 95, False, False, "test-p4.js"))
    test_scripts.append(("cssQuery.js", 0, False, True, "cssQuery-p3.js"))
    test_scripts.append(("cssQuery.js", 62, False, True, "cssQuery-p4.js"))

    import difflib
    p = JavaScriptPacker()
    for script, encoding, fastDecode, specialChars, expected in test_scripts:
        if os.path.exists(script):
            _script = open(script).read()
        else:
            _script = script
        if os.path.exists(expected):
            _expected = open(expected).read()
        else:
            _expected = expected
        print(script[:20], encoding, fastDecode, specialChars, expected[:20])
        print("="*40)
        result = p.pack(_script, encoding, fastDecode, specialChars)
        print(len(result), len(_script))
        if (result != _expected):
            print("ERROR!!!!!!!!!!!!!!!!")
            print(_expected)
            print(result)
            #print list(difflib.unified_diff(result, _expected))

if __name__=='__main__':
    run()
