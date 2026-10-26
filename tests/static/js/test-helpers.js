QUnit.test.each(
    "bytesFromSize",
    [
        // empty inputs
        {title: "UndefinedSize", input: undefined, expected: undefined},
        {title: "EmptySize", input: "", expected: undefined},

        // unknown units
        {title: "UnknownPBSuffix", input: "1 PB", expected: undefined},
        {
            title: "UnknownSuffixSpace",
            input: "234.5 unknown",
            expected: undefined
        },
        {title: "UnknownSuffix", input: "234.5unknown", expected: undefined},

        // conversion
        {title: "WholeByteNoSuffix", input: "1", expected: 1},
        {title: "WholeByteAbbreviatedSuffix", input: "1b", expected: 1},
        {title: "WholeByteAbbreviatedSuffixSpace", input: "1 B", expected: 1},
        {title: "WholeByteWordSuffix", input: "1 byte", expected: 1},
        {
            title: "WholeByteWordSuffixCapitalization",
            input: "1 bYtES",
            expected: 1
        },
        {title: "WholeFractionalBytesNoSuffix", input: "1.1", expected: 1.1},
        {title: "FractionalBytesNoSuffix", input: ".1", expected: 0.1},
        {title: "OneKilobyte", input: "1 KB", expected: 1024},
        {title: "TwoKilobytes", input: "2 KB", expected: 2048},
        {title: "OneMegabyte", input: "1 MB", expected: Math.pow(1024, 2)},
        {title: "WholeMB", input: "500mb", expected: 500 * Math.pow(1024, 2)},
        {
            title: "DecimalMB",
            input: "500.2mb",
            expected: 500.2 * Math.pow(1024, 2)
        },
        {title: "OneGigabyte", input: "1 GB", expected: Math.pow(1024, 3)},
        {title: "OneTerabyte", input: "1 TB", expected: Math.pow(1024, 4)}
    ],
    (assert, params) => {
        assert.equal(
            bytesFromSize(params.input),
            params.expected,
            "As expected: " + String(params.expected)
        );
    }
);

QUnit.test.each(
    "formatSize",
    [
        {title: "UndefinedSize", input: undefined, expected: "-"},
        {title: "NaN", input: NaN, expected: "-"},
        {title: "Text", input: "text", expected: "-"},
        {title: "EmptySize", input: "", expected: "-"},
        {title: "WholeByte", input: 1, expected: "1.0B"},
        {title: "FractionalBytes", input: 1.1, expected: "1.1B"},
        {title: "OneKilobyte", input: 1024, expected: "1.0KB"},
        {title: "TwoKilobytes", input: 2048, expected: "2.0KB"},
        {title: "FractionalKilobytes", input: 2.2 * 1024, expected: "2.2KB"},
        {
            title: "FractionalMB",
            input: 23.5 * Math.pow(1024, 2),
            expected: "23.5MB"
        },
        {
            title: "FractionalGB",
            input: 23.5 * Math.pow(1024, 3),
            expected: "23.5GB"
        },
        {
            title: "FractionalTB",
            input: 23.5 * Math.pow(1024, 4),
            expected: "23.5TB"
        },
        {
            title: "PetabyteAsTB",
            input: 2 * Math.pow(1024, 5),
            expected: "2048.0TB"
        }
    ],
    (assert, params) => {
        assert.equal(
            formatSize(params.input),
            params.expected,
            "As expected: " + String(params.expected)
        );
    }
);

