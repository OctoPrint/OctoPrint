(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrint", "jquery"], factory);
    } else {
        factory(window.OctoPrint, window.$);
    }
})(window || this, function(OctoPrint, $) {
    var url = "api/timelapse";

    var timelapseUrl = function(filename) {
        return url + "/" + filename;
    };

    var unrenderedTimelapseUrl = function(name) {
        return url + "/unrendered/" + name;
    };

    var getTimelapseData = function (opts) {
        return OctoPrint.get(url, opts);
    };

    OctoPrint.timelapse = {
        get: getTimelapseData,

        list: function (opts) {
            var deferred = $.Deferred();

            getTimelapseData(opts)
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

        deleteUnrendered: function(name, opts) {
            return OctoPrint.delete(unrenderedTimelapseUrl(name), opts);
        },

        renderUnrendered: function(name, opts) {
            return OctoPrint.issueCommand(unrenderedTimelapseUrl(name), "render");
        },

        getConfig: function (opts) {
            var deferred = $.Deferred();
            getTimelapseData(opts)
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
