_.mixin({sprintf: sprintf, vsprintf: vsprintf});

QUnit.module("bytesFromSize");
QUnit.cases(
    (function () {
        var cases = [];

        var params = [
            // empty inputs
            {input: undefined, expected: undefined},
            {input: "", expected: undefined},

            // unknown units
            {input: "1 PB", expected: undefined},
            {input: "234.5 unknown", expected: undefined},
            {input: "234.5unknown", expected: undefined},

            // conversion
            {input: "1", expected: 1},
            {input: "1b", expected: 1},
            {input: "1 B", expected: 1},
            {input: "1 byte", expected: 1},
            {input: "1 bYtES", expected: 1},
            {input: "1.1", expected: 1.1},
            {input: ".1", expected: 0.1},
            {input: "1 KB", expected: 1024},
            {input: "2 KB", expected: 2048},
            {input: "1 MB", expected: Math.pow(1024, 2)},
            {input: "500mb", expected: 500 * Math.pow(1024, 2)},
            {input: "500.2mb", expected: 500.2 * Math.pow(1024, 2)},
            {input: "1 GB", expected: Math.pow(1024, 3)},
            {input: "1 TB", expected: Math.pow(1024, 4)}
        ];

        var param, i;
        for (i = 0; i < params.length; i++) {
            param = params[i];
            param["title"] =
                param.input != undefined ? '"' + String(param.input) + '"' : "undefined";
            cases.push(param);
        }

        return cases;
    })()
).test("bytesFromSize", function (params, assert) {
    assert.equal(
        params.expected,
        bytesFromSize(params.input),
        "As expected: " + String(params.expected)
    );
});

QUnit.module("formatSize");
QUnit.cases(
    (function () {
        var cases = [];

        var params = [
            {input: undefined, expected: "-"},
            {input: "", expected: "-"},
            {input: 1, expected: "1.0bytes"},
            {input: 1.1, expected: "1.1bytes"},
            {input: 1024, expected: "1.0KB"},
            {input: 2048, expected: "2.0KB"},
            {input: 2.2 * 1024, expected: "2.2KB"},
            {input: 23.5 * Math.pow(1024, 2), expected: "23.5MB"},
            {input: 23.5 * Math.pow(1024, 3), expected: "23.5GB"},
            {input: 23.5 * Math.pow(1024, 4), expected: "23.5TB"},
            {input: 2 * Math.pow(1024, 5), expected: "2048.0TB"}
        ];

        var param, i;
        for (i = 0; i < params.length; i++) {
            param = params[i];
            param["title"] = String(param.input);
            cases.push(param);
        }

        return cases;
    })()
).test("formatSize", function (params, assert) {
    assert.equal(
        params.expected,
        formatSize(params.input),
        "As expected: " + String(params.expected)
    );
});

