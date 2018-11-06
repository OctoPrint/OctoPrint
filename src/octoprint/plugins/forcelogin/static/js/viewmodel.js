/*
 * View model that takes care to redirect to / on logout in the regular
 * OctoPrint web application.
 */

$(function() {
    function ForceLoginViewModel(parameters) {
        var self = this;

        self.onUserLoggedOut = function() {
            location.reload();
        }
    }

    // view model class, parameters for constructor, container to bind to
    ADDITIONAL_VIEWMODELS.push([ForceLoginViewModel, [], []]);
});
