$(function () {
    function AppKeysDialogViewModel(parameters) {
        var self = this;

        self.dialog = undefined;

        self.onStartup = function () {
            self.dialog = $("#plugin_appkeys_keygenerated");
        };

        self.showDialog = function (title, data) {
            if (self.dialog === undefined) return;

            var qrcode = {
                text: data.api_key,
                size: 180,
                fill: "#000",
                background: null,
                label: "",
                fontname: "sans",
                fontcolor: "#000",
                radius: 0,
                ecLevel: "L"
            };

            self.dialog.find("#plugin_appkeys_keygenerated_title").text(title);
            self.dialog.find("#plugin_appkeys_keygenerated_user").text(data.user_id);
            self.dialog.find("#plugin_appkeys_keygenerated_app").text(data.app_id);
            self.dialog.find("#plugin_appkeys_keygenerated_key_text").text(data.api_key);
            self.dialog
                .find("#plugin_appkeys_keygenerated_key_copy")
                .off()
                .click(function () {
                    copyToClipboard(data.api_key);
                });
            self.dialog
                .find("#plugin_appkeys_keygenerated_key_qrcode")
                .empty()
                .qrcode(qrcode);

            self.dialog.modal("show");
        };
    }

    function UserAppKeysViewModel(parameters) {
        var self = this;
        self.dialog = parameters[0];
        self.loginState = parameters[1];

        self.keys = new ItemListHelper(
            "plugin.appkeys.userkeys",
            {
                app: function (a, b) {
                    // sorts ascending
                    if (a["app_id"].toLowerCase() < b["app_id"].toLowerCase()) return -1;
                    if (a["app_id"].toLowerCase() > b["app_id"].toLowerCase()) return 1;
                    return 0;
                }
            },
            {},
            "app",
            [],
            [],
            5
        );
        self.pending = {};
        self.openRequests = {};

        self.editorApp = ko.observable();

        self.requestData = function () {
            OctoPrint.plugins.appkeys.getKeys().done(self.fromResponse);
        };

        self.fromResponse = function (response) {
            self.keys.updateItems(response.keys);
            self.pending = response.pending;
            _.each(self.pending, function (data, token) {
                self.openRequests[token] = self.promptForAccess(data.app_id, token);
            });
        };

        self.generateKey = function () {
            return OctoPrint.plugins.appkeys
                .generateKey(self.editorApp())
                .done(self.requestData)
                .done(function () {
                    self.editorApp("");
                });
        };

        self.revokeKey = function (key) {
            var perform = function () {
                OctoPrint.plugins.appkeys.revokeKey(key).done(self.requestData);
            };

            showConfirmationDialog(
                _.sprintf(
                    gettext('You are about to revoke the application key "%(key)s".'),
                    {key: _.escape(key)}
                ),
                perform
            );
        };

        self.allowApp = function (token) {
            return OctoPrint.plugins.appkeys.decide(token, true).done(self.requestData);
        };

        self.denyApp = function (token) {
            return OctoPrint.plugins.appkeys.decide(token, false).done(self.requestData);
        };

        self.promptForAccess = function (app, token) {
            var message = gettext(
                '"<strong>%(app)s</strong>" has requested access to control OctoPrint through the API.'
            );
            message = _.sprintf(message, {app: _.escape(app)});
            message =
                "<p>" +
                message +
                "</p><p>" +
                gettext(
                    "Do you want to allow access to this application with your user account?"
                ) +
                "</p>";
            return new PNotify({
                title: gettext("Access Request"),
                text: message,
                hide: false,
                icon: "fa fa-key",
                confirm: {
                    confirm: true,
                    buttons: [
                        {
                            text: gettext("Allow"),
                            click: function (notice) {
                                self.allowApp(token);
                                notice.remove();
                            }
                        },
                        {
                            text: gettext("Deny"),
                            click: function (notice) {
                                self.denyApp(token);
                                notice.remove();
                            }
                        }
                    ]
                },
                buttons: {
                    sticker: false,
                    closer: false
                }
            });
        };

        self.onUserSettingsShown = function () {
            self.requestData();
        };

        self.onUserLoggedIn = function () {
            self.requestData();
        };

        self.onDataUpdaterPluginMessage = function (plugin, data) {
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
                    delete self.openRequests[token];
                }
            }
        };
    }

    function AllAppKeysViewModel(parameters) {
        var self = this;
        self.dialog = parameters[0];
        self.loginState = parameters[1];
        self.access = parameters[2];

        self.keys = new ItemListHelper(
            "plugin.appkeys.allkeys",
            {
                user_app: function (a, b) {
                    // sorts ascending, first by user, then by app
                    if (a["user_id"] > b["user_id"]) return 1;
                    if (a["user_id"] < b["user_id"]) return -1;

                    if (a["app_id"].toLowerCase() > b["app_id"].toLowerCase()) return 1;
                    if (a["app_id"].toLowerCase() < b["app_id"].toLowerCase()) return -1;

                    return 0;
                }
            },
            {},
            "user_app",
            [],
            [],
            10
        );
        self.users = ko.observableArray([]);
        self.apps = ko.observableArray([]);

        self.editorApp = ko.observable();
        self.editorUser = ko.observable();

        self.markedForDeletion = ko.observableArray([]);

        self.onSettingsShown = function () {
            self.requestData();
            self.editorUser(self.loginState.username());
            self.editorApp("");
        };

        self.onUserLoggedIn = function () {
            self.requestData();
            self.editorUser(self.loginState.username());
            self.editorApp("");
        };

        self.requestData = function () {
            OctoPrint.plugins.appkeys.getAllKeys().done(self.fromResponse);
        };

        self.fromResponse = function (response) {
            self.keys.updateItems(response.keys);

            var users = [];
            var apps = [];
            _.each(response.keys, function (key) {
                users.push(key.user_id);
                apps.push(key.app_id.toLowerCase());
            });

            users = _.uniq(users);
            users.sort();
            self.users(users);

            apps = _.uniq(apps);
            apps.sort();
            self.apps(apps);
        };

        self.generateKey = function () {
            return OctoPrint.plugins.appkeys
                .generateKeyForUser(self.editorUser(), self.editorApp())
                .done(self.requestData)
                .done(function () {
                    self.editorUser(self.loginState.username());
                    self.editorApp("");
                })
                .done(function (data) {
                    self.dialog.showDialog(gettext("New key generated!"), data);
                });
        };

        self.revokeKey = function (key) {
            var perform = function () {
                OctoPrint.plugins.appkeys.revokeKey(key).done(self.requestData);
            };

            showConfirmationDialog(
                _.sprintf(
                    gettext('You are about to revoke the application key "%(key)s".'),
                    {key: _.escape(key)}
                ),
                perform
            );
        };

        self.revokeMarked = function () {
            var perform = function () {
                self._bulkRevoke(self.markedForDeletion()).done(function () {
                    self.markedForDeletion.removeAll();
                });
            };

            showConfirmationDialog(
                _.sprintf(
                    gettext("You are about to revoke %(count)d application keys."),
                    {count: self.markedForDeletion().length}
                ),
                perform
            );
        };

        self.markAllOnPageForDeletion = function () {
            self.markedForDeletion(
                _.uniq(
                    self
                        .markedForDeletion()
                        .concat(_.map(self.keys.paginatedItems(), "api_key"))
                )
            );
        };

        self.markAllForDeletion = function () {
            self.markedForDeletion(_.uniq(_.map(self.keys.allItems, "api_key")));
        };

        self.markAllByUserForDeletion = function (user) {
            self.markAllByFilterForDeletion(function (e) {
                return e.user_id === user;
            });
        };

        self.markAllByAppForDeletion = function (app) {
            self.markAllByFilterForDeletion(function (e) {
                return e.app_id.toLowerCase() === app;
            });
        };

        self.markAllByFilterForDeletion = function (filter) {
            self.markedForDeletion(
                _.uniq(
                    self
                        .markedForDeletion()
                        .concat(_.map(_.filter(self.keys.allItems, filter), "api_key"))
                )
            );
        };

        self.clearMarked = function () {
            self.markedForDeletion.removeAll();
        };

        self._bulkRevoke = function (keys) {
            var title, message, handler;

            title = gettext("Revoking application keys");
            message = _.sprintf(gettext("Revoking %(count)d application keys..."), {
                count: keys.length
            });
            handler = function (key) {
                return OctoPrint.plugins.appkeys
                    .revokeKey(key)
                    .done(function () {
                        deferred.notify(
                            _.sprintf(gettext("Revoked %(key)s..."), {
                                key: _.escape(key)
                            }),
                            true
                        );
                    })
                    .fail(function (jqXHR) {
                        var short = _.sprintf(
                            gettext("Revocation of %(key)s failed, continuing..."),
                            {key: _.escape(key)}
                        );
                        var long = _.sprintf(
                            gettext("Deletion of %(key)s failed: %(error)s"),
                            {key: _.escape(key), error: _.escape(jqXHR.responseText)}
                        );
                        deferred.notify(short, long, false);
                    });
            };

            var deferred = $.Deferred();

            var promise = deferred.promise();

            var options = {
                title: title,
                message: message,
                max: keys.length,
                output: true
            };
            showProgressModal(options, promise);

            var requests = [];
            _.each(keys, function (key) {
                var request = handler(key);
                requests.push(request);
            });
            $.when.apply($, _.map(requests, wrapPromiseWithAlways)).done(function () {
                deferred.resolve();
                self.requestData();
            });

            return promise;
        };
    }

    OCTOPRINT_VIEWMODELS.push([AppKeysDialogViewModel, [], []]);

    OCTOPRINT_VIEWMODELS.push([
        UserAppKeysViewModel,
        ["appKeysDialogViewModel", "loginStateViewModel"],
        ["#usersettings_plugin_appkeys"]
    ]);

    OCTOPRINT_VIEWMODELS.push([
        AllAppKeysViewModel,
        ["appKeysDialogViewModel", "loginStateViewModel", "accessViewModel"],
        ["#settings_plugin_appkeys"]
    ]);
});
