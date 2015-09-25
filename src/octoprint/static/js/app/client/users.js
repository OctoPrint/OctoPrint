OctoPrint.users = (function($, _) {
    var exports = {};

    var baseUrl = "api/users";

    var url = function() {
        if (arguments.length) {
            return baseUrl + "/" + Array.prototype.join.call(arguments, "/");
        } else {
            return baseUrl;
        }
    };

    exports.list = function(opts) {
        return OctoPrint.get(url(), opts);
    };

    exports.add = function(user, opts) {
        if (!user.name || !user.password) {
            throw new OctoPrint.InvalidArgumentError("Both user's name and password need to be set");
        }

        var data = {
            name: user.name,
            password: user.password,
            active: user.hasOwnProperty("active") ? !!user.active : true,
            admin: user.hasOwnProperty("admin") ? !!user.admin : false
        };

        return OctoPrint.postJson(url(), data, opts);
    };

    exports.get = function(name, opts) {
        return OctoPrint.get(url(name), opts);
    };

    exports.update = function(name, active, admin, opts) {
        var data = {
            active: !!active,
            admin: !!admin
        };
        return OctoPrint.putJson(url(name), data, opts);
    };

    exports.delete = function(name, opts) {
        return OctoPrint.delete(url(name), opts);
    };

    exports.changePassword = function(name, password, opts) {
        var data = {
            password: password
        };
        return OctoPrint.putJson(url(name, "password"), data, opts);
    };

    exports.generateApiKey = function(name, opts) {
        return OctoPrint.postJson(url(name, "apikey"), opts);
    };

    exports.resetApiKey = function(name, opts) {
        return OctoPrint.delete(url(name, "apikey"), opts);
    };

    exports.getSettings = function(name, opts) {
        return OctoPrint.get(url(name, "settings"), opts);
    };

    exports.saveSettings = function(name, settings, opts) {
        settings = settings || {};
        return OctoPrint.patchJson(url(name, "settings"), settings, opts);
    };

    return exports;
})($, _);