QUnit.test.each(
    "formatTemperature",
    [
        {
            title: "UndefinedTemperature",
            input: undefined,
            showF: undefined,
            useUnicode: undefined,
            offThreshold: undefined,
            expected: "-"
        },
        {
            title: "EmptyTemperature",
            input: "",
            showF: undefined,
            useUnicode: undefined,
            offThreshold: undefined,
            expected: "-"
        },
        {
            title: "NaNTemperature",
            input: NaN,
            showF: undefined,
            useUnicode: undefined,
            offThreshold: undefined,
            expected: "-"
        },
        {
            title: "TemperatureUnderOffThreshold",
            input: 1.0,
            showF: undefined,
            useUnicode: undefined,
            offThreshold: 1.1,
            expected: "off"
        },
        {
            title: "TemperatureEqualToOffThreshold",
            input: 1.0,
            showF: undefined,
            useUnicode: undefined,
            offThreshold: 1.0,
            expected: "1.0&deg;C"
        },
        {
            title: "TemperatureWithNoOffThreshold",
            input: 1.0,
            showF: undefined,
            useUnicode: undefined,
            offThreshold: undefined,
            expected: "1.0&deg;C"
        },
        {
            title: "TemperatureWithFahrenheit",
            input: 1.0,
            showF: true,
            useUnicode: undefined,
            offThreshold: undefined,
            expected: "1.0&deg;C (33.8&deg;F)"
        },
        {
            title: "TemperatureWithFahrenheitUnicode",
            input: 1.0,
            showF: true,
            useUnicode: true,
            offThreshold: undefined,
            expected: "1.0\u00B0C (33.8\u00B0F)"
        },
        {
            title: "TemperatureHtmlEntities",
            input: 1.0,
            showF: undefined,
            useUnicode: false,
            offThreshold: undefined,
            expected: "1.0&deg;C"
        },
        {
            title: "TemperatureUnicode",
            input: 1.0,
            showF: undefined,
            useUnicode: true,
            offThreshold: undefined,
            expected: "1.0\u00B0C"
        },
        {
            title: "TemperatureIncrease",
            input: 1.1,
            showF: undefined,
            useUnicode: undefined,
            offThreshold: undefined,
            expected: "1.1&deg;C"
        }
    ],
    (assert, params) => {
        assert.equal(
            formatTemperature(
                params.input,
                params.showF,
                params.offThreshold,
                params.useUnicode
            ),
            params.expected,
            "As expected: " + String(params.expected)
        );
    }
);

QUnit.test.each(
    "determineWebcamStreamType",
    [
        {
            title: "UndefinedUrlThrowsException",
            streamUrl: undefined,
            exceptionExpected: "Empty streamUrl. Cannot determine stream type.",
            expectedResult: undefined
        },
        {
            title: "InvalidUrlThrowsException",
            streamUrl: "invalidUrl",
            exceptionExpected: "Invalid streamUrl. Cannot determine stream type.",
            expectedResult: undefined
        },
        {
            title: "Webrtc",
            streamUrl: "webrtc://localhost/stream",
            exceptionExpected: undefined,
            expectedResult: "webrtc"
        },
        {
            title: "Webrtcs",
            streamUrl: "webrtcs://localhost/stream",
            exceptionExpected: undefined,
            expectedResult: "webrtc"
        },
        {
            title: "HlsPlaylist",
            streamUrl: "https://localhost/stream.m3u8",
            exceptionExpected: undefined,
            expectedResult: "hls"
        },
        {
            title: "DefaultMjpg",
            streamUrl: "https://localhost/stream",
            exceptionExpected: undefined,
            expectedResult: "mjpg"
        }
    ],
    (assert, params) => {
        let exceptionMessage = undefined;
        let result = undefined;

        try {
            result = determineWebcamStreamType(params.streamUrl);
        } catch (ex) {
            exceptionMessage = ex;
        }

        assert.equal(
            exceptionMessage,
            params.exceptionExpected,
            "Exception expected: " + String(params.exceptionExpected)
        );

        assert.equal(
            result,
            params.expectedResult,
            "As expected: " + String(params.expectedResult)
        );
    }
);

