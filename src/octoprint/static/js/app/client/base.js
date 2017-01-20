(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define("OctoPrintClient", ["jquery", "lodash"], factory);
    } else {
        global.OctoPrintClient = factory(global.$, global._);
        global.OctoPrint = new global.OctoPrintClient();
    }
})(this, function($, _) {
    var PluginRegistry = function(base) {
        this.base = base;
        this.components = {};
    };

    var OctoPrintClient = function(options) {
        this.options = options || {
            "baseurl": undefined,
            "apikey": undefined,
            "locale": undefined
        };

        this.components = {};
        this.plugins = new PluginRegistry(this);
    };

    OctoPrintClient.registerComponent = function(name, component) {
        Object.defineProperty(OctoPrintClient.prototype, name, {
            get: function() {
                if (this.components[name] !== undefined) {
                    return this.components[name];
                }

                var instance = new component(this);
                this.components[name] = instance;
                return instance;
           },
            enumerable: false,
            configurable: false
        });
    };

    OctoPrintClient.registerPluginComponent = function(name, component) {
        Object.defineProperty(PluginRegistry.prototype, name, {
            get: function() {
                if (this.components[name] !== undefined) {
                    return this.components[name];
                }

                var instance = new component(this.base);
                this.components[name] = instance;
                return instance;
            },
            enumerable: false,
            configurable: false
        });
    };

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

    var contentTypeFalse = function(opts) {
        opts = opts || {};

        var params = $.extend({}, opts);
        params.contentType = false;

        return params;
    };

    var noProcessData = function(opts) {
        opts = opts || {};

        var params = $.extend({}, opts);
        params.processData = false;

        return params;
    };

    OctoPrintClient.prototype.getBaseUrl = function() {
        var url = this.options.baseurl;
        if (!_.endsWith(url, "/")) {
            url = url + "/";
        }
        return url;
    };

    OctoPrintClient.prototype.getRequestHeaders = function(additional) {
        additional = additional || {};

        var headers = $.extend({}, additional);
        headers["X-Api-Key"] = this.options.apikey;

        if (this.options.locale !== undefined) {
            headers["X-Locale"] = this.options.locale;
        }

        return headers;
    };

    OctoPrintClient.prototype.ajax = function(method, url, opts) {
        opts = opts || {};

        method = opts.method || method || "GET";
        url = opts.url || url || "";

        var urlToCall = url;
        if (!_.startsWith(url, "http://") && !_.startsWith(url, "https://")) {
            urlToCall = this.getBaseUrl() + url;
            opts.url = urlToCall;
        }

        var headers = this.getRequestHeaders(opts.headers);

        var params = $.extend({}, opts);
        params.type = method;
        params.headers = headers;
        params.dataType = params.dataType || "json";

        return $.ajax(urlToCall, params);
    };

    OctoPrintClient.prototype.ajaxWithData = function(method, url, data, opts) {
        opts = opts || {};

        var params = $.extend({}, opts);
        params.data = data;

        return this.ajax(method, url, params);
    };

    OctoPrintClient.prototype.get = function(url, opts) {
        return this.ajax("GET", url, opts);
    };

    OctoPrintClient.prototype.getWithQuery = function(url, data, opts) {
        return this.ajaxWithData("GET", url, data, opts);
    };

    OctoPrintClient.prototype.post = function(url, data, opts) {
        return this.ajaxWithData("POST", url, data, noCache(opts));
    };

    OctoPrintClient.prototype.postForm = function(url, data, opts) {
        var form = new FormData();
        _.each(data, function(value, key) {
            form.append(key, value);
        });

        return this.post(url, form, contentTypeFalse(noProcessData(opts)));
    };

    OctoPrintClient.prototype.postJson = function(url, data, opts) {
        return this.post(url, JSON.stringify(data), contentTypeJson(opts));
    };

    OctoPrintClient.prototype.put = function(url, data, opts) {
        return this.ajaxWithData("PUT", url, data, noCache(opts));
    };

    OctoPrintClient.prototype.putJson = function(url, data, opts) {
        return this.put(url, JSON.stringify(data), contentTypeJson(opts));
    };

    OctoPrintClient.prototype.patch = function(url, data, opts) {
        return this.ajaxWithData("PATCH", url, data, noCache(opts));
    };

    OctoPrintClient.prototype.patchJson = function(url, data, opts) {
        return this.patch(url, JSON.stringify(data), contentTypeJson(opts));
    };

    OctoPrintClient.prototype.delete = function(url, opts) {
        return this.ajax("DELETE", url, opts);
    };

    OctoPrintClient.prototype.download = function(url, opts) {
        var params = $.extend({}, opts || {});
        params.dataType = "text";
        return this.get(url, params);
    };

    OctoPrintClient.prototype.upload = function(url, file, filename, additional) {
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
        var filesize = fileData.size;

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

        var headers = this.getRequestHeaders();

        var urlToCall = url;
        if (!_.startsWith(url, "http://") && !_.startsWith(url, "https://")) {
            urlToCall = this.getBaseUrl() + url;
        }

        request.open("POST", urlToCall);
        _.each(headers, function(value, key) {
            request.setRequestHeader(key, value);
        });
        request.send(form);

        return deferred.promise();
    };

    OctoPrintClient.prototype.issueCommand = function(url, command, payload, opts) {
        payload = payload || {};

        var data = $.extend({}, payload);
        data.command = command;

        return this.postJson(url, data, opts);
    };

    OctoPrintClient.prototype.getSimpleApiUrl = function(plugin) {
        return "api/plugin/" + plugin;
    };

    OctoPrintClient.prototype.simpleApiGet = function(plugin, opts) {
        return this.get(OctoPrintClient.prototype.getSimpleApiUrl(plugin), opts);
    };

    OctoPrintClient.prototype.simpleApiCommand = function(plugin, command, payload, opts) {
        return this.issueCommand(OctoPrintClient.prototype.getSimpleApiUrl(plugin), command, payload, opts);
    };

    OctoPrintClient.prototype.getBlueprintUrl = function(plugin) {
        return "plugin/" + plugin + "/";
    };

    OctoPrintClient.createRejectedDeferred = function() {
        var deferred = $.Deferred();
        deferred.reject(arguments);
        return deferred;
    };

    OctoPrintClient.createCustomException = function(name) {
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

    OctoPrintClient.InvalidArgumentError = OctoPrintClient.createCustomException("InvalidArgumentError");

    return OctoPrintClient;
});
