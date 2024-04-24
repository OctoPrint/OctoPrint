$(function () {
    function FirstRunWizardViewModel(parameters) {
        var self = this;

        self.dontPrintUnattendedAcknowledged = ko.observable(false);
        self.dontPortForwardAcknowledged = ko.observable(false);
        self.fundingRequestAcknowledged = ko.observable(false);
        self.error = ko.observable(false);
        self.acknowledgementNeeded = false;

        self.allAcknowledged = ko.pureComputed(function () {
            return (
                self.dontPrintUnattendedAcknowledged() &&
                self.dontPortForwardAcknowledged() &&
                self.fundingRequestAcknowledged()
            );
        });

        self.onBeforeWizardTabChange = function (next, current) {
            if (!self.acknowledgementNeeded) {
                return true;
            }
            if (!current || current !== "wizard_firstrun_end" || self.allAcknowledged()) {
                return true;
            }

            self._showAcknowledgementNeededDialog();
            return false;
        };

        self.onBeforeWizardFinish = function () {
            if (!self.acknowledgementNeeded || self.allAcknowledged()) {
                return true;
            }

            self._showAcknowledgementNeededDialog();
            return false;
        };

        self.onAfterBinding = function () {
            self.acknowledgementNeeded =
                document.getElementById("wizard_firstrun_end") !== null;
        };

        self._showAcknowledgementNeededDialog = function () {
            self.error(true);
            showMessageDialog({
                title: gettext(
                    "Please acknowledge the safety warnings and call for funding"
                ),
                message: gettext(
                    "You haven't yet acknowledged all safety warnings and the call for funding. Please do so first."
                )
            });
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: FirstRunWizardViewModel,
        elements: ["#wizard_firstrun_start", "#wizard_firstrun_end"]
    });
});
