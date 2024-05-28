$(() => {
    function MfaTotpViewModel(parameters) {
        var self = this;

        self.enrolled = ko.observable(false);
        self.active = ko.observable(false);

        self.enrollmentUri = ko.observable();
        self.verificationToken = ko.observable();

        self.requestData = () => {
            OctoPrint.plugins.mfa_totp.get().done((response) => {
                self.enrolled(response.enrolled);
                self.active(response.active);
            });
        };

        self.enroll = () => {
            OctoPrint.plugins.mfa_totp.enroll().done((response) => {
                self.qrCodeUri(response.uri);
            });
        };

        self.activate = () => {
            OctoPrint.plugins.mfa_totp.activate(self.verificationToken()).done(() => {
                self.requestData();
            });
        };

        self.deactivate = () => {
            OctoPrint.plugins.mfa_totp.deactivate().done(() => {
                self.requestData();
            });
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: MfaTotpViewModel,
        dependencies: [],
        elements: ["#usersettings_plugin_mfa_totp"]
    });
});
