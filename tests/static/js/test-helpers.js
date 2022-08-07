_.mixin({sprintf: sprintf, vsprintf: vsprintf});

QUnit.module("bytesFromSize");
QUnit.cases(
    (function () {
        var cases = [];

        var params = [
            // empty inputs
            {title: "UndefinedSize", input: undefined, expected: undefined},
            {title: "EmptySize", input: "", expected: undefined},

            // unknown units
            {title: "UnknownPBSuffix", input: "1 PB", expected: undefined},
            {title: "UnknownSuffixSpace", input: "234.5 unknown", expected: undefined},
            {title: "UnknownSuffix", input: "234.5unknown", expected: undefined},

            // conversion
            {title: "WholeByteNoSuffix", input: "1", expected: 1},
            {title: "WholeByteAbbreviatedSuffix", input: "1b", expected: 1},
            {title: "WholeByteAbbreviatedSuffixSpace", input: "1 B", expected: 1},
            {title: "WholeByteWordSuffix", input: "1 byte", expected: 1},
            {title: "WholeByteWordSuffixCapitalization", input: "1 bYtES", expected: 1},
            {title: "WholeFractionalBytesNoSuffix", input: "1.1", expected: 1.1},
            {title: "FractionalBytesNoSuffix", input: ".1", expected: 0.1},
            {title: "OneKilobyte", input: "1 KB", expected: 1024},
            {title: "TwoKilobytes", input: "2 KB", expected: 2048},
            {title: "OneMegabyte", input: "1 MB", expected: Math.pow(1024, 2)},
            {title: "WholeMB", input: "500mb", expected: 500 * Math.pow(1024, 2)},
            {title: "DecimalMB", input: "500.2mb", expected: 500.2 * Math.pow(1024, 2)},
            {title: "OneGigabyte", input: "1 GB", expected: Math.pow(1024, 3)},
            {title: "OneTerabyte", input: "1 TB", expected: Math.pow(1024, 4)}
        ];

        var param, i;
        for (i = 0; i < params.length; i++) {
            param = params[i];
            cases.push(param);
        }

        return cases;
    })()
).test("bytesFromSize", function (params, assert) {
    assert.equal(
        bytesFromSize(params.input),
        params.expected,
        "As expected: " + String(params.expected)
    );
});

QUnit.module("formatSize");
QUnit.cases(
    (function () {
        var cases = [];

        var params = [
            {title: "UndefinedSize", input: undefined, expected: "-"},
            {title: "EmptySize", input: "", expected: "-"},
            {title: "WholeByte", input: 1, expected: "1.0bytes"},
            {title: "FractionalBytes", input: 1.1, expected: "1.1bytes"},
            {title: "OneKilobyte", input: 1024, expected: "1.0KB"},
            {title: "TwoKilobytes", input: 2048, expected: "2.0KB"},
            {title: "FractionalKilobytes", input: 2.2 * 1024, expected: "2.2KB"},
            {title: "FractionalMB", input: 23.5 * Math.pow(1024, 2), expected: "23.5MB"},
            {title: "FractionalGB", input: 23.5 * Math.pow(1024, 3), expected: "23.5GB"},
            {title: "FractionalTB", input: 23.5 * Math.pow(1024, 4), expected: "23.5TB"},
            {title: "PetabyteAsTB", input: 2 * Math.pow(1024, 5), expected: "2048.0TB"}
        ];

        var param, i;
        for (i = 0; i < params.length; i++) {
            param = params[i];
            cases.push(param);
        }

        return cases;
    })()
).test("formatSize", function (params, assert) {
    assert.equal(
        formatSize(params.input),
        params.expected,
        "As expected: " + String(params.expected)
    );
});

QUnit.module("formatTemperature");
QUnit.cases(
    (function () {
        var cases = [];

        var params = [
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
        ];

        var param, i;
        for (i = 0; i < params.length; i++) {
            param = params[i];
            cases.push(param);
        }

        return cases;
    })()
).test("formatTemperature", function (params, assert) {
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
});

QUnit.module("determineWebcamStreamType");
QUnit.cases(
    (function () {
        var cases = [];

        var params = [
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
        ];

        var param, i;
        for (i = 0; i < params.length; i++) {
            param = params[i];
            cases.push(param);
        }

        return cases;
    })()
).test("determineWebcamStreamType", function (params, assert) {
    var exceptionMessage = undefined;
    var result = undefined;

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
});

QUnit.module("validateWebcamUrl");
QUnit.cases(
    (function () {
        var cases = [];

        var params = [
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
        ];

        var param, i;
        for (i = 0; i < params.length; i++) {
            param = params[i];
            cases.push(param);
        }

        return cases;
    })()
).test("validateWebcamUrl", function (params, assert) {
    if (params.windowLocationOverride) {
        fetchWindowLocation = function () {
            return params.windowLocationOverride;
        };
    }

    var result = validateWebcamUrl(params.streamUrl);

    assert.equal(
        result.toString(),
        params.expected.toString(),
        "As expected: " + String(params.expected)
    );
});

