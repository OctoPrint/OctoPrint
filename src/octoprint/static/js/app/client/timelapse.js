(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrint", "jquery"], factory);
    } else {
        factory(window.OctoPrint, window.$);
    }
})(window || this, function(OctoPrint, $) {
    var url = "api/timelapse";

    var downloadUrl = "downloads/timelapse";

    var timelapseUrl = function(filename) {
        return url + "/" + filename;
    };

    var timelapseDownloadUrl = function(filename) {
        return downloadUrl + "/" + filename;
    };

    var unrenderedTimelapseUrl = function(name) {
        return url + "/unrendered/" + name;
    };

    var getTimelapseData = function (unrendered, opts) {
        if (unrendered) {
            opts = opts || {};
            opts.data = {unrendered: unrendered};
        }
        return OctoPrint.get(url, opts);
    };

    OctoPrint.timelapse = {
        get: getTimelapseData,

        list: function(opts) {
            var deferred = $.Deferred();

            getTimelapseData(true, opts)
                .done(function (response, status, request) {
                    deferred.resolve({
                        rendered: response.files,
                        unrendered: response.unrendered
                    }, status, request);
                })
                .fail(function () {
                    deferred.reject.apply(null, arguments);
                });

            return deferred.promise();
        },

        listRendered: function (opts) {
            var deferred = $.Deferred();

            getTimelapseData(false, opts)
                .done(function (response, status, request) {
                    deferred.resolve(response.files, status, request);
                })
                .fail(function () {
                    deferred.reject.apply(null, arguments);
                });

            return deferred.promise();
        },

        listUnrendered: function (opts) {
            var deferred = $.Deferred();

            getTimelapseData(true, opts)
                .done(function (response, status, request) {
                    deferred.resolve(response.unrendered, status, request);
                })
                .fail(function () {
                    deferred.reject.apply(null, arguments);
                });

            return deferred.promise();
        },

        download: function (filename, opts) {
            return OctoPrint.download(timelapseDownloadUrl(filename), opts);
        },

        delete: function (filename, opts) {
            return OctoPrint.delete(timelapseUrl(filename), opts);
        },

        deleteUnrendered: function(name, opts) {
            return OctoPrint.delete(unrenderedTimelapseUrl(name), opts);
        },

        renderUnrendered: function(name, opts) {
            return OctoPrint.issueCommand(unrenderedTimelapseUrl(name), "render");
        },

        getConfig: function (opts) {
            var deferred = $.Deferred();
            getTimelapseData(false, opts)
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
