$(function() {
    function AppearanceViewModel(parameters) {
        var self = this;

        self.name = parameters[0].appearance_name;
        self.color = parameters[0].appearance_color;
        self.colorTransparent = parameters[0].appearance_colorTransparent;

        self.brand = ko.pureComputed(function() {
            if (self.name())
                return gettext("OctoPrint") + ": " + self.name();
            else
                return gettext("OctoPrint");
        });

        self.title = ko.pureComputed(function() {
            if (self.name())
                return self.name() + " [" + gettext("OctoPrint") + "]";
            else
                return gettext("OctoPrint");
        });
    }

    OCTOPRINT_VIEWMODELS.push([
        AppearanceViewModel,
        ["settingsViewModel"],
        "head"
    ]);
});
