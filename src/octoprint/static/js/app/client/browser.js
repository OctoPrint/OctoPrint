(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrint"], factory);
    } else {
        factory(window.OctoPrint);
    }
})(window || this, function(OctoPrint) {
    var loginUrl = "api/login";
    var logoutUrl = "api/logout";

    OctoPrint.browser = {
        login: function(username, password, remember, opts) {
            var data = {
                user: username,
                pass: password,
                remember: !!remember
            };
            return OctoPrint.postJson(loginUrl, data, opts);
        },

        passiveLogin: function(opts) {
            return OctoPrint.postJson(loginUrl, {passive: true}, opts);
        },

        logout: function(opts) {
            return OctoPrint.postJson(logoutUrl, {}, opts);
        }
    };
});
