(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient", "jquery", "lodash"], factory);
    } else {
        factory(global.OctoPrintClient, global.$, global._);
    }
})(this, function (OctoPrintClient, $, _) {
    var url = "api/files";
    var downloadUrl = "downloads/files";
    var testUrl = url + "/test";

    var OctoPrintFilesClient = function (base) {
        this.base = base;
    };

    var resourceForLocation = function (location) {
        return url + "/" + OctoPrintClient.escapePath(location);
    };

    var downloadForLocation = function (location) {
        return downloadUrl + "/" + OctoPrintClient.escapePath(location);
    };

    var downloadForEntry = function (location, filename) {
        return downloadForLocation(location) + "/" + OctoPrintClient.escapePath(filename);
    };

    var resourceForEntry = function (location, filename) {
        return resourceForLocation(location) + "/" + OctoPrintClient.escapePath(filename);
    };

    var preProcessList = function (response) {
        var recursiveCheck = function (element, index, list) {
            if (!element.hasOwnProperty("parent"))
                element.parent = {children: list, parent: undefined};
            if (!element.hasOwnProperty("size")) element.size = undefined;
            if (!element.hasOwnProperty("date")) element.date = undefined;

            if (element.type == "folder") {
                element.weight = 0;
                _.each(element.children, function (e, i, l) {
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

    OctoPrintFilesClient.prototype.get = function (location, entryname, opts) {
        return this.base.get(resourceForEntry(location, entryname), opts);
    };

    OctoPrintFilesClient.prototype.list = function (recursively, force, opts) {
        recursively = recursively || false;
        force = force || false;

        var query = {};
        if (recursively) {
            query.recursive = recursively;
        }
        if (force) {
            query.force = force;
        }

        return this.base.getWithQuery(url, query, opts).done(preProcessList);
    };

    OctoPrintFilesClient.prototype.listForLocation = function (
        location,
        recursively,
        opts
    ) {
        recursively = recursively || false;
        return this.base
            .getWithQuery(resourceForLocation(location), {recursive: recursively}, opts)
            .done(preProcessList);
    };

    OctoPrintFilesClient.prototype.issueEntryCommand = function (
        location,
        entryname,
        command,
        data,
        opts
    ) {
        var url = resourceForEntry(location, entryname);
        return this.base.issueCommand(url, command, data, opts);
    };

    OctoPrintFilesClient.prototype.select = function (location, path, print, opts) {
        print = print || false;

        var data = {
            print: print
        };

        return this.issueEntryCommand(location, path, "select", data, opts);
    };

    OctoPrintFilesClient.prototype.analyse = function (location, path, parameters, opts) {
        return this.issueEntryCommand(location, path, "analyse", parameters || {}, opts);
    };

    OctoPrintFilesClient.prototype.slice = function (location, path, parameters, opts) {
        return this.issueEntryCommand(location, path, "slice", parameters || {}, opts);
    };

    OctoPrintFilesClient.prototype.delete = function (location, path, opts) {
        return this.base.delete(resourceForEntry(location, path), opts);
    };

    OctoPrintFilesClient.prototype.copy = function (location, path, destination, opts) {
        return this.issueEntryCommand(
            location,
            path,
            "copy",
            {destination: destination},
            opts
        );
    };

    OctoPrintFilesClient.prototype.move = function (location, path, destination, opts) {
        return this.issueEntryCommand(
            location,
            path,
            "move",
            {destination: destination},
            opts
        );
    };

    OctoPrintFilesClient.prototype.createFolder = function (location, name, path, opts) {
        var data = {foldername: name};
        if (path !== undefined && path !== "") {
            data.path = path;
        }

        return this.base.postForm(resourceForLocation(location), data, opts);
    };

    OctoPrintFilesClient.prototype.upload = function (location, file, data) {
        data = data || {};

        var filename = data.filename || undefined;
        if (data.userdata && typeof data.userdata === "object") {
            data.userdata = JSON.stringify(userdata);
        }
        return this.base.upload(resourceForLocation(location), file, filename, data);
    };

    OctoPrintFilesClient.prototype.download = function (location, path, opts) {
        return this.base.download(downloadForEntry(location, path), opts);
    };

    OctoPrintFilesClient.prototype.downloadPath = function (location, path) {
        var url = downloadForEntry(location, path);
        if (!_.startsWith(url, "http://") && !_.startsWith(url, "https://")) {
            url = this.base.getBaseUrl() + url;
        }
        return url;
    };

    OctoPrintFilesClient.prototype.pathForEntry = function (entry) {
        if (!entry || !entry.hasOwnProperty("parent") || entry.parent == undefined) {
            return "";
        }

        var recursivePath = function (element, path) {
            if (element.hasOwnProperty("parent") && element.parent != undefined) {
                return recursivePath(element.parent, element.name + "/" + path);
            }

            return path;
        };

        return recursivePath(entry.parent, entry.name);
    };

    OctoPrintFilesClient.prototype.entryForPath = function (path, root) {
        if (_.isArray(root)) {
            root = {children: root};
        }

        var recursiveSearch = function (path, entry) {
            if (path.length == 0) {
                return entry;
            }

            if (!entry.hasOwnProperty("children") || !entry.children) {
                return undefined;
            }

            var name = path.shift();
            for (var i = 0; i < entry.children.length; i++) {
                if (name == entry.children[i].name) {
                    return recursiveSearch(path, entry.children[i]);
                }
            }

            return undefined;
        };

        return recursiveSearch(path.split("/"), root);
    };

    OctoPrintFilesClient.prototype.sanitize = function (location, path, filename, opts) {
        return this.base.issueCommand(
            testUrl,
            "sanitize",
            {storage: location, path: path, filename: filename},
            opts
        );
    };

    OctoPrintFilesClient.prototype.exists = function (location, path, filename, opts) {
        return this.base.issueCommand(
            testUrl,
            "exists",
            {storage: location, path: path, filename: filename},
            opts
        );
    };

    OctoPrintClient.registerComponent("files", OctoPrintFilesClient);
    return OctoPrintFilesClient;
});
