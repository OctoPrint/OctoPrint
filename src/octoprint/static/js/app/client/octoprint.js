var OctoPrint = (function($, _) {
    var exports = {};

    exports.options = {
        "baseurl": undefined,
        "apikey": undefined
    };

    exports.ajax = function(opts) {
        opts = opts || {};

        var url = exports.options.baseurl;
        if (!_.endsWith(url, "/")) {
            url = url + "/";
        }
        url += opts.url;

        var headers = $.extend({}, opts.headers || {});
        headers["X-Api-Key"] = exports.options.apikey;

        var params = $.extend({}, opts);
        params.url = url;
        params.headers = headers;

        return $.ajax(params);
    };

    exports.get = function(opts) {
        opts = opts || {};

        var params = $.extend({}, opts);
        params.type = "GET";

        return exports.ajax(params);
    };

    exports.post = function(data, opts) {
        opts = opts || {};

        var headers = $.extend({}, opts.headers || {});
        headers["Cache-Control"] = "no-cache";

        var params = $.extend({}, opts);
        params.type = "POST";
        params.data = data;
        params.headers = headers;

        return exports.ajax(params);
    };

    exports.delete = function(opts) {
        opts = opts || {};

        var params = $.extend({}, opts);
        params.type = "DELETE";

        return exports.ajax(params);
    };

    exports.getJson = function(opts) {
        opts = opts || {};

        var params = $.extend({}, opts);
        params.dataType = "json";

        return exports.get(params);
    };

    exports.postJson = function(data, opts) {
        opts = opts || {};

        var params = $.extend({}, opts);
        params.contentType = "application/json; charset=UTF-8";
        params.dataType = "json";

        return exports.post(JSON.stringify(data), params);
    };

    return exports;
})($, _);
