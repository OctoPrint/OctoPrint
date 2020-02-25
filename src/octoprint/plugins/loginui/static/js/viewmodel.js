/*
 * View model that takes care to redirect to / on logout in the regular
 * OctoPrint web application.
 */

$(function() {
    function LoginUiViewModel(parameters) {
        var self = this;
        self.loginState = parameters[0];
        self.access = parameters[1];

        self.onUserLoggedOut = self.onUserPermissionsChanged = function() {
            if (!self.loginState.hasAllPermissions(self.access.permissions.STATUS, self.access.permissions.SETTINGS_READ) && !CONFIG_FIRST_RUN) {
                location.reload();
            }
        };

    }

    OCTOPRINT_VIEWMODELS.push({
        construct: LoginUiViewModel,
        dependencies: ["loginStateViewModel", "accessViewModel"]
    });
});
