(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function(OctoPrintClient) {
    var loginUrl = "api/login";
    var logoutUrl = "api/logout";

    var OctoPrintBrowserClient = function(base) {
        this.base = base;
    };

    OctoPrintBrowserClient.prototype.login = function(username, password, remember, opts) {
        var data = {
            user: username,
            pass: password,
            remember: !!remember
        };
        return this.base.postJson(loginUrl, data, opts);
    };

    OctoPrintBrowserClient.prototype.passiveLogin = function(opts) {
        return this.base.postJson(loginUrl, {passive: true}, opts);
    };

    OctoPrintBrowserClient.prototype.logout = function(opts) {
        return this.base.postJson(logoutUrl, {}, opts);
    };

    OctoPrintClient.registerComponent("browser", OctoPrintBrowserClient);
    return OctoPrintBrowserClient;
});
