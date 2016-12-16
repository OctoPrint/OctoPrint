(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrint"], factory);
    } else {
        factory(window.OctoPrint);
    }
})(window || this, function(OctoPrint) {
    var url = "api/system";
    var commandUrl = "api/system/commands";

    OctoPrint.system = {
        getCommands: function (opts) {
            return OctoPrint.get(commandUrl, opts);
        },

        getCommandsForSource: function (source, opts) {
            return OctoPrint.get(commandUrl + "/" + source, opts);
        },

        executeCommand: function (source, action, opts) {
            return OctoPrint.postJson(commandUrl + "/" + source + "/" + action, {}, opts);
        }
    };
});
