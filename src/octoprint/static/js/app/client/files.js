(function (factory) {
    'use strict';
    if (typeof define === 'function' && define.amd) {
        // Register as an anonymous AMD module:
        define(["OctoPrint", "jquery", "lodash"], factory);
    } else {
        // Browser globals:
        factory(window.OctoPrint, window.jQuery, window._);
    }
})(function(OctoPrint, $, _) {
    var url = "api/files";

    var resourceForLocation = function(location) {
        return url + "/" + location;
    };

    var resourceForEntry = function(location, filename) {
        return resourceForLocation(location) + "/" + filename;
    };

    var issueEntryCommand = function(location, entryname, command, data, opts) {
        var url = resourceForEntry(location, entryname);
        return OctoPrint.issueCommand(url, command, data, opts);
    };

    var getEntry = function(location, entryname, opts) {
        return OctoPrint.get(resourceForEntry(location, entryname), opts);
    };

    var preProcessList = function(response) {
        var recursiveCheck = function(element, index, list) {
            if (!element.hasOwnProperty("parent")) element.parent = { children: list, parent: undefined };
            if (!element.hasOwnProperty("size")) element.size = undefined;
            if (!element.hasOwnProperty("date")) element.date = undefined;

            if (element.type == "folder") {
                element.weight = 0;
                _.each(element.children, function(e, i, l) {
                    e.parent = element;
                    recursiveCheck(e, i, l);
                    element.weight += e.weight;
                });
            } else {
                element.weight = 1;
            }
        };
        _.each(response.files, recursiveCheck);
    };

    OctoPrint.files = {
        get: getEntry,

        list: function (recursively, force, opts) {
            recursively = recursively || false;
            force = force || false;

            var query = {};
            if (recursively) {
                query.recursive = recursively;
            }
            if (force) {
                query.force = force;
            }

            return OctoPrint.getWithQuery(url, query, opts)
                .done(preProcessList);
        },

        listForLocation: function (location, recursively, opts) {
            recursively = recursively || false;
            return OctoPrint.getWithQuery(resourceForLocation(location), {recursive: recursively}, opts)
                .done(preProcessList);
        },

        select: function (location, path, print, opts) {
            print = print || false;

            var data = {
                print: print
            };

            return issueEntryCommand(location, path, "select", data, opts);
        },

        slice: function (location, path, parameters, opts) {
            return issueEntryCommand(location, path, "slice",
                parameters || {}, opts);
        },

        delete: function (location, path, opts) {
            return OctoPrint.delete(resourceForEntry(location, path), opts);
        },

        copy: function(location, path, destination, opts) {
            return issueEntryCommand(location, path, "copy", { destination: destination }, opts);
        },

        move: function(location, path, destination, opts) {
            return issueEntryCommand(location, path, "move", { destination: destination }, opts);
        },

        createFolder: function (location, name, path, opts) {
            var data = {foldername: name};
            if (path !== undefined && path !== "") {
                data.path = path;
            }

            return OctoPrint.postForm(resourceForLocation(location), data, opts);
        },

        upload: function (location, file, data) {
            data = data || {};

            var filename = data.filename || undefined;
            if (data.userdata && typeof data.userdata === "object") {
                data.userdata = JSON.stringify(userdata);
            }
            return OctoPrint.upload(resourceForLocation(location), file, filename, data);
        },

        download: function (location, path, opts) {
            var deferred = $.Deferred();
            getEntry(location, path, opts)
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
