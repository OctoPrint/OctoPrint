function AppearanceViewModel(settingsViewModel, printerStateViewModel) {
    var self = this;

    self.settings = settingsViewModel;
    self.printerState = printerStateViewModel;

    self.connected = ko.observable(false);

    self.printerState.isErrorOrClosed.subscribe(function() {
        self.connected(!self.printerState.isErrorOrClosed());
    });

    self.brand = ko.computed(function() {
        if (self.settings.printerProfiles.currentProfileData().name() && self.connected())
            return gettext("OctoPrint") + ": " + self.settings.printerProfiles.currentProfileData().name();
        else
            return gettext("OctoPrint");
    });

    self.title = ko.computed(function() {
        if (self.settings.printerProfiles.currentProfileData().name() && self.connected())
            return self.settings.printerProfiles.currentProfileData().name() + " [" + gettext("OctoPrint") + "]";
        else
            return gettext("OctoPrint");
    });

    self.color = ko.computed(function() {
        if (self.settings.printerProfiles.currentProfileData().color() && self.connected())
            return self.settings.printerProfiles.currentProfileData().color();
        else
            return "default";
    });
}
