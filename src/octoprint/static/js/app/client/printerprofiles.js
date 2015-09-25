OctoPrint.printerprofiles = (function($, _) {
    var exports = {};

    var url = "api/printerprofiles";

    exports.get = function(opts) {
        return OctoPrint.get(url, opts);
    };

    exports.add = function(profile, additional, opts) {
        profile = profile || {};
        additional = additional || {};

        var data = $.extend({}, additional);
        data.profile = profile;

        return OctoPrint.postJson(url, data, opts);
    };

    exports.update = function(id, profile, additional, opts) {
        profile = profile || {};
        additional = addtional || {};

        var data = $.extend({}, additional);
        data.profile = profile;

        var profileUrl = url + "/" + id;
        return OctoPrint.patchJson(profileUrl, data, opts);
    };

    exports.delete = function(id, opts) {
        var profileUrl = url + "/" + id;
        return OctoPrint.delete(profileUrl, opts);
    };

    return exports;
})($, _);
