$(function () {
    function FirstRunWizardViewModel(parameters) {
        var self = this;

        self.dontPrintUnattendedAcknowledged = ko.observable(false);
        self.dontPortForwardAcknowledged = ko.observable(false);
        self.error = ko.observable(false);

        self.allAcknowledged = ko.pureComputed(function () {
            return (
                self.dontPrintUnattendedAcknowledged() &&
                self.dontPortForwardAcknowledged()
            );
        });

        self.onBeforeWizardTabChange = function (next, current) {
            if (!current || current !== "wizard_firstrun_end" || self.allAcknowledged()) {
                return true;
            }

            self._showAcknowledgementNeededDialog();
            return false;
        };

        self.onBeforeWizardFinish = function () {
            if (self.allAcknowledged()) {
                return true;
            }

            self._showAcknowledgementNeededDialog();
            return false;
        };

        self._showAcknowledgementNeededDialog = function () {
            self.error(true);
            showMessageDialog({
                title: gettext("Please acknowledge the safety warnings"),
                message: gettext(
                    "You haven't yet acknowledged all safety warnings. Please do so first."
                )
            });
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: FirstRunWizardViewModel,
        elements: ["#wizard_firstrun_start", "#wizard_firstrun_end"]
    });
});
