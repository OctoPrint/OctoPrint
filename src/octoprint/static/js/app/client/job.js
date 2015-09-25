OctoPrint.job = (function($, _) {
    var exports = {};

    var url = "api/job";

    var issueCommand = function(command, data, opts) {
        return OctoPrint.issueCommand(url, command, data, opts);
    };

    exports.get = function(opts) {
        return OctoPrint.get(url, opts);
    };

    exports.start = function(opts) {
        return issueCommand("start", {}, opts);
    };

    exports.restart = function(opts) {
        return issueCommand("restart", {}, opts);
    };

    exports.pause = function(opts) {
        return issueCommand("pause", {}, opts);
    };

    exports.cancel = function(opts) {
        return issueCommand("cancel", {}, opts);
    };

    return exports;
})($, _);
