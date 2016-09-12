(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrint", "jquery"], factory);
    } else {
        factory(window.OctoPrint, window.$);
    }
})(window || this, function(OctoPrint, $) {
    var url = "api/util";
    var testUrl = url + "/test";

    var test = function(command, data, opts) {
        return OctoPrint.issueCommand(testUrl, command, data, opts);
    };

    OctoPrint.util = {
        test: test,

        testPath: function(path, additional, opts) {
            additional = additional || {};

            var data = $.extend({}, additional);
            data.path = path;

            return test("path", data, opts);
        },

        testExecutable: function(path, additional, opts) {
            additional = additional || {};

            var data = $.extend({}, additional);
            data.path = path;
            data.check_type = "file";
            data.check_access = "x";

            return test("path", data, opts);
        },

        testUrl: function(url, additional, opts) {
            additional = additional || {};

            var data = $.extend({}, additional);
            data.url = url;

            return test("url", data, opts);
        }
    };
});
