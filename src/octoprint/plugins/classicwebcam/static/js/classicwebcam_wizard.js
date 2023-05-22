$(function () {
    function ClassicWebcamWizardViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0];

        self.onWizardFinish = function () {
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
