_.mixin({"sprintf": sprintf, "vsprintf": vsprintf});

QUnit.module("bytesFromSize");
QUnit
    .cases(function(){
        var cases = [];

        var params = [
            // empty inputs
            { input: undefined, expected: undefined },
            { input: "", expected: undefined },

            // unknown units
            { input: "1 PB", expected: undefined },
            { input: "234.5 unknown", expected: undefined },
            { input: "234.5unknown", expected: undefined },

            // conversion
            { input: "1", expected: 1 },
            { input: "1b", expected: 1 },
            { input: "1 B", expected: 1 },
            { input: "1 byte", expected: 1 },
            { input: "1 bYtES", expected: 1 },
            { input: "1.1", expected: 1.1 },
            { input: ".1", expected: 0.1 },
            { input: "1 KB", expected: 1024 },
            { input: "2 KB", expected: 2048 },
            { input: "1 MB", expected: Math.pow(1024, 2)},
            { input: "500mb", expected: 500 * Math.pow(1024, 2)},
            { input: "500.2mb", expected: 500.2 * Math.pow(1024, 2)},
            { input: "1 GB", expected: Math.pow(1024, 3)},
            { input: "1 TB", expected: Math.pow(1024, 4)}
        ];

        var param, i;
        for (i = 0; i < params.length; i++) {
            param = params[i];
            param["title"] = param.input != undefined ? '"' + String(param.input) + '"' : "undefined";
            cases.push(param);
        }

        return cases;
    }())
    .test("bytesFromSize", function(params, assert) {
        assert.equal(params.expected, bytesFromSize(params.input), "As expected: " + String(params.expected));
    }
);

QUnit.module("formatSize");
QUnit
    .cases(function(){
        var cases = [];

        var params = [
            { input: undefined, expected: "-" },
            { input: "", expected: "-" },
            { input: 1, expected: "1.0bytes" },
            { input: 1.1, expected: "1.1bytes" },
            { input: 1024, expected: "1.0KB" },
            { input: 2048, expected: "2.0KB" },
            { input: 2.2 * 1024, expected: "2.2KB" },
            { input: 23.5 * Math.pow(1024, 2), expected: "23.5MB" },
            { input: 23.5 * Math.pow(1024, 3), expected: "23.5GB" },
            { input: 23.5 * Math.pow(1024, 4), expected: "23.5TB" },
            { input: 2 * Math.pow(1024, 5), expected: "2048.0TB" }
        ];

        var param, i;
        for (i = 0; i < params.length; i++) {
            param = params[i];
            param["title"] = String(param.input);
            cases.push(param);
        }

        return cases;
    }())
    .test("formatSize", function(params, assert) {
        assert.equal(params.expected, formatSize(params.input), "As expected: " + String(params.expected));
    }
);
