(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define("OctoPrint", ["jquery", "lodash"], factory);
    } else {
        global.OctoPrint = factory(window.$, window._);
    }
})(window || this, function($, _) {
    var OctoPrint = {};

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

    OctoPrint.options = {
        "baseurl": undefined,
        "apikey": undefined
    };

    OctoPrint.plugins = {};

    OctoPrint.getBaseUrl = function() {
        var url = OctoPrint.options.baseurl;
        if (!_.endsWith(url, "/")) {
            url = url + "/";
        }
        return url;
    };

    OctoPrint.getRequestHeaders = function(additional) {
        additional = additional || {};

        var headers = $.extend({}, additional);
        headers["X-Api-Key"] = OctoPrint.options.apikey;

        return headers;
    };

    OctoPrint.ajax = function(method, url, opts) {
        opts = opts || {};

        method = opts.method || method || "GET";
        url = opts.url || url || "";

        var urlToCall = url;
        if (!_.startsWith(url, "http://") && !_.startsWith(url, "https://")) {
            urlToCall = OctoPrint.getBaseUrl() + url;
        }

        var headers = OctoPrint.getRequestHeaders(opts.headers);

        var params = $.extend({}, opts);
        params.type = method;
        params.headers = headers;
        params.dataType = params.dataType || "json";

        return $.ajax(urlToCall, params);
    };

    OctoPrint.ajaxWithData = function(method, url, data, opts) {
        opts = opts || {};

        var params = $.extend({}, opts);
        params.data = data;

        return OctoPrint.ajax(method, url, params);
    };

    OctoPrint.get = function(url, opts) {
        return OctoPrint.ajax("GET", url, opts);
    };

    OctoPrint.post = function(url, data, opts) {
        return OctoPrint.ajaxWithData("POST", url, data, noCache(opts));
    };

    OctoPrint.postJson = function(url, data, opts) {
        return OctoPrint.post(url, JSON.stringify(data), contentTypeJson(opts));
    };

    OctoPrint.put = function(url, data, opts) {
        return OctoPrint.ajaxWithData("PUT", url, data, noCache(opts));
    };

    OctoPrint.putJson = function(url, data, opts) {
        return OctoPrint.put(url, JSON.stringify(data), contentTypeJson(opts));
    };

    OctoPrint.patch = function(url, data, opts) {
        return OctoPrint.ajaxWithData("PATCH", url, data, noCache(opts));
    };

    OctoPrint.patchJson = function(url, data, opts) {
        return OctoPrint.patch(url, JSON.stringify(data), contentTypeJson(opts));
    };

    OctoPrint.delete = function(url, opts) {
        return OctoPrint.ajax("DELETE", url, opts);
    };

    OctoPrint.download = function(url, opts) {
        var params = $.extend({}, opts || {});
        params.dataType = "text";
        return OctoPrint.get(url, params);
    };

    OctoPrint.upload = function(url, file, filename, additional) {
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

    OctoPrint.issueCommand = function(url, command, payload, opts) {
        payload = payload || {};

        var data = $.extend({}, payload);
        data.command = command;

        return OctoPrint.postJson(url, data, opts);
    };

    OctoPrint.getSimpleApiUrl = function(plugin) {
        return "api/plugin/" + plugin;
    };

    OctoPrint.simpleApiGet = function(plugin, opts) {
        return OctoPrint.get(OctoPrint.getSimpleApiUrl(plugin), opts);
    };

    OctoPrint.simpleApiCommand = function(plugin, command, payload, opts) {
        return OctoPrint.issueCommand(OctoPrint.getSimpleApiUrl(plugin), command, payload, opts);
    };

    OctoPrint.getBlueprintUrl = function(plugin) {
        return "plugin/" + plugin + "/";
    };

    OctoPrint.createRejectedDeferred = function() {
        var deferred = $.Deferred();
        deferred.reject(arguments);
        return deferred;
    };

    OctoPrint.createCustomException = function(name) {
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

    OctoPrint.InvalidArgumentError = OctoPrint.createCustomException("InvalidArgumentError");

    return OctoPrint;
});
