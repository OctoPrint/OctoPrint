(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function(OctoPrintClient) {
    var url = "api/logs";

    var OctoPrintLogsClient = function(base) {
        this.base = base;
    };

    OctoPrintLogsClient.prototype.list = function(opts) {
        return this.base.get(url, opts);
    };

    OctoPrintLogsClient.prototype.delete = function(file, opts) {
        var fileUrl = url + "/" + file;
        return this.base.delete(fileUrl, opts);
    };

    OctoPrintLogsClient.prototype.download = function(file, opts) {
        var fileUrl = url + "/" + file;
        return this.base.download(fileUrl, opts);
    };

    OctoPrintClient.registerComponent("logs", OctoPrintLogsClient);
    return OctoPrintLogsClient;
});