QUnit.module("getExternalHostUrl");
QUnit.cases(
    (function () {
        var cases = [];

        var params = [
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
        ];

        var param, i;
        for (i = 0; i < params.length; i++) {
            param = params[i];
            cases.push(param);
        }

        return cases;
    })()
).test("getExternalHostUrl", function (params, assert) {
    if (params.windowLocation) {
        fetchWindowLocation = function () {
            return params.windowLocation;
        };
    }

    var result = getExternalHostUrl();
    assert.equal(result, params.expected, "As expected: " + String(params.expected));
});

QUnit.module("escapeUnprintableCharacters");
QUnit.cases(
    (function () {
        var cases = [];

        var params = [
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
        ];

        var param, i;
        for (i = 0; i < params.length; i++) {
            param = params[i];
            cases.push(param);
        }

        return cases;
    })()
).test("escapeUnprintableCharacters", function (params, assert) {
    var result = undefined;
    var exceptionThrown = false;

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
});

QUnit.module("getQueryParameterByName");
QUnit.cases(
    (function () {
        var cases = [];

        var params = [
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
        ];

        var param, i;
        for (i = 0; i < params.length; i++) {
            param = params[i];
            cases.push(param);
        }

        return cases;
    })()
).test("getQueryParameterByName", function (params, assert) {
    if (params.windowLocation) {
        fetchWindowLocation = function () {
            return params.windowLocation;
        };
    }

    var result = getQueryParameterByName(params.inputName, params.inputUrl);
    assert.equal(result, params.expected, "As expected: " + String(params.expected));
});

QUnit.module("formatNumberK");
QUnit.cases(
    (function () {
        var cases = [];

        var params = [
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
        ];

        var param, i;
        for (i = 0; i < params.length; i++) {
            param = params[i];
            cases.push(param);
        }

        return cases;
    })()
).test("formatNumberK", function (params, assert) {
    var result = undefined;
    var exceptionMessage = undefined;

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
});

QUnit.module("formatHuman");
QUnit.cases(
    (function () {
        var cases = [];

        var params = [
            {
                title: "UndefinedNumber",
                input: undefined,
                expected: "-"
            },
            {
                title: "Text",
                input: "text",
                expected: "-NaNK"
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
                title: "ThousandTen",
                input: 1100,
                expected: "1.1K"
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
        ];

        var param, i;
        for (i = 0; i < params.length; i++) {
            param = params[i];
            cases.push(param);
        }

        return cases;
    })()
).test("formatHuman", function (params, assert) {
    var result = formatHuman(params.input);
    assert.equal(result, params.expected, "As expected: " + String(params.expected));
});

QUnit.module("cleanTemperature");
QUnit.cases(
    (function () {
        var cases = [];

        var params = [
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
        ];

        var param, i;
        for (i = 0; i < params.length; i++) {
            param = params[i];
            cases.push(param);
        }

        return cases;
    })()
).test("cleanTemperature", function (params, assert) {
    var result = cleanTemperature(params.temp, params.offThreshold);
    assert.equal(result, params.expected, "As expected: " + String(params.expected));
});

QUnit.module("formatFilament");
QUnit.cases(
    (function () {
        var cases = [];

        var params = [
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
        ];

        var param, i;
        for (i = 0; i < params.length; i++) {
            param = params[i];
            cases.push(param);
        }

        return cases;
    })()
).test("formatFilament", function (params, assert) {
    var result = formatFilament(params.filament);
    assert.equal(result, params.expected, "As expected: " + String(params.expected));
});

QUnit.module("formatTimeAgo");
QUnit.cases(
    (function () {
        var cases = [];

        var params = [
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
        ];

        var param, i;
        for (i = 0; i < params.length; i++) {
            param = params[i];
            cases.push(param);
        }

        return cases;
    })()
).test("formatTimeAgo", function (params, assert) {
    var result = formatTimeAgo(params.unixTimestamp);
    assert.equal(result, params.expected, "As expected: " + String(params.expected));
});

QUnit.module("splitTextToArray");
QUnit.cases(
    (function () {
        var cases = [];

        var params = [
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
        ];

        var param, i;
        for (i = 0; i < params.length; i++) {
            param = params[i];
            cases.push(param);
        }

        return cases;
    })()
).test("splitTextToArray", function (params, assert) {
    var result = splitTextToArray(
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
});

QUnit.module("formatDate");
QUnit.cases(
    (function () {
        var cases = [];

        var params = [
            {
                title: "UndefinedTimestamp",
                unixTimestamp: undefined,
                options: undefined,
                expected: "-"
            },
            {
                title: "Millennium",
                unixTimestamp: 946684800,
                options: undefined,
                expected: moment.unix(946684800).format("YYYY-MM-DD HH:mm")
            },
            {
                title: "ExplicitNoSeconds",
                unixTimestamp: 10,
                options: {seconds: false},
                expected: moment.unix(10).format("YYYY-MM-DD HH:mm")
            },
            {
                title: "WithSeconds",
                unixTimestamp: 10,
                options: {seconds: true},
                expected: moment.unix(10).format("YYYY-MM-DD HH:mm:ss")
            }
        ];

        var param, i;
        for (i = 0; i < params.length; i++) {
            param = params[i];
            cases.push(param);
        }

        return cases;
    })()
).test("formatDate", function (params, assert) {
    var result = formatDate(params.unixTimestamp, params.options);
    assert.equal(result, params.expected, "As expected: " + String(params.expected));
});
