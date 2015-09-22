OctoPrint.files = (function($, _) {
    var exports = {};

    exports.get = function(opts) {
        opts = opts || {};

        var path = "api/files";
        var location = opts.location || "";

        if (location && _.contains(["local", "sdcard"], location)) {
            path += "/" + location;
        }

        var params = _.extend({}, opts);
        params.url = path;

        return OctoPrint.getJson(params);
    };

    exports.listAll = function(opts) {
        opts = opts || {};

        if (opts.location) {
            opts.location = undefined;
        }

        return exports.get(opts);
    };

    exports.listAllForLocation = function(location, opts) {
        opts = opts || {};
        opts.location = location;

        return exports.get(opts);
    };

    exports.getInfoForFile = function(location, filename, opts) {
        opts = opts || {};

        var params = $.extend({}, opts);
        params.url = exports.resourceForFile(location, filename);

        return OctoPrint.getJson(params);
    };

    exports.selectFile = function(location, filename, print, opts) {
        print = print || false;

        var data = {
            print: print
        };

        return exports.issueFileCommand(location, filename, "select", data, opts);
    };

    exports.sliceFile = function(location, filename, parameters, opts) {
        parameters = parameters || {};

        return exports.issueFileCommand(location, filename, "slice", parameters, opts);
    };

    exports.issueFileCommand = function(location, filename, command, data, opts) {
        opts = opts || {};
        data = data || {};

        var payload = $.extend({}, data);
        payload.command = command;

        var params = $.extend({}, opts);
        params.url = exports.resourceForFile(location, filename);

        return OctoPrint.postJson(payload, params);
    };

    exports.deleteFile = function(location, filename, opts) {
        opts = opts || {};

        var params = $.extend({}, opts);
        params.url = exports.resourceForFile(location, filename);

        return OctoPrint.delete(opts);
    };

    exports.resourceForFile = function(location, filename) {
        return "api/files/" + location + "/" + filename;
    };

    return exports;
})($, _);
