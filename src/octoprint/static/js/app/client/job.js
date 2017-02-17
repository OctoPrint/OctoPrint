(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function(OctoPrintClient) {
    var url = "api/job";

    var OctoPrintJobClient = function(base) {
        this.base = base;
    };

    OctoPrintJobClient.prototype.issueCommand = function(command, payload, opts) {
        if (arguments.length == 2) {
            opts = payload;
            payload = {};
        }

        return this.base.issueCommand(url, command, payload, opts);
    };

    OctoPrintJobClient.prototype.get = function(opts) {
        return OctoPrint.get(url, opts);
    };

    OctoPrintJobClient.prototype.start = function(opts) {
        return this.issueCommand("start", opts);
    };

    OctoPrintJobClient.prototype.restart = function(opts) {
        return this.issueCommand("restart", opts);
    };

    OctoPrintJobClient.prototype.pause = function(opts) {
        return this.issueCommand("pause", {"action": "pause"}, opts);
    };

    OctoPrintJobClient.prototype.resume = function(opts) {
        return this.issueCommand("pause", {"action": "resume"}, opts)
    };

    OctoPrintJobClient.prototype.togglePause = function(opts) {
        return this.issueCommand("pause", {"action": "toggle"}, opts);
    };

    OctoPrintJobClient.prototype.cancel = function(opts) {
        return this.issueCommand("cancel", opts);
    };

    OctoPrintClient.registerComponent("job", OctoPrintJobClient);
    return OctoPrintJobClient;
});
