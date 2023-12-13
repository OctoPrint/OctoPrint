(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function (OctoPrintClient) {
    var OctoPrintAchievementsClient = function (base) {
        this.base = base;

        this.baseUrl = this.base.getSimpleApiUrl("achievements");
    };

    OctoPrintAchievementsClient.prototype.get = function (opts) {
        return this.base.get(this.baseUrl, opts);
    };

    // register plugin component
    OctoPrintClient.registerPluginComponent("achievements", OctoPrintAchievementsClient);

    return OctoPrintAchievementsClient;
});
