function AppearanceViewModel(settingsViewModel) {
    var self = this;

    self.name = settingsViewModel.appearance_name;
    self.color = settingsViewModel.appearance_color;

    self.brand = ko.computed(function() {
        if (self.name())
            return "OctoPrint | SeeMeCNC Remix: " + self.name();
        else
            return "OctoPrint | SeeMeCNC Remix";
    })

    self.title = ko.computed(function() {
        if (self.name())
            return self.name() + " [SeeMeCNC: OrionPrint]";
        else
            return "OctoPrint | SeeMeCNC Remix";
    })
}