QUnit.module("formatTemperature");
QUnit.cases(
    (function () {
        var cases = [];

        var params = [
            {
                input: undefined,
                showF: undefined,
                useUnicode: undefined,
                offThreshold: undefined,
                expected: "-"
            },
            {
                input: "",
                showF: undefined,
                useUnicode: undefined,
                offThreshold: undefined,
                expected: "-"
            },
            {
                input: 1.0,
                showF: undefined,
                useUnicode: undefined,
                offThreshold: 1.1,
                expected: "off"
            },
            {
                input: 1.0,
                showF: undefined,
                useUnicode: undefined,
                offThreshold: 1.0,
                expected: "1.0&deg;C"
            },
            {
                input: 1.0,
                showF: undefined,
                useUnicode: undefined,
                offThreshold: undefined,
                expected: "1.0&deg;C"
            },
            {
                input: 1.0,
                showF: true,
                useUnicode: undefined,
                offThreshold: undefined,
                expected: "1.0&deg;C (33.8&deg;F)"
            },
            {
                input: 1.0,
                showF: true,
                useUnicode: true,
                offThreshold: undefined,
                expected: "1.0\u00B0C (33.8\u00B0F)"
            },
            {
                input: 1.0,
                showF: undefined,
                useUnicode: false,
                offThreshold: undefined,
                expected: "1.0&deg;C"
            },
            {
                input: 1.0,
                showF: undefined,
                useUnicode: true,
                offThreshold: undefined,
                expected: "1.0\u00B0C"
            },
            {
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
            param["title"] =
                String(param.input) +
                String(param.showF) +
                String(param.offThreshold) +
                String(param.useUnicode);
            cases.push(param);
        }

        return cases;
    })()
).test("formatTemperature", function (params, assert) {
    assert.equal(
        params.expected,
        formatTemperature(
            params.input,
            params.showF,
            params.offThreshold,
            params.useUnicode
        ),
        "As expected: " + String(params.expected)
    );
});

QUnit.module("determineWebcamStreamType");
QUnit.cases(
    (function () {
        var cases = [];

        var params = [
            {
                streamUrl: undefined,
                exceptionExpected: "Empty streamUrl. Cannot determine stream type.",
                expectedResult: undefined
            },
            {
                streamUrl: "invalidUrl",
                exceptionExpected: "Invalid streamUrl. Cannot determine stream type.",
                expectedResult: undefined
            },
            {
                streamUrl: "webrtc://localhost/stream",
                exceptionExpected: undefined,
                expectedResult: "webrtc"
            },
            {
                streamUrl: "webrtcs://localhost/stream",
                exceptionExpected: undefined,
                expectedResult: "webrtc"
            },
            {
                streamUrl: "https://localhost/stream.m3u8",
                exceptionExpected: undefined,
                expectedResult: "hls"
            },
            {
                streamUrl: "https://localhost/stream",
                exceptionExpected: undefined,
                expectedResult: "mjpg"
            }
        ];

        var param, i;
        for (i = 0; i < params.length; i++) {
            param = params[i];
            param["title"] =
                String(param.streamUrl) +
                String(param.exceptionExpected) +
                String(param.expectedResult);
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
        params.exceptionExpected,
        exceptionMessage,
        "Exception expected: " + String(params.exceptionExpected)
    );

    assert.equal(
        params.expectedResult,
        result,
        "As expected: " + String(params.expectedResult)
    );
});

QUnit.module("validateWebcamUrl");
QUnit.cases(
    (function () {
        var cases = [];

        var params = [
            {
                streamUrl: undefined,
                expected: false,
                windowLocationOverride: undefined
            },
            {
                streamUrl: "//localhost/stream",
                expected: new URL("https://localhost/stream"),
                windowLocationOverride: {protocol: "https:"}
            },
            {
                streamUrl: "/stream",
                expected: new URL("https://localhost/stream"),
                windowLocationOverride: {
                    protocol: "https:",
                    port: "443",
                    hostname: "localhost"
                }
            },
            {
                streamUrl: "http://localhost/stream",
                expected: new URL("http://localhost/stream"),
                windowLocationOverride: undefined
            },
            {
                streamUrl: "https://localhost/stream",
                expected: new URL("https://localhost/stream"),
                windowLocationOverride: undefined
            },
            {
                streamUrl: "webrtc://localhost/stream",
                expected: new URL("webrtc://localhost/stream"),
                windowLocationOverride: undefined
            },
            {
                streamUrl: "webrtcs://localhost/stream",
                expected: new URL("webrtcs://localhost/stream"),
                windowLocationOverride: undefined
            },
            {
                streamUrl: "invalid",
                expected: false,
                windowLocationOverride: undefined
            },
            {
                streamUrl: "//exception",
                expected: false,
                windowLocationOverride: {protocol: ":"}
            }
        ];

        var param, i;
        for (i = 0; i < params.length; i++) {
            param = params[i];
            param["title"] = String(param.streamUrl) + String(param.expected);
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
        params.expected.toString(),
        result.toString(),
        "As expected: " + String(params.expected)
    );
});

QUnit.module("getExternalHostUrl");
QUnit.cases(
    (function () {
        var cases = [];

        var params = [
            {
                windowLocation: {
                    protocol: "https:",
                    port: "443",
                    hostname: "localhost"
                },
                expected: "https://localhost"
            },
            {
                windowLocation: {
                    protocol: "https:",
                    port: "8000",
                    hostname: "localhost"
                },
                expected: "https://localhost:8000"
            },

            {
                windowLocation: {
                    protocol: "http:",
                    port: "80",
                    hostname: "localhost"
                },
                expected: "http://localhost"
            },
            {
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
            param["title"] =
                String(param.windowLocation.protocol) +
                "//" +
                String(param.windowLocation.hostname) +
                String(param.windowLocation.port);
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

    assert.equal(params.expected, result, "As expected: " + String(params.expected));
});
