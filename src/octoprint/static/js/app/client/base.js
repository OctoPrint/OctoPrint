(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define("OctoPrintClient", ["jquery", "lodash"], factory);
    } else {
        global.OctoPrintClient = factory(global.$, global._);
        global.OctoPrint = new global.OctoPrintClient();
    }
})(this, function ($, _) {
    var PluginRegistry = function (base) {
        this.base = base;
        this.components = {};
    };

    var OctoPrintClient = function (options) {
        this.options = options || {
            baseurl: undefined,
            apikey: undefined,
            locale: undefined
        };

        this.components = {};
        this.plugins = new PluginRegistry(this);
    };

    OctoPrintClient.registerComponent = function (name, component) {
        Object.defineProperty(OctoPrintClient.prototype, name, {
            get: function () {
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

    OctoPrintClient.registerPluginComponent = function (name, component) {
        Object.defineProperty(PluginRegistry.prototype, name, {
            get: function () {
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

    var noCache = function (opts) {
        opts = opts || {};

        var params = $.extend({}, opts);
        params.headers = $.extend({}, params.headers || {});
        params.headers["Cache-Control"] = "no-cache";

        return params;
    };

    var contentTypeJson = function (opts) {
        opts = opts || {};

        var params = $.extend({}, opts);
        params.contentType = "application/json; charset=UTF-8";

        return params;
    };

    var contentTypeFalse = function (opts) {
        opts = opts || {};

        var params = $.extend({}, opts);
        params.contentType = false;

        return params;
    };

    var noProcessData = function (opts) {
        opts = opts || {};

        var params = $.extend({}, opts);
        params.processData = false;

        return params;
    };

    var replaceUndefinedWithNull = function (key, value) {
        if (value === undefined) {
            return null;
        } else {
            return value;
        }
    };

    OctoPrintClient.prototype.getBaseUrl = function () {
        var url = this.options.baseurl;
        if (!_.endsWith(url, "/")) {
            url = url + "/";
        }
        return url;
    };

    OctoPrintClient.prototype.getParsedBaseUrl = function (location) {
        if (!this.options.baseurl) return "";

        try {
            var url = new URL(this.options.baseurl);
        } catch (e) {
            location = location || window.location;
            var parsed = new URL(location);
            var path = this.options.baseurl;
            if (!path || path[0] !== "/") {
                path = "/" + (path ? path : "");
            }
            var url = new URL(parsed.protocol + "//" + parsed.host + path);
        }

        return url;
    };

    OctoPrintClient.prototype.getCookieSuffix = function () {
        if (!this.options.baseurl) return "";

        var url = this.getParsedBaseUrl();

        var port = url.port || (url.protocol === "https:" ? 443 : 80);
        if (url.pathname && url.pathname !== "/") {
            var path = url.pathname;
            if (path.endsWith("/")) {
                path = path.substring(0, path.length - 1);
            }
            return "_P" + port + "_R" + path.replace(/\//g, "|");
        } else {
            return "_P" + port;
        }
    };

    OctoPrintClient.prototype.getCookieName = function (name) {
        return name + this.getCookieSuffix();
    };

    OctoPrintClient.prototype.getCookie = function (name) {
        name = this.getCookieName(name);
        return ("; " + document.cookie)
            .split("; " + name + "=")
            .pop()
            .split(";")[0];
    };

    OctoPrintClient.prototype.getRequestHeaders = function (method, additional, opts) {
        if (arguments.length <= 1) {
            // versions prior 1.8.3 don't know method and opts
            if (!_.isString(method)) {
                additional = method;
                console.warn(
                    "Calling OctoPrintClient.getRequestHeaders with additional " +
                        "headers as the first parameter is deprecated. Please " +
                        "consult the docs about the current signature and adjust " +
                        "your code accordingly."
                );
            }
        }

        method = method || "GET";
        additional = additional || {};
        opts = opts || {};

        var headers = $.extend({}, additional);

        if (this.options.apikey) {
            headers["X-Api-Key"] = this.options.apikey;
        } else {
            // no API key, so browser context, so let's make sure the CSRF token
            // header is set
            var csrfToken = this.getCookie("csrf_token");
            if (!/^(GET|HEAD|OPTIONS)$/.test(method) && csrfToken && !opts.crossDomain) {
                headers["X-CSRF-Token"] = csrfToken;
            }
        }

        if (this.options.locale !== undefined) {
            headers["X-Locale"] = this.options.locale;
        }

        return headers;
    };

    OctoPrintClient.prototype.ajax = function (method, url, opts) {
        opts = opts || {};

        method = opts.method || method || "GET";
        url = opts.url || url || "";

        var urlToCall = url;
        if (!_.startsWith(url, "http://") && !_.startsWith(url, "https://")) {
            urlToCall = this.getBaseUrl() + url;
            opts.url = urlToCall;
        }

        var headers = this.getRequestHeaders(method, opts.headers, opts);

        var params = $.extend({}, opts);
        params.type = method;
        params.headers = headers;
        params.dataType = params.dataType || "json";

        return $.ajax(urlToCall, params);
    };

    OctoPrintClient.prototype.ajaxWithData = function (method, url, data, opts) {
        opts = opts || {};

        var params = $.extend({}, opts);
        params.data = data;

        return this.ajax(method, url, params);
    };

    OctoPrintClient.prototype.get = function (url, opts) {
        return this.ajax("GET", url, opts);
    };

    OctoPrintClient.prototype.getWithQuery = function (url, data, opts) {
        return this.ajaxWithData("GET", url, data, opts);
    };

    OctoPrintClient.prototype.post = function (url, data, opts) {
        return this.ajaxWithData("POST", url, data, noCache(opts));
    };

    OctoPrintClient.prototype.postForm = function (url, data, opts) {
        var form = new FormData();
        _.each(data, function (value, key) {
            form.append(key, value);
        });

        return this.post(url, form, contentTypeFalse(noProcessData(opts)));
    };

    OctoPrintClient.prototype.postJson = function (url, data, opts) {
        return this.post(
            url,
            JSON.stringify(data, replaceUndefinedWithNull),
            contentTypeJson(opts)
        );
    };

    OctoPrintClient.prototype.put = function (url, data, opts) {
        return this.ajaxWithData("PUT", url, data, noCache(opts));
    };

    OctoPrintClient.prototype.putJson = function (url, data, opts) {
        return this.put(
            url,
            JSON.stringify(data, replaceUndefinedWithNull),
            contentTypeJson(opts)
        );
    };

    OctoPrintClient.prototype.patch = function (url, data, opts) {
        return this.ajaxWithData("PATCH", url, data, noCache(opts));
    };

    OctoPrintClient.prototype.patchJson = function (url, data, opts) {
        return this.patch(
            url,
            JSON.stringify(data, replaceUndefinedWithNull),
            contentTypeJson(opts)
        );
    };

    OctoPrintClient.prototype.delete = function (url, opts) {
        return this.ajax("DELETE", url, opts);
    };

    OctoPrintClient.prototype.download = function (url, opts) {
        var params = $.extend({}, opts || {});
        params.dataType = "text";
        return this.get(url, params);
    };

    OctoPrintClient.prototype.bulkDownloadUrl = function (url, files) {
        return (
            url +
            "?" +
            _.map(files, function (f) {
                return "files=" + encodeURIComponent(f);
            }).join("&")
        );
    };

    OctoPrintClient.prototype.upload = function (url, file, filename, additional) {
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

        _.each(additional, function (value, key) {
            form.append(key, value);
        });

        var deferred = $.Deferred();

        var request = new XMLHttpRequest();
        request.onreadystatechange = function () {
            if (request.readyState == 4) {
                deferred.notify({loaded: filesize, total: filesize});

                var success =
                    (request.status >= 200 && request.status < 300) ||
                    request.status === 304;
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
        request.ontimeout = function () {
            deferred.reject([request, "timeout", "Timeout"]);
        };
        request.upload.addEventListener("loadstart", function (e) {
            deferred.notify({loaded: e.loaded, total: e.total});
        });
        request.upload.addEventListener("progress", function (e) {
            deferred.notify({loaded: e.loaded, total: e.total});
        });
        request.upload.addEventListener("loadend", function (e) {
            deferred.notify({loaded: e.loaded, total: e.total});
        });

        var method = "POST";
        var headers = this.getRequestHeaders(method);

        var urlToCall = url;
        if (!_.startsWith(url, "http://") && !_.startsWith(url, "https://")) {
            urlToCall = this.getBaseUrl() + url;
        }

        request.open(method, urlToCall);
        _.each(headers, function (value, key) {
            request.setRequestHeader(key, value);
        });
        request.send(form);

        return deferred.promise();
    };

    OctoPrintClient.prototype.issueCommand = function (url, command, payload, opts) {
        payload = payload || {};

        var data = $.extend({}, payload);
        data.command = command;

        return this.postJson(url, data, opts);
    };

    OctoPrintClient.prototype.getSimpleApiUrl = function (plugin) {
        return "api/plugin/" + plugin;
    };

    OctoPrintClient.prototype.simpleApiGet = function (plugin, opts) {
        return this.get(OctoPrintClient.prototype.getSimpleApiUrl(plugin), opts);
    };

    OctoPrintClient.prototype.simpleApiCommand = function (
        plugin,
        command,
        payload,
        opts
    ) {
        return this.issueCommand(
            OctoPrintClient.prototype.getSimpleApiUrl(plugin),
            command,
            payload,
            opts
        );
    };

    OctoPrintClient.prototype.getBlueprintUrl = function (plugin) {
        return "plugin/" + plugin + "/";
    };

    OctoPrintClient.createRejectedDeferred = function () {
        var deferred = $.Deferred();
        deferred.reject(arguments);
        return deferred;
    };

    OctoPrintClient.createCustomException = function (name) {
        var constructor;

        if (_.isFunction(name)) {
            constructor = name;
        } else {
            constructor = function (message) {
                this.name = name;
                this.message = message;
                this.stack = new Error().stack;
            };
        }

        constructor.prototype = Object.create(Error.prototype);
        constructor.prototype.constructor = constructor;

        return constructor;
    };

    OctoPrintClient.InvalidArgumentError =
        OctoPrintClient.createCustomException("InvalidArgumentError");

    OctoPrintClient.deprecated = function (deprecatedFct, newFct, fn) {
        return function () {
            console.warn(
                deprecatedFct +
                    " is deprecated, please use the new " +
                    newFct +
                    " function instead"
            );
            return fn.apply(this, arguments);
        };
    };

    OctoPrintClient.deprecatedMethod = function (
        object,
        oldNamespace,
        oldFct,
        newNamespace,
        newFct,
        fn
    ) {
        object[oldFct] = OctoPrintClient.deprecated(
            oldNamespace + "." + oldFct,
            newNamespace + "." + newFct,
            fn
        );
    };

    OctoPrintClient.deprecatedVariable = function (
        object,
        oldNamespace,
        oldVar,
        newNamespace,
        newVar,
        getter,
        setter
    ) {
        Object.defineProperty(object, oldVar, {
            get: function () {
                return OctoPrintClient.deprecated(
                    oldNamespace + "." + oldVar,
                    newNamespace + "." + newVar,
                    getter
                )();
            },
            set: function (val) {
                OctoPrintClient.deprecated(
                    oldNamespace + "." + oldVar,
                    newNamespace + "." + newVar,
                    setter
                )(val);
            }
        });
    };

    OctoPrintClient.escapePath = function (path) {
        return _.map(path.split("/"), function (p) {
            return encodeURIComponent(p);
        }).join("/");
    };

    return OctoPrintClient;
});
