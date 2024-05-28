(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function (OctoPrintClient) {
    var OctoPrintMfaTotpClient = function (base) {
        this.base = base;
    };

    OctoPrintMfaTotpClient.prototype.get = (options) => {
        return this.base.simpleApiGet("mfa_totp", options);
    };

    OctoPrintMfaTotpClient.prototype.enroll = (options) => {
        return this.base.simpleApiCommand("mfa_totp", "enroll", {}, options);
    };

    OctoPrintMfaTotpClient.prototype.activate = (token, options) => {
        return this.base.simpleApiCommand("mfa_totp", "activate", {token}, options);
    };

    OctoPrintMfaTotpClient.prototype.deactivate = (token, options) => {
        return this.base.simpleApiCommand("mfa_totp", "deactivate", {token}, options);
    };

    OctoPrintClient.registerPluginComponent("mfa_totp", OctoPrintMfaTotpClient);
    return OctoPrintMfaTotpClient;
});
