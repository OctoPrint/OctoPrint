_.mixin({sprintf: sprintf, vsprintf: vsprintf});

QUnit.module("getParsedBaseUrl");
QUnit.cases(
    (function () {
        return [
            {
                title: "fully qualified baseurl",
                baseurl: "https://example.com",
                location: undefined,
                expected: "https://example.com/"
            },
            {
                title: "fully qualified baseurl with http",
                baseurl: "http://example.com",
                location: undefined,
                expected: "http://example.com/"
            },
            {
                title: "fully qualified baseurl with custom port",
                baseurl: "https://example.com:5000",
                location: undefined,
                expected: "https://example.com:5000/"
            },
            {
                title: "website root",
                baseurl: "/",
                location: "https://example.com",
                expected: "https://example.com/"
            },
            {
                title: "website root with custom port",
                baseurl: "/",
                location: "https://example.com:5000",
                expected: "https://example.com:5000/"
            },
            {
                title: "single level prefix",
                baseurl: "/octoprint/",
                location: "https://example.com",
                expected: "https://example.com/octoprint/"
            },
            {
                title: "multi level prefix",
                baseurl: "/path/to/octoprint/",
                location: "https://example.com",
                expected: "https://example.com/path/to/octoprint/"
            },
            {
                title: "multi level prefix with http and custom port",
                baseurl: "/path/to/octoprint/",
                location: "http://example.com:5000",
                expected: "http://example.com:5000/path/to/octoprint/"
            },
            {
                title: "multi level prefix with https, custom port, no trailing slash",
                baseurl: "/path/to/octoprint",
                location: "https://example.com:5001",
                expected: "https://example.com:5001/path/to/octoprint"
            }
        ];
    })()
).test("getParsedBaseUrl", function (params, assert) {
    OctoPrint.options.baseurl = params.baseurl;
    assert.equal(
        OctoPrint.getParsedBaseUrl(params.location).toString(),
        params.expected,
        "Expected: " + String(params.expected)
    );
});

QUnit.module("getCookieSuffix");
QUnit.cases(
    (function () {
        return [
            {
                title: "http with default port",
                baseurl: "http://example.com",
                expected: "_P80"
            },
            {
                title: "https with default port",
                baseurl: "https://example.com",
                expected: "_P443"
            },
            {
                title: "custom port",
                baseurl: "http://example.com:5000",
                expected: "_P5000"
            },
            {
                title: "single level prefix",
                baseurl: "https://example.com/octoprint/",
                expected: "_P443_R|octoprint"
            },
            {
                title: "multi level prefix",
                baseurl: "https://example.com/path/to/octoprint",
                expected: "_P443_R|path|to|octoprint"
            }
        ];
    })()
).test("getCookieSuffix", function (params, assert) {
    OctoPrint.options.baseurl = params.baseurl;
    assert.equal(
        OctoPrint.getCookieSuffix(),
        params.expected,
        "Expected: " + String(params.expected)
    );
});
