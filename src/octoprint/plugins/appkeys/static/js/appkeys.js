$(function() {
    function AppKeysViewModel(parameters) {
        var self = this;
        self.loginState = parameters[0];

        self.keys = new ItemListHelper(
            "plugin.appkeys.keys",
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

    OCTOPRINT_VIEWMODELS.push([
        AppKeysViewModel,
        ["loginStateViewModel"],
        ["#usersettings_plugin_appkeys"]
    ]);
});
