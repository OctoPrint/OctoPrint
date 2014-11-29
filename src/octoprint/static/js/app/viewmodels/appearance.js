function AppearanceViewModel(settingsViewModel) {
    var self = this;

    self.settings = settingsViewModel;

    self.brand = ko.computed(function() {
        if (self.settings.printerProfiles.currentProfileData().name())
            return gettext("OctoPrint") + ": " + self.settings.printerProfiles.currentProfileData().name();
        else
            return gettext("OctoPrint");
    });

    self.title = ko.computed(function() {
        if (self.settings.printerProfiles.currentProfileData().name())
            return self.settings.printerProfiles.currentProfileData().name() + " [" + gettext("OctoPrint") + "]";
        else
            return gettext("OctoPrint");
    });

    self.color = ko.computed(function() {
        if (self.settings.printerProfiles.currentProfileData().color())
            return self.settings.printerProfiles.currentProfileData().color();
        else
            return "default";
    });
}
