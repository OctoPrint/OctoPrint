OctoPrint.languages = (function($, _) {
    var exports = {};

    var url = "api/languages";

    exports.list = function(opt) {
        return OctoPrint.get(url, opt);
    };

    exports.upload = function(file) {
        return OctoPrint.upload(url, file);
    };

    exports.delete = function(locale, pack, opts) {
        var packUrl = url + "/" + locale + "/" + pack;
        return OctoPrint.delete(packUrl, opts);
    };

    return exports;
})($, _);
