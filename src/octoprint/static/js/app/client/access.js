(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define("OctoPrintAccessClient", ["OctoPrintClient"], factory);
    } else {
        global.OctoPrintAccessClient = factory(global.OctoPrintClient);
    }
})(this, function (OctoPrintClient) {
    var baseAccessUrl = "api/access";

    //~~ permissions client api

    var OctoPrintAccessPermissionsClient = function (access) {
        this.access = access;
        this.base = this.access.base;

        var baseUrl = baseAccessUrl + "/permissions";
        this.url = function () {
            if (arguments.length) {
                return baseUrl + "/" + Array.prototype.join.call(arguments, "/");
            } else {
                return baseUrl;
            }
        };
    };

    OctoPrintAccessPermissionsClient.prototype.list = function (opts) {
        return this.base.get(this.url(), opts);
    };

    //~~ groups client api

    var OctoPrintAccessGroupsClient = function (access) {
        this.access = access;
        this.base = this.access.base;

        var baseUrl = baseAccessUrl + "/groups";
        this.url = function () {
            if (arguments.length) {
                return baseUrl + "/" + Array.prototype.join.call(arguments, "/");
            } else {
                return baseUrl;
            }
        };
    };

    OctoPrintAccessGroupsClient.prototype.list = function (opts) {
        return this.base.get(this.url(), opts);
    };

    OctoPrintAccessGroupsClient.prototype.add = function (group, opts) {
        if (!group.key) {
            throw new OctoPrintClient.InvalidArgumentError("group key must be set");
        }
        if (!group.name) {
            throw new OctoPrintClient.InvalidArgumentError("group name must be set");
        }

        var data = {
            key: group.key,
            name: group.name,
            description: group.description,
            permissions: group.permissions,
            subgroups: group.subgroups,
            default: group.default
        };

        return this.base.postJson(this.url(), data, opts);
    };

    OctoPrintAccessGroupsClient.prototype.get = function (key, opts) {
        if (!key) {
            throw new OctoPrintClient.InvalidArgumentError("group key must be set");
        }

        return this.base.get(this.url(key), opts);
    };

    OctoPrintAccessGroupsClient.prototype.update = function (group, opts) {
        if (!group.key) {
            throw new OctoPrintClient.InvalidArgumentError("group key must be set");
        }

        var data = {
            description: group.hasOwnProperty("description") ? group.description : "",
            permissions: group.permissions,
            subgroups: group.subgroups,
            default: group.default
        };
        return this.base.putJson(this.url(group.key), data, opts);
    };

    OctoPrintAccessGroupsClient.prototype.delete = function (key, opts) {
        if (!key) {
            throw new OctoPrintClient.InvalidArgumentError("group key must be set");
        }

        return this.base.delete(this.url(key), opts);
    };

    //~~ users client api

    var OctoPrintAccessUsersClient = function (access) {
        this.access = access;
        this.base = this.access.base;

        var baseUrl = baseAccessUrl + "/users";
        this.url = function () {
            if (arguments.length) {
                return baseUrl + "/" + Array.prototype.join.call(arguments, "/");
            } else {
                return baseUrl;
            }
        };
    };

    OctoPrintAccessUsersClient.prototype.list = function (opts) {
        return this.base.get(this.url(), opts);
    };

    OctoPrintAccessUsersClient.prototype.add = function (user, opts) {
        if (!user.name || !user.password) {
            throw new OctoPrintClient.InvalidArgumentError(
                "Both user's name and password need to be set"
            );
        }

        var data = {
            name: user.name,
            password: user.password,
            groups: user.hasOwnProperty("groups") ? user.groups : [],
            permissions: user.hasOwnProperty("permissions") ? user.permissions : [],
            active: user.hasOwnProperty("active") ? !!user.active : true,
            admin: user.hasOwnProperty("admin") ? !!user.admin : false
        };

        return this.base.postJson(this.url(), data, opts);
    };

    OctoPrintAccessUsersClient.prototype.get = function (name, opts) {
        if (!name) {
            throw new OctoPrintClient.InvalidArgumentError("user name must be set");
        }

        return this.base.get(this.url(name), opts);
    };

    OctoPrintAccessUsersClient.prototype.update = function (
        name,
        active,
        admin,
        permissions,
        groups,
        opts
    ) {
        if (!name) {
            throw new OctoPrintClient.InvalidArgumentError("user name must be set");
        }

        var data = {
            active: !!active,
            groups: groups,
            permissions: permissions,
            admin: !!admin
        };
        return this.base.putJson(this.url(name), data, opts);
    };

    OctoPrintAccessUsersClient.prototype.delete = function (name, opts) {
        if (!name) {
            throw new OctoPrintClient.InvalidArgumentError("user name must be set");
        }

        return this.base.delete(this.url(name), opts);
    };

    OctoPrintAccessUsersClient.prototype.changePassword = function (
        name,
        password,
        oldpw,
        opts
    ) {
        if (_.isObject(oldpw)) {
            opts = oldpw;
            oldpw = undefined;
        }

        if (!name || !password) {
            throw new OctoPrintClient.InvalidArgumentError(
                "user name and new password must be set"
            );
        }

        var data = {
            password: password
        };
        if (oldpw) {
            data["current"] = oldpw;
        }
        return this.base.putJson(this.url(name, "password"), data, opts);
    };

    OctoPrintAccessUsersClient.prototype.generateApiKey = function (name, opts) {
        if (!name) {
            throw new OctoPrintClient.InvalidArgumentError("user name must be set");
        }

        return this.base.postJson(this.url(name, "apikey"), opts);
    };

    OctoPrintAccessUsersClient.prototype.resetApiKey = function (name, opts) {
        if (!name) {
            throw new OctoPrintClient.InvalidArgumentError("user name must be set");
        }

        return this.base.delete(this.url(name, "apikey"), opts);
    };

    OctoPrintAccessUsersClient.prototype.getSettings = function (name, opts) {
        if (!name) {
            throw new OctoPrintClient.InvalidArgumentError("user name must be set");
        }

        return this.base.get(this.url(name, "settings"), opts);
    };

    OctoPrintAccessUsersClient.prototype.saveSettings = function (name, settings, opts) {
        if (!name) {
            throw new OctoPrintClient.InvalidArgumentError("user name must be set");
        }

        settings = settings || {};
        return this.base.patchJson(this.url(name, "settings"), settings, opts);
    };

    var OctoPrintAccessClient = function (base) {
        this.base = base;

        this.permissions = new OctoPrintAccessPermissionsClient(this);
        this.groups = new OctoPrintAccessGroupsClient(this);
        this.users = new OctoPrintAccessUsersClient(this);
    };
    OctoPrintClient.registerComponent("access", OctoPrintAccessClient);
    return OctoPrintAccessClient;
});
