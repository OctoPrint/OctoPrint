$(function () {
    function UserSettingsViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.access = parameters[1];

        self.users = self.access.users;

        self.userSettingsDialog = undefined;

        var auto_locale = {
            language: "_default",
            display: gettext("Site default"),
            english: undefined
        };
        self.locales = ko.observableArray(
            [auto_locale].concat(
                _.sortBy(_.values(AVAILABLE_LOCALES), function (n) {
                    return n.display;
                })
            )
        );
        self.locale_languages = _.keys(AVAILABLE_LOCALES);

        self.access_password = ko.observable(undefined);
        self.access_repeatedPassword = ko.observable(undefined);
        self.access_currentPassword = ko.observable(undefined);
        self.access_currentPasswordMismatch = ko.observable(false);
        self.access_apikey = ko.observable(undefined);
        self.interface_language = ko.observable(undefined);

        self.apiKeyVisible = ko.observable(false);
        self.revealingApiKey = ko.observable(false);

        self.currentUser = ko.observable(undefined);
        self.currentUser.subscribe(function (newUser) {
            self.access_password(undefined);
            self.access_repeatedPassword(undefined);
            self.access_currentPassword(undefined);
            self.access_currentPasswordMismatch(false);
            self.access_apikey(undefined);
            self.interface_language("_default");

            if (newUser !== undefined) {
                self.access_apikey(newUser.apikey);
                if (
                    newUser.settings.hasOwnProperty("interface") &&
                    newUser.settings.interface.hasOwnProperty("language")
                ) {
                    self.interface_language(newUser.settings.interface.language);
                }
            }
        });
        self.access_currentPassword.subscribe(function () {
            self.access_currentPasswordMismatch(false);
        });

        self.passwordMismatch = ko.pureComputed(function () {
            return self.access_password() !== self.access_repeatedPassword();
        });

        self.show = (user) => {
            if (!CONFIG_ACCESS_CONTROL) return;

            if (user === undefined) {
                user = self.loginState.currentUser();
            }

            // make sure we have the current user data, see #2534
            self.requestData(user.name)
                .done(() => {
                    self.userSettingsDialog.modal("show");
                })
                .fail(() => {
                    log.warn(
                        "Could not fetch current user data, proceeding with client side data copy"
                    );
                    self.fromResponse(user);
                });
        };

        self.requestData = (name) => {
            if (name === undefined && self.currentUser() === undefined) return;
            if (name === undefined) {
                name = self.currentUser().name;
            }

            return OctoPrint.access.users.get(name).done((data) => {
                self.fromResponse(data);
            });
        };

        self.fromResponse = (data) => {
            self.currentUser(data);

            // this should only ever return true if we triggered the request through the "reveal api key" button
            self.apiKeyVisible(self.revealingApiKey());
        };

        self.save = function () {
            if (!CONFIG_ACCESS_CONTROL) return;

            self.userSettingsDialog.trigger("beforeSave");

            function saveSettings() {
                var settings = {
                    interface: {
                        language: self.interface_language()
                    }
                };
                self.updateSettings(self.currentUser().name, settings).done(function () {
                    // close dialog
                    self.currentUser(undefined);
                    self.userSettingsDialog.modal("hide");
                    self.loginState.reloadUser();
                });
            }

            if (self.access_password() && !self.passwordMismatch()) {
                self.users
                    .updatePassword(
                        self.currentUser().name,
                        self.access_password(),
                        self.access_currentPassword()
                    )
                    .done(function () {
                        saveSettings();
                    })
                    .fail(function (xhr) {
                        if (xhr.status === 403) {
                            self.access_currentPasswordMismatch(true);
                        }
                    });
            } else {
                saveSettings();
            }
        };

        self.copyApikey = function () {
            copyToClipboard(self.access_apikey());
        };

        self.generateApikey = function () {
            if (!CONFIG_ACCESS_CONTROL) return;

            const generate = () => {
                self.loginState.reauthenticateIfNecessary(() => {
                    self.users
                        .generateApikey(self.currentUser().name)
                        .done((response) => {
                            self.access_apikey(response.apikey);
                        });
                });
            };

            if (self.access_apikey()) {
                showConfirmationDialog(
                    gettext(
                        "This will generate a new API Key. The old API Key will cease to function immediately."
                    ),
                    generate
                );
            } else {
                generate();
            }
        };

        self.deleteApikey = function () {
            if (!CONFIG_ACCESS_CONTROL) return;
            if (!self.access_apikey()) return;

            showConfirmationDialog(
                gettext(
                    "This will delete the API Key. It will cease to to function immediately."
                ),
                () => {
                    self.loginState.reauthenticateIfNecessary(() => {
                        self.users.deleteApikey(self.currentUser().name).done(() => {
                            self.access_apikey(undefined);
                        });
                    });
                }
            );
        };

        self.revealApiKey = () => {
            self.loginState.reauthenticateIfNecessary(() => {
                self.revealingApiKey(true);
                self.requestData(self.currentUser().name).always(() => {
                    self.revealingApiKey(false);
                });
            });
        };

        self.updateSettings = function (username, settings) {
            return OctoPrint.access.users.saveSettings(username, settings);
        };

        self.saveEnabled = function () {
            return !self.passwordMismatch();
        };

        self.onStartup = function () {
            self.userSettingsDialog = $("#usersettings_dialog");
        };

        self.onAllBound = function (allViewModels) {
            self.userSettingsDialog.on("show", function () {
                callViewModels(allViewModels, "onUserSettingsShown");
            });
            self.userSettingsDialog.on("hidden", function () {
                callViewModels(allViewModels, "onUserSettingsHidden");
            });
            self.userSettingsDialog.on("beforeSave", function () {
                callViewModels(allViewModels, "onUserSettingsBeforeSave");
            });
        };

        self.onUserCredentialsOutdated = () => {
            self.apiKeyVisible(false);
            self.requestData();
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: UserSettingsViewModel,
        dependencies: ["loginStateViewModel", "accessViewModel"],
        elements: ["#usersettings_dialog"]
    });
});
