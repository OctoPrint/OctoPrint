(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function (OctoPrintClient) {
    const OctoPrintMfaTotpClient = function (base) {
        this.base = base;
    };

    OctoPrintMfaTotpClient.prototype.getStatus = function (options) {
        return this.base.simpleApiGet("mfa_totp", options);
    };

    OctoPrintMfaTotpClient.prototype.enroll = function (options) {
        return this.base.simpleApiCommand("mfa_totp", "enroll", {}, options);
    };

    OctoPrintMfaTotpClient.prototype.activate = function (token, options) {
        return this.base.simpleApiCommand("mfa_totp", "activate", {token}, options);
    };

    OctoPrintMfaTotpClient.prototype.deactivate = function (token, options) {
        return this.base.simpleApiCommand("mfa_totp", "deactivate", {token}, options);
    };

    OctoPrintClient.registerPluginComponent("mfa_totp", OctoPrintMfaTotpClient);
    return OctoPrintMfaTotpClient;
});
