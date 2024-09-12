(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function (OctoPrintClient) {
    const OctoPrintHealthCheckClient = function (base) {
        this.base = base;
        this.url = this.base.getSimpleApiUrl("health_check");
    };

    OctoPrintHealthCheckClient.prototype.get = function (refresh, opts) {
        let query = "";
        if (refresh) {
            query += "refresh=true";
        }
        return this.base.get(this.url + (query ? "?" + query : ""), opts);
    };

    OctoPrintClient.registerPluginComponent("health_check", OctoPrintHealthCheckClient);
    return OctoPrintHealthCheckClient;
});