QUnit.test.each(
    "validateWebcamUrl",
    [
        {
            title: "UndefinedUrlReturnsFalse",
            streamUrl: undefined,
            windowLocationOverride: undefined,
            expected: false
        },
        {
            title: "RelativeProtocolUrl",
            streamUrl: "//localhost/stream",
            windowLocationOverride: {protocol: "https:"},
            expected: new URL("https://localhost/stream")
        },
        {
            title: "RelativePathUrl",
            streamUrl: "/stream",
            windowLocationOverride: {
                protocol: "https:",
                port: "443",
                hostname: "localhost"
            },
            expected: new URL("https://localhost/stream")
        },
        {
            title: "Http",
            streamUrl: "http://localhost/stream",
            windowLocationOverride: undefined,
            expected: new URL("http://localhost/stream")
        },
        {
            title: "Https",
            streamUrl: "https://localhost/stream",
            windowLocationOverride: undefined,
            expected: new URL("https://localhost/stream")
        },
        {
            title: "Webrtc",
            streamUrl: "webrtc://localhost/stream",
            windowLocationOverride: undefined,
            expected: new URL("webrtc://localhost/stream")
        },
        {
            title: "Webrtcs",
            streamUrl: "webrtcs://localhost/stream",
            windowLocationOverride: undefined,
            expected: new URL("webrtcs://localhost/stream")
        },
        {
            title: "InvalidUrlReturnsFalse",
            streamUrl: "invalid",
            windowLocationOverride: undefined,
            expected: false
        },
        {
            title: "ParsingExceptionReturnsFalse",
            streamUrl: "//exception",
            windowLocationOverride: {protocol: ":"},
            expected: false
        }
    ],
    (assert, params) => {
        if (params.windowLocationOverride) {
            fetchWindowLocation = () => {
                return params.windowLocationOverride;
            };
        }

        const result = validateWebcamUrl(params.streamUrl);

        assert.equal(
            result.toString(),
            params.expected.toString(),
            "As expected: " + String(params.expected)
        );
    }
);

QUnit.test.each(
    "getExternalHostUrl",
    [
        {
            title: "HttpsDefaultPortOmitted",
            windowLocation: {
                protocol: "https:",
                port: "443",
                hostname: "localhost"
            },
            expected: "https://localhost"
        },
        {
            title: "HttpsNonDefaultPortNotOmitted",
            windowLocation: {
                protocol: "https:",
                port: "8000",
                hostname: "localhost"
            },
            expected: "https://localhost:8000"
        },
        {
            title: "HttpDefaultPortOmitted",
            windowLocation: {
                protocol: "http:",
                port: "80",
                hostname: "localhost"
            },
            expected: "http://localhost"
        },
        {
            title: "HttpNonDefaultPortNotOmitted",
            windowLocation: {
                protocol: "http:",
                port: "8000",
                hostname: "localhost"
            },
            expected: "http://localhost:8000"
        }
    ],
    (assert, params) => {
        if (params.windowLocation) {
            fetchWindowLocation = () => {
                return params.windowLocation;
            };
        }

        const result = getExternalHostUrl();

        assert.equal(result, params.expected, "As expected: " + String(params.expected));
    }
);

QUnit.test.each(
    "escapeUnprintableCharacters",
    [
        {
            title: "EmptyText",
            input: "",
            isExpectingException: false,
            expectedResult: ""
        },
        {
            title: "UndefinedText",
            input: undefined,
            isExpectingException: true,
            expectedResult: undefined
        },
        {
            title: "PrintableTextUnchanged",
            input: "Test123",
            isExpectingException: false,
            expectedResult: "Test123"
        },
        {
            title: "MultipleCharacterAsHex",
            input: "\x00\x01\x02",
            isExpectingException: false,
            expectedResult: "\\x00\\x01\\x02"
        },
        {
            title: "MixedPrintableNonPrintable",
            input: "\x00Hello123\x01",
            isExpectingException: false,
            expectedResult: "\\x00Hello123\\x01"
        },
        {
            title: "NullCharacterAsHex",
            input: "\x00",
            isExpectingException: false,
            expectedResult: "\\x00"
        },
        {
            title: "UnitSeparatorCharacterAsHex",
            input: "\x1F",
            isExpectingException: false,
            expectedResult: "\\x1f"
        },
        {
            title: "DeleteCharacterAsHex",
            input: "\x7F",
            isExpectingException: false,
            expectedResult: "\\x7f"
        },
        {
            title: "ExtendedAsciiEuroAsHex",
            input: "\x80",
            isExpectingException: false,
            expectedResult: "\\x80"
        },
        {
            title: "ExtendedAsciiCapitalYumlAsHex",
            input: "\x9F",
            isExpectingException: false,
            expectedResult: "\\x9f"
        },
        {
            title: "ExtendedAsciiYumlAsHex",
            input: "\xFF",
            isExpectingException: false,
            expectedResult: "\\xff"
        },
        {
            title: "SpaceCharacterUnchanged",
            input: " ",
            isExpectingException: false,
            expectedResult: " "
        },
        {
            title: "TabCharacterUnchanged",
            input: "\t",
            isExpectingException: false,
            expectedResult: "\t"
        },
        {
            title: "LineFeedCharacterUnchanged",
            input: "\x0A",
            isExpectingException: false,
            expectedResult: "\x0A"
        },
        {
            title: "CarriageReturnCharacterUnchanged",
            input: "\x0D",
            isExpectingException: false,
            expectedResult: "\x0D"
        },
        {
            title: "UnicodeUnchanged",
            input: "\u1F419",
            isExpectingException: false,
            expectedResult: "\u1F419"
        }
    ],
    (assert, params) => {
        let result = undefined;
        let exceptionThrown = false;

        try {
            result = escapeUnprintableCharacters(params.input);
        } catch (ex) {
            exceptionThrown = true;
        }

        assert.equal(
            result,
            params.expectedResult,
            "As expected: " + String(params.expectedResult)
        );
        assert.equal(
            exceptionThrown,
            params.isExpectingException,
            "As expected: " + String(params.expectedException)
        );
    }
);

