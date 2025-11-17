(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function (OctoPrintClient) {
    var url = "api/job";

    var OctoPrintJobClient = function (base) {
        this.base = base;
    };

    OctoPrintJobClient.prototype.issueCommand = function (command, payload, opts) {
        if (arguments.length == 2) {
            opts = payload;
            payload = {};
        }

        return this.base.issueCommand(url, command, payload, opts);
    };

    OctoPrintJobClient.prototype.get = function (opts) {
        return OctoPrint.get(url, opts);
    };

    OctoPrintJobClient.prototype.start = function (parameters, opts) {
        parameters = _.isPlainObject(parameters) ? parameters : {};
        return this.issueCommand("start", parameters, opts);
    };

    OctoPrintJobClient.prototype.restart = function (parameters, opts) {
        parameters = _.isPlainObject(parameters) ? parameters : {};
        return this.issueCommand("restart", parameters, opts);
    };

    OctoPrintJobClient.prototype.pause = function (parameters, opts) {
        parameters = _.isPlainObject(parameters) ? parameters : {};
        return this.issueCommand("pause", {...parameters, action: "pause"}, opts);
    };

    OctoPrintJobClient.prototype.resume = function (parameters, opts) {
        parameters = _.isPlainObject(parameters) ? parameters : {};
        return this.issueCommand("pause", {...parameters, action: "resume"}, opts);
    };

    OctoPrintJobClient.prototype.togglePause = function (parameters, opts) {
        parameters = _.isPlainObject(parameters) ? parameters : {};
        return this.issueCommand("pause", {...parameters, action: "toggle"}, opts);
    };

    OctoPrintJobClient.prototype.cancel = function (parameters, opts) {
        parameters = _.isPlainObject(parameters) ? parameters : {};
        return this.issueCommand("cancel", parameters, opts);
    };

    OctoPrintClient.registerComponent("job", OctoPrintJobClient);
    return OctoPrintJobClient;
});
