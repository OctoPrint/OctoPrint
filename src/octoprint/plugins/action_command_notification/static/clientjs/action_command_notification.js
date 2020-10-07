(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function (OctoPrintClient) {
    var OctoPrintActionCommandNotificationClient = function (base) {
        this.base = base;
    };

    OctoPrintActionCommandNotificationClient.prototype.get = function (refresh, opts) {
        return this.base.get(
            this.base.getSimpleApiUrl("action_command_notification"),
            opts
        );
    };

    OctoPrintActionCommandNotificationClient.prototype.clear = function (opts) {
        return this.base.simpleApiCommand(
            "action_command_notification",
            "clear",
            {},
            opts
        );
    };

    OctoPrintClient.registerPluginComponent(
        "action_command_notification",
        OctoPrintActionCommandNotificationClient
    );
    return OctoPrintActionCommandNotificationClient;
});
