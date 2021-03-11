(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function (OctoPrintClient) {
    var OctoPrintPluginManagerClient = function (base) {
        this.base = base;
    };

    OctoPrintPluginManagerClient.prototype.get = function (refresh, opts) {
        console.log(
            "Deprecated endpoint OctoPrint.plugin.pluginmanager.get, " +
                "please use OctoPrint.plugin.pluginmanager.get*"
        );
        var refresh_repo, refresh_notices, refresh_orphans;
        if (_.isPlainObject(refresh)) {
            refresh_repo = refresh.repo || false;
            refresh_notices = refresh.notices || false;
            refresh_orphans = refresh.orphans || false;
        } else {
            refresh_repo = refresh;
            refresh_notices = false;
            refresh_orphans = false;
        }

        var query = [];
        if (refresh_repo) query.push("refresh_repository=true");
        if (refresh_notices) query.push("refresh_notices=true");
        if (refresh_orphans) query.push("refresh_orphans=true");

        return this.base.get(
            this.base.getSimpleApiUrl("pluginmanager") +
                (query.length ? "?" + query.join("&") : ""),
            opts
        );
    };

    OctoPrintPluginManagerClient.prototype.getWithRefresh = function (opts) {
        console.log(
            "Deprecated endpoint OctoPrint.plugin.pluginmanager.getWithRefresh, " +
                "please use OctoPrint.plugin.pluginmanager.get*"
        );
        return this.get(true, opts);
    };

    OctoPrintPluginManagerClient.prototype.getWithoutRefresh = function (opts) {
        console.log(
            "Deprecated endpoint OctoPrint.plugin.pluginmanager.getWithoutRefresh, " +
                "please use OctoPrint.plugin.pluginmanager.get*"
        );
        return this.get(false, opts);
    };

    OctoPrintPluginManagerClient.prototype.getPlugins = function (refresh, opts) {
        var url = this.base.getBlueprintUrl("pluginmanager") + "plugins";
        return this.base.get(url + (refresh ? "?refresh=true" : ""), opts);
    };

    OctoPrintPluginManagerClient.prototype.getPlugin = function (plugin, opts) {
        var url = this.base.getBlueprintUrl("pluginmanager") + "plugins/" + plugin;
        return this.base.get(url, opts);
    };

    OctoPrintPluginManagerClient.prototype.getOrphans = function (refresh, opts) {
        var url = this.base.getBlueprintUrl("pluginmanager") + "orphans";
        return this.base.get(url + (refresh ? "?refresh=true" : ""), opts);
    };

    OctoPrintPluginManagerClient.prototype.getRepository = function (refresh, opts) {
        var url = this.base.getBlueprintUrl("pluginmanager") + "repository";
        return this.base.get(url + (refresh ? "?refresh=true" : ""), opts);
    };

    OctoPrintPluginManagerClient.prototype.install = function (
        pluginUrl,
        dependencyLinks,
        opts
    ) {
        var data = {
            url: pluginUrl,
            dependency_links: !!dependencyLinks
        };
        return this.base.simpleApiCommand("pluginmanager", "install", data, opts);
    };

    OctoPrintPluginManagerClient.prototype.reinstall = function (
        plugin,
        pluginUrl,
        dependencyLinks,
        opts
    ) {
        var data = {
            url: pluginUrl,
            dependency_links: !!dependencyLinks,
            reinstall: plugin,
            force: true
        };
        return this.base.simpleApiCommand("pluginmanager", "install", data, opts);
    };

    OctoPrintPluginManagerClient.prototype.uninstall = function (plugin, cleanup, opts) {
        // backwards compatibility to former argument list (plugin, opts)
        if (arguments.length === 2 && typeof cleanup === "object") {
            opts = cleanup;
            cleanup = false;
        }

        var data = {
            plugin: plugin,
            cleanup: !!cleanup
        };
        return this.base.simpleApiCommand("pluginmanager", "uninstall", data, opts);
    };

    OctoPrintPluginManagerClient.prototype.cleanup = function (plugin, opts) {
        var data = {
            plugin: plugin
        };
        return this.base.simpleApiCommand("pluginmanager", "cleanup", data, opts);
    };

    OctoPrintPluginManagerClient.prototype.cleanupAll = function (plugin, opts) {
        var data = {};
        return this.base.simpleApiCommand("pluginmanager", "cleanup_all", data, opts);
    };

    OctoPrintPluginManagerClient.prototype.enable = function (plugin, opts) {
        var data = {
            plugin: plugin
        };
        return this.base.simpleApiCommand("pluginmanager", "enable", data, opts);
    };

    OctoPrintPluginManagerClient.prototype.disable = function (plugin, opts) {
        var data = {
            plugin: plugin
        };
        return this.base.simpleApiCommand("pluginmanager", "disable", data, opts);
    };

    OctoPrintPluginManagerClient.prototype.upload = function (file) {
        return this.base.upload(
            this.base.getBlueprintUrl("pluginmanager") + "upload_archive",
            file
        );
    };

    OctoPrintClient.registerPluginComponent(
        "pluginmanager",
        OctoPrintPluginManagerClient
    );
    return OctoPrintPluginManagerClient;
});
