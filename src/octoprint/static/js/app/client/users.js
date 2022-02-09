(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient", "OctoPrintAccessClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function (OctoPrintClient) {
    var deprecatedUserClient = function (deprecatedFct, newFct, fn) {
        return OctoPrintClient.deprecated(
            "OctoPrint.users." + deprecatedFct,
            "OctoPrint.access.users." + newFct,
            fn
        );
    };

    var OctoPrintUserClient = function (base) {
        this.base = base;
    };

    OctoPrintUserClient.prototype.list = deprecatedUserClient(
        "list",
        "list",
        function (opts) {
            return this.base.access.users.list(opts);
        }
    );

    OctoPrintUserClient.prototype.add = deprecatedUserClient(
        "add",
        "add",
        function (user, opts) {
            return this.base.access.users.add(user, opts);
        }
    );

    OctoPrintUserClient.prototype.get = deprecatedUserClient(
        "get",
        "get",
        function (name, opts) {
            return this.base.access.users.get(name, opts);
        }
    );

    OctoPrintUserClient.prototype.update = deprecatedUserClient(
        "update",
        "update",
        function (name, active, admin, permissions, groups, opts) {
            return this.base.access.users.update(
                name,
                active,
                admin,
                permissions,
                groups,
                opts
            );
        }
    );

    OctoPrintUserClient.prototype.delete = deprecatedUserClient(
        "delete",
        "delete",
        function (name, opts) {
            return this.base.access.users.delete(name, opts);
        }
    );

    OctoPrintUserClient.prototype.changePassword = deprecatedUserClient(
        "changePassword",
        "changePassword",
        function (name, password, opts) {
            return this.base.access.users.changePassword(name, password, opts);
        }
    );

    OctoPrintUserClient.prototype.generateApiKey = deprecatedUserClient(
        "generateApiKey",
        "generateApiKey",
        function (name, opts) {
            return this.base.access.users.generateApiKey(name, opts);
        }
    );

    OctoPrintUserClient.prototype.resetApiKey = deprecatedUserClient(
        "resetApiKey",
        "resetApiKey",
        function (name, opts) {
            return this.base.access.users.resetApiKey(name, opts);
        }
    );

    OctoPrintUserClient.prototype.getSettings = deprecatedUserClient(
        "getSettings",
        "getSettings",
        function (name, opts) {
            return this.base.access.users.getSettings(name, opts);
        }
    );

    OctoPrintUserClient.prototype.saveSettings = deprecatedUserClient(
        "saveSettings",
        "saveSettings",
        function (name, settings, opts) {
            return this.base.access.users.saveSettings(name, settings, opts);
        }
    );

    OctoPrintClient.registerComponent("users", OctoPrintUserClient);
    return OctoPrintUserClient;
});
