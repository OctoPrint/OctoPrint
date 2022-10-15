$(function () {
    function CoreWizardAclViewModel(parameters) {
        var self = this;

        self.loginStateViewModel = parameters[0];

        self.username = ko.observable(undefined);
        self.password = ko.observable(undefined);
        self.confirmedPassword = ko.observable(undefined);

        self.setup = ko.observable(false);

        self.required = false;

        self.passwordMismatch = ko.pureComputed(function () {
            return self.password() !== self.confirmedPassword();
        });

        self.providedUsername = ko.pureComputed(function () {
            return self.username() && self.username().trim();
        });

        self.validUsername = ko.pureComputed(function () {
            return !self.username() || self.username() == self.username().trim();
        });

        self.validPassword = ko.pureComputed(function () {
            return self.password() && self.password().trim() !== "";
        });

        self.validData = ko.pureComputed(function () {
            return (
                self.providedUsername() &&
                self.validUsername() &&
                !self.passwordMismatch() &&
                self.validPassword()
            );
        });

        self.createAccount = function () {
            if (!self.validData()) return;

            var data = {
                user: self.username(),
                pass1: self.password(),
                pass2: self.confirmedPassword()
            };
            self._sendData(data);
        };

        self._sendData = function (data, callback) {
            OctoPrint.postJson("plugin/corewizard/acl", data).done(function () {
                self.setup(true);

                // we now log the user in
                var user = data.user;
                var pass = data.pass1;
                self.loginStateViewModel.login(user, pass, true).done(function () {
                    if (callback) callback();
                });
            });
        };

        self._showDecisionNeededDialog = function () {
            showMessageDialog({
                title: gettext("Please set up Access Control"),
                message: gettext(
                    "You haven't yet set up access control. You need to setup a " +
                        'username and password and click "Create Account" before ' +
                        "continuing."
                )
            });
        };

        self.onBeforeWizardTabChange = function (next, current) {
            if (!self.required) return true;

            if (
                !current ||
                !_.startsWith(current, "wizard_plugin_corewizard_acl_") ||
                self.setup()
            ) {
                return true;
            }

            self._showDecisionNeededDialog();
            return false;
        };

        self.onBeforeWizardFinish = function () {
            if (!self.required) return true;

            if (self.setup()) return true;

            self._showDecisionNeededDialog();
            return false;
        };

        self.onWizardDetails = function (response) {
            self.required =
                response &&
                response.corewizard &&
                response.corewizard.details &&
                response.corewizard.details.acl &&
                response.corewizard.details.acl.required;
        };
    }

    function CoreWizardWebcamViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0];

        self.required = false;

        self.onWizardDetails = function (response) {
            self.required =
                response &&
                response.corewizard &&
                response.corewizard.details &&
                response.corewizard.details.webcam &&
                response.corewizard.details.webcam.required;
        };

        self.onWizardFinish = function () {
            if (!self.required) return;
            if (
                self.settingsViewModel.webcam_streamUrl() ||
                (self.settingsViewModel.webcam_snapshotUrl() &&
                    self.settingsViewModel.webcam_ffmpegPath())
            ) {
                return "reload";
            }
        };
    }

    function CoreWizardServerCommandsViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0];
    }

    function CoreWizardOnlineCheckViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0];

        self.setup = ko.observable(false);

        self.decision = ko.observable();
        self.required = false;
        self.active = false;

        self.enableOnlineCheck = function () {
            self.settingsViewModel.server_onlineCheck_enabled(true);
            self.decision(true);
            self._sendData();
        };

        self.disableOnlineCheck = function () {
            self.settingsViewModel.server_onlineCheck_enabled(false);
            self.decision(false);
            self._sendData();
        };

        self.onBeforeWizardTabChange = function (next, current) {
            if (!self.required) return true;

            if (
                !current ||
                !_.startsWith(current, "wizard_plugin_corewizard_onlinecheck_") ||
                self.setup()
            ) {
                return true;
            }

            self._showDecisionNeededDialog();
            return false;
        };

        self.onBeforeWizardFinish = function () {
            if (!self.required) return true;

            if (self.setup()) {
                return true;
            }

            self._showDecisionNeededDialog();
            return false;
        };

        self.onWizardDetails = function (response) {
            self.required =
                response &&
                response.corewizard &&
                response.corewizard.details &&
                response.corewizard.details.onlinecheck &&
                response.corewizard.details.onlinecheck.required;
        };

        self._showDecisionNeededDialog = function () {
            showMessageDialog({
                title: gettext("Please set up the online connectivity check"),
                message: gettext(
                    "You haven't yet decided on whether to enable or disable the online connectivity check. You need to either enable or disable it before continuing."
                )
            });
        };

        self._sendData = function () {
            var data = {
                server: {
                    onlineCheck: {
                        enabled: self.settingsViewModel.server_onlineCheck_enabled(),
                        interval: self.settingsViewModel.server_onlineCheck_interval(),
                        host: self.settingsViewModel.server_onlineCheck_host(),
                        port: self.settingsViewModel.server_onlineCheck_port()
                    }
                }
            };

            self.active = true;
            self.settingsViewModel.saveData(data).done(function () {
                self.setup(true);
                self.active = false;
            });
        };
    }

    function CoreWizardPluginBlacklistViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0];

        self.setup = ko.observable(false);

        self.decision = ko.observable();
        self.required = false;
        self.active = false;

        self.enablePluginBlacklist = function () {
            self.settingsViewModel.server_pluginBlacklist_enabled(true);
            self.decision(true);
            self._sendData();
        };

        self.disablePluginBlacklist = function () {
            self.settingsViewModel.server_pluginBlacklist_enabled(false);
            self.decision(false);
            self._sendData();
        };

        self.onBeforeWizardTabChange = function (next, current) {
            if (!self.required) return true;

            if (
                !current ||
                !_.startsWith(current, "wizard_plugin_corewizard_pluginblacklist_") ||
                self.setup()
            ) {
                return true;
            }

            self._showDecisionNeededDialog();
            return false;
        };

        self.onBeforeWizardFinish = function () {
            if (!self.required) return true;

            if (self.setup()) {
                return true;
            }

            self._showDecisionNeededDialog();
            return false;
        };

        self.onWizardDetails = function (response) {
            self.required =
                response &&
                response.corewizard &&
                response.corewizard.details &&
                response.corewizard.details.pluginblacklist &&
                response.corewizard.details.pluginblacklist.required;
        };

        self._showDecisionNeededDialog = function () {
            showMessageDialog({
                title: gettext("Please set up the plugin blacklist processing"),
                message: gettext(
                    "You haven't yet decided on whether to enable or disable the plugin blacklist processing. You need to either enable or disable it before continuing."
                )
            });
        };

        self._sendData = function () {
            var data = {
                server: {
                    pluginBlacklist: {
                        enabled: self.settingsViewModel.server_pluginBlacklist_enabled()
                    }
                }
            };

            self.active = true;
            self.settingsViewModel.saveData(data).done(function () {
                self.setup(true);
                self.active = false;
            });
        };
    }

    function CoreWizardPrinterProfileViewModel(parameters) {
        var self = this;

        self.printerProfiles = parameters[0];

        self.required = false;

        self.editor = self.printerProfiles.createProfileEditor();
        self.editorLoaded = ko.observable(false);

        self.onWizardDetails = function (response) {
            self.required =
                response &&
                response.corewizard &&
                response.corewizard.details &&
                response.corewizard.details.printerprofile &&
                response.corewizard.details.printerprofile.required;
            if (!self.required) return;

            OctoPrint.printerprofiles
                .get("_default")
                .done(function (data) {
                    self.editor.fromProfileData(data);
                    self.editorLoaded(true);
                })
                .fail(function () {
                    self.editor.fromProfileData();
                    self.editorLoaded(true);
                });
        };

        self.onWizardFinish = function () {
            if (!self.required) return;

            OctoPrint.printerprofiles
                .update("_default", self.editor.toProfileData())
                .done(function () {
                    self.printerProfiles.requestData();
                });
        };
    }

    OCTOPRINT_VIEWMODELS.push(
        {
            construct: CoreWizardAclViewModel,
            dependencies: ["loginStateViewModel"],
            elements: ["#wizard_plugin_corewizard_acl"]
        },
        {
            construct: CoreWizardWebcamViewModel,
            dependencies: ["settingsViewModel"],
            elements: ["#wizard_plugin_corewizard_webcam"]
        },
        {
            construct: CoreWizardServerCommandsViewModel,
            dependencies: ["settingsViewModel"],
            elements: ["#wizard_plugin_corewizard_servercommands"]
        },
        {
            construct: CoreWizardOnlineCheckViewModel,
            dependencies: ["settingsViewModel"],
            elements: ["#wizard_plugin_corewizard_onlinecheck"]
        },
        {
            construct: CoreWizardPluginBlacklistViewModel,
            dependencies: ["settingsViewModel"],
            elements: ["#wizard_plugin_corewizard_pluginblacklist"]
        },
        {
            construct: CoreWizardPrinterProfileViewModel,
            dependencies: ["printerProfilesViewModel"],
            elements: ["#wizard_plugin_corewizard_printerprofile"]
        }
    );
});
