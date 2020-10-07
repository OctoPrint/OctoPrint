(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function (OctoPrintClient) {
    var OctoPrintBackupClient = function (base) {
        this.base = base;
        this.url = this.base.getBlueprintUrl("backup");
    };

    OctoPrintBackupClient.prototype.get = function (refresh, opts) {
        return this.base.get(this.url, opts);
    };

    OctoPrintBackupClient.prototype.createBackup = function (exclude, opts) {
        exclude = exclude || [];

        var data = {
            exclude: exclude
        };

        return this.base.postJson(this.url + "backup", data, opts);
    };

    OctoPrintBackupClient.prototype.deleteBackup = function (backup, opts) {
        return this.base.delete(this.url + "backup/" + backup, opts);
    };

    OctoPrintBackupClient.prototype.restoreBackup = function (backup, opts) {
        var data = {
            path: backup
        };

        return this.base.postJson(this.url + "restore", data, opts);
    };

    OctoPrintBackupClient.prototype.restoreBackupFromUpload = function (file, data) {
        data = data || {};

        var filename = data.filename || undefined;
        return this.base.upload(this.url + "restore", file, filename, data);
    };

    OctoPrintBackupClient.prototype.deleteUnknownPlugins = function (opts) {
        return this.base.delete(this.url + "unknown_plugins", opts);
    };

    OctoPrintClient.registerPluginComponent("backup", OctoPrintBackupClient);
    return OctoPrintBackupClient;
});
