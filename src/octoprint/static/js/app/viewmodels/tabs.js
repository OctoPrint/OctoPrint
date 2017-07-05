$(function() {
    function TabsViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.access = parameters[1];
    }

    // view model class, parameters for constructor, container to bind to
    OCTOPRINT_VIEWMODELS.push([
        TabsViewModel,
        ["loginStateViewModel", "accessViewModel"],
        ["#tabs", "#tab_content", "#sidebar"]
    ]);
});
