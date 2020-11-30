(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient", "jquery"], factory);
    } else {
        factory(global.OctoPrintClient, global.$);
    }
})(this, function (OctoPrint, $) {
    var url = "api/util";
    var testUrl = url + "/test";

    var OctoPrintUtilClient = function (base) {
        this.base = base;
    };

    OctoPrintUtilClient.prototype.test = function (command, parameters, opts) {
        return this.base.issueCommand(testUrl, command, parameters, opts);
    };

    OctoPrintUtilClient.prototype.testPath = function (path, additional, opts) {
        additional = additional || {};

        var data = $.extend({}, additional);
        data.path = path;

        return this.test("path", data, opts);
    };

    OctoPrintUtilClient.prototype.testExecutable = function (path, additional, opts) {
        additional = additional || {};

        var data = $.extend({}, additional);
        data.path = path;
        data.check_type = "file";
        data.check_access = "x";

        return this.test("path", data, opts);
    };

    OctoPrintUtilClient.prototype.testUrl = function (url, additional, opts) {
        additional = additional || {};

        var data = $.extend({}, additional);
        data.url = url;

        return this.test("url", data, opts);
    };

    OctoPrintUtilClient.prototype.testServer = function (host, port, additional, opts) {
        additional = additional || {};

        var data = $.extend({}, additional);
        data.host = host;
        data.port = port;

        return this.test("server", data, opts);
    };

    OctoPrintUtilClient.prototype.testResolution = function (name, additional, opts) {
        additional = additional || {};

        var data = $.extend({}, additional);
        data.name = name;

        return this.test("resolution", data, opts);
    };

    OctoPrintUtilClient.prototype.testAddress = function (address, additional, opts) {
        additional = additional || {};

        var data = $.extend({}, additional);
        data.address = address;

        return this.test("address", data, opts);
    };

    OctoPrintClient.registerComponent("util", OctoPrintUtilClient);
    return OctoPrintUtilClient;
});
