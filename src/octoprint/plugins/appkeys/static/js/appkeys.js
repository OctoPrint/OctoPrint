$(function () {
    function AppKeysDialogViewModel(parameters) {
        var self = this;

        self.dialog = undefined;

        self.onStartup = function () {
            self.dialog = $("#plugin_appkeys_keygenerated");
            self.dialog.on("hidden", () => {
                self.resetDialog();
            });
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

        self.resetDialog = () => {
            if (self.dialog === undefined) return;

            self.dialog.find("#plugin_appkeys_keygenerated_title").text("");
            self.dialog.find("#plugin_appkeys_keygenerated_user").text("");
            self.dialog.find("#plugin_appkeys_keygenerated_app").text("");
            self.dialog.find("#plugin_appkeys_keygenerated_key_text").text("");
            self.dialog.find("#plugin_appkeys_keygenerated_key_copy").off();
            self.dialog.find("#plugin_appkeys_keygenerated_key_qrcode").empty();
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
            return OctoPrint.plugins.appkeys.getKeys().done(self.fromResponse);
        };

        self.fromResponse = function (response) {
            self.keys.updateItems(response.keys);
            self.pending = response.pending;
            _.each(self.pending, function (data, token) {
                self.openRequests[token] = self.promptForAccess(data.app_id, token);
            });
        };

        self.generateKey = function () {
            self.loginState.reauthenticateIfNecessary(() => {
                OctoPrint.plugins.appkeys
                    .generateKey(self.editorApp())
                    .done(self.requestData)
                    .done(function () {
                        self.editorApp("");
                    });
            });
        };

        self.revokeKey = (data) => {
            const app = data.app_id;

            self.loginState.reauthenticateIfNecessary(() => {
                showConfirmationDialog(
                    _.sprintf(
                        gettext(
                            "You are about to revoke the application key for %(app)s."
                        ),
                        {app: _.escape(app)}
                    ),
                    () => {
                        OctoPrint.plugins.appkeys
                            .revokeKeyForApp(app)
                            .done(self.requestData);
                    }
                );
            });
        };

        self.showKeyDetails = (data) => {
            self.loginState.reauthenticateIfNecessary(() => {
                OctoPrint.plugins.appkeys.getKey(data.app_id).done((response) => {
                    self.dialog.showDialog(gettext("Details"), response.key);
                });
            });
        };

        self.allowApp = function (token) {
            return OctoPrint.plugins.appkeys.decide(token, true).done(self.requestData);
        };

        self.denyApp = function (token) {
            return OctoPrint.plugins.appkeys.decide(token, false).done(self.requestData);
        };

        self.promptForAccess = function (app, remote_address, token) {
            var message = gettext(
                'A client identifying itself as "<strong>%(app)s</strong>" has requested access to control OctoPrint through the API. The request originates from <code>%(remote_address)s</code>.'
            );
            message = _.sprintf(message, {
                app: _.escape(app),
                remote_address: _.escape(remote_address)
            });
            message =
                "<p>" +
                message +
                "</p><p>" +
                gettext(
                    "Do you want to give this client access with your user account?"
                ) +
                "</p><p><strong>" +
                gettext(
                    "This will allow this client to fully act on your behalf! Make absolutely sure you trust this client and understand why it requested access!"
                ) +
                "</strong></p>";
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
                                self.loginState.reauthenticateIfNecessary(() => {
                                    self.allowApp(token);
                                    notice.remove();
                                });
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
                remote_address = data.remote_address;

                if (user && user !== self.loginState.username()) {
                    return;
                }

                if (self.pending[token] !== undefined) {
                    return;
                }

                self.openRequests[token] = self.promptForAccess(
                    app,
                    remote_address,
                    token
                );
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
            return OctoPrint.plugins.appkeys.getAllKeys().done(self.fromResponse);
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

        self.showKeyDetails = (data) => {
            self.loginState.reauthenticateIfNecessary(() => {
                OctoPrint.plugins.appkeys
                    .getKey(data.app_id, data.user_id)
                    .done((response) => {
                        self.dialog.showDialog(gettext("Details"), response.key);
                    });
            });
        };

        self.generateKey = function () {
            self.loginState.reauthenticateIfNecessary(() => {
                OctoPrint.plugins.appkeys
                    .generateKeyForUser(self.editorUser(), self.editorApp())
                    .done(self.requestData)
                    .done(function () {
                        self.editorUser(self.loginState.username());
                        self.editorApp("");
                    })
                    .done(function (data) {
                        self.dialog.showDialog(gettext("New key generated!"), data);
                    });
            });
        };

        self.revokeKey = function (data) {
            const app = data.app_id;
            const user = data.user_id;

            showConfirmationDialog(
                _.sprintf(
                    gettext(
                        "You are about to revoke the application key for %(app)s for user %(user)s."
                    ),
                    {app: _.escape(app), user: _.escape(user)}
                ),
                () => {
                    self.loginState.reauthenticateIfNecessary(() => {
                        OctoPrint.plugins.appkeys
                            .revokeKeyForApp(app, user)
                            .done(self.requestData);
                    });
                }
            );
        };

        self.revokeMarked = function () {
            showConfirmationDialog(
                _.sprintf(
                    gettext("You are about to revoke %(count)d application keys."),
                    {count: self.markedForDeletion().length}
                ),
                () => {
                    self.loginState.forceReauthentication(() => {
                        self._bulkRevoke(self.markedForDeletion()).done(() => {
                            self.markedForDeletion.removeAll();
                        });
                    });
                }
            );
        };

        self.markAllOnPageForDeletion = function () {
            self.markedForDeletion(
                _.uniq(
                    self
                        .markedForDeletion()
                        .concat(
                            _.map(
                                self.keys.paginatedItems(),
                                (item) => `${item.user_id}:${item.app_id}`
                            )
                        )
                )
            );
        };

        self.markAllForDeletion = function () {
            self.markedForDeletion(
                _.uniq(
                    _.map(self.keys.allItems, (item) => `${item.user_id}:${item.app_id}`)
                )
            );
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
                        .concat(
                            _.map(
                                _.filter(self.keys.allItems, filter),
                                (item) => `${item.user_id}:${item.app_id}`
                            )
                        )
                )
            );
        };

        self.clearMarked = function () {
            self.markedForDeletion.removeAll();
        };

        self._bulkRevoke = function (keys) {
            /*
             * TODO: This still has a risk of running into reauthentication for REALLY large numbers of keys
             * whose bulk removal takes longer than the reauthentication timeout.
             */

            var title, message, handler;

            title = gettext("Revoking application keys");
            message = _.sprintf(gettext("Revoking %(count)d application keys..."), {
                count: keys.length
            });
            handler = function (id) {
                const [user, app] = rsplit(id, ":", 1);
                return OctoPrint.plugins.appkeys
                    .revokeKeyForApp(app, user)
                    .done(function () {
                        deferred.notify(
                            _.sprintf(gettext("Revoked %(app)s for %(user)s..."), {
                                app: _.escape(app),
                                user: _.escape(user)
                            }),
                            true
                        );
                    })
                    .fail(function (jqXHR) {
                        var short = _.sprintf(
                            gettext(
                                "Revocation of %(app)s for user %(user)s failed, continuing..."
                            ),
                            {
                                app: _.escape(app),
                                user: _.escape(user)
                            }
                        );
                        var long = _.sprintf(
                            gettext(
                                "Deletion of %(app)s for user %(user)s failed: %(error)s"
                            ),
                            {
                                app: _.escape(app),
                                user: _.escape(user),
                                error: _.escape(jqXHR.responseText)
                            }
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
