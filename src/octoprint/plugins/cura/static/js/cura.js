$(function() {
    function CuraViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settingsViewModel = parameters[1];
        self.slicingViewModel = parameters[2];

        self.pathBroken = ko.observable(false);
        self.pathOk = ko.observable(false);
        self.pathText = ko.observable();
        self.pathHelpVisible = ko.pureComputed(function() {
            return self.pathBroken() || self.pathOk();
        });

        self.fileName = ko.observable();

        self.placeholderName = ko.observable();
        self.placeholderDisplayName = ko.observable();
        self.placeholderDescription = ko.observable();

        self.profileName = ko.observable();
        self.profileDisplayName = ko.observable();
        self.profileDescription = ko.observable();
        self.profileAllowOverwrite = ko.observable(true);
        self.profileMakeDefault = ko.observable(false);
        self.profileFirst = ko.observable(false);

        // make sure to update form data if any of the metadata changes
        self.profileName.subscribe(function() { self.copyProfileMetadata(); });
        self.profileDisplayName.subscribe(function() {
            if (self.profileDisplayName()) {
                self.placeholderName(self._sanitize(self.profileDisplayName()).toLowerCase());
            }
            self.copyProfileMetadata();
        });
        self.profileDescription.subscribe(function() { self.copyProfileMetadata(); });
        self.profileAllowOverwrite.subscribe(function() { self.copyProfileMetadata(); });
        self.profileMakeDefault.subscribe(function() { self.copyProfileMetadata(); });

        self.unconfiguredCuraEngine = ko.observable();
        self.unconfiguredSlicingProfile = ko.observable();

        self.uploadDialog = $("#settings_plugin_cura_import");
        self.uploadElement = $("#settings-cura-import");
        self.uploadData = ko.observable(undefined);
        self.uploadBusy = ko.observable(false);

        self.uploadEnabled = ko.pureComputed(function() {
            return self.fieldsEnabled();
        });
        self.fieldsEnabled = ko.pureComputed(function() {
            return self.uploadData() && !self.uploadBusy()
                && (self.profileName() || self.placeholderName())
                && (self.profileDisplayName() || self.placeholderDisplayName())
                && (self.profileDescription() || self.placeholderDescription());
        });

        self.profiles = new ItemListHelper(
            "plugin_cura_profiles",
            {
                "id": function(a, b) {
                    if (a["key"].toLocaleLowerCase() < b["key"].toLocaleLowerCase()) return -1;
                    if (a["key"].toLocaleLowerCase() > b["key"].toLocaleLowerCase()) return 1;
                    return 0;
                },
                "name": function(a, b) {
                    // sorts ascending
                    var aName = a.name();
                    if (aName === undefined) {
                        aName = "";
                    }
                    var bName = b.name();
                    if (bName === undefined) {
                        bName = "";
                    }

                    if (aName.toLocaleLowerCase() < bName.toLocaleLowerCase()) return -1;
                    if (aName.toLocaleLowerCase() > bName.toLocaleLowerCase()) return 1;
                    return 0;
                }
            },
            {},
            "id",
            [],
            [],
            5
        );

        self._sanitize = function(name) {
            return name.replace(/[^a-zA-Z0-9\-_\.\(\) ]/g, "").replace(/ /g, "_");
        };

        self.performUpload = function() {
            if (self.uploadData()) {
                self.uploadData().submit();
            }
        };

        self.copyProfileMetadata = function(form) {
            form = form || (self.uploadData() ? self.uploadData().formData : {});

            if (self.profileName() !== undefined) {
                form["name"] = self.profileName();
            } else if (self.placeholderName() !== undefined) {
                form["name"] = self.placeholderName();
            }

            if (self.profileDisplayName() !== undefined) {
                form["displayName"] = self.profileDisplayName();
            } else if (self.placeholderDisplayName() !== undefined) {
                form["displayName"] = self.placeholderDisplayName();
            }

            if (self.profileDescription() !== undefined) {
                form["description"] = self.profileDescription();
            } else if (self.placeholderDescription() !== undefined) {
                form["description"] = self.placeholderDescription();
            }

            if (self.profileMakeDefault()) {
                form["default"] = true;
            }

            return form;
        };

        self.clearUpload = function() {
            self.uploadData(undefined);
            self.fileName(undefined);
            self.placeholderName(undefined);
            self.placeholderDisplayName(undefined);
            self.placeholderDescription(undefined);
            self.profileName(undefined);
            self.profileDisplayName(undefined);
            self.profileDescription(undefined);
            self.profileAllowOverwrite(true);

            var firstProfile = self.profiles.items().length === 0;
            self.profileMakeDefault(firstProfile);
            self.profileFirst(firstProfile);
        };

        self.uploadElement.fileupload({
            dataType: "json",
            maxNumberOfFiles: 1,
            autoUpload: false,
            headers: OctoPrint.getRequestHeaders(),
            add: function(e, data) {
                if (data.files.length == 0) {
                    // no files? ignore
                    return false;
                }
                if (self.uploadData()) {
                    // data already defined? ignore (should never happen)
                    return false;
                }

                self.fileName(data.files[0].name);

                var name = self.fileName().substr(0, self.fileName().lastIndexOf("."));
                self.placeholderName(self._sanitize(name).toLowerCase());
                self.placeholderDisplayName(name);
                self.placeholderDescription("Imported from " + self.fileName() + " on " + formatDate(new Date().getTime() / 1000));

                var form = {
                    allowOverwrite: self.profileAllowOverwrite()
                };
                data.formData = self.copyProfileMetadata(form);

                self.uploadData(data);
            },
            submit: function(e, data) {
                self.copyProfileMetadata();
                self.uploadBusy(true);
            },
            done: function(e, data) {
                self.uploadBusy(false);
                self.clearUpload();

                self.uploadDialog.modal("hide");
                self.requestData();
                self.slicingViewModel.requestData();
            }
        });

        self.removeProfile = function(data) {
            if (!data.resource) {
                return;
            }

            self.profiles.removeItem(function(item) {
                return (item.key == data.key);
            });

            OctoPrint.slicing.deleteProfileForSlicer("cura", data.key, {url: data.resource()})
                .done(function() {
                    self.requestData();
                    self.slicingViewModel.requestData();
                });
        };

        self.makeProfileDefault = function(data) {
            if (!data.resource) {
                return;
            }

            _.each(self.profiles.items(), function(item) {
                item.isdefault(false);
            });
            var item = self.profiles.getItem(function(item) {
                return item.key == data.key;
            });
            if (item !== undefined) {
                item.isdefault(true);
            }

            OctoPrint.slicing.updateProfileForSlicer("cura", data.key, {default: true}, {url: data.resource()})
                .done(function() {
                    self.requestData();
                });
        };

        self.showImportProfileDialog = function() {
            self.clearUpload();
            self.uploadDialog.modal("show");
        };

        self.testEnginePath = function() {
            OctoPrint.util.testExecutable(self.settings.plugins.cura.cura_engine())
                .done(function(response) {
                    if (!response.result) {
                        if (!response.exists) {
                            self.pathText(gettext("The path doesn't exist"));
                        } else if (!response.typeok) {
                            self.pathText(gettext("The path is not a file"));
                        } else if (!response.access) {
                            self.pathText(gettext("The path is not an executable"));
                        }
                    } else {
                        self.pathText(gettext("The path is valid"));
                    }
                    self.pathOk(response.result);
                    self.pathBroken(!response.result);
                });
        };

        self.requestData = function() {
            self.slicingViewModel.requestData();
        };

        self.fromResponse = function(data) {
            var profiles = [];
            _.each(_.keys(data), function(key) {
                profiles.push({
                    key: key,
                    name: ko.observable(data[key].displayName),
                    description: ko.observable(data[key].description),
                    isdefault: ko.observable(data[key].default),
                    resource: ko.observable(data[key].resource)
                });
            });
            self.profiles.updateItems(profiles);
        };

        self.onBeforeBinding = function () {
            self.settings = self.settingsViewModel.settings;
        };

        self.onAllBound = function() {
            self.uploadDialog.on("hidden", function(event) {
                if (event.target.id == "settings_plugin_cura_import") {
                    self.clearUpload();
                }
            });
        };

        self.onSettingsShown = function() {
            self.requestData();
        };

        self.onSettingsHidden = function() {
            self.resetPathTest();
        };

        self.onSlicingData = function(data) {
            if (data && data.hasOwnProperty("cura") && data.cura.hasOwnProperty("profiles")) {
                self.fromResponse(data.cura.profiles);
            }
        };

        self.resetPathTest = function() {
            self.pathBroken(false);
            self.pathOk(false);
            self.pathText("");
        };

        self.onWizardDetails = function(response) {
            if (!response.hasOwnProperty("cura") || !response.cura.required) return;

            if (response.cura.details.hasOwnProperty("engine")) {
                self.unconfiguredCuraEngine(!response.cura.details.engine);
            }
            if (response.cura.details.hasOwnProperty("profile")) {
                self.unconfiguredSlicingProfile(!response.cura.details.profile);
            }
        };

        self.onWizardFinish = function() {
            self.resetPathTest();
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: CuraViewModel,
        dependencies: ["loginStateViewModel", "settingsViewModel", "slicingViewModel"],
        elements: ["#settings_plugin_cura", "#wizard_plugin_cura"]
    });
});
