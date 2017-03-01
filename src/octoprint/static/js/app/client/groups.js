(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrint"], factory);
    } else {
        factory(window.OctoPrint);
    }
})(window || this, function(OctoPrint) {
    var baseUrl = "api/groups";

    var url = function() {
        if (arguments.length) {
            return baseUrl + "/" + Array.prototype.join.call(arguments, "/");
        } else {
            return baseUrl;
        }
    };

    OctoPrint.groups = {
        list: function (opts) {
            return OctoPrint.get(url(), opts);
        },

        add: function (group, opts) {
            if (!group.name) {
                throw new OctoPrint.InvalidArgumentError("group's name need to be set");
            }

            var data = {
                name: group.name,
                permissions: group.hasOwnProperty("permissions") ? group.permissions : [],
                defaultOn: group.defaultOn
            };

            return OctoPrint.postJson(url(), data, opts);
        },

        get: function (name, opts) {
            if (!name) {
                throw new OctoPrint.InvalidArgumentError("group name must be set");
            }

            return OctoPrint.get(url(name), opts);
        },

        update: function (name, description, permissions, defaultOn, opts) {
            if (!name) {
                throw new OctoPrint.InvalidArgumentError("group name must be set");
            }

            //

            var data = {
                description: description,
                permissions: permissions,
                defaultOn: defaultOn,
            };
            return OctoPrint.putJson(url(name), data, opts);
        },

        delete: function (name, opts) {
            if (!name) {
                throw new OctoPrint.InvalidArgumentError("group name must be set");
            }

            return OctoPrint.delete(url(name), opts);
        },
    };
});
