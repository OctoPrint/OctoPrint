(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient", "OctoPrintAccessClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function(OctoPrintClient) {
    var deprecatedUserClient = function (deprecatedFct, newFct, fn) {
        return OctoPrintClient.deprecated("OctoPrint.users." + deprecatedFct, "OctoPrint.access." + newFct, fn);
    };

    var OctoPrintUserClient = function(base) {
        this.base = base;
    };

    OctoPrintUserClient.prototype.list = deprecatedUserClient("list", "listUsers", function (opts) {
        return this.base.access.listUsers(opts);
    });

    OctoPrintUserClient.prototype.add = deprecatedUserClient("add", "addUser", function (user, opts) {
        return this.base.access.addUser(user, opts);
    });

    OctoPrintUserClient.prototype.get = deprecatedUserClient("get", "getUser", function (name, opts) {
        return this.base.access.getUser(name, opts);
    });

    OctoPrintUserClient.prototype.update = deprecatedUserClient("update", "updateUser", function (name, active, admin, permissions, groups, opts) {
        return this.base.access.updateUser(name, active, admin, permissions, groups, opts);
    });

    OctoPrintUserClient.prototype.delete = deprecatedUserClient("delete", "delete", function (name, opts) {
        return this.base.access.deleteUser(name, opts);
    });

    OctoPrintUserClient.prototype.changePassword = deprecatedUserClient("changePassword", "changePassword", function (name, password, opts) {
        return this.base.access.changeUserPassword(name, password, opts);
    });

    OctoPrintUserClient.prototype.generateApiKey = deprecatedUserClient("generateApiKey", "generateApiKey", function (name, opts) {
        return this.base.access.generateUserApiKey(name, opts);
    });

    OctoPrintUserClient.prototype.resetApiKey = deprecatedUserClient("resetApiKey", "resetApiKey", function (name, opts) {
        return this.base.access.resetUserApiKey(name, opts);
    });

    OctoPrintUserClient.prototype.getSettings = deprecatedUserClient("getSettings", "getSettings", function (name, opts) {
        return this.base.access.getUserSettings(name, opts);
    });

    OctoPrintUserClient.prototype.saveSettings = deprecatedUserClient("saveSettings", "saveSettings", function (name, settings, opts) {
        return this.base.access.saveUserSettings(name, settings, opts);
    });

    OctoPrintClient.registerComponent("users", OctoPrintUserClient);
    return OctoPrintUserClient;
});
