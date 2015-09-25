var OctoPrint = (function($, _) {
    var exports = {};

    var noCache = function(opts) {
        opts = opts || {};

        var params = $.extend({}, opts);
        params.headers = $.extend({}, params.headers || {});
        params.headers["Cache-Control"] = "no-cache";

        return params;
    };

    var contentTypeJson = function(opts) {
        opts = opts || {};

        var params = $.extend({}, opts);
        params.contentType = "application/json; charset=UTF-8";

        return params;
    };

    exports.options = {
        "baseurl": undefined,
        "apikey": undefined
    };

    exports.plugins = {};

    exports.getBaseUrl = function() {
        var url = exports.options.baseurl;
        if (!_.endsWith(url, "/")) {
            url = url + "/";
        }
        return url;
    };

    exports.getRequestHeaders = function(additional) {
        additional = additional || {};

        var headers = $.extend({}, additional);
        headers["X-Api-Key"] = exports.options.apikey;

        return headers;
    };

    exports.ajax = function(method, url, opts) {
        opts = opts || {};

        method = opts.method || method || "GET";
        url = opts.url || url || "";

        var urlToCall = url;
        if (!_.startsWith(url, "http://") && !_.startsWith(url, "https://")) {
            urlToCall = exports.getBaseUrl() + url;
        }

        var headers = exports.getRequestHeaders(opts.headers);

        var params = $.extend({}, opts);
        params.type = method;
        params.headers = headers;
        params.dataType = params.dataType || "json";

        return $.ajax(urlToCall, params);
    };

    exports.ajaxWithData = function(method, url, data, opts) {
        opts = opts || {};

        var params = $.extend({}, opts);
        params.data = data;

        return exports.ajax(method, url, params);
    };

    exports.get = function(url, opts) {
        return exports.ajax("GET", url, opts);
    };

    exports.post = function(url, data, opts) {
        return exports.ajaxWithData("POST", url, data, noCache(opts));
    };

    exports.postJson = function(url, data, opts) {
        return exports.post(url, JSON.stringify(data), contentTypeJson(opts));
    };

    exports.put = function(url, data, opts) {
        return exports.ajaxWithData("PUT", url, data, noCache(opts));
    };

    exports.putJson = function(url, data, opts) {
        return exports.put(url, data, contentTypeJson(opts));
    };

    exports.patch = function(url, data, opts) {
        return exports.ajaxWithData("PATCH", url, data, noCache(opts));
    };

    exports.patchJson = function(url, data, opts) {
        return exports.patch(url, JSON.stringify(data), contentTypeJson(opts));
    };

    exports.delete = function(url, opts) {
        return exports.ajax("DELETE", url, opts);
    };

    exports.download = function(url, opts) {
        var params = $.extend({}, opts || {});
        params.dataType = "text";
        return exports.get(url, params);
    };

    exports.upload = function(url, file, filename, additional) {
        additional = additional || {};

        var fileData;
        if (file instanceof jQuery) {
            fileData = file[0].files[0];
        } else if (typeof file == "string") {
            fileData = $(file)[0].files[0];
        } else {
            fileData = file;
        }

        filename = filename || fileData.name;

        var form = new FormData();
        form.append("file", fileData, filename);

        _.each(additional, function(value, key) {
            form.append(key, value);
        });

        var deferred = $.Deferred();

        var request = new XMLHttpRequest();
        request.onreadystatechange = function() {
            if (request.readyState == 4) {
                deferred.notify({loaded: filesize, total: filesize});

                var success = request.status >= 200 && request.status < 300
                    || request.status === 304;
                var error, json, statusText;

                try {
                    json = JSON.parse(request.response);
                    statusText = "success";
                } catch (e) {
                    success = false;
                    error = e;
                    statusText = "parsererror";
                }

                if (success) {
                    deferred.resolve([json, statusText, request]);
                } else {
                    if (!statusText) {
                        statusText = request.statusText;
                    }
                    deferred.reject([request, statusText, error]);
                }
            }
        };
        request.ontimeout = function() {
            deferred.reject([request, "timeout", "Timeout"]);
        };
        request.upload.addEventListener("loadstart", function(e) {
            deferred.notify({loaded: e.loaded, total: e.total});
        });
        request.upload.addEventListener("progress", function(e) {
            deferred.notify({loaded: e.loaded, total: e.total});
        });
        request.upload.addEventListener("loadend", function(e) {
            deferred.notify({loaded: e.loaded, total: e.total});
        });

        var headers = OctoPrint.getRequestHeaders();

        request.open("POST", OctoPrint.getBaseUrl() + url);
        _.each(headers, function(value, key) {
            request.setRequestHeader(key, value);
        });
        request.send(form);

        return deferred.promise();
    };

    exports.issueCommand = function(url, command, payload, opts) {
        payload = payload || {};

        var data = $.extend({}, payload);
        data.command = command;

        return exports.postJson(url, data, opts);
    };

    exports.getSimpleApiUrl = function(plugin) {
        return "api/plugin/" + plugin;
    };

    exports.simpleApiGet = function(plugin, opts) {
        return OctoPrint.get(exports.getSimpleApiUrl(plugin), opts);
    };

    exports.simpleApiCommand = function(plugin, command, payload, opts) {
        return OctoPrint.issueCommand(exports.getSimpleApiUrl(plugin), command, payload, opts);
    };

    exports.getBlueprintUrl = function(plugin) {
        return "plugin/" + plugin + "/";
    };

    exports.createRejectedDeferred = function() {
        var deferred = $.Deferred();
        deferred.reject(arguments);
        return deferred;
    };

    exports.createCustomException = function(name) {
        var constructor;

        if (_.isFunction(name)) {
            constructor = name;
        } else {
            constructor = function(message) {
                this.name = name;
                this.message = message;
                this.stack = (new Error()).stack;
            };
        }

        constructor.prototype = Object.create(Error.prototype);
        constructor.prototype.constructor = constructor;

        return constructor;
    };

    exports.InvalidArgumentError = exports.createCustomException("InvalidArgumentError");

    return exports;
})($, _);
