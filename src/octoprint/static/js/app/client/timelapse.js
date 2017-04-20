(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient", "jquery"], factory);
    } else {
        factory(global.OctoPrintClient, global.$);
    }
})(this, function(OctoPrintClient, $) {
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

    var OctoPrintTimelapseClient = function(base) {
        this.base = base;
    };

    OctoPrintTimelapseClient.prototype.get = function (unrendered, opts) {
        if (unrendered) {
            opts = opts || {};
            opts.data = {unrendered: unrendered};
        }
        return this.base.get(url, opts);
    };

    OctoPrintTimelapseClient.prototype.list = function(opts) {
        var deferred = $.Deferred();

        this.get(true, opts)
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
    };

    OctoPrintTimelapseClient.prototype.listRendered = function (opts) {
        var deferred = $.Deferred();

        this.get(false, opts)
            .done(function (response, status, request) {
                deferred.resolve(response.files, status, request);
            })
            .fail(function () {
                deferred.reject.apply(null, arguments);
            });

        return deferred.promise();
    };

    OctoPrintTimelapseClient.prototype.listUnrendered = function (opts) {
        var deferred = $.Deferred();

        this.get(true, opts)
            .done(function (response, status, request) {
                deferred.resolve(response.unrendered, status, request);
            })
            .fail(function () {
                deferred.reject.apply(null, arguments);
            });

        return deferred.promise();
    };

    OctoPrintTimelapseClient.prototype.download = function (filename, opts) {
        return this.base.download(timelapseDownloadUrl(filename), opts);
    };

    OctoPrintTimelapseClient.prototype.delete = function (filename, opts) {
        return this.base.delete(timelapseUrl(filename), opts);
    };

    OctoPrintTimelapseClient.prototype.deleteUnrendered = function(name, opts) {
        return this.base.delete(unrenderedTimelapseUrl(name), opts);
    };

    OctoPrintTimelapseClient.prototype.renderUnrendered = function(name, opts) {
        return this.base.issueCommand(unrenderedTimelapseUrl(name), "render");
    };

    OctoPrintTimelapseClient.prototype.getConfig = function (opts) {
        var deferred = $.Deferred();
        this.get(false, opts)
            .done(function (response, status, request) {
                deferred.resolve(response.config, status, request);
            })
            .fail(function () {
                deferred.reject.apply(null, arguments);
            });
        return deferred.promise();
    };

    OctoPrintTimelapseClient.prototype.saveConfig = function (config, opts) {
        config = config || {};
        return OctoPrint.postJson(url, config, opts);
    };

    OctoPrintClient.registerComponent("timelapse", OctoPrintTimelapseClient);
    return OctoPrintTimelapseClient;
});
