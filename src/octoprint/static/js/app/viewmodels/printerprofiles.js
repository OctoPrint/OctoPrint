$(function() {
    function PrinterProfilesViewModel() {
        var self = this;

        self._cleanProfile = function() {
            return {
                id: "",
                name: "",
                model: "",
                color: "default",
                volume: {
                    formFactor: "rectangular",
                    width: 200,
                    depth: 200,
                    height: 200,
                    origin: "lowerleft"
                },
                heatedBed: true,
                axes: {
                    x: {speed: 6000, inverted: false},
                    y: {speed: 6000, inverted: false},
                    z: {speed: 200, inverted: false},
                    e: {speed: 300, inverted: false}
                },
                extruder: {
                    count: 1,
                    offsets: [
                        [0,0]
                    ],
                    nozzleDiameter: 0.4
                }
            }
        };

        self.requestInProgress = ko.observable(false);

        self.profiles = new ItemListHelper(
            "printerProfiles",
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

        self.currentProfileData = ko.observable(ko.mapping.fromJS(self._cleanProfile()));

        self.editorNew = ko.observable(false);

        self.editorName = ko.observable();
        self.editorColor = ko.observable();
        self.editorIdentifier = ko.observable();
        self.editorIdentifierPlaceholder = ko.observable();
        self.editorModel = ko.observable();

        self.editorVolumeWidth = ko.observable();
        self.editorVolumeDepth = ko.observable();
        self.editorVolumeHeight = ko.observable();
        self.editorVolumeFormFactor = ko.observable();
        self.editorVolumeOrigin = ko.observable();

        self.editorVolumeFormFactor.subscribe(function(value) {
            if (value == "circular") {
                self.editorVolumeOrigin("center");
            }
        });

        self.editorHeatedBed = ko.observable();

        self.editorNozzleDiameter = ko.observable();
        self.editorExtruders = ko.observable();
        self.editorExtruderOffsets = ko.observableArray();

        self.editorAxisXSpeed = ko.observable();
        self.editorAxisYSpeed = ko.observable();
        self.editorAxisZSpeed = ko.observable();
        self.editorAxisESpeed = ko.observable();

        self.editorAxisXInverted = ko.observable(false);
        self.editorAxisYInverted = ko.observable(false);
        self.editorAxisZInverted = ko.observable(false);
        self.editorAxisEInverted = ko.observable(false);

        self.availableColors = ko.observable([
            {key: "default", name: gettext("default")},
            {key: "red", name: gettext("red")},
            {key: "orange", name: gettext("orange")},
            {key: "yellow", name: gettext("yellow")},
            {key: "green", name: gettext("green")},
            {key: "blue", name: gettext("blue")},
            {key: "black", name: gettext("black")}
        ]);

        self.availableOrigins = ko.pureComputed(function() {
            var formFactor = self.editorVolumeFormFactor();

            var possibleOrigins = {
                "lowerleft": gettext("Lower Left"),
                "center": gettext("Center")
            };

            var keys = [];
            if (formFactor == "rectangular") {
                keys = ["lowerleft", "center"];
            } else if (formFactor == "circular") {
                keys = ["center"];
            }

            var result = [];
            _.each(keys, function(key) {
               result.push({key: key, name: possibleOrigins[key]});
            });
            return result;
        });

        self.koEditorExtruderOffsets = ko.pureComputed(function() {
            var extruderOffsets = self.editorExtruderOffsets();
            var numExtruders = self.editorExtruders();
            if (!numExtruders) {
                numExtruders = 1;
            }

            if (numExtruders - 1 > extruderOffsets.length) {
                for (var i = extruderOffsets.length; i < numExtruders; i++) {
                    extruderOffsets[i] = {
                        idx: i + 1,
                        x: ko.observable(0),
                        y: ko.observable(0)
                    }
                }
                self.editorExtruderOffsets(extruderOffsets);
            }

            return extruderOffsets.slice(0, numExtruders - 1);
        });

        self.editorNameInvalid = ko.pureComputed(function() {
            return !self.editorName();
        });

        self.editorIdentifierInvalid = ko.pureComputed(function() {
            var identifier = self.editorIdentifier();
            var placeholder = self.editorIdentifierPlaceholder();
            var data = identifier;
            if (!identifier) {
                data = placeholder;
            }

            var validCharacters = (data && (data == self._sanitize(data)));

            var existingProfile = self.profiles.getItem(function(item) {return item.id == data});
            return !data || !validCharacters || (self.editorNew() && existingProfile != undefined);
        });

        self.editorIdentifierInvalidText = ko.pureComputed(function() {
            if (!self.editorIdentifierInvalid()) {
                return "";
            }

            if (!self.editorIdentifier() && !self.editorIdentifierPlaceholder()) {
                return gettext("Identifier must be set");
            } else if (self.editorIdentifier() != self._sanitize(self.editorIdentifier())) {
                return gettext("Invalid characters, only a-z, A-Z, 0-9, -, ., _, ( and ) are allowed")
            } else {
                return gettext("A profile with such an identifier already exists");
            }
        });

        self.enableEditorSubmitButton = ko.pureComputed(function() {
            return !self.editorNameInvalid() && !self.editorIdentifierInvalid() && !self.requestInProgress();
        });

        self.editorName.subscribe(function() {
            self.editorIdentifierPlaceholder(self._sanitize(self.editorName()).toLowerCase());
        });

        self.makeDefault = function(data) {
            var profile = {
                id: data.id,
                default: true
            };

            self.updateProfile(profile);
        };

        self.requestData = function() {
            OctoPrint.printerprofiles.get()
                .done(self.fromResponse);
        };

        self.fromResponse = function(data) {
            var items = [];
            var defaultProfile = undefined;
            var currentProfile = undefined;
            var currentProfileData = undefined;
            _.each(data.profiles, function(entry) {
                if (entry.default) {
                    defaultProfile = entry.id;
                }
                if (entry.current) {
                    currentProfile = entry.id;
                    currentProfileData = ko.mapping.fromJS(entry, self.currentProfileData);
                }
                entry["isdefault"] = ko.observable(entry.default);
                entry["iscurrent"] = ko.observable(entry.current);
                items.push(entry);
            });
            self.profiles.updateItems(items);
            self.defaultProfile(defaultProfile);
            self.currentProfile(currentProfile);
            self.currentProfileData(currentProfileData);
        };

        self.addProfile = function(callback) {
            var profile = self._editorData();
            self.requestInProgress(true);
            OctoPrint.printerprofiles.add(profile)
                .done(function() {
                    if (callback !== undefined) {
                        callback();
                    }
                    self.requestData();
                })
                .fail(function() {
                    var text = gettext("There was unexpected error while saving the printer profile, please consult the logs.");
                    new PNotify({title: gettext("Saving failed"), text: text, type: "error", hide: false});
                })
                .always(function() {
                    self.requestInProgress(false);
                });
        };

        self.removeProfile = function(data) {
            self.requestInProgress(true);
            OctoPrint.printerprofiles.delete(data.id, {url: data.resource})
                .done(function() {
                    self.requestData();
                })
                .fail(function() {
                    var text = gettext("There was unexpected error while removing the printer profile, please consult the logs.");
                    new PNotify({title: gettext("Saving failed"), text: text, type: "error", hide: false});
                })
                .always(function() {
                    self.requestInProgress(false);
                });
        };

        self.updateProfile = function(profile, callback) {
            if (profile == undefined) {
                profile = self._editorData();
            }

            self.requestInProgress(true);
            OctoPrint.printerprofiles.update(profile.id, profile)
                .done(function() {
                    if (callback !== undefined) {
                        callback();
                    }
                    self.requestData();
                })
                .fail(function() {
                    var text = gettext("There was unexpected error while updating the printer profile, please consult the logs.");
                    new PNotify({title: gettext("Saving failed"), text: text, type: "error", hide: false});
                })
                .always(function() {
                    self.requestInProgress(false);
                });
        };

        self.showEditProfileDialog = function(data) {
            var add = false;
            if (data == undefined) {
                data = self._cleanProfile();
                add = true;
            }

            self.editorNew(add);

            self.editorIdentifier(data.id);
            self.editorName(data.name);
            self.editorColor(data.color);
            self.editorModel(data.model);

            self.editorVolumeWidth(data.volume.width);
            self.editorVolumeDepth(data.volume.depth);
            self.editorVolumeHeight(data.volume.height);
            self.editorVolumeFormFactor(data.volume.formFactor);
            self.editorVolumeOrigin(data.volume.origin);

            self.editorHeatedBed(data.heatedBed);

            self.editorNozzleDiameter(data.extruder.nozzleDiameter);
            self.editorExtruders(data.extruder.count);
            var offsets = [];
            if (data.extruder.count > 1) {
                _.each(_.slice(data.extruder.offsets, 1), function(offset, index) {
                    offsets.push({
                        idx: index + 1,
                        x: ko.observable(offset[0]),
                        y: ko.observable(offset[1])
                    });
                });
            }
            self.editorExtruderOffsets(offsets);

            self.editorAxisXSpeed(data.axes.x.speed);
            self.editorAxisXInverted(data.axes.x.inverted);
            self.editorAxisYSpeed(data.axes.y.speed);
            self.editorAxisYInverted(data.axes.y.inverted);
            self.editorAxisZSpeed(data.axes.z.speed);
            self.editorAxisZInverted(data.axes.z.inverted);
            self.editorAxisESpeed(data.axes.e.speed);
            self.editorAxisEInverted(data.axes.e.inverted);

            var editDialog = $("#settings_printerProfiles_editDialog");
            var confirmButton = $("button.btn-confirm", editDialog);
            var dialogTitle = $("h3.modal-title", editDialog);

            dialogTitle.text(add ? gettext("Add Printer Profile") : _.sprintf(gettext("Edit Printer Profile \"%(name)s\""), {name: data.name}));
            confirmButton.unbind("click");
            confirmButton.bind("click", function() {
                if (self.enableEditorSubmitButton()) {
                    self.confirmEditProfile(add);
                }
            });
            editDialog.modal("show");
        };

        self.confirmEditProfile = function(add) {
            var callback = function() {
                $("#settings_printerProfiles_editDialog").modal("hide");
            };

            if (add) {
                self.addProfile(callback);
            } else {
                self.updateProfile(undefined, callback);
            }
        };

        self._editorData = function() {
            var identifier = self.editorIdentifier();
            if (!identifier) {
                identifier = self.editorIdentifierPlaceholder();
            }

            var profile = {
                id: identifier,
                name: self.editorName(),
                color: self.editorColor(),
                model: self.editorModel(),
                volume: {
                    width: parseFloat(self.editorVolumeWidth()),
                    depth: parseFloat(self.editorVolumeDepth()),
                    height: parseFloat(self.editorVolumeHeight()),
                    formFactor: self.editorVolumeFormFactor(),
                    origin: self.editorVolumeOrigin()
                },
                heatedBed: self.editorHeatedBed(),
                extruder: {
                    count: parseInt(self.editorExtruders()),
                    offsets: [
                        [0.0, 0.0]
                    ],
                    nozzleDiameter: parseFloat(self.editorNozzleDiameter())
                },
                axes: {
                    x: {
                        speed: parseInt(self.editorAxisXSpeed()),
                        inverted: self.editorAxisXInverted()
                    },
                    y: {
                        speed: parseInt(self.editorAxisYSpeed()),
                        inverted: self.editorAxisYInverted()
                    },
                    z: {
                        speed: parseInt(self.editorAxisZSpeed()),
                        inverted: self.editorAxisZInverted()
                    },
                    e: {
                        speed: parseInt(self.editorAxisESpeed()),
                        inverted: self.editorAxisEInverted()
                    }
                }
            };

            if (self.editorExtruders() > 1) {
                for (var i = 0; i < self.editorExtruders() - 1; i++) {
                    var offset = [0.0, 0.0];
                    if (i < self.editorExtruderOffsets().length) {
                        try {
                            offset = [parseFloat(self.editorExtruderOffsets()[i]["x"]()), parseFloat(self.editorExtruderOffsets()[i]["y"]())];
                        } catch (exc) {
                            log.error("Invalid offset in profile", identifier, "for extruder", i+1, ":", self.editorExtruderOffsets()[i]["x"], ",", self.editorExtruderOffsets()[i]["y"]);
                        }
                    }
                    profile.extruder.offsets.push(offset);
                }
            }

            return profile;
        };

        self._sanitize = function(name) {
            return name.replace(/[^a-zA-Z0-9\-_\.\(\) ]/g, "").replace(/ /g, "_");
        };

        self.onSettingsShown = self.requestData;
        self.onStartup = self.requestData;
    }

    OCTOPRINT_VIEWMODELS.push([
        PrinterProfilesViewModel,
        [],
        []
    ]);
});
