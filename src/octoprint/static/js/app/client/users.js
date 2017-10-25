(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function(OctoPrintClient) {
    var baseUrl = "api/users";

    var url = function() {
        if (arguments.length) {
            return baseUrl + "/" + Array.prototype.join.call(arguments, "/");
        } else {
            return baseUrl;
        }
    };

    var OctoPrintUserClient = function(base) {
        this.base = base;
    };

    OctoPrintUserClient.prototype.list = function (opts) {
        return this.base.get(url(), opts);
    };

    OctoPrintUserClient.prototype.add = function (user, opts) {
        if (!user.name || !user.password) {
            throw new OctoPrintClient.InvalidArgumentError("Both user's name and password need to be set");
        }

        var data = {
            name: user.name,
            password: user.password,
            active: user.hasOwnProperty("active") ? !!user.active : true,
            admin: user.hasOwnProperty("admin") ? !!user.admin : false
        };

        return this.base.postJson(url(), data, opts);
    };

    OctoPrintUserClient.prototype.get = function (name, opts) {
        if (!name) {
            throw new OctoPrintClient.InvalidArgumentError("user name must be set");
        }

        return this.base.get(url(name), opts);
    };

    OctoPrintUserClient.prototype.update = function (name, active, admin, opts) {
        if (!name) {
            throw new OctoPrintClient.InvalidArgumentError("user name must be set");
        }

        var data = {
            active: !!active,
            admin: !!admin
        };
        return this.base.putJson(url(name), data, opts);
    };

    OctoPrintUserClient.prototype.delete = function (name, opts) {
        if (!name) {
            throw new OctoPrintClient.InvalidArgumentError("user name must be set");
        }

        return this.base.delete(url(name), opts);
    };

    OctoPrintUserClient.prototype.changePassword = function (name, password, opts) {
        if (!name || !password) {
            throw new OctoPrintClient.InvalidArgumentError("user name and password must be set");
        }

        var data = {
            password: password
        };
        return this.base.putJson(url(name, "password"), data, opts);
    };

    OctoPrintUserClient.prototype.generateApiKey = function (name, opts) {
        if (!name) {
            throw new OctoPrintClient.InvalidArgumentError("user name must be set");
        }

        return this.base.postJson(url(name, "apikey"), opts);
    };

    OctoPrintUserClient.prototype.resetApiKey = function (name, opts) {
        if (!name) {
            throw new OctoPrintClient.InvalidArgumentError("user name must be set");
        }

        return this.base.delete(url(name, "apikey"), opts);
    };

    OctoPrintUserClient.prototype.getSettings = function (name, opts) {
        if (!name) {
            throw new OctoPrintClient.InvalidArgumentError("user name must be set");
        }

        return this.base.get(url(name, "settings"), opts);
    };

    OctoPrintUserClient.prototype.saveSettings = function (name, settings, opts) {
        if (!name) {
            throw new OctoPrintClient.InvalidArgumentError("user name must be set");
        }

        settings = settings || {};
        return this.base.patchJson(url(name, "settings"), settings, opts);
    };

    OctoPrintClient.registerComponent("users", OctoPrintUserClient);
    return OctoPrintUserClient;
});