QUnit.test.each(
    "getQueryParameterByName",
    [
        {
            title: "WindowLocationFirstParameter",
            inputName: "parameter1",
            inputUrl: undefined,
            windowLocation: {
                href: "https://localhost/stream?parameter1=test&parameter2=value"
            },
            expected: "test"
        },
        {
            title: "WindowLocationSecondParameter",
            inputName: "parameter2",
            inputUrl: undefined,
            windowLocation: {
                href: "https://localhost/stream?parameter1=test&parameter2=value"
            },
            expected: "value"
        },
        {
            title: "UrlFirstParameter",
            inputName: "parameter1",
            inputUrl: "https://localhost/stream?parameter1=test&parameter2=value",
            windowLocation: undefined,
            expected: "test"
        },
        {
            title: "UrlSecondParameter",
            inputName: "parameter2",
            inputUrl: "https://localhost/stream?parameter1=test&parameter2=value",
            windowLocation: undefined,
            expected: "value"
        },
        {
            title: "ArrayParameter",
            inputName: "array[0]",
            inputUrl: "https://localhost/stream?array[0]=first&array[1]=second",
            windowLocation: undefined,
            expected: "first"
        },
        {
            title: "NoParameters",
            inputName: "array[0]",
            inputUrl: "https://localhost/stream",
            windowLocation: undefined,
            expected: null
        },
        {
            title: "UnknownParameter",
            inputName: "unknown",
            inputUrl: "https://localhost/stream?parameter=first",
            windowLocation: undefined,
            expected: null
        },
        {
            title: "EmptyParameter",
            inputName: "parameter",
            inputUrl: "https://localhost/stream?parameter=",
            windowLocation: undefined,
            expected: ""
        },
        {
            title: "EmptyParameterNoEqual",
            inputName: "parameter",
            inputUrl: "https://localhost/stream?parameter",
            windowLocation: undefined,
            expected: ""
        },
        {
            title: "PlusReplacedBySpace",
            inputName: "Sentence",
            inputUrl: "https://localhost/stream?Sentence=Hello+World",
            windowLocation: undefined,
            expected: "Hello World"
        }
    ],
    (assert, params) => {
        if (params.windowLocation) {
            fetchWindowLocation = () => {
                return params.windowLocation;
            };
        }

        const result = getQueryParameterByName(params.inputName, params.inputUrl);
        assert.equal(result, params.expected, "As expected: " + String(params.expected));
    }
);

QUnit.test.each(
    "formatNumberK",
    [
        {
            title: "UndefinedNumber",
            input: undefined,
            expectedException: "[sprintf] expecting number but found undefined",
            expectedResult: undefined
        },
        {
            title: "Text",
            input: "text",
            expectedException: "[sprintf] expecting number but found string",
            expectedResult: undefined
        },
        {
            title: "Zero",
            input: 0,
            expectedException: undefined,
            expectedResult: "0"
        },
        {
            title: "Thousand",
            input: 1000,
            expectedException: undefined,
            expectedResult: "1000"
        },
        {
            title: "ThousandOne",
            input: 1001,
            expectedException: undefined,
            expectedResult: "1.00k"
        },
        {
            title: "ThousandTen",
            input: 1010,
            expectedException: undefined,
            expectedResult: "1.01k"
        },
        {
            title: "Decimal",
            input: 0.1,
            expectedException: undefined,
            expectedResult: "0"
        },
        {
            title: "Negative",
            input: -1,
            expectedException: undefined,
            expectedResult: "-1"
        },
        {
            title: "NegativeThousandOne",
            input: -1001,
            expectedException: undefined,
            expectedResult: "-1001"
        }
    ],
    (assert, params) => {
        let result = undefined;
        let exceptionMessage = undefined;

        try {
            result = formatNumberK(params.input);
        } catch (ex) {
            exceptionMessage = ex.message;
        }

        assert.equal(
            result,
            params.expectedResult,
            "As expected: " + String(params.expectedResult)
        );
        assert.equal(
            exceptionMessage,
            params.expectedException,
            "As expected: " + String(params.expectedException)
        );
    }
);

