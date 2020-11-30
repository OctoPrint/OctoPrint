(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function (OctoPrintClient) {
    var OctoPrintActionCommandPromptClient = function (base) {
        this.base = base;
    };

    OctoPrintActionCommandPromptClient.prototype.get = function (refresh, opts) {
        return this.base.get(this.base.getSimpleApiUrl("action_command_prompt"), opts);
    };

    OctoPrintActionCommandPromptClient.prototype.select = function (choice, opts) {
        var data = {
            choice: choice
        };
        return this.base.simpleApiCommand("action_command_prompt", "select", data, opts);
    };

    OctoPrintClient.registerPluginComponent(
        "action_command_prompt",
        OctoPrintActionCommandPromptClient
    );
    return OctoPrintActionCommandPromptClient;
});
