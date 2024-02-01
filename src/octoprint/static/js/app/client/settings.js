(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient", "jquery"], factory);
    } else {
        factory(global.OctoPrintClient, global.$);
    }
})(this, function (OctoPrintClient, $) {
    var url = "api/settings";
    var apiKeyUrl = url + "/apikey";

    var OctoPrintSettingsClient = function (base) {
        this.base = base;
    };

    OctoPrintSettingsClient.prototype.get = function (opts) {
        return this.base.get(url, opts);
    };

    OctoPrintSettingsClient.prototype.save = function (settings, opts) {
        settings = settings || {};
        return this.base.postJson(url, settings, opts);
    };

    OctoPrintSettingsClient.prototype.getPluginSettings = function (plugin, opts) {
        return this.get(opts).then(function (settings, statusText, request) {
            if (!settings.plugins || !settings.plugins[plugin]) {
                return $.Deferred()
                    .reject(request, "dataerror", "No settings for plugin " + plugin)
                    .promise();
            } else {
                return settings.plugins[plugin];
            }
        });
    };

    OctoPrintSettingsClient.prototype.savePluginSettings = function (
        plugin,
        settings,
        opts
    ) {
        var data = {};
        data["plugins"] = {};
        data["plugins"][plugin] = settings;
        return this.save(data, opts);
    };

    OctoPrintSettingsClient.prototype.generateApiKey = function (opts) {
        return this.base.postJson(apiKeyUrl, opts);
    };

    OctoPrintSettingsClient.prototype.deleteApiKey = function (opts) {
        return this.base.delete(apiKeyUrl, opts);
    };

    OctoPrintClient.registerComponent("settings", OctoPrintSettingsClient);
    return OctoPrintSettingsClient;
});