QUnit.test.each(
    "formatHuman",
    [
        {
            title: "UndefinedNumber",
            input: undefined,
            expected: "-"
        },
        {
            title: "NaN",
            input: undefined,
            expected: "-"
        },
        {
            title: "Text",
            input: "text",
            expected: "-"
        },
        {
            title: "Zero",
            input: 0,
            expected: "0"
        },
        {
            title: "Thousand",
            input: 1000,
            expected: "1.0K"
        },
        {
            title: "ThousandOne",
            input: 1001,
            expected: "1.0K"
        },
        {
            title: "ThousandHundred",
            input: 1100,
            expected: "1.1K"
        },
        {
            title: "Million",
            input: 1000000,
            expected: "1.0M"
        },
        {
            title: "MillionOne",
            input: 1000001,
            expected: "1.0M"
        },
        {
            title: "MillionThousand",
            input: 1001000,
            expected: "1.0M"
        },
        {
            title: "MillionHundredThousand",
            input: 1100000,
            expected: "1.1M"
        },
        {
            title: "Billion",
            input: 1000000000,
            expected: "1000.0M"
        },
        {
            title: "Decimal",
            input: 0.1,
            expected: "0.1"
        },
        {
            title: "Negative",
            input: -1,
            expected: "-1"
        },
        {
            title: "NegativeThousandOne",
            input: -1001,
            expected: "-1001"
        }
    ],
    (assert, params) => {
        const result = formatHuman(params.input);
        assert.equal(result, params.expected, "As expected: " + String(params.expected));
    }
);

QUnit.test.each(
    "cleanTemperature",
    [
        {
            title: "UndefinedNumber",
            temp: undefined,
            offThreshold: undefined,
            expected: "-"
        },
        {
            title: "EmptyNumber",
            temp: "",
            offThreshold: undefined,
            expected: "-"
        },
        {
            title: "Text",
            temp: "A",
            offThreshold: undefined,
            expected: "-"
        },
        {
            title: "One",
            temp: 1,
            offThreshold: undefined,
            expected: "1"
        },
        {
            title: "Zero",
            temp: 0,
            offThreshold: undefined,
            expected: "0"
        },
        {
            title: "BelowThreshold",
            temp: 0,
            offThreshold: 1,
            expected: "off"
        },
        {
            title: "AboveThreshold",
            temp: 1,
            offThreshold: 0,
            expected: "1"
        }
    ],
    (assert, params) => {
        const result = cleanTemperature(params.temp, params.offThreshold);
        assert.equal(result, params.expected, "As expected: " + String(params.expected));
    }
);

QUnit.test.each(
    "formatFilament",
    [
        {
            title: "UndefinedFilament",
            filament: undefined,
            expected: "-"
        },
        {
            title: "UndefinedLength",
            filament: {length: undefined},
            expected: "-"
        },
        {
            title: "PositiveFilamentNoVolume",
            filament: {length: 1},
            expected: "0.00m"
        },
        {
            title: "PositiveFilamentDecimal",
            filament: {length: 10},
            expected: "0.01m"
        },
        {
            title: "OneMeterFilament",
            filament: {length: 1000},
            expected: "1.00m"
        },
        {
            title: "PositiveFilamentUndefinedVolume",
            filament: {length: 1, volume: undefined},
            expected: "0.00m"
        },
        {
            title: "PositiveFilamentWithVolume",
            filament: {length: 1, volume: 1},
            expected: "0.00m / 1.00cm\u00B3"
        }
    ],
    (assert, params) => {
        const result = formatFilament(params.filament);
        assert.equal(result, params.expected, "As expected: " + String(params.expected));
    }
);

