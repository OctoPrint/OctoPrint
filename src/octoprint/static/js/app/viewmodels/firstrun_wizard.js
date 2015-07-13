$(function() {
    function AclWizardViewModel() {
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
            showConfirmationDialog(message, function(e) {
                var data = {
                    "ac": false
                };
                self._sendData(data);
            });
        };

        self._sendData = function(data, callback) {
            $.ajax({
                url: API_BASEURL + "setup",
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
            if (!current || !_.startsWith(current, "wizard_firstrun_acl") || self.setup()) {
                return true;
            }
            showMessageDialog(gettext("You haven't yet set up access control. You need to either setup a username and password and click \"Keep Access Control Enabled\" or click \"Disable Access Control\" before continuing"), {title: "Please set up Access Control"});
            return false;
        };

        self.onWizardFinished = function() {
            if (!self.decision()) {
                return "reload";
            }
        };
    }

    OCTOPRINT_VIEWMODELS.push([
        AclWizardViewModel,
        [],
        "#wizard_firstrun_acl"
    ]);
});
