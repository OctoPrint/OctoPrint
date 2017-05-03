(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintAccessClient"], factory);
    } else {
        factory(global.OctoPrintAccessClient);
    }
})(this, function(OctoPrintAccessClient) {
    var baseUrl = "api/groups";

    var url = function() {
        if (arguments.length) {
            return baseUrl + "/" + Array.prototype.join.call(arguments, "/");
        } else {
            return baseUrl;
        }
    };

    var OctoPrintAccessGroupsClient = function(access) {
        this.access = access;
        this.base = this.access.base;
    };

    OctoPrintAccessGroupsClient.prototype.list = function (opts) {
        return this.base.get(url(), opts);
    };

    OctoPrintAccessGroupsClient.prototype.add = function (group, opts) {
        if (!group.name) {
            throw new OctoPrintClient.InvalidArgumentError("group's name need to be set");
        }

        var data = {
            name: group.name,
            permissions: group.hasOwnProperty("permissions") ? group.permissions : [],
            defaultOn: group.defaultOn
        };

        return this.base.postJson(url(), data, opts);
    };

    OctoPrintAccessGroupsClient.prototype.get = function (name, opts) {
        if (!name) {
            throw new OctoPrintClient.InvalidArgumentError("group name must be set");
        }

        return this.base.get(url(name), opts);
    };

    OctoPrintAccessGroupsClient.prototype.update = function (name, description, permissions, defaultOn, opts) {
        if (!name) {
            throw new OctoPrintClient.InvalidArgumentError("group name must be set");
        }

        var data = {
            description: description,
            permissions: permissions,
            defaultOn: defaultOn,
        };
        return this.base.putJson(url(name), data, opts);
    };

    OctoPrintAccessGroupsClient.prototype.delete = function (name, opts) {
        if (!name) {
            throw new OctoPrintClient.InvalidArgumentError("group name must be set");
        }

        return this.base.delete(url(name), opts);
    };

    OctoPrintAccessClient.registerComponent("groups", OctoPrintAccessGroupsClient);
    return OctoPrintAccessGroupsClient;
});
