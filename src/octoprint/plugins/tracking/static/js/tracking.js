$(function() {
    function TrackingViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0];

        self.setup = ko.observable(false);

        self.decision = ko.observable();
        self.required = false;
        self.active = false;

        self.enableTracking = function() {
            self.settingsViewModel.settings.plugins.tracking.enabled(true);
            self.decision(true);
            self._sendData();
        };

        self.disableTracking = function() {
            self.settingsViewModel.settings.plugins.tracking.enabled(false);
            self.decision(false);
            self._sendData();
        };

        self.onBeforeWizardTabChange = function(next, current) {
            if (!self.required) return true;

            if (!current || !_.startsWith(current, "wizard_plugin_tracking") || self.setup()) {
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
            self.required = response && response.tracking && response.tracking.required;
        };

        self._showDecisionNeededDialog = function() {
            showMessageDialog({
                title: gettext("Please set up anonymous usage tracking"),
                message: gettext("You haven't yet decided on whether to enable or disable anonymous usage tracking. You need to either enable or disable it before continuing.")
            });
        };

        self._sendData = function() {
            var data = {
                plugins: {
                    tracking: {
                        enabled: self.settingsViewModel.settings.plugins.tracking.enabled()
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

    OCTOPRINT_VIEWMODELS.push([
        TrackingViewModel,
        ["settingsViewModel"],
        "#wizard_plugin_tracking"
    ]);
});
