OctoPrint.settings = (function($, _) {
    var exports = {};

    var url = "api/settings";

    exports.get = function(opts) {
        return OctoPrint.get(url, opts);
    };

    exports.save = function(settings, opts) {
        settings = settings || {};
        return OctoPrint.postJson(url, settings, opts);
    };

    exports.getPluginSettings = function(plugin, opts) {
        return exports.get(opts)
            .then(function(settings, statusText, request) {
                if (!settings.plugins || !settings.plugins[plugin]) {
                    return $.Deferred()
                        .reject(request, "dataerror", "No settings for plugin " + plugin)
                        .promise();
                } else {
                    return settings.plugins[plugin];
                }
            });
    };

    exports.savePluginSettings = function(plugin, settings, opts) {
        var data = {};
        data["plugins"] = {};
        data["plugins"][plugin] = settings;
        return exports.save(data, opts);
    };

    return exports;
})($, _);
