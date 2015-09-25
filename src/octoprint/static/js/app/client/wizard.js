OctoPrint.wizard = (function($, _) {
    var exports = {};

    var url = "api/setup/wizard";

    exports.get = function(opts) {
        return OctoPrint.get(url, opts);
    };

    exports.finish = function(handled, opts) {
        return OctoPrint.postJson(url, {handled: handled || []}, opts);
    };

    return exports;
})($, _);
