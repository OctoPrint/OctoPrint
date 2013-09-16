function AppearanceViewModel(settingsViewModel) {
    var self = this;

    self.name = settingsViewModel.appearance_name;
    self.color = settingsViewModel.appearance_color;

    self.brand = ko.computed(function() {
        if (self.name())
            return "OctoPrint: " + self.name();
        else
            return "OctoPrint";
    })

    self.title = ko.computed(function() {
        if (self.name())
            return self.name() + " [OctoPrint]";
        else
            return "OctoPrint";
    })
}
