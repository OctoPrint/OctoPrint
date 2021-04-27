(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function (OctoPrintClient) {
    var OctoPrintLoggingClient = function (base) {
        this.base = base;

        this.baseUrl = this.base.getBlueprintUrl("logging");
        this.logsUrl = this.baseUrl + "logs";
        this.setupUrl = this.baseUrl + "setup";
    };

    var bulkDownloadUrl = "downloads/logs";

    OctoPrintLoggingClient.prototype.get = function (opts) {
        return this.base.get(this.baseUrl, opts);
    };

    OctoPrintLoggingClient.prototype.listLogs = function (opts) {
        return this.base.get(this.logsUrl, opts);
    };

    OctoPrintLoggingClient.prototype.deleteLog = function (file, opts) {
        var fileUrl = this.logsUrl + "/" + file;
        return this.base.delete(fileUrl, opts);
    };

    OctoPrintLoggingClient.prototype.downloadLog = function (file, opts) {
        var fileUrl = this.logsUrl + "/" + file;
        return this.base.download(fileUrl, opts);
    };

    OctoPrintLoggingClient.prototype.bulkDownloadUrl = function (filenames) {
        return this.base.bulkDownloadUrl(bulkDownloadUrl, filenames);
    };

    OctoPrintLoggingClient.prototype.updateLevels = function (config, opts) {
        return this.base.putJson(this.setupUrl + "/levels", config, opts);
    };

    //~~ wrapper for backwards compatibility

    var DeprecatedOctoPrintLogsClient = function (base) {
        this.base = base;
        this.wrapped = this.base.plugins.logging;
    };

    DeprecatedOctoPrintLogsClient.prototype.list = function (opts) {
        log.warn(
            "OctoPrintClient.logs.list has been deprecated as of OctoPrint 1.3.7, use OctoPrintClient.plugins.logging.listLogs instead"
        );
        return this.wrapped.listLogs(opts);
    };

    DeprecatedOctoPrintLogsClient.prototype.delete = function (file, opts) {
        log.warn(
            "OctoPrintClient.logs.delete has been deprecated as of OctoPrint 1.3.7, use OctoPrintClient.plugins.logging.deleteLog instead"
        );
        return this.wrapped.deleteLog(file, opts);
    };

    DeprecatedOctoPrintLogsClient.prototype.download = function (file, opts) {
        log.warn(
            "OctoPrintClient.logs.download has been deprecated as of OctoPrint 1.3.7, use OctoPrintClient.plugins.logging.downloadLog instead"
        );
        return this.wrapped.downloadLog(file, opts);
    };

    // register plugin component
    OctoPrintClient.registerPluginComponent("logging", OctoPrintLoggingClient);

    // also register deprecated client under old endpoint
    OctoPrintClient.registerComponent("logs", DeprecatedOctoPrintLogsClient);

    return OctoPrintLoggingClient;
});
