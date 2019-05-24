$(function() {
    function ConnectionProfileEditorViewModel() {
        var self = this;

        self.active = ko.observable(false);
        self.deferred = undefined;

        self.buttonText = ko.observable(gettext("Save"));

        self.profile = undefined;

        self.name = ko.observable();
        self.identifier = ko.observable();
        self.identifierPlaceholder = ko.observable();

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

            self.deferred = $.Deferred();
            $("#connectionprofiles_save_dialog").modal("show");
            return self.deferred.promise();
        };

        self.confirm = function() {
            self.profile.id = self.identifier();
            if (self.profile.id === undefined) {
                self.profile.id = self.identifierPlaceholder();
            }

            self.profile.name = self.name();

            OctoPrint.connectionprofiles.add(self.profile)
                .done(function(response) {
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

        self.makeDefault = function(data) {
            /*
            var profile = {
                id: data.id,
                default: true
            };

            self.updateProfile(profile);
            */
        };

        self.canMakeDefault = function(data) {
            //return !data.isdefault();
            return true;
        };

        self.canRemove = function(data) {
            //return !data.iscurrent() && !data.isdefault();
            return true;
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
            _.each(data.profiles, function(profile) {
                items.push(profile);
            });
            self.profiles.updateItems(items);
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
