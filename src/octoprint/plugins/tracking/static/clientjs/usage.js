(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function (OctoPrintClient) {
    var OctoPrintTrackingClient = function (base) {
        this.base = base;
    };

    OctoPrintTrackingClient.prototype.track = function (event, payload, opts) {
        return this.base.simpleApiCommand(
            "tracking",
            "track",
            {event: event, payload: payload},
            opts
        );
    };

    OctoPrintClient.registerPluginComponent("tracking", OctoPrintTrackingClient);
    return OctoPrintTrackingClient;
});
