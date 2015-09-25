OctoPrint.timelapse = (function($, _) {
    var exports = {};

    var url = "api/timelapse";

    exports.get = function(opts) {
        return OctoPrint.get(url, opts);
    };

    exports.list = function(opts) {
        var deferred = $.Deferred();

        exports.get(opts)
            .done(function(response, status, request) {
                deferred.resolve(response.files, status, request);
            })
            .fail(function() {
                deferred.reject.apply(null, arguments);
            });

        return deferred.promise();
    };

    exports.download = function(filename, opts) {
        return OctoPrint.download(url + "/" + filename, opts);
    };

    exports.delete = function(filename, opts) {
        return OctoPrint.delete(url + "/" + filename, opts);
    };

    exports.getConfig = function(opts) {
        var deferred = $.Deferred();
        exports.get(opts)
            .done(function(response, status, request) {
                deferred.resolve(response.config, status, request);
            })
            .fail(function() {
                deferred.reject.apply(null, arguments);
            });
        return deferred.promise();
    };

    exports.saveConfig = function(config, opts) {
        config = config || {};
        return OctoPrint.postJson(url, config, opts);
    };

    return exports;
})($, _);
