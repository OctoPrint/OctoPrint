(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrint", "jquery"], factory);
    } else {
        factory(window.OctoPrint, window.$);
    }
})(window || this, function(OctoPrint, $) {
    var exports = {};

    var url = "api/timelapse";

    var timelapseUrl = function(filename) {
        return url + "/" + filename;
    };

    OctoPrint.timelapse = {
        get: function (opts) {
            return OctoPrint.get(url, opts);
        },

        list: function (opts) {
            var deferred = $.Deferred();

            exports.get(opts)
                .done(function (response, status, request) {
                    deferred.resolve(response.files, status, request);
                })
                .fail(function () {
                    deferred.reject.apply(null, arguments);
                });

            return deferred.promise();
        },

        download: function (filename, opts) {
            return OctoPrint.download(timelapseUrl(filename), opts);
        },

        delete: function (filename, opts) {
            return OctoPrint.delete(timelapseUrl(filename), opts);
        },

        getConfig: function (opts) {
            var deferred = $.Deferred();
            exports.get(opts)
                .done(function (response, status, request) {
                    deferred.resolve(response.config, status, request);
                })
                .fail(function () {
                    deferred.reject.apply(null, arguments);
                });
            return deferred.promise();
        },

        saveConfig: function (config, opts) {
            config = config || {};
            return OctoPrint.postJson(url, config, opts);
        }
    }
});
