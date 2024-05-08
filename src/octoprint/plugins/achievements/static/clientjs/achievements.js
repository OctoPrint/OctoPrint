(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function (OctoPrintClient) {
    var OctoPrintAchievementsClient = function (base) {
        this.base = base;

        this.baseUrl = this.base.getBlueprintUrl("achievements");
    };

    OctoPrintAchievementsClient.prototype.get = function (opts) {
        return this.base.get(this.baseUrl, opts);
    };

    OctoPrintAchievementsClient.prototype.getYear = function (year, opts) {
        return this.base.get(this.baseUrl + "/year/" + year, opts);
    };

    OctoPrintAchievementsClient.prototype.resetAchievements = function (
        achievements,
        opts
    ) {
        return this.base.postJson(
            this.baseUrl + "/reset/achievements",
            {achievements: achievements},
            opts
        );
    };

    // register plugin component
    OctoPrintClient.registerPluginComponent("achievements", OctoPrintAchievementsClient);

    return OctoPrintAchievementsClient;
});
