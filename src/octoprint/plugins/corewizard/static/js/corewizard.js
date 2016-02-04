$(function() {
    function CoreWizardAclViewModel(parameters) {
        var self = this;

        self.loginStateViewModel = parameters[0];

        self.username = ko.observable(undefined);
        self.password = ko.observable(undefined);
        self.confirmedPassword = ko.observable(undefined);

        self.setup = ko.observable(false);
        self.decision = ko.observable();

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

        self.onWizardTabChange = function(current, next) {
            if (!current || !_.startsWith(current, "wizard_plugin_corewizard_acl_") || self.setup()) {
                return true;
            }
            showMessageDialog({
                title: gettext("Please set up Access Control"),
                message: gettext("You haven't yet set up access control. You need to either setup a username and password and click \"Keep Access Control Enabled\" or click \"Disable Access Control\" before continuing")
            });
            return false;
        };

        self.onWizardFinish = function() {
            if (!self.decision()) {
                return "reload";
            }
        };
    }

    function CoreWizardWebcamViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0];

        self.onWizardFinish = function() {
            if (self.settingsViewModel.webcam_streamUrl()
                || (self.settingsViewModel.webcam_snapshotUrl() && self.settingsViewModel.webcam_ffmpegPath())) {
                return "reload";
            }
        }
    }

    OCTOPRINT_VIEWMODELS.push([
        CoreWizardAclViewModel,
        ["loginStateViewModel"],
        "#wizard_plugin_corewizard_acl"
    ], [
        CoreWizardWebcamViewModel,
        ["settingsViewModel"],
        "#wizard_plugin_corewizard_webcam"
    ]);
});
