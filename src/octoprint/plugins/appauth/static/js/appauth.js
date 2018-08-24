(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function(OctoPrintClient) {
    var OctoPrintAppAuthClient = function(base) {
        this.base = base;
    };

    OctoPrintAppAuthClient.prototype.getKeys = function(opts) {
        return this.base.simpleApiGet("appauth", opts);
    };

    OctoPrintAppAuthClient.prototype.generateKey = function(app, opts) {
        return this.base.simpleApiCommand("appauth", "generate", {"app": app}, opts);
    };

    OctoPrintAppAuthClient.prototype.revokeKey = function(key, opts) {
        return this.base.simpleApiCommand("appauth", "revoke", {"key": key}, opts);
    };

    OctoPrintAppAuthClient.prototype.decide = function(token, decision, opts) {
        return this.base.postJson(this.base.getBlueprintUrl("appauth") + "decision/" + token, {decision: !!decision}, opts);
    };

    OctoPrintClient.registerPluginComponent("appauth", OctoPrintAppAuthClient);
    return OctoPrintAppAuthClient;
});

$(function() {
    function AppAuthViewModel(parameters) {
        var self = this;
        self.loginState = parameters[0];

        self.keys = new ItemListHelper(
            "plugin.appauth.keys",
            {
                "app": function (a, b) {
                    // sorts descending
                    if (a["app"] > b["app"]) return -1;
                    if (a["app"] < b["app"]) return 1;
                    return 0;
                }
            },
            {
            },
            "app",
            [],
            [],
            10
        );
        self.pending = {};
        self.openRequests = {};

        self.editorApp = ko.observable();

        self.requestData = function() {
            OctoPrint.plugins.appauth.getKeys()
                .done(self.fromResponse);
        };

        self.fromResponse = function(response) {
            self.keys.updateItems(response.keys);
            self.pending = response.pending;
            _.each(self.pending, function(data, token) {
                self.openRequests[token] = self.promptForAccess(data.app_id, token);
            })
        };

        self.generateKey = function() {
            return OctoPrint.plugins.appauth.generateKey(self.editorApp())
                .done(self.requestData);
        };

        self.revokeKey = function(key) {
            return OctoPrint.plugins.appauth.revokeKey(key)
                .done(self.requestData);
        };

        self.allowApp = function(token) {
            return OctoPrint.plugins.appauth.decide(token, true)
                .done(self.requestData);
        };

        self.denyApp = function(token) {
            return OctoPrint.plugins.appauth.decide(token, false)
                .done(self.requestData);
        };

        self.promptForAccess = function(app, token) {
            var message = gettext("\"%(app)s\" has requested access to control OctoPrint through the API. Do you want to allow access to this application with your user account?");
            message = _.sprintf(message, {app: app});

            return new PNotify({
                title: gettext("Access Request"),
                text: message,
                confirm: {
                    confirm: true,
                    buttons: [{
                        text: gettext("Allow"),
                        click: function(notice) {
                            self.allowApp(token);
                        }
                    }, {
                        text: gettext("Deny"),
                        click: function(notice) {
                            self.denyApp(token);
                        }
                    }]
                },
                buttons: {
                    sticker: false,
                    closer: false
                }
            });
        };

        self.onUserSettingsShown = function() {
            self.requestData();
        };

        self.onUserLoggedIn = function() {
            self.requestData();
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin !== "appauth") {
                return;
            }

            var app, token, user;

            if (data.type === "request_access" && self.loginState.isUser()) {
                app = data.app_name;
                token = data.user_token;
                user = data.user_id;

                if (user && user !== self.loginState.username()) {
                    return;
                }

                if (self.pending[token] === undefined) {
                    return;
                }

                self.openRequests[token] = self.promptForAccess(app, token);

            } else if (data.type === "end_request") {
                token = data.user_token;

                if (self.openRequests[token] !== undefined) {
                    // another instance responded to the access request before the current user did
                    if (self.openRequests[token].state !== "closed") {
                        self.openRequests[token].remove();
                    }
                    delete self.openRequests[token]
                }
            }
        };
    }

    OCTOPRINT_VIEWMODELS.push([
        AppAuthViewModel,
        ["loginStateViewModel"],
        ["#usersettings_plugin_appauth"]
    ]);
});
