(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient", "jquery"], factory);
    } else {
        factory(global.OctoPrintClient, global.$);
    }
})(this, function(OctoPrintClient, $) {
    var url = "api/connectionprofiles";

    var profileUrl = function(profile) {
        return url + "/" + profile;
    };

    var OctoPrintConnectionProfileClient = function(base) {
        this.base = base;
    };

    OctoPrintConnectionProfileClient.prototype.list = function (opts) {
        return this.base.get(url, opts);
    };

    OctoPrintConnectionProfileClient.prototype.get = function (id, opts) {
        return this.base.get(profileUrl(id), opts);
    };

    OctoPrintConnectionProfileClient.prototype.set = function (id, profile, allowOverwrite, makeDefault, opts) {
        profile = profile || {};

        var data = {profile: profile, overwrite: allowOverwrite, default: makeDefault};

        return this.base.putJson(profileUrl(id), data, opts);
    };

    OctoPrintConnectionProfileClient.prototype.update = function (id, profile, opts) {
        profile = profile || {};

        var data = {profile: profile};

        return this.base.patchJson(profileUrl(id), data, opts);
    };

    OctoPrintConnectionProfileClient.prototype.delete = function (id, opts) {
        return this.base.delete(profileUrl(id), opts);
    };

    OctoPrintClient.registerComponent("connectionprofiles", OctoPrintConnectionProfileClient);
    return OctoPrintConnectionProfileClient;
});
