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

    var resourceForFile = function(location, filename) {
        return resourceForLocation(location) + "/" + filename;
    };

    var issueFileCommand = function(location, filename, command, data, opts) {
        var url = resourceForFile(location, filename);
        return OctoPrint.issueCommand(url, command, data, opts);
    };

    var getFile = function(location, filename, opts) {
        return OctoPrint.get(resourceForFile(location, filename), opts);
    };

    var preProcessList = function(response) {
        var recursiveCheck = function(element, index, list) {
            if (!element.hasOwnProperty("parent")) element.parent = { children: list, parent: undefined };
            if (!element.hasOwnProperty("size")) element.size = undefined;
            if (!element.hasOwnProperty("date")) element.date = undefined;

            if (element.type == "folder") {
                _.each(element.children, function(e, i, l) {
                    e.parent = element;
                    recursiveCheck(e, i, l);
                });
            }
        };
        _.each(response.files, recursiveCheck);
    };

    OctoPrint.files = {
        get: getFile,

        list: function (opts) {
            return OctoPrint.get(url, opts)
                .done(preProcessList);
        },

        listForLocation: function (location, opts) {
            return OctoPrint.get(resourceForLocation(location), opts)
                .done(preProcessList);
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

        copy: function(location, filename, destination, opts) {
            return issueFileCommand(location, filename, "copy", { destination: destination }, opts);
        },

        move: function(location, filename, destination, opts) {
            return issueFileCommand(location, filename, "move", { destination: destination }, opts);
        },

        createFolder: function (location, name, path) {
            var data = "foldername=" + name;
            if (path != undefined && path != "") {
                data = "foldername:" + path + "/" + name;
            }

            return OctoPrint.post(resourceForLocation(location), data);

        },

        upload: function (location, file, data) {
            data = data || {};

            var filename = data.filename || undefined;
            return OctoPrint.upload(resourceForLocation(location), file, filename, data);
        },

        download: function (location, filename, opts) {
            var deferred = $.Deferred();
            getFile(location, filename, opts)
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
        },

        pathForElement: function(element) {
            if (!element || !element.hasOwnProperty("parent") || element.parent == undefined) {
                return "";
            }

            var recursivePath = function(element, path) {
              if (element.hasOwnProperty("parent") && element.parent != undefined) {
                  return recursivePath(element.parent, element.name + "/" + path);
              }

              return path;
            };

            return recursivePath(element.parent, element.name);
        },

        elementByPath: function(location, startElement) {
            var recursiveSearch = function(location, element) {
                if (location.length == 0) {
                    return element;
                }

                if (!element.hasOwnProperty("children")) {
                    return undefined;
                }

                var name = location.shift();
                for(var i = 0; i < element.children.length; i++) {
                    if (name == element.children[i].name) {
                        return recursiveSearch(location, element.children[i]);
                    }
                }

                return undefined;
            };

            return recursiveSearch(location.split("/"), startElement);
        }
    }
});
