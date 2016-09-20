$(function() {
    var cleanProfile = function() {
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

    function EditedProfileViewModel(profiles) {
        var self = this;

        self.profiles = profiles;

        self.isNew = ko.observable(false);

        self.name = ko.observable();
        self.color = ko.observable();
        self.identifier = ko.observable();
        self.identifierPlaceholder = ko.observable();
        self.model = ko.observable();

        self.volumeWidth = ko.observable();
        self.volumeHeight = ko.observable();
        self.volumeDepth = ko.observable();
        self.volumeFormFactor = ko.observable();
        self.volumeOrigin = ko.observable();

        self.volumeFormFactor.subscribe(function(value) {
            if (value == "circular") {
                self.volumeOrigin("center");
            }
        });

        self.heatedBed = ko.observable();

        self.nozzleDiameter = ko.observable();
        self.extruders = ko.observable();
        self.extruderOffsets = ko.observableArray();

        self.axisXSpeed = ko.observable();
        self.axisYSpeed = ko.observable();
        self.axisZSpeed = ko.observable();
        self.axisESpeed = ko.observable();

        self.axisXInverted = ko.observable(false);
        self.axisYInverted = ko.observable(false);
        self.axisZInverted = ko.observable(false);
        self.axisEInverted = ko.observable(false);

        self.koExtruderOffsets = ko.pureComputed(function() {
            var extruderOffsets = self.extruderOffsets();
            var numExtruders = self.extruders();
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
                self.extruderOffsets(extruderOffsets);
            }

            return extruderOffsets.slice(0, numExtruders - 1);
        });

        self.nameInvalid = ko.pureComputed(function() {
            return !self.name();
        });

        self.identifierInvalid = ko.pureComputed(function() {
            var identifier = self.identifier();
            var placeholder = self.identifierPlaceholder();
            var data = identifier;
            if (!identifier) {
                data = placeholder;
            }

            var validCharacters = (data && (data == self._sanitize(data)));

            var existingProfile = self.profiles.getItem(function(item) {return item.id == data});
            return !data || !validCharacters || (self.isNew() && existingProfile != undefined);
        });

        self.identifierInvalidText = ko.pureComputed(function() {
            if (!self.identifierInvalid()) {
                return "";
            }

            if (!self.identifier() && !self.identifierPlaceholder()) {
                return gettext("Identifier must be set");
            } else if (self.identifier() != self._sanitize(self.identifier())) {
                return gettext("Invalid characters, only a-z, A-Z, 0-9, -, ., _, ( and ) are allowed")
            } else {
                return gettext("A profile with such an identifier already exists");
            }
        });

        self.name.subscribe(function() {
            self.identifierPlaceholder(self._sanitize(self.name()).toLowerCase());
        });

        self.valid = function() {
            return !self.nameInvalid() && !self.identifierInvalid();
        };

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
            var formFactor = self.volumeFormFactor();

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

        self.fromProfileData = function(data) {
            self.isNew(data === undefined);

            if (data === undefined) {
                data = cleanProfile();
            }

            self.identifier(data.id);
            self.name(data.name);
            self.color(data.color);
            self.model(data.model);

            self.volumeWidth(data.volume.width);
            self.volumeHeight(data.volume.height);
            self.volumeDepth(data.volume.depth);
            self.volumeFormFactor(data.volume.formFactor);
            self.volumeOrigin(data.volume.origin);

            self.heatedBed(data.heatedBed);

            self.nozzleDiameter(data.extruder.nozzleDiameter);
            self.extruders(data.extruder.count);
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
            self.extruderOffsets(offsets);

            self.axisXSpeed(data.axes.x.speed);
            self.axisXInverted(data.axes.x.inverted);
            self.axisYSpeed(data.axes.y.speed);
            self.axisYInverted(data.axes.y.inverted);
            self.axisZSpeed(data.axes.z.speed);
            self.axisZInverted(data.axes.z.inverted);
            self.axisESpeed(data.axes.e.speed);
            self.axisEInverted(data.axes.e.inverted);
        };

        self.toProfileData = function() {
            var identifier = self.identifier();
            if (!identifier) {
                identifier = self.identifierPlaceholder();
            }

            var defaultProfile = cleanProfile();
            var valid = function(value, f, def) {
                var v = f(value);
                if (isNaN(v)) {
                    return def;
                }
                return v;
            };
            var validFloat = function(value, def) {
                return valid(value, parseFloat, def);
            };
            var validInt = function(value, def) {
                return valid(value, parseInt, def);
            };

            var profile = {
                id: identifier,
                name: self.name(),
                color: self.color(),
                model: self.model(),
                volume: {
                    width: validFloat(self.volumeWidth(), defaultProfile.volume.width),
                    depth: validFloat(self.volumeDepth(), defaultProfile.volume.depth),
                    height: validFloat(self.volumeHeight(), defaultProfile.volume.height),
                    formFactor: self.volumeFormFactor(),
                    origin: self.volumeOrigin()
                },
                heatedBed: self.heatedBed(),
                extruder: {
                    count: parseInt(self.extruders()),
                    offsets: [
                        [0.0, 0.0]
                    ],
                    nozzleDiameter: validFloat(self.nozzleDiameter(), defaultProfile.extruder.nozzleDiameter)
                },
                axes: {
                    x: {
                        speed: validInt(self.axisXSpeed(), defaultProfile.axes.x.speed),
                        inverted: self.axisXInverted()
                    },
                    y: {
                        speed: validInt(self.axisYSpeed(), defaultProfile.axes.y.speed),
                        inverted: self.axisYInverted()
                    },
                    z: {
                        speed: validInt(self.axisZSpeed(), defaultProfile.axes.z.speed),
                        inverted: self.axisZInverted()
                    },
                    e: {
                        speed: validInt(self.axisESpeed(), defaultProfile.axes.e.speed),
                        inverted: self.axisEInverted()
                    }
                }
            };

            var offsetX, offsetY;
            if (self.extruders() > 1) {
                for (var i = 0; i < self.extruders() - 1; i++) {
                    var offset = [0.0, 0.0];
                    if (i < self.extruderOffsets().length) {
                        offsetX = validFloat(self.extruderOffsets()[i]["x"](), 0.0);
                        offsetY = validFloat(self.extruderOffsets()[i]["y"](), 0.0);
                        offset = [offsetX, offsetY];
                    }
                    profile.extruder.offsets.push(offset);
                }
            }

            return profile;
        };

        self._sanitize = function(name) {
            return name.replace(/[^a-zA-Z0-9\-_\.\(\) ]/g, "").replace(/ /g, "_");
        };

        self.fromProfileData(cleanProfile());
    }

    function PrinterProfilesViewModel() {
        var self = this;

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

        self.createProfileEditor = function(data) {
            var editor = new EditedProfileViewModel(self.profiles);
            if (data !== undefined) {
                editor.fromProfileData(data);
            }
            return editor;
        };

        self.editor = self.createProfileEditor();
        self.currentProfileData = ko.observable(ko.mapping.fromJS(cleanProfile()));

        self.enableEditorSubmitButton = ko.pureComputed(function() {
            return self.editor.valid() && !self.requestInProgress();
        });

        self.makeDefault = function(data) {
            var profile = {
                id: data.id,
                default: true
            };

            self.updateProfile(profile);
        };

        self.requestData = function() {
            OctoPrint.printerprofiles.list()
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
            var profile = self.editor.toProfileData();
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
                profile = self.editor.toProfileData();
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
            self.editor.fromProfileData(data);

            var editDialog = $("#settings_printerProfiles_editDialog");
            var confirmButton = $("button.btn-confirm", editDialog);
            var dialogTitle = $("h3.modal-title", editDialog);

            var add = data === undefined;
            dialogTitle.text(add ? gettext("Add Printer Profile") : _.sprintf(gettext("Edit Printer Profile \"%(name)s\""), {name: data.name}));
            confirmButton.unbind("click");
            confirmButton.bind("click", function() {
                if (self.enableEditorSubmitButton()) {
                    self.confirmEditProfile(add);
                }
            });

            $('ul.nav-pills a[data-toggle="tab"]:first', editDialog).tab("show");
            editDialog.modal({
                minHeight: function() { return Math.max($.fn.modal.defaults.maxHeight() - 80, 250); }
            }).css({
                width: 'auto',
                'margin-left': function() { return -($(this).width() /2); }
            });
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

        self.onSettingsShown = self.requestData;
        self.onStartup = self.requestData;
    }

    OCTOPRINT_VIEWMODELS.push([
        PrinterProfilesViewModel,
        [],
        []
    ]);
});
