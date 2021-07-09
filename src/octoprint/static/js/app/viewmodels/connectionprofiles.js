$(function () {
    function ConnectionProfilesViewModel(parameters) {
        var self = this;

        self.connection = parameters[0];

        self.requestInProgress = ko.observable(false);

        self.profiles = new ItemListHelper(
            "connectionProfiles",
            {
                name: function (a, b) {
                    // sorts ascending
                    if (a["name"].toLocaleLowerCase() < b["name"].toLocaleLowerCase())
                        return -1;
                    if (a["name"].toLocaleLowerCase() > b["name"].toLocaleLowerCase())
                        return 1;
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

        self.connection.availableConnectionProfiles.subscribe(function () {
            var profiles = self.connection.availableConnectionProfiles();
            self.profiles.updateItems(profiles);
        });
        self.connection.preferredConnectionProfile.subscribe(function (profileId) {
            self.defaultProfile(profileId);
        });
        self.connection.selectedConnectionProfile.subscribe(function (profile) {
            var profileId = profile ? profile.id : undefined;
            self.currentProfile(profileId);
        });

        self.editProfile = function (data) {
            self.connection.editor.showEditDialog(data);
        };

        self.canMakeDefault = function (data) {
            return !data.isDefault();
        };

        self.makeDefault = function (data) {
            self.requestInProgress(true);
            return OctoPrint.connectionprofiles
                .update(data.id, {default: true})
                .done(function () {
                    self.connection.requestData().always(function () {
                        self.requestInProgress(false);
                    });
                });
        };

        self.canRemove = function (data) {
            return !data.isCurrent() && !data.isDefault();
        };

        self.removeProfile = function (data) {
            var proceed = function () {
                self.requestInProgress(true);
                OctoPrint.connectionprofiles.delete(data.id).done(function () {
                    self.connection.requestData().always(function () {
                        self.requestInProgress(false);
                    });
                });
            };

            showConfirmationDialog({
                message: _.sprintf(
                    gettext(
                        'You are about to delete the connection profile "%(profile)s".'
                    ),
                    {profile: data.name}
                ),
                onproceed: proceed
            });
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: ConnectionProfilesViewModel,
        dependencies: ["connectionViewModel"],
        elements: ["#settings_connection_connectionprofiles"]
    });
});
