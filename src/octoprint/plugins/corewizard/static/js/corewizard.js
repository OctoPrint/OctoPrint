$(function() {
    function CoreWizardAclViewModel() {
        var self = this;

        self.username = ko.observable(undefined);
        self.password = ko.observable(undefined);
        self.confirmedPassword = ko.observable(undefined);

        self.setup = ko.observable(false);
        self.decision = ko.observable();

        self.passwordMismatch = ko.computed(function() {
            return self.password() != self.confirmedPassword();
        });

        self.validUsername = ko.computed(function() {
            return self.username() && self.username().trim() != "";
        });

        self.validPassword = ko.computed(function() {
            return self.password() && self.password().trim() != "";
        });

        self.validData = ko.computed(function() {
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
            $.ajax({
                url: API_BASEURL + "plugin/corewizard/acl",
                type: "POST",
                dataType: "json",
                data: data,
                success: function() {
                    self.setup(true);
                    self.decision(data.ac);
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
            if (self.unbound) return;

            self.settingsViewModel.enqueueForSaving({
                webcam: {
                    streamUrl: self.settingsViewModel.webcam_streamUrl(),
                    snapshotUrl: self.settingsViewModel.webcam_snapshotUrl()
                }
            });
        }
    }

    OCTOPRINT_VIEWMODELS.push([
        CoreWizardAclViewModel,
        [],
        "#wizard_plugin_corewizard_acl"
    ], [
        CoreWizardWebcamViewModel,
        ["settingsViewModel"],
        "#wizard_plugin_corewizard_webcam"
    ]);
});
