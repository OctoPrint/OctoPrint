$(() => {
    function MfaTotpViewModel(parameters) {
        var self = this;

        self.active = ko.observable(false);

        self.enrollmentUri = ko.observable();
        self.verificationToken = ko.observable();
        self.verificationError = ko.observable(false);

        self.enrollmentDialog = $("#plugin_mfa_totp_enroll");
        self.verificationDialog = $("#plugin_mfa_totp_verify");

        self.enrollmentStatus = ko.pureComputed(() => {
            if (self.active()) {
                return gettext("Enrolled");
            } else {
                return gettext("Not enrolled");
            }
        });

        self.requestData = () => {
            OctoPrint.plugins.mfa_totp.getStatus().done((response) => {
                self.active(response.active);
            });
        };

        self.enroll = () => {
            self.verificationToken("");
            OctoPrint.plugins.mfa_totp.enroll().done((response) => {
                self.enrollmentUri(response.uri);
                self.enrollmentDialog.modal("show");
                $("#mfa_totp_enrollment_token").focus();
            });
        };

        self.finishEnrollment = () => {
            const token = self.verificationToken();
            self.verificationToken("");
            OctoPrint.plugins.mfa_totp
                .activate(token)
                .done(() => {
                    self.verificationError(true);
                    self.enrollmentDialog.modal("hide");
                    self.requestData();
                })
                .fail(() => {
                    self.verificationError(true);
                });
        };

        self.deactivate = () => {
            self.verificationToken("");
            self.verificationDialog.modal("show");
            $("#mfa_totp_verification_token").focus();
        };

        self.finishDeactivation = () => {
            const token = self.verificationToken();
            self.verificationToken("");
            OctoPrint.plugins.mfa_totp
                .deactivate(token)
                .done(() => {
                    self.verificationError(true);
                    self.verificationDialog.modal("hide");
                    self.requestData();
                })
                .fail(() => {
                    self.verificationError(true);
                });
        };

        self.onUserSettingsShown = self.onUserLoggedIn = () => {
            self.requestData();
        };

        self.onStartupComplete = () => {
            const cleanup = () => {
                self.verificationToken("");
                self.verificationError(false);
            };
            self.enrollmentDialog.on("hidden", cleanup);
            self.verificationDialog.on("hidden", cleanup);
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: MfaTotpViewModel,
        dependencies: [],
        elements: [
            "#usersettings_plugin_mfa_totp",
            "#plugin_mfa_totp_enroll",
            "#plugin_mfa_totp_verify"
        ]
    });
});
