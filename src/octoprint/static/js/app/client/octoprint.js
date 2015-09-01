var OctoPrint = (function($) {
    var self = {};

    self.options = {
        "baseurl": undefined,
        "apikey": undefined
    };

    self.ajax = function(opts) {
        var url = self.options.baseurl + opts.url;
        var headers = $.extend({}, opts.headers || {});
        headers["X-Api-Key"] = self.options.apikey;

        var params = $.extend({}, opts);
        params.url = url;

        $.ajax(params);
    };

    self.get = function(opts) {
        var params = $.extend({}, opts);
        params.type = "GET";

        self.ajax(params);
    };

    self.post = function(opts) {
        var headers = $.extend({}, opts.headers || {});
        headers["Cache-Control"] = "no-cache";

        var params = $.extend({}, opts);
        params.type = "POST";
        params.data = JSON.stringify(data);
        params.headers = headers;

        self.ajax(params);
    };

    self.delete = function(opts) {
        var params = $.extend({}, opts);
        params.type = "DELETE";

        self.ajax(params);
    };

    self.get_json = function(opts) {
        var params = $.extend({}, opts);
        params.dataType = "json";

        self.get(params);
    };

    self.post_json = function(opts) {
        var data = opts.data || {};

        var params = $.extend({}, opts);
        params.contentType = "application/json; charset=UTF-8";
        params.dataType = "json";
        params.data = JSON.stringify(data);

        self.post(params);
    };

    return self;
})($);
