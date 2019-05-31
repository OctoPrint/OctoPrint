$(function() {
    function ConnectionProfileEditorViewModel() {
        var self = this;

        self.active = ko.observable(false);
        self.deferred = undefined;

        self.buttonText = ko.observable(gettext("Save"));

        self.dialog = $("#connectionprofiles_save_dialog");

        self.profile = undefined;

        self.name = ko.observable();
        self.identifier = ko.observable();
        self.identifierPlaceholder = ko.observable();

        self.overwrite = ko.observable(false);
        self.makeDefault = ko.observable(false);

        self.name.subscribe(function() {
            self.identifierPlaceholder(self._sanitize(self.name()).toLowerCase());
        });

        self.showDialog = function(profile, button) {
            if (button) {
                self.buttonText(button);
            } else {
                self.buttonText(gettext("Save"));
            }

            self.profile = profile;

            self.name(profile.name);
            self.identifier(profile.identifier);

            self.overwrite(profile.identifier !== undefined);

            self.deferred = $.Deferred();
            self.dialog.modal("show");
            return self.deferred.promise();
        };

        self.confirm = function() {
            self.profile.id = self.identifier();
            if (self.profile.id === undefined) {
                self.profile.id = self.identifierPlaceholder();
            }

            self.profile.name = self.name();

            OctoPrint.connectionprofiles.set(self.profile.id, self.profile, self.overwrite(), self.makeDefault())
                .done(function(response) {
                    self.dialog.modal("hide");
                    if (self.deferred) {
                        self.deferred.resolve(response.profile);
                    }
                })
        };

        self._sanitize = function(name) {
            return name.replace(/[^a-zA-Z0-9\-_\.\(\) ]/g, "").replace(/ /g, "_");
        };
    }

    function ConnectionProfilesViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.access = parameters[1];

        self.requestInProgress = ko.observable(false);

        self.editor = new ConnectionProfileEditorViewModel();

        self.profiles = new ItemListHelper(
            "connectionProfiles",
            {
                "name": function(a, b) {
                    // sorts ascending
                    if (a["name"].toLocaleLowerCase() < b["name"].toLocaleLowerCase()) return -1;
                    if (a["name"].toLocaleLowerCase() > b["name"].toLocaleLowerCase()) return 1;
                    return 0;
                }
            },
            {},
            "name",
            [],
            [],
            10
        );
        self.defaultProfile = ko.observable();
        self.currentProfile = ko.observable();

        self.makeDefault = function(data) {
            return OctoPrint.connectionprofiles.update(data.id, {default: true})
                .done(function() {
                    self.requestData();
                });
        };

        self.canMakeDefault = function(data) {
            return !data.is_default();
        };

        self.canRemove = function(data) {
            return !data.is_current() && !data.is_default();
        };

        self.requestData = function() {
            if (!self.loginState.hasPermission(self.access.permissions.CONNECTION)) {
                return;
            }

            return OctoPrint.connectionprofiles.list()
                .done(self.fromResponse);
        };

        self.fromResponse = function(data) {
            var items = [];
            var defaultProfile = undefined;
            var currentProfile = undefined;
            _.each(data.profiles, function(profile) {
                if (profile.default) {
                    defaultProfile = profile.id;
                }
                if (profile.current) {
                    currentProfile = profile.id;
                }
                profile.is_default = ko.observable(profile.default);
                profile.is_current = ko.observable(profile.current);
                items.push(profile);
            });
            self.profiles.updateItems(items);
            self.defaultProfile(defaultProfile);

            if (currentProfile) {
                self.currentProfile(currentProfile);
            } else {
                // shouldn't normally happen, but just to not have anything else crash...
                log.warn("Current printer profile could not be detected, using default values");
                self.currentProfile(undefined);
            }
        };

        self.removeProfile = function(data) {
            var proceed = function() {
                OctoPrint.connectionprofiles.delete(data.id)
                    .done(function() {
                        self.requestData();
                    });
            };

            showConfirmationDialog({
                message: _.sprintf(gettext("You are about to delete the connection profile \"%(profile)s\"."), {profile: data.name}),
                onproceed: proceed
            });
        };

        self.onSettingsShown = self.requestData;

        self.onUserPermissionsChanged = self.onUserLoggedIn = self.onUserLoggedOut = function() {
            self.requestData();
        }
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: ConnectionProfilesViewModel,
        dependencies: ["loginStateViewModel", "accessViewModel"],
        elements: ["#connectionprofiles_save_dialog"]
    });
});
