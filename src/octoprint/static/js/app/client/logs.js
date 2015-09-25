OctoPrint.logs = (function($, _) {
    var exports = {};

    var url = "api/logs";

    exports.list = function(opts) {
        return OctoPrint.get(url, opts);
    };

    exports.delete = function(file, opts) {
        var fileUrl = url + "/" + file;
        return OctoPrint.delete(fileUrl, opts);
    };

    exports.download = function(file, opts) {
        var fileUrl = url + "/" + file;
        return OctoPrint.download(fileUrl, opts);
    };

    return exports;
})($, _);
