OctoPrint.util = (function($, _) {
    var exports = {};

    var url = "api/util";

    exports.test = function(command, data, opts) {
        return OctoPrint.issueCommand(url + "/test", command, data, opts);
    };

    return exports;
})($, _);
