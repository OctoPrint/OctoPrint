$(function() {
    function UserAppKeysViewModel(parameters) {
        var self = this;
        self.loginState = parameters[0];

        self.keys = new ItemListHelper(
            "plugin.appkeys.userkeys",
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
            OctoPrint.plugins.appkeys.getKeys()
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
            return OctoPrint.plugins.appkeys.generateKey(self.editorApp())
                .done(self.requestData);
        };

        self.revokeKey = function(key) {
            return OctoPrint.plugins.appkeys.revokeKey(key)
                .done(self.requestData);
        };

        self.allowApp = function(token) {
            return OctoPrint.plugins.appkeys.decide(token, true)
                .done(self.requestData);
        };

        self.denyApp = function(token) {
            return OctoPrint.plugins.appkeys.decide(token, false)
                .done(self.requestData);
        };

        self.promptForAccess = function(app, token) {
            var message = gettext("\"<strong>%(app)s</strong>\" has requested access to control OctoPrint through the API.");
            message = _.sprintf(message, {app: app});
            message = "<p>" + message + "</p><p>" + gettext("Do you want to allow access to this application with your user account?") + "</p>";
            return new PNotify({
                title: gettext("Access Request"),
                text: message,
                hide: false,
                icon: "fa fa-key",
                confirm: {
                    confirm: true,
                    buttons: [{
                        text: gettext("Allow"),
                        click: function(notice) {
                            self.allowApp(token);
                            notice.remove();
                        }
                    }, {
                        text: gettext("Deny"),
                        click: function(notice) {
                            self.denyApp(token);
                            notice.remove();
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
            if (plugin !== "appkeys") {
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

                if (self.pending[token] !== undefined) {
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

    function AllAppKeysViewModel(parameters) {
        var self = this;
        self.loginState = parameters[0];

        self.keys = new ItemListHelper(
            "plugin.appkeys.allkeys",
            {
                "user": function (a, b) {
                    // sorts ascending
                    if (a["user_id"] > b["user_id"]) return 1;
                    if (a["user_id"] < b["user_id"]) return -1;
                    return 0;
                },
                "app": function (a, b) {
                    // sorts ascending
                    if (a["app"] > b["app"]) return 1;
                    if (a["app"] < b["app"]) return -1;
                    return 0;
                }
            },
            {
            },
            "user",
            [],
            [],
            10
        );

        self.onSettingsShown = function() {
            self.requestData();
        };

        self.onUserLoggedIn = function() {
            self.requestData();
        };

        self.requestData = function() {
            OctoPrint.plugins.appkeys.getAllKeys()
                .done(self.fromResponse);
        };

        self.fromResponse = function(response) {
            self.keys.updateItems(response.keys);
        };

        self.revokeKey = function(key, user) {
            return OctoPrint.plugins.appkeys.revokeKeyFor(key, user)
                .done(self.requestData);
        };

        self.revokeAllForUser = function() {
            var user = self.revokeUsername();
            return OctoPrint.plugins.appkeys.revokeAllForUser(user)
                .done(self.requestData);
        };

        self.revokeAllForApp = function() {
            var app = self.revokeApp();
            return OctoPrint.plugins.appkeys.revokeAlLForApp(app)
                .done(self.requestData);
        };
    }

    OCTOPRINT_VIEWMODELS.push([
        UserAppKeysViewModel,
        ["loginStateViewModel"],
        ["#usersettings_plugin_appkeys"]
    ]);

    OCTOPRINT_VIEWMODELS.push([
        AllAppKeysViewModel,
        ["loginStateViewModel"],
        ["#settings_plugin_appkeys"]
    ])
});
