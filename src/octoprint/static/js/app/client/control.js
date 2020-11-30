(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function (OctoPrintClient) {
    var customUrl = "api/printer/command/custom";
    var commandUrl = "api/printer/command";

    var OctoPrintControlClient = function (base) {
        this.base = base;
    };

    OctoPrintControlClient.prototype.getCustomControls = function (opts) {
        return this.base.get(customUrl, opts);
    };

    OctoPrintControlClient.prototype.sendGcodeWithParameters = function (
        commands,
        parameters,
        opts
    ) {
        commands = commands || [];
        parameters = parameters || {};

        if (typeof commands === "string") {
            commands = [commands];
        }

        return this.base.postJson(
            commandUrl,
            {
                commands: commands,
                parameters: parameters
            },
            opts
        );
    };

    OctoPrintControlClient.prototype.sendGcodeScriptWithParameters = function (
        script,
        context,
        parameters,
        opts
    ) {
        script = script || "";
        context = context || {};
        parameters = parameters || {};

        return this.base.postJson(
            commandUrl,
            {
                script: script,
                context: context,
                parameters: parameters
            },
            opts
        );
    };

    OctoPrintControlClient.prototype.sendGcode = function (commands, opts) {
        return this.sendGcodeWithParameters(commands, undefined, opts);
    };

    OctoPrintControlClient.prototype.sendGcodeScript = function (script, context, opts) {
        return this.sendGcodeScriptWithParameters(script, context, undefined, opts);
    };

    OctoPrintClient.registerComponent("control", OctoPrintControlClient);
    return OctoPrintControlClient;
});
