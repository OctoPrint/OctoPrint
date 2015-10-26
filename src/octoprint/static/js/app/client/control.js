(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrint"], factory);
    } else {
        factory(window.OctoPrint);
    }
})(window || this, function(OctoPrint) {
    var customUrl = "api/printer/command/custom";
    var commandUrl = "api/printer/command";

    var sendGcodeWithParameters = function(commands, parameters, opts) {
        commands = commands || [];
        parameters = parameters || {};

        if (typeof commands === "string") {
            commands = [commands];
        }

        return OctoPrint.postJson(commandUrl, {
            commands: commands,
            parameters: parameters
        }, opts);
    };

    var sendGcodeScriptWithParameters = function(script, context, parameters, opts) {
        script = script || "";
        context = context || {};
        parameters = parameters || {};

        return OctoPrint.postJson(commandUrl, {
            script: script,
            context: context,
            parameters: parameters
        }, opts);
    };

    OctoPrint.control = {
        sendGcodeWithParameters: sendGcodeWithParameters,
        sendGcodeScriptWithParameters: sendGcodeScriptWithParameters,

        getCustomControls: function (opts) {
            return OctoPrint.get(customUrl, opts);
        },

        sendGcode: function (commands, opts) {
            return sendGcodeWithParameters(commands, undefined, opts);
        },

        sendGcodeScript: function (script, context, opts) {
            return sendGcodeScriptWithParameters(script, context, undefined, opts);
        }
    }
});
