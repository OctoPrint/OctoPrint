(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function (OctoPrintClient) {
    var OctoPrintSoftwareUpdateClient = function (base) {
        this.base = base;

        var url = this.base.getBlueprintUrl("softwareupdate");
        this.checkUrl = url + "check";
        this.updateUrl = url + "update";
        this.configureUrl = url + "configure";
        this.updatelogUrl = url + "updatelog";
        this.queuedURL = this.updateUrl + "/queued";
    };

    OctoPrintSoftwareUpdateClient.prototype.checkEntries = function (
        entries,
        force,
        opts
    ) {
        if (arguments.length == 1 && _.isObject(arguments[0])) {
            var params = arguments[0];
            entries = params.entries;
            force = params.force;
            opts = params.opts;
        }

        entries = entries || [];
        if (typeof entries == "string") {
            entries = [entries];
        }

        var data = {};
        if (!!force) {
            data.force = true;
        }
        if (entries && entries.length) {
            data.targets = entries.join(",");
        }
        return this.base.getWithQuery(this.checkUrl, data, opts);
    };

    OctoPrintSoftwareUpdateClient.prototype.check = function (force, opts) {
        if (arguments.length === 1 && _.isObject(arguments[0])) {
            var params = arguments[0];
            force = params.force;
            opts = params.opts;
        }

        return this.checkEntries({entries: [], force: force, opts: opts});
    };

    OctoPrintSoftwareUpdateClient.prototype.update = function (targets, force, opts) {
        if (arguments.length === 1 && _.isObject(arguments[0])) {
            var params = arguments[0];
            targets = params.targets;
            force = params.force;
            opts = params.opts;
        }

        targets = targets || [];
        if (typeof targets === "string") {
            targets = [targets];
        }

        var data = {
            targets: targets,
            force: !!force
        };
        return this.base.postJson(this.updateUrl, data, opts);
    };

    OctoPrintSoftwareUpdateClient.prototype.cancelQueued = function (targets, opts) {
        if (arguments.length === 1 && _.isObject(arguments[0])) {
            var params = arguments[0];
            targets = params.targets;
        }

        targets = targets || [];
        if (typeof targets === "string") {
            targets = [targets];
        }

        var data = {
            command: "cancel",
            targets: targets
        };
        return this.base.postJson(this.queuedURL, data, opts);
    };

    OctoPrintSoftwareUpdateClient.prototype.cancelAllQueued = function (opts) {
        if (arguments.length === 1 && _.isObject(arguments[0])) {
            var params = arguments[0];
            opts = params.opts;
        }

        var data = {
            command: "cancel"
        };

        return this.base.postJson(this.queuedURL, data, opts);
    };

    OctoPrintSoftwareUpdateClient.prototype.updateAll = function (force, opts) {
        if (arguments.length === 1 && _.isObject(arguments[0])) {
            var params = arguments[0];
            force = params.force;
            opts = params.opts;
        }

        var data = {
            force: !!force
        };
        return this.base.postJson(this.updateUrl, data, opts);
    };

    OctoPrintSoftwareUpdateClient.prototype.configure = function (data, opts) {
        return this.base.postJson(this.configureUrl, data, opts);
    };

    OctoPrintSoftwareUpdateClient.prototype.getUpdatelog = function (opts) {
        return this.base.get(this.updatelogUrl, opts);
    };

    OctoPrintClient.registerPluginComponent(
        "softwareupdate",
        OctoPrintSoftwareUpdateClient
    );
    return OctoPrintSoftwareUpdateClient;
});
