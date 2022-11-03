/*
 * View model that takes care to redirect to / on logout in the regular
 * OctoPrint web application.
 */

$(function () {
    function LoginUiViewModel(parameters) {
        var self = this;
        self.loginState = parameters[0];
        self.access = parameters[1];
        self.coreWizardAcl = parameters[2];

        self.onUserLoggedOut = self.onUserPermissionsChanged = function () {
            // reload if user now lacks STATUS & SETTINGS_READ permissions and is not in first run setup, or is in
            // first run setup but the ACL wizard has already run
            if (
                !self.loginState.hasAllPermissions(
                    self.access.permissions.STATUS,
                    self.access.permissions.SETTINGS_READ
                ) &&
                (!CONFIG_FIRST_RUN || (self.coreWizardAcl && self.coreWizardAcl.setup()))
            ) {
                location.reload();
            }
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: LoginUiViewModel,
        dependencies: [
            "loginStateViewModel",
            "accessViewModel",
            "coreWizardAclViewModel"
        ],
        optional: ["coreWizardAclViewModel"]
    });
});
