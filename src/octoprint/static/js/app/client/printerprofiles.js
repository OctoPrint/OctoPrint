(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient", "jquery"], factory);
    } else {
        factory(global.OctoPrintClient, global.$);
    }
})(this, function(OctoPrintClient, $) {
    var url = "api/printerprofiles";

    var profileUrl = function(profile) {
        return url + "/" + profile;
    };

    var OctoPrintPrinterProfileClient = function(base) {
        this.base = base;
    };

    OctoPrintPrinterProfileClient.prototype.list = function (opts) {
        return this.base.get(url, opts);
    };

    OctoPrintPrinterProfileClient.prototype.add = function (profile, basedOn, opts) {
        profile = profile || {};

        var data = {profile: profile};
        if (basedOn) {
            data.basedOn = basedOn;
        }

        return this.base.postJson(url, data, opts);
    };

    OctoPrintPrinterProfileClient.prototype.get = function (id, opts) {
        return this.base.get(profileUrl(id), opts);
    };

   OctoPrintPrinterProfileClient.prototype. update = function (id, profile, opts) {
        profile = profile || {};

        var data = {profile: profile};

        return this.base.patchJson(profileUrl(id), data, opts);
    };

    OctoPrintPrinterProfileClient.prototype.delete = function (id, opts) {
        return this.base.delete(profileUrl(id), opts);
    };

    OctoPrintClient.registerComponent("printerprofiles", OctoPrintPrinterProfileClient);
    return OctoPrintPrinterProfileClient;
});
