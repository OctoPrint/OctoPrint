$(function () {
    function ClassicWebcamWizardViewModel(parameters) {
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
            if (self.settingsViewModel.streamUrl()) {
                return "reload";
            }
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: ClassicWebcamWizardViewModel,
        dependencies: ["classicWebcamSettingsViewModel"],
        elements: ["#wizard_classicwebcam"]
    });
});
