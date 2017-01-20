(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function(OctoPrintClient) {
    var url = "api/system";
    var commandUrl = "api/system/commands";

    var OctoPrintSystemClient = function(base) {
        this.base = base;
    };

    OctoPrintSystemClient.prototype.getCommands = function (opts) {
        return this.base.get(commandUrl, opts);
    };

    OctoPrintSystemClient.prototype.getCommandsForSource = function (source, opts) {
        return this.base.get(commandUrl + "/" + source, opts);
    };

    OctoPrintSystemClient.prototype.executeCommand = function (source, action, opts) {
        return this.base.postJson(commandUrl + "/" + source + "/" + action, {}, opts);
    };

    OctoPrintClient.registerComponent("system", OctoPrintSystemClient);
    return OctoPrintSystemClient;
});
