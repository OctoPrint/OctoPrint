OctoPrint.settings = (function($, _) {
    var exports = {};

    var url = "api/settings";

    exports.get = function(opts) {
        return OctoPrint.get(url, opts);
    };

    exports.save = function(settings, opts) {
        settings = settings || {};
        return OctoPrint.postJson(url, settings, opts);
    };

    return exports;
})($, _);
