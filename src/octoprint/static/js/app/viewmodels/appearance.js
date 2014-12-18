function AppearanceViewModel(settingsViewModel, printerStateViewModel) {
    var self = this;

    self.name = settingsViewModel.appearance_name;
    self.color = settingsViewModel.appearance_color;

    self.brand = ko.computed(function() {
        if (self.name())
            return gettext("OctoPrint") + ": " + self.name();
        else
            return gettext("OctoPrint");
    });

    self.title = ko.computed(function() {
        if (self.name())
            return self.name() + " [" + gettext("OctoPrint") + "]";
        else
            return gettext("OctoPrint");
    });
}
