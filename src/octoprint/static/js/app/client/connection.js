OctoPrint.connection = (function() {
    var exports = {};

    exports.getSettings = function(opts) {
        return OctoPrint.get("api/connection", opts);
    };

    exports.connect = function(data, opts) {
        return exports.issueCommand("connect", data || {}, opts);
    };

    exports.disconnect = function(opts) {
        return exports.issueCommand("disconnect", {}, opts);
    };

    exports.fakeAck = function(opts) {
        return exports.issueCommand("fake_ack", {}, opts);
    };

    exports.issueCommand = function(command, data, opts) {
        return OctoPrint.issueCommand("api/connection", command, data, opts);
    };

    return exports;
})($, _);