QUnit.test.each(
    "formatTimeAgo",
    [
        {
            title: "UndefinedTimestamp",
            unixTimestamp: undefined,
            expected: "-"
        },
        {
            title: "ZeroTimestamp",
            unixTimestamp: 0,
            expected: "-"
        },
        {
            title: "RecentTimestamp",
            unixTimestamp: moment().unix() - 1,
            expected: "a few seconds ago"
        }
    ],
    (assert, params) => {
        const result = formatTimeAgo(params.unixTimestamp);
        assert.equal(result, params.expected, "As expected: " + String(params.expected));
    }
);

QUnit.test.each(
    "splitTextToArray",
    [
        {
            title: "EmptyText",
            input: "",
            sep: undefined,
            stripEmpty: false,
            filter: undefined,
            expected: [""]
        },
        {
            title: "EmptyTextStripEmpty",
            input: "",
            sep: undefined,
            stripEmpty: true,
            filter: undefined,
            expected: []
        },
        {
            title: "Text",
            input: "abcd",
            sep: undefined,
            stripEmpty: false,
            filter: undefined,
            expected: ["abcd"]
        },
        {
            title: "TextSeparator",
            input: "ab#cd",
            sep: "#",
            stripEmpty: false,
            filter: undefined,
            expected: ["ab", "cd"]
        },
        {
            title: "TrimmedText",
            input: "ab # cd",
            sep: "#",
            stripEmpty: false,
            filter: undefined,
            expected: ["ab", "cd"]
        }
    ],
    (assert, params) => {
        const result = splitTextToArray(
            params.input,
            params.sep,
            params.stripEmpty,
            params.filter
        );
        assert.equal(
            JSON.stringify(result),
            JSON.stringify(params.expected),
            "As expected: " + String(params.expected)
        );
    }
);

QUnit.test.each("formatDate", [], (assert, params) => {
    const result = formatDate(params.unixTimestamp, params.options);
    assert.equal(result, params.expected, "As expected: " + String(params.expected));
});

QUnit.test.each(
    "rsplit",
    [
        {
            title: "Basic",
            text: "a:b:c",
            sep: ":",
            limit: undefined,
            expected: ["a", "b", "c"]
        },
        {
            title: "With Limit",
            text: "a:b:c",
            sep: ":",
            limit: 1,
            expected: ["a:b", "c"]
        },
        {
            title: "No Match",
            text: "a-b-c",
            sep: ":",
            limit: undefined,
            expected: ["a-b-c"]
        }
    ],
    (assert, params) => {
        const result = rsplit(params.text, params.sep, params.limit);
        assert.deepEqual(
            result,
            params.expected,
            "As expected: " + String(params.expected)
        );
    }
);

QUnit.test.each(
    "recursiveMatch",
    [
        {
            matcher: {},
            data: {
                a: {ba: {ca: {da: []}, cb: "test"}, bb: 123},
                b: "hello",
                c: "world"
            },
            expected: false
        },
        {
            matcher: {a: {ba: {ca: true}}},
            data: {},
            expected: false
        },
        {
            matcher: true,
            data: {
                a: {ba: {ca: {da: []}, cb: "test"}, bb: 123},
                b: "hello",
                c: "world"
            },
            expected: true
        },
        {
            matcher: {a: {ba: {ca: true}}},
            data: {
                a: {ba: {ca: {da: []}, cb: "test"}, bb: 123},
                b: "hello",
                c: "world"
            },
            expected: true
        },
        {
            matcher: {a: {ba: {ca: 1}}},
            data: {
                a: {ba: {ca: {da: []}, cb: "test"}, bb: 123},
                b: "hello",
                c: "world"
            },
            expected: true
        },
        {
            matcher: {a: {ba: {ca: {}}}},
            data: {
                a: {ba: {ca: {da: []}, cb: "test"}, bb: 123},
                b: "hello",
                c: "world"
            },
            expected: true
        }
    ],
    (assert, params) => {
        const result = recursiveMatch(params.matcher, params.data);
        assert.deepEqual(
            result,
            params.expected,
            "As expected: " + String(params.expected)
        );
    }
);
