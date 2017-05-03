(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintAccessClient"], factory);
    } else {
        factory(global.OctoPrintAccessClient);
    }
})(this, function(OctoPrintAccessClient) {
    var baseUrl = "api/permissions";

    var url = function() {
        if (arguments.length) {
            return baseUrl + "/" + Array.prototype.join.call(arguments, "/");
        } else {
            return baseUrl;
        }
    };

    var OctoPrintAccessPermissionsClient = function(access) {
        this.access = access;
        this.base = this.access.base;
    };

    OctoPrintAccessPermissionsClient.prototype.list = function (opts) {
        return this.base.get(url(), opts);
    };

    OctoPrintAccessClient.registerComponent("permissions", OctoPrintAccessPermissionsClient);
    return OctoPrintAccessPermissionsClient;
});
