OctoPrint.control = (function($, _) {
    var exports = {};

    var customUrl = "api/printer/command/custom";
    var commandUrl = "api/printer/command";

    exports.getCustomControls = function(opts) {
        return OctoPrint.get(customUrl, opts);
    };

    exports.sendGcode = function(commands, opts) {
        commands = commands || [];

        if (typeof commands === "string") {
            commands = [commands];
        }

        return OctoPrint.postJson(commandUrl, {commands: commands}, opts);
    };

    exports.sendGcodeWithParameters = function(commands, parameters, opts) {
        commands = commands || [];
        parameters = parameters || {};

        if (typeof commands === "string") {
            commands = [commands];
        }

        return OctoPrint.postJson(commandUrl, {commands: commands, parameters: parameters}, opts);
    };

    exports.sendGcodeScript = function(script, context, opts) {
        script = script || "";
        context = context || {};

        return OctoPrint.postJson(commandUrl, {script: script, context: context}, opts);
    };

    exports.executeSystemCommand = function(action, opts) {
        return OctoPrint.postJson("api/system", {action: action}, opts);
    };

    return exports;
})($, _);
