// Copyright © 2013 Pieroxy <pieroxy@pieroxy.net>
// This work is free. You can redistribute it and/or modify it
// under the terms of the WTFPL, Version 2
// For more information see LICENSE.txt or http://www.wtfpl.net/
//
// LZ-based compression algorithm, version 1.0.2-rc1
var LZString = {
    writeBit: function (value, data) {
        data.val = (data.val << 1) | value;
        if (data.position == 15) {
            data.position = 0;
            data.string += String.fromCharCode(data.val);
            data.val = 0;
        } else {
            data.position++;
        }
    },

    writeBits: function (numBits, value, data) {
        if (typeof value == "string") value = value.charCodeAt(0);
        for (var i = 0; i < numBits; i++) {
            this.writeBit(value & 1, data);
            value = value >> 1;
        }
    },

    produceW: function (context) {
        if (Object.prototype.hasOwnProperty.call(context.dictionaryToCreate, context.w)) {
            if (context.w.charCodeAt(0) < 256) {
                this.writeBits(context.numBits, 0, context.data);
                this.writeBits(8, context.w, context.data);
            } else {
                this.writeBits(context.numBits, 1, context.data);
                this.writeBits(16, context.w, context.data);
            }
            this.decrementEnlargeIn(context);
            delete context.dictionaryToCreate[context.w];
        } else {
            this.writeBits(context.numBits, context.dictionary[context.w], context.data);
        }
        this.decrementEnlargeIn(context);
    },

    decrementEnlargeIn: function (context) {
        context.enlargeIn--;
        if (context.enlargeIn == 0) {
            context.enlargeIn = Math.pow(2, context.numBits);
            context.numBits++;
        }
    },

    compress: function (uncompressed) {
        var context = {
                dictionary: {},
                dictionaryToCreate: {},
                c: "",
                wc: "",
                w: "",
                enlargeIn: 2, // Compensate for the first entry which should not count
                dictSize: 3,
                numBits: 2,
                result: "",
                data: {string: "", val: 0, position: 0}
            },
            i;

        for (i = 0; i < uncompressed.length; i += 1) {
            context.c = uncompressed.charAt(i);
            if (!Object.prototype.hasOwnProperty.call(context.dictionary, context.c)) {
                context.dictionary[context.c] = context.dictSize++;
                context.dictionaryToCreate[context.c] = true;
            }

            context.wc = context.w + context.c;
            if (Object.prototype.hasOwnProperty.call(context.dictionary, context.wc)) {
                context.w = context.wc;
            } else {
                this.produceW(context);
                // Add wc to the dictionary.
                context.dictionary[context.wc] = context.dictSize++;
                context.w = String(context.c);
            }
        }

        // Output the code for w.
        if (context.w !== "") {
            this.produceW(context);
        }

        // Mark the end of the stream
        this.writeBits(context.numBits, 2, context.data);

        // Flush the last char
        while (context.data.val > 0) this.writeBit(0, context.data);
        return context.data.string;
    },

    readBit: function (data) {
        var res = data.val & data.position;
        data.position >>= 1;
        if (data.position == 0) {
            data.position = 32768;
            data.val = data.string.charCodeAt(data.index++);
        }
        //data.val = (data.val << 1);
        return res > 0 ? 1 : 0;
    },

    readBits: function (numBits, data) {
        var res = 0;
        var maxpower = Math.pow(2, numBits);
        var power = 1;
        while (power != maxpower) {
            res |= this.readBit(data) * power;
            power <<= 1;
        }
        return res;
    },

    decompress: function (compressed) {
        var dictionary = {},
            next,
            enlargeIn = 4,
            dictSize = 4,
            numBits = 3,
            entry = "",
            result = "",
            i,
            w,
            c,
            errorCount = 0,
            literal,
            data = {
                string: compressed,
                val: compressed.charCodeAt(0),
                position: 32768,
                index: 1
            };

        for (i = 0; i < 3; i += 1) {
            dictionary[i] = i;
        }

        next = this.readBits(2, data);
        switch (next) {
            case 0:
                c = String.fromCharCode(this.readBits(8, data));
                break;
            case 1:
                c = String.fromCharCode(this.readBits(16, data));
                break;
            case 2:
                return "";
        }
        dictionary[3] = c;
        w = result = c;
        while (true) {
            c = this.readBits(numBits, data);

            switch (c) {
                case 0:
                    if (errorCount++ > 10000) return "Error";
                    c = String.fromCharCode(this.readBits(8, data));
                    dictionary[dictSize++] = c;
                    c = dictSize - 1;
                    enlargeIn--;
                    break;
                case 1:
                    c = String.fromCharCode(this.readBits(16, data));
                    dictionary[dictSize++] = c;
                    c = dictSize - 1;
                    enlargeIn--;
                    break;
                case 2:
                    return result;
            }

            if (enlargeIn == 0) {
                enlargeIn = Math.pow(2, numBits);
                numBits++;
            }

            if (dictionary[c]) {
                entry = dictionary[c];
            } else {
                if (c === dictSize) {
                    entry = w + w.charAt(0);
                } else {
                    return null;
                }
            }
            result += entry;

            // Add w+entry[0] to the dictionary.
            dictionary[dictSize++] = w + entry.charAt(0);
            enlargeIn--;

            w = entry;

            if (enlargeIn == 0) {
                enlargeIn = Math.pow(2, numBits);
                numBits++;
            }
        }
        return result;
    }
}; /*global LZString*/
JSONC = function () {
    var root,
        JSONC = {},
        isNodeEnvironment,
        _nCode = -1,
        toString = {}.toString;

    /**
     * set the correct root depending from the environment.
     * @type {Object}
     * @private
     */
    root = this;
    /**
     * Check if JSONC is loaded in Node.js environment
     * @type {Boolean}
     * @private
     */
    isNodeEnvironment =
        typeof exports === "object" &&
        typeof module === "object" &&
        typeof module.exports === "object" &&
        typeof require === "function";
    /**
     * Checks if the value exist in the array.
     * @param arr
     * @param v
     * @returns {boolean}
     */
    function contains(arr, v) {
        var nIndex,
            nLen = arr.length;
        for (nIndex = 0; nIndex < nLen; nIndex++) {
            if (arr[nIndex][1] === v) {
                return true;
            }
        }
        return false;
    }
    /**
     * Removes duplicated values in an array
     * @param oldArray
     * @returns {Array}
     */
    function unique(oldArray) {
        var nIndex,
            nLen = oldArray.length,
            aArr = [];
        for (nIndex = 0; nIndex < nLen; nIndex++) {
            if (!contains(aArr, oldArray[nIndex][1])) {
                aArr.push(oldArray[nIndex]);
            }
        }
        return aArr;
    }
    /**
     * Escapes a RegExp
     * @param text
     * @returns {*}
     */
    function escapeRegExp(text) {
        return text.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, "\\$&");
    }
    /**
     * Returns if the obj is an object or not.
     * @param obj
     * @returns {boolean}
     * @private
     */
    function _isObject(obj) {
        return toString.call(obj) === "[object Object]";
    }
    /**
     * Returns if the obj is an array or not
     * @param obj
     * @returns {boolean}
     * @private
     */
    function _isArray(obj) {
        return toString.call(obj) === "[object Array]";
    }
    /**
     * Converts a bidimensional array to object
     * @param aArr
     * @returns {{}}
     * @private
     */
    function _biDimensionalArrayToObject(aArr) {
        var obj = {},
            nIndex,
            nLen = aArr.length,
            oItem;
        for (nIndex = 0; nIndex < nLen; nIndex++) {
            oItem = aArr[nIndex];
            obj[oItem[0]] = oItem[1];
        }
        return obj;
    }

    /**
     * Convert a number to their ascii code/s.
     * @param index
     * @param totalChar
     * @param offset
     * @returns {Array}
     * @private
     */
    function _numberToKey(index, totalChar, offset) {
        var aArr = [],
            currentChar = index;
        totalChar = totalChar || 26;
        offset = offset || 65;
        while (currentChar >= totalChar) {
            aArr.push((currentChar % totalChar) + offset);
            currentChar = Math.floor(currentChar / totalChar - 1);
        }
        aArr.push(currentChar + offset);
        return aArr.reverse();
    }

    /**
     * Returns the string using an array of ASCII values
     * @param aKeys
     * @returns {string}
     * @private
     */
    function _getSpecialKey(aKeys) {
        return String.fromCharCode.apply(String, aKeys);
    }

    /**
     * Traverse all the objects looking for keys and set an array with the new keys
     * @param json
     * @param aKeys
     * @returns {*}
     * @private
     */
    function _getKeys(json, aKeys) {
        var aKey, sKey, oItem;

        for (sKey in json) {
            if (json.hasOwnProperty(sKey)) {
                oItem = json[sKey];
                if (_isObject(oItem) || _isArray(oItem)) {
                    aKeys = aKeys.concat(unique(_getKeys(oItem, aKeys)));
                }
                if (isNaN(Number(sKey))) {
                    if (!contains(aKeys, sKey)) {
                        _nCode += 1;
                        aKey = [];
                        aKey.push(_getSpecialKey(_numberToKey(_nCode)), sKey);
                        aKeys.push(aKey);
                    }
                }
            }
        }
        return aKeys;
    }

    /**
     * Method to compress array objects
     * @private
     * @param json
     * @param aKeys
     */
    function _compressArray(json, aKeys) {
        var nIndex, nLenKeys;

        for (nIndex = 0, nLenKeys = json.length; nIndex < nLenKeys; nIndex++) {
            json[nIndex] = JSONC.compress(json[nIndex], aKeys);
        }
    }

    /**
     * Method to compress anything but array
     * @private
     * @param json
     * @param aKeys
     * @returns {*}
     */
    function _compressOther(json, aKeys) {
        var oKeys, aKey, str, nLenKeys, nIndex, obj;
        aKeys = _getKeys(json, aKeys);
        aKeys = unique(aKeys);
        oKeys = _biDimensionalArrayToObject(aKeys);

        str = JSON.stringify(json);
        nLenKeys = aKeys.length;

        for (nIndex = 0; nIndex < nLenKeys; nIndex++) {
            aKey = aKeys[nIndex];
            str = str.replace(
                new RegExp('(?:"' + escapeRegExp('"' + aKey[1] + '"') + '"):', "g"),
                '"' + aKey[0] + '"'
            );
        }
        obj = JSON.parse(str);
        obj._ = oKeys;
        return obj;
    }

    /**
     * Method to decompress array objects
     * @private
     * @param json
     */
    function _decompressArray(json) {
        var nIndex, nLenKeys;

        for (nIndex = 0, nLenKeys = json.length; nIndex < nLenKeys; nIndex++) {
            json[nIndex] = JSONC.decompress(json[nIndex]);
        }
    }

    /**
     * Method to decompress anything but array
     * @private
     * @param jsonCopy
     * @returns {*}
     */
    function _decompressOther(jsonCopy) {
        var oKeys, str, sKey;

        oKeys = JSON.parse(JSON.stringify(jsonCopy._));
        delete jsonCopy._;
        str = JSON.stringify(jsonCopy);
        for (sKey in oKeys) {
            if (oKeys.hasOwnProperty(sKey)) {
                str = str.replace(
                    new RegExp('(?:"' + sKey + '"):', "g"),
                    '"' + oKeys[sKey] + '"'
                );
            }
        }
        return str;
    }

    /**
     * Compress a RAW JSON
     * @param json
     * @param optKeys
     * @returns {*}
     */
    JSONC.compress = function (json, optKeys) {
        if (!optKeys) {
            _nCode = -1;
        }
        var aKeys = optKeys || [],
            obj;

        if (_isArray(json)) {
            _compressArray(json, aKeys);
            obj = json;
        } else {
            obj = _compressOther(json, aKeys);
        }
        return obj;
    };
    /**
     * Use LZString to get the compressed string.
     * @param json
     * @param bCompress
     * @returns {String}
     */
    JSONC.pack = function (json, bCompress) {
        var str = JSON.stringify(bCompress ? JSONC.compress(json) : json);
        return LZString.compress(str);
    };
    /**
     * Decompress a compressed JSON
     * @param json
     * @returns {*}
     */
    JSONC.decompress = function (json) {
        var str,
            jsonCopy = JSON.parse(JSON.stringify(json));
        if (_isArray(jsonCopy)) {
            _decompressArray(jsonCopy);
        } else {
            str = _decompressOther(jsonCopy);
        }
        return str ? JSON.parse(str) : jsonCopy;
    };
    /**
     * Returns the JSON object from the LZW string
     * @param lzw
     * @param bDecompress
     * @returns {Object}
     */
    JSONC.unpack = function (lzw, bDecompress) {
        var str = LZString.decompress(lzw),
            json = JSON.parse(str);
        return bDecompress ? JSONC.decompress(json) : json;
    };

    return JSONC;
}.call(this);
