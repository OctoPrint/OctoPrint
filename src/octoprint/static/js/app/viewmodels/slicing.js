$(function() {
    function SlicingViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.printerProfiles = parameters[1];

        self.target = undefined;
        self.file = undefined;
        self.path = undefined;
        self.data = undefined;

        self.defaultSlicer = undefined;
        self.defaultProfile = undefined;

        self.gcodeFilename = ko.observable();

        self.title = ko.observable();
        self.slicer = ko.observable();
        self.slicers = ko.observableArray();
        self.profile = ko.observable();
        self.profiles = ko.observableArray();
        self.printerProfile = ko.observable();

        self.configured_slicers = ko.pureComputed(function() {
            return _.filter(self.slicers(), function(slicer) {
                return slicer.configured;
            });
        });

        self.afterSlicingOptions = [
            {"value": "none", "text": gettext("Do nothing")},
            {"value": "select", "text": gettext("Select for printing")},
            {"value": "print", "text": gettext("Start printing")}
        ];
        self.afterSlicing = ko.observable("none");

        self.show = function(target, file, force, path) {
            if (!self.enableSlicingDialog() && !force) {
                return;
            }

            var filename = file.substr(0, file.lastIndexOf("."));
            if (filename.lastIndexOf("/") != 0) {
                path = path || filename.substr(0, filename.lastIndexOf("/"));
                filename = filename.substr(filename.lastIndexOf("/") + 1);
            }

            self.requestData();
            self.target = target;
            self.file = file;
            self.path = path;
            self.title(_.sprintf(gettext("Slicing %(filename)s"), {filename: filename}));
            self.gcodeFilename(filename);
            self.printerProfile(self.printerProfiles.currentProfile());
            self.afterSlicing("none");
            $("#slicing_configuration_dialog").modal("show");
        };

        self.slicer.subscribe(function(newValue) {
            self.profilesForSlicer(newValue);
        });

        self.enableSlicingDialog = ko.pureComputed(function() {
            return self.configured_slicers().length > 0;
        });

        self.enableSliceButton = ko.pureComputed(function() {
            return self.gcodeFilename() != undefined
                && self.gcodeFilename().trim() != ""
                && self.slicer() != undefined
                && self.profile() != undefined;
        });

        self.requestData = function() {
            return OctoPrint.slicing.listAllSlicersAndProfiles()
                .done(function(data) {
                    self.fromResponse(data);
                });
        };

        self.fromResponse = function(data) {
            self.data = data;

            var selectedSlicer = undefined;
            self.slicers.removeAll();
            _.each(_.values(data), function(slicer) {
                var name = slicer.displayName;
                if (name == undefined) {
                    name = slicer.key;
                }

                if (slicer.default && slicer.configured) {
                    selectedSlicer = slicer.key;
                }

                self.slicers.push({
                    key: slicer.key,
                    name: name,
                    configured: slicer.configured
                });
            });

            if (selectedSlicer != undefined) {
                self.slicer(selectedSlicer);
            }

            self.defaultSlicer = selectedSlicer;
        };

        self.profilesForSlicer = function(key) {
            if (key == undefined) {
                key = self.slicer();
            }
            if (key == undefined || !self.data.hasOwnProperty(key)) {
                return;
            }
            var slicer = self.data[key];

            var selectedProfile = undefined;
            self.profiles.removeAll();
            _.each(_.values(slicer.profiles), function(profile) {
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
                })
            });

            if (selectedProfile != undefined) {
                self.profile(selectedProfile);
            }

            self.defaultProfile = selectedProfile;
        };

        self.slice = function() {
            var gcodeFilename = self._sanitize(self.gcodeFilename());
            if (!_.endsWith(gcodeFilename.toLowerCase(), ".gco")
                && !_.endsWith(gcodeFilename.toLowerCase(), ".gcode")
                && !_.endsWith(gcodeFilename.toLowerCase(), ".g")) {
                gcodeFilename = gcodeFilename + ".gco";
            }

            var data = {
                slicer: self.slicer(),
                profile: self.profile(),
                printerProfile: self.printerProfile(),
                gcode: gcodeFilename
            };

            if (self.path != undefined) {
                data["path"] = self.path;
            }

            if (self.afterSlicing() == "print") {
                data["print"] = true;
            } else if (self.afterSlicing() == "select") {
                data["select"] = true;
            }

            OctoPrint.files.slice(self.target, self.file, data)
                .done(function() {
                    $("#slicing_configuration_dialog").modal("hide");

                    self.gcodeFilename(undefined);
                    self.slicer(self.defaultSlicer);
                    self.profile(self.defaultProfile);
                });
        };

        self._sanitize = function(name) {
            return name.replace(/[^a-zA-Z0-9\-_\.\(\) ]/g, "").replace(/ /g, "_");
        };

        self.onStartup = function() {
            self.requestData();
        };

        self.onEventSettingsUpdated = function(payload) {
            self.requestData();
        };
    }

    OCTOPRINT_VIEWMODELS.push([
        SlicingViewModel,
        ["loginStateViewModel", "printerProfilesViewModel"],
        "#slicing_configuration_dialog"
    ]);
});
