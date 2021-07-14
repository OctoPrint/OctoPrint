(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function (OctoPrintClient) {
    var url = "api/connection";
    var optionsUrl = url + "/options";
    var protocolsUrl = url + "/protocols";
    var transportsUrl = url + "/transports";

    var OctoPrintConnectionClient = function (base) {
        this.base = base;
    };

    OctoPrintConnectionClient.prototype.getSettings = function (opts) {
        return this.base.get(url, opts);
    };

    OctoPrintConnectionClient.prototype.connect = function (data, opts) {
        return this.base.issueCommand(url, "connect", data || {}, opts);
    };

    OctoPrintConnectionClient.prototype.disconnect = function (opts) {
        return this.base.issueCommand(url, "disconnect", {}, opts);
    };

    OctoPrintConnectionClient.prototype.fakeAck = function (opts) {
        return this.base.issueCommand(url, "fake_ack", {}, opts);
    };

    OctoPrintConnectionClient.prototype.getOptions = function (opts) {
        return this.base.get(optionsUrl, opts);
    };

    OctoPrintConnectionClient.prototype.getProtocols = function (opts) {
        return this.base.get(protocolsUrl, opts);
    };

    OctoPrintConnectionClient.prototype.getTransports = function (opts) {
        return this.base.get(transportsUrl, opts);
    };

    OctoPrintClient.registerComponent("connection", OctoPrintConnectionClient);
    return OctoPrintConnectionClient;
});
