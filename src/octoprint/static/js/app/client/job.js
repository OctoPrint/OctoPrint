(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrint"], factory);
    } else {
        factory(window.OctoPrint);
    }
})(window || this, function(OctoPrint) {
    var url = "api/job";

    var issueCommand = function(command, opts) {
        return OctoPrint.issueCommand(url, command, {}, opts);
    };

    OctoPrint.job = {
        get: function(opts) {
            return OctoPrint.get(url, opts);
        },
        start: function(opts) {
            return issueCommand("start", opts);
        },
        restart: function(opts) {
            return issueCommand("restart", opts);
        },
        pause: function(opts) {
            return issueCommand("pause", opts);
        },
        cancel: function(opts) {
            return issueCommand("cancel", opts);
        }
    }
});
