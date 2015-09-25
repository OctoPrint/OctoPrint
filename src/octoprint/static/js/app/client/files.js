OctoPrint.files = (function($, _) {
    var exports = {};

    var resourceForFile = function(location, filename) {
        return "api/files/" + location + "/" + filename;
    };

    var issueFileCommand = function(location, filename, command, data, opts) {
        var url = resourceForFile(location, filename);
        return OctoPrint.issueCommand(url, command, data, opts);
    };

    exports.list = function(opts) {
        return OctoPrint.get("api/files", opts);
    };

    exports.listForLocation = function(location, opts) {
        return OctoPrint.get("api/files/" + location, opts);
    };

    exports.get = function(location, filename, opts) {
        return OctoPrint.get(resourceForFile(location, filename), opts);
    };

    exports.select = function(location, filename, print, opts) {
        print = print || false;

        var data = {
            print: print
        };

        return issueFileCommand(location, filename, "select", data, opts);
    };

    exports.slice = function(location, filename, parameters, opts) {
        return issueFileCommand(location, filename, "slice",
            parameters || {}, opts);
    };

    exports.delete = function(location, filename, opts) {
        return OctoPrint.delete(resourceForFile(location, filename), opts);
    };

    exports.upload = function(location, file, data) {
        data = data || {};

        var filename = data.filename || undefined;
        return OctoPrint.upload("api/files/" + location, file, filename, data);
    };

    exports.download = function(location, filename, opts) {
        var deferred = $.Deferred();
        exports.get(location, filename, opts)
            .done(function(response) {
                OctoPrint.download(response.refs.download, opts)
                    .done(function() {
                        deferred.resolve.apply(null, arguments);
                    })
                    .fail(function() {
                        deferred.reject.apply(null, arguments);
                    });
            })
            .fail(function() {
                deferred.reject.apply(null, arguments);
            });
        return deferred.promise();
    };

    return exports;
})($, _);
