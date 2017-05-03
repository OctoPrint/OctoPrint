(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintAccessClient"], factory);
    } else {
        factory(global.OctoPrintAccessClient);
    }
})(this, function(OctoPrintAccessClient) {
    var baseUrl = "api/users";

    var url = function() {
        if (arguments.length) {
            return baseUrl + "/" + Array.prototype.join.call(arguments, "/");
        } else {
            return baseUrl;
        }
    };

    var OctoPrintAccessUsersClient = function(access) {
        this.access = access;
        this.base = this.access.base;
    };

    OctoPrintAccessUsersClient.prototype.list = function (opts) {
        return this.base.get(url(), opts);
    };

    OctoPrintAccessUsersClient.prototype.add = function (user, opts) {
        if (!user.name || !user.password) {
            throw new OctoPrintClient.InvalidArgumentError("Both user's name and password need to be set");
        }

            var data = {
                name: user.name,
                password: user.password,
                groups: user.hasOwnProperty("groups") ? user.groups : [],
                permissions: user.hasOwnProperty("permissions") ? user.permissions : [],
                active: user.hasOwnProperty("active") ? !!user.active : true,
                admin: user.hasOwnProperty("admin") ? !!user.admin : false
            };

        return this.base.postJson(url(), data, opts);
    };

    OctoPrintAccessUsersClient.prototype.get = function (name, opts) {
        if (!name) {
            throw new OctoPrintClient.InvalidArgumentError("user name must be set");
        }

        return this.base.get(url(name), opts);
    };

    OctoPrintAccessUsersClient.prototype.update = function (name, active, admin, permissions, groups, opts) {
        if (!name) {
            throw new OctoPrintClient.InvalidArgumentError("user name must be set");
        }

        var data = {
            active: !!active,
            groups: groups,
            permissions: permissions,
            admin: !!admin
        };
        return this.base.putJson(url(name), data, opts);
    };

    OctoPrintAccessUsersClient.prototype.delete = function (name, opts) {
        if (!name) {
            throw new OctoPrintClient.InvalidArgumentError("user name must be set");
        }

        return this.base.delete(url(name), opts);
    };

    OctoPrintAccessUsersClient.prototype.changePassword = function (name, password, opts) {
        if (!name || !password) {
            throw new OctoPrintClient.InvalidArgumentError("user name and password must be set");
        }

        var data = {
            password: password
        };
        return this.base.putJson(url(name, "password"), data, opts);
    };

    OctoPrintAccessUsersClient.prototype.generateApiKey = function (name, opts) {
        if (!name) {
            throw new OctoPrintClient.InvalidArgumentError("user name must be set");
        }

        return this.base.postJson(url(name, "apikey"), opts);
    };

    OctoPrintAccessUsersClient.prototype.resetApiKey = function (name, opts) {
        if (!name) {
            throw new OctoPrintClient.InvalidArgumentError("user name must be set");
        }

        return this.base.delete(url(name, "apikey"), opts);
    };

    OctoPrintAccessUsersClient.prototype.getSettings = function (name, opts) {
        if (!name) {
            throw new OctoPrintClient.InvalidArgumentError("user name must be set");
        }

        return this.base.get(url(name, "settings"), opts);
    };

    OctoPrintAccessUsersClient.prototype.saveSettings = function (name, settings, opts) {
        if (!name) {
            throw new OctoPrintClient.InvalidArgumentError("user name must be set");
        }

        settings = settings || {};
        return this.base.patchJson(url(name, "settings"), settings, opts);
    };

    OctoPrintAccessClient.registerComponent("users", OctoPrintAccessUsersClient);
    return OctoPrintAccessUsersClient;
});
