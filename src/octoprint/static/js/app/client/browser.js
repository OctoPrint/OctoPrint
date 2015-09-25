OctoPrint.browser = (function($, _) {
    var exports = {};

    exports.login = function(username, password, remember, opts) {
        var data = {
            user: username,
            pass: password,
            remember: !!remember
        };
        return OctoPrint.postJson("api/login", data, opts);
    };

    exports.passiveLogin = function(opts) {
        return OctoPrint.postJson("api/login", {passive: true}, opts);
    };

    exports.logout = function(opts) {
        return OctoPrint.postJson("api/logout", {}, opts);
    };

    return exports;
})($, _);
