$(function () {
    function SlicingViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.printerProfiles = parameters[1];
        self.printerState = parameters[2];
        self.access = parameters[3];

        self.file = ko.observable(undefined);
        self.target = undefined;
        self.path = undefined;
        self.data = undefined;

        self.defaultSlicer = undefined;
        self.defaultProfile = undefined;

        self.destinationFilename = ko.observable();
        self.gcodeFilename = self.destinationFilename; // TODO: for backwards compatibility, mark deprecated ASAP

        self.title = ko.observable();
        self.slicer = ko.observable();
        self.slicers = ko.observableArray();
        self.profile = ko.observable();
        self.profiles = ko.observableArray();
        self.printerProfile = ko.observable();

        self.slicerSameDevice = ko.observable();

        self.allViewModels = undefined;

        self.slicersForFile = function (file) {
            if (file === undefined) {
                return [];
            }

            return _.filter(self.configuredSlicers(), function (slicer) {
                return _.any(slicer.sourceExtensions, function (extension) {
                    return _.endsWith(file.toLowerCase(), "." + extension.toLowerCase());
                });
            });
        };

        self.profilesForSlicer = function (key) {
            if (key == undefined) {
                key = self.slicer();
            }
            if (key == undefined || !self.data.hasOwnProperty(key)) {
                return;
            }
            var slicer = self.data[key];

            var selectedProfile = undefined;
            self.profiles.removeAll();
            _.each(_.values(slicer.profiles), function (profile) {
                var name = profile.displayName;
                if (name == undefined) {
                    name = profile.key;
                }

                if (profile.default) {
                    selectedProfile = profile.key;
                }

                self.profiles.push({
                    key: profile.key,
                    name: name
                });
            });

            self.profile(selectedProfile);
            self.defaultProfile = selectedProfile;
        };

        self.resetProfiles = function () {
            self.profiles.removeAll();
            self.profile(undefined);
        };

        self.metadataForSlicer = function (key) {
            if (key == undefined || !self.data.hasOwnProperty(key)) {
                return;
            }

            var slicer = self.data[key];
            self.slicerSameDevice(slicer.sameDevice);
        };

        self.resetMetadata = function () {
            self.slicerSameDevice(true);
        };

        self.configuredSlicers = ko.pureComputed(function () {
            return _.filter(self.slicers(), function (slicer) {
                return slicer.configured;
            });
        });

        self.matchingSlicers = ko.computed(function () {
            var slicers = self.slicersForFile(self.file());

            var containsSlicer = function (key) {
                return _.any(slicers, function (slicer) {
                    return slicer.key == key;
                });
            };

            var current = self.slicer();
            if (!containsSlicer(current)) {
                if (
                    self.defaultSlicer !== undefined &&
                    containsSlicer(self.defaultSlicer)
                ) {
                    self.slicer(self.defaultSlicer);
                } else {
                    self.slicer(undefined);
                    self.resetProfiles();
                }
            } else {
                self.profilesForSlicer(self.slicer());
            }

            return slicers;
        });

        self.afterSlicingOptions = [
            {value: "none", text: gettext("Do nothing")},
            {value: "select", text: gettext("Select for printing")},
            {value: "print", text: gettext("Start printing")}
        ];
        self.afterSlicing = ko.observable("none");

        self.show = function (target, file, force, path, options) {
            options = options || {};

            if (!self.enableSlicingDialog() && !force) {
                return;
            }

            var filename = file;
            if (filename.lastIndexOf("/") != 0) {
                path = path || filename.substr(0, filename.lastIndexOf("/"));
                filename = filename.substr(filename.lastIndexOf("/") + 1);
            }

            var display = options.display || filename;
            var destination = display.substr(0, display.lastIndexOf("."));

            self.requestData();
            self.target = target;
            self.file(file);
            self.path = path;
            self.title(
                _.sprintf(gettext("Slicing %(filename)s"), {filename: _.escape(display)})
            );
            self.destinationFilename(destination);
            self.printerProfile(self.printerProfiles.currentProfile());
            self.afterSlicing("none");

            $("#slicing_configuration_dialog").modal("show");
        };

        self.slicer.subscribe(function (newValue) {
            if (newValue === undefined) {
                self.resetProfiles();
                self.resetMetadata();
            } else {
                self.profilesForSlicer(newValue);
                self.metadataForSlicer(newValue);
            }
        });

        self.enableSlicingDialog = ko.pureComputed(function () {
            return self.configuredSlicers().length > 0;
        });

        self.enableSlicingDialogForFile = function (file) {
            return self.slicersForFile(file).length > 0;
        };

        self.enableSliceButton = ko.pureComputed(function () {
            return (
                self.destinationFilename() != undefined &&
                self.destinationFilename().trim() != "" &&
                self.slicer() != undefined &&
                self.profile() != undefined &&
                (!(self.printerState.isPrinting() || self.printerState.isPaused()) ||
                    !self.slicerSameDevice())
            );
        });

        self.sliceButtonTooltip = ko.pureComputed(function () {
            if (!self.enableSliceButton()) {
                if (
                    (self.printerState.isPrinting() || self.printerState.isPaused()) &&
                    self.slicerSameDevice()
                ) {
                    return gettext("Cannot slice on the same device while printing");
                } else {
                    return gettext("Cannot slice, not all parameters specified");
                }
            } else {
                return gettext("Start the slicing process");
            }
        });

        self.requestData = function () {
            if (!self.loginState.hasPermission(self.access.permissions.SLICE)) {
                return;
            }

            return OctoPrint.slicing.listAllSlicersAndProfiles().done(function (data) {
                self.fromResponse(data);
            });
        };

        self.destinationExtension = ko.pureComputed(function () {
            var fallback = "???";
            if (self.slicer() === undefined) {
                return fallback;
            }
            var slicer = self.data[self.slicer()];
            if (slicer === undefined) {
                return fallback;
            }
            var extensions = slicer.extensions;
            if (extensions === undefined) {
                return fallback;
            }
            var destinationExtensions = extensions.destination;
            if (destinationExtensions === undefined || !destinationExtensions.length) {
                return fallback;
            }

            return destinationExtensions[0] || fallback;
        });

        self.fromResponse = function (data) {
            self.data = data;

            var selectedSlicer = undefined;
            self.slicers.removeAll();
            _.each(_.values(data), function (slicer) {
                var name = slicer.displayName;
                if (name == undefined) {
                    name = slicer.key;
                }

                if (slicer.default && slicer.configured) {
                    selectedSlicer = slicer.key;
                }

                var props = {
                    key: slicer.key,
                    name: name,
                    configured: slicer.configured,
                    sourceExtensions: slicer.extensions.source,
                    destinationExtensions: slicer.extensions.destination,
                    sameDevice: slicer.sameDevice
                };
                self.slicers.push(props);
            });

            self.defaultSlicer = selectedSlicer;

            if (self.allViewModels) {
                callViewModels(self.allViewModels, "onSlicingData", [data]);
            }
        };

        self.slice = function () {
            if (!self.enableSliceButton()) {
                return;
            }

            var destinationFilename = self.destinationFilename();

            var destinationExtensions =
                self.data[self.slicer()] &&
                self.data[self.slicer()].extensions &&
                self.data[self.slicer()].extensions.destination
                    ? self.data[self.slicer()].extensions.destination
                    : ["???"];
            if (
                !_.any(destinationExtensions, function (extension) {
                    return _.endsWith(
                        destinationFilename.toLowerCase(),
                        "." + extension.toLowerCase()
                    );
                })
            ) {
                destinationFilename =
                    destinationFilename + "." + destinationExtensions[0];
            }

            var data = {
                slicer: self.slicer(),
                profile: self.profile(),
                printerProfile: self.printerProfile(),
                destination: destinationFilename
            };

            if (self.path != undefined) {
                data["path"] = self.path;
            }

            if (self.afterSlicing() == "print") {
                data["print"] = true;
            } else if (self.afterSlicing() == "select") {
                data["select"] = true;
            }

            OctoPrint.files.slice(self.target, self.file(), data).done(function () {
                $("#slicing_configuration_dialog").modal("hide");

                self.destinationFilename(undefined);
                self.slicer(self.defaultSlicer);
                self.profile(self.defaultProfile);
            });
        };

        self._sanitize = function (name) {
            return name.replace(/[^a-zA-Z0-9\-_\.\(\) ]/g, "").replace(/ /g, "_");
        };

        self.onUserPermissionsChanged =
            self.onUserLoggedIn =
            self.onUserLoggedOut =
                function () {
                    self.requestData();
                };

        self.onEventSettingsUpdated = function (payload) {
            self.requestData();
        };

        self.onAllBound = function (allViewModels) {
            self.allViewModels = allViewModels;
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: SlicingViewModel,
        dependencies: [
            "loginStateViewModel",
            "printerProfilesViewModel",
            "printerStateViewModel",
            "accessViewModel"
        ],
        elements: ["#slicing_configuration_dialog"]
    });
});
