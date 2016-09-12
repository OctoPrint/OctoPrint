(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrint", "jquery"], factory);
    } else {
        factory(window.OctoPrint, window.$);
    }
})(window || this, function(OctoPrint, $) {
    var url = "api/settings";

    var get = function(opts) {
        return OctoPrint.get(url, opts);
    };

    var save = function(settings, opts) {
        settings = settings || {};
        return OctoPrint.postJson(url, settings, opts);
    };

    OctoPrint.settings = {
        get: get,
        save: save,

        getPluginSettings: function (plugin, opts) {
            return get(opts)
                .then(function (settings, statusText, request) {
                    if (!settings.plugins || !settings.plugins[plugin]) {
                        return $.Deferred()
                            .reject(request, "dataerror", "No settings for plugin " + plugin)
                            .promise();
                    } else {
                        return settings.plugins[plugin];
                    }
                });
        },

        savePluginSettings: function (plugin, settings, opts) {
            var data = {};
            data["plugins"] = {};
            data["plugins"][plugin] = settings;
            return save(data, opts);
        }
    }
});
