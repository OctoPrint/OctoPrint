(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrint"], factory);
    } else {
        factory(window.OctoPrint);
    }
})(window || this, function(OctoPrint) {
    var baseUrl = "api/users";

    var url = function() {
        if (arguments.length) {
            return baseUrl + "/" + Array.prototype.join.call(arguments, "/");
        } else {
            return baseUrl;
        }
    };

    OctoPrint.users = {
        list: function (opts) {
            return OctoPrint.get(url(), opts);
        },

        add: function (user, opts) {
            if (!user.name || !user.password) {
                throw new OctoPrint.InvalidArgumentError("Both user's name and password need to be set");
            }

            var data = {
                name: user.name,
                password: user.password,
                active: user.hasOwnProperty("active") ? !!user.active : true,
                admin: user.hasOwnProperty("admin") ? !!user.admin : false
            };

            return OctoPrint.postJson(url(), data, opts);
        },

        get: function (name, opts) {
            if (!name) {
                throw new OctoPrint.InvalidArgumentError("user name must be set");
            }

            return OctoPrint.get(url(name), opts);
        },

        update: function (name, active, admin, opts) {
            if (!name) {
                throw new OctoPrint.InvalidArgumentError("user name must be set");
            }

            var data = {
                active: !!active,
                admin: !!admin
            };
            return OctoPrint.putJson(url(name), data, opts);
        },

        delete: function (name, opts) {
            if (!name) {
                throw new OctoPrint.InvalidArgumentError("user name must be set");
            }

            return OctoPrint.delete(url(name), opts);
        },

        changePassword: function (name, password, opts) {
            if (!name || !password) {
                throw new OctoPrint.InvalidArgumentError("user name and password must be set");
            }

            var data = {
                password: password
            };
            return OctoPrint.putJson(url(name, "password"), data, opts);
        },

        generateApiKey: function (name, opts) {
            if (!name) {
                throw new OctoPrint.InvalidArgumentError("user name must be set");
            }

            return OctoPrint.postJson(url(name, "apikey"), opts);
        },

        resetApiKey: function (name, opts) {
            if (!name) {
                throw new OctoPrint.InvalidArgumentError("user name must be set");
            }

            return OctoPrint.delete(url(name, "apikey"), opts);
        },

        getSettings: function (name, opts) {
            if (!name) {
                throw new OctoPrint.InvalidArgumentError("user name must be set");
            }

            return OctoPrint.get(url(name, "settings"), opts);
        },

        saveSettings: function (name, settings, opts) {
            if (!name) {
                throw new OctoPrint.InvalidArgumentError("user name must be set");
            }

            settings = settings || {};
            return OctoPrint.patchJson(url(name, "settings"), settings, opts);
        }
    };
});
