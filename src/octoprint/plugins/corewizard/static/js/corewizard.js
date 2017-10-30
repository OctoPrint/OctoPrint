$(function() {
    function CoreWizardAclViewModel(parameters) {
        var self = this;

        self.loginStateViewModel = parameters[0];

        self.username = ko.observable(undefined);
        self.password = ko.observable(undefined);
        self.confirmedPassword = ko.observable(undefined);

        self.setup = ko.observable(false);
        self.decision = ko.observable();

        self.required = false;

        self.passwordMismatch = ko.pureComputed(function() {
            return self.password() != self.confirmedPassword();
        });

        self.validUsername = ko.pureComputed(function() {
            return self.username() && self.username().trim() != "";
        });

        self.validPassword = ko.pureComputed(function() {
            return self.password() && self.password().trim() != "";
        });

        self.validData = ko.pureComputed(function() {
            return !self.passwordMismatch() && self.validUsername() && self.validPassword();
        });

        self.keepAccessControl = function() {
            if (!self.validData()) return;

            var data = {
                "ac": true,
                "user": self.username(),
                "pass1": self.password(),
                "pass2": self.confirmedPassword()
            };
            self._sendData(data);
        };

        self.disableAccessControl = function() {
            var message = gettext("If you disable Access Control <strong>and</strong> your OctoPrint installation is accessible from the internet, your printer <strong>will be accessible by everyone - that also includes the bad guys!</strong>");
            showConfirmationDialog({
                message: message,
                onproceed: function (e) {
                    var data = {
                        "ac": false
                    };
                    self._sendData(data);
                }
            });
        };

        self._sendData = function(data, callback) {
            OctoPrint.postJson("plugin/corewizard/acl", data)
                .done(function() {
                    self.setup(true);
                    self.decision(data.ac);
                    if (data.ac) {
                        // we now log the user in
                        var user = data.user;
                        var pass = data.pass1;
                        self.loginStateViewModel.login(user, pass, true)
                            .done(function() {
                                if (callback) callback();
                            });
                    } else {
                        if (callback) callback();
                    }
                });
        };

        self.onBeforeWizardTabChange = function(next, current) {
            if (!self.required) return true;

            if (!current || !_.startsWith(current, "wizard_plugin_corewizard_acl_") || self.setup()) {
                return true;
            }
            showMessageDialog({
                title: gettext("Please set up Access Control"),
                message: gettext("You haven't yet set up access control. You need to either setup a username and password and click \"Keep Access Control Enabled\" or click \"Disable Access Control\" before continuing")
            });
            return false;
        };

        self.onWizardDetails = function(response) {
            self.required = response && response.corewizard && response.corewizard.details && response.corewizard.details.acl && response.corewizard.details.acl.required;
        };

        self.onWizardFinish = function() {
            if (!self.required) return;

            if (!self.decision()) {
                return "reload";
            }
        };
    }

    function CoreWizardWebcamViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0];

        self.required = false;

        self.onWizardDetails = function(response) {
            self.required = response && response.corewizard && response.corewizard.details && response.corewizard.details.webcam && response.corewizard.details.webcam.required;
        };

        self.onWizardFinish = function() {
            if (!self.required) return;
            if (self.settingsViewModel.webcam_streamUrl()
                || (self.settingsViewModel.webcam_snapshotUrl() && self.settingsViewModel.webcam_ffmpegPath())) {
                return "reload";
            }
        }
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

        self.enableOnlineCheck = function() {
            self.settingsViewModel.server_onlineCheck_enabled(true);
            self.decision(true);
            self._sendData();
        };

        self.disableOnlineCheck = function() {
            self.settingsViewModel.server_onlineCheck_enabled(false);
            self.decision(false);
            self._sendData();
        };

        self.onBeforeWizardTabChange = function(next, current) {
            if (!self.required) return true;

            if (!current || !_.startsWith(current, "wizard_plugin_corewizard_onlinecheck_") || self.setup()) {
                return true;
            }

            self._showDecisionNeededDialog();
            return false;
        };

        self.onBeforeWizardFinish = function() {
            if (!self.required) return true;

            if (self.setup()) {
                return true;
            }

            self._showDecisionNeededDialog();
            return false;
        };

        self.onWizardPreventSettingsRefreshDialog = function() {
            return self.active;
        };

        self.onWizardDetails = function(response) {
            self.required = response && response.corewizard && response.corewizard.details && response.corewizard.details.onlinecheck && response.corewizard.details.onlinecheck.required;
        };

        self._showDecisionNeededDialog = function() {
            showMessageDialog({
                title: gettext("Please set up the online connectivity check"),
                message: gettext("You haven't yet decided on whether to enable or disable the online connectivity check. You need to either enable or disable it before continuing.")
            });
        };

        self._sendData = function() {
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
            self.settingsViewModel.saveData(data)
                .done(function() {
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

        self.enablePluginBlacklist = function() {
            self.settingsViewModel.server_pluginBlacklist_enabled(true);
            self.decision(true);
            self._sendData();
        };

        self.disablePluginBlacklist = function() {
            self.settingsViewModel.server_pluginBlacklist_enabled(false);
            self.decision(false);
            self._sendData();
        };

        self.onBeforeWizardTabChange = function(next, current) {
            if (!self.required) return true;

            if (!current || !_.startsWith(current, "wizard_plugin_corewizard_pluginblacklist_") || self.setup()) {
                return true;
            }

            self._showDecisionNeededDialog();
            return false;
        };

        self.onBeforeWizardFinish = function() {
            if (!self.required) return true;

            if (self.setup()) {
                return true;
            }

            self._showDecisionNeededDialog();
            return false;
        };

        self.onWizardPreventSettingsRefreshDialog = function() {
            return self.active;
        };

        self.onWizardDetails = function(response) {
            self.required = response && response.corewizard && response.corewizard.details && response.corewizard.details.pluginblacklist && response.corewizard.details.pluginblacklist.required;
        };

        self._showDecisionNeededDialog = function() {
            showMessageDialog({
                title: gettext("Please set up the plugin blacklist processing"),
                message: gettext("You haven't yet decided on whether to enable or disable the plugin blacklist processing. You need to either enable or disable it before continuing.")
            });
        };

        self._sendData = function() {
            var data = {
                server: {
                    pluginBlacklist: {
                        enabled: self.settingsViewModel.server_pluginBlacklist_enabled()
                    }
                }
            };

            self.active = true;
            self.settingsViewModel.saveData(data)
                .done(function() {
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

        self.onWizardDetails = function(response) {
            self.required = response && response.corewizard && response.corewizard.details && response.corewizard.details.printerprofile && response.corewizard.details.printerprofile.required;
            if (!self.required) return;

            OctoPrint.printerprofiles.get("_default")
                .done(function(data) {
                    self.editor.fromProfileData(data);
                    self.editorLoaded(true);
                })
                .fail(function() {
                    self.editor.fromProfileData();
                    self.editorLoaded(true);
                });
        };

        self.onWizardFinish = function() {
            if (!self.required) return;

            OctoPrint.printerprofiles.update("_default", self.editor.toProfileData())
                .done(function() {
                    self.printerProfiles.requestData();
                });
        };
    }

    OCTOPRINT_VIEWMODELS.push([
        CoreWizardAclViewModel,
        ["loginStateViewModel"],
        "#wizard_plugin_corewizard_acl"
    ], [
        CoreWizardWebcamViewModel,
        ["settingsViewModel"],
        "#wizard_plugin_corewizard_webcam"
    ], [
        CoreWizardServerCommandsViewModel,
        ["settingsViewModel"],
        "#wizard_plugin_corewizard_servercommands"
    ], [
        CoreWizardOnlineCheckViewModel,
        ["settingsViewModel"],
        "#wizard_plugin_corewizard_onlinecheck"
    ], [
        CoreWizardPluginBlacklistViewModel,
        ["settingsViewModel"],
        "#wizard_plugin_corewizard_pluginblacklist"
    ], [
        CoreWizardPrinterProfileViewModel,
        ["printerProfilesViewModel"],
        "#wizard_plugin_corewizard_printerprofile"
    ]);
});
