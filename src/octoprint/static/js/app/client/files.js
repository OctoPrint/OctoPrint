(function (factory) {
    'use strict';
    if (typeof define === 'function' && define.amd) {
        // Register as an anonymous AMD module:
        define(["OctoPrint", "jquery"], factory);
    } else {
        // Browser globals:
        factory(window.OctoPrint, window.jQuery);
    }
})(function(OctoPrint, $) {
    var url = "api/files";

    var resourceForLocation = function(location) {
        return url + "/" + location;
    };

    var resourceForFile = function(location, filename) {
        return resourceForLocation(location) + "/" + filename;
    };

    var issueFileCommand = function(location, filename, command, data, opts) {
        var url = resourceForFile(location, filename);
        return OctoPrint.issueCommand(url, command, data, opts);
    };

    OctoPrint.files = {
        list: function (opts) {
            return OctoPrint.get(url, opts);
        },

        listForLocation: function (location, opts) {
            return OctoPrint.get(resourceForLocation(location), opts);
        },

        get: function (location, filename, opts) {
            return OctoPrint.get(resourceForFile(location, filename), opts);
        },

        select: function (location, filename, print, opts) {
            print = print || false;

            var data = {
                print: print
            };

            return issueFileCommand(location, filename, "select", data, opts);
        },

        slice: function (location, filename, parameters, opts) {
            return issueFileCommand(location, filename, "slice",
                parameters || {}, opts);
        },

        delete: function (location, filename, opts) {
            return OctoPrint.delete(resourceForFile(location, filename), opts);
        },

        upload: function (location, file, data) {
            data = data || {};

            var filename = data.filename || undefined;
            return OctoPrint.upload(resourceForLocation(location), file, filename, data);
        },

        download: function (location, filename, opts) {
            var deferred = $.Deferred();
            exports.get(location, filename, opts)
                .done(function (response) {
                    OctoPrint.download(response.refs.download, opts)
                        .done(function () {
                            deferred.resolve.apply(null, arguments);
                        })
                        .fail(function () {
                            deferred.reject.apply(null, arguments);
                        });
                })
                .fail(function () {
                    deferred.reject.apply(null, arguments);
                });
            return deferred.promise();
        }
    }
});
