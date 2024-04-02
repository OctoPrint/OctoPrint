$(function () {
    var cleanProfile = function () {
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
                origin: "lowerleft",
                custom_box: false
            },
            heatedBed: true,
            heatedChamber: false,
            axes: {
                x: {speed: 6000, inverted: false},
                y: {speed: 6000, inverted: false},
                z: {speed: 200, inverted: false},
                e: {speed: 300, inverted: false}
            },
            extruder: {
                count: 1,
                offsets: [[0, 0]],
                nozzleDiameter: 0.4,
                sharedNozzle: false,
                defaultExtrusionLength: 5
            }
        };
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

        self.volumeFormFactor.subscribe(function (value) {
            if (value == "circular") {
                self.volumeOrigin("center");
            }
        });
        self.volumeOrigin.subscribe(function () {
            self.toBoundingBoxPlaceholders(
                self.defaultBoundingBox(
                    self.volumeWidth(),
                    self.volumeDepth(),
                    self.volumeHeight(),
                    self.volumeOrigin()
                )
            );
        });

        self.heatedBed = ko.observable();
        self.heatedChamber = ko.observable();

        self.nozzleDiameter = ko.observable();
        self.extruders = ko.observable();
        self.extruderOffsets = ko.observableArray();
        self.sharedNozzle = ko.observable();
        self.defaultExtrusionLength = ko.observable();

        self.axisXSpeed = ko.observable();
        self.axisYSpeed = ko.observable();
        self.axisZSpeed = ko.observable();
        self.axisESpeed = ko.observable();

        self.axisXInverted = ko.observable(false);
        self.axisYInverted = ko.observable(false);
        self.axisZInverted = ko.observable(false);
        self.axisEInverted = ko.observable(false);

        self.customBoundingBox = ko.observable(false);
        self.boundingBoxMinX = ko.observable();
        self.boundingBoxMinY = ko.observable();
        self.boundingBoxMinZ = ko.observable();
        self.boundingBoxMaxX = ko.observable();
        self.boundingBoxMaxY = ko.observable();
        self.boundingBoxMaxZ = ko.observable();
        self.boundingBoxMinXPlaceholder = ko.observable();
        self.boundingBoxMinYPlaceholder = ko.observable();
        self.boundingBoxMinZPlaceholder = ko.observable();
        self.boundingBoxMaxXPlaceholder = ko.observable();
        self.boundingBoxMaxYPlaceholder = ko.observable();
        self.boundingBoxMaxZPlaceholder = ko.observable();

        self.koExtruderOffsets = ko.pureComputed(function () {
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
                    };
                }
                self.extruderOffsets(extruderOffsets);
            }

            return extruderOffsets.slice(0, numExtruders - 1);
        });

        self.nameInvalid = ko.pureComputed(function () {
            return !self.name();
        });

        self.sizeInvalid = ko.pureComputed(function () {
            return (
                !(self.volumeWidth() > 0 && self.volumeWidth() < 10000) ||
                !(self.volumeDepth() > 0 && self.volumeDepth() < 10000) ||
                !(self.volumeHeight() > 0 && self.volumeHeight() < 10000)
            );
        });

        self.identifierInvalid = ko.pureComputed(function () {
            var identifier = self.identifier();
            var placeholder = self.identifierPlaceholder();
            var data = identifier;
            if (!identifier) {
                data = placeholder;
            }

            var validCharacters = data && data == self._sanitize(data);

            var existingProfile = self.profiles.getItem(function (item) {
                return item.id == data;
            });
            return (
                !data ||
                !validCharacters ||
                (self.isNew() && existingProfile != undefined)
            );
        });

        self.identifierInvalidText = ko.pureComputed(function () {
            if (!self.identifierInvalid()) {
                return "";
            }

            if (!self.identifier() && !self.identifierPlaceholder()) {
                return gettext("Identifier must be set");
            } else if (self.identifier() != self._sanitize(self.identifier())) {
                return gettext(
                    "Invalid characters, only a-z, A-Z, 0-9, -, ., _, ( and ) are allowed"
                );
            } else {
                return gettext("A profile with such an identifier already exists");
            }
        });

        self.name.subscribe(function () {
            self.identifierPlaceholder(self._sanitize(self.name()).toLowerCase());
        });

        self.valid = function () {
            return (
                !self.nameInvalid() && !self.identifierInvalid() && !self.sizeInvalid()
            );
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

        self.availableOrigins = ko.pureComputed(function () {
            var formFactor = self.volumeFormFactor();

            var possibleOrigins = {
                lowerleft: gettext("Lower Left"),
                center: gettext("Center")
            };

            var keys = [];
            if (formFactor == "rectangular") {
                keys = ["lowerleft", "center"];
            } else if (formFactor == "circular") {
                keys = ["center"];
            }

            var result = [];
            _.each(keys, function (key) {
                result.push({key: key, name: possibleOrigins[key]});
            });
            return result;
        });

        self.fromProfileData = function (data) {
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

            if (data.volume.custom_box) {
                self.toBoundingBoxData(data.volume.custom_box, true);
            } else {
                var box = self.defaultBoundingBox(
                    data.volume.width,
                    data.volume.depth,
                    data.volume.height,
                    data.volume.origin
                );
                self.toBoundingBoxData(box, false);
            }

            self.heatedBed(data.heatedBed);
            self.heatedChamber(data.heatedChamber);

            self.nozzleDiameter(data.extruder.nozzleDiameter);
            self.sharedNozzle(data.extruder.sharedNozzle);
            self.defaultExtrusionLength(data.extruder.defaultExtrusionLength);
            self.extruders(data.extruder.count);
            var offsets = [];
            if (data.extruder.count > 1) {
                _.each(_.slice(data.extruder.offsets, 1), function (offset, index) {
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

        self.toProfileData = function () {
            var identifier = self.identifier();
            if (!identifier) {
                identifier = self.identifierPlaceholder();
            }

            var defaultProfile = cleanProfile();
            var valid = function (value, f, def) {
                var v = f(value);
                if (isNaN(v)) {
                    return def;
                }
                return v;
            };
            var runChecks = function (value, def, checks) {
                if (checks.gt !== undefined) {
                    if (!(value > checks.gt)) {
                        return def;
                    }
                }
                if (checks.lt !== undefined) {
                    if (!(value < checks.lt)) {
                        return def;
                    }
                }
                return value;
            };
            var validFloat = function (value, def, checks) {
                var v = valid(value, parseFloat, def);
                if (checks) {
                    v = runChecks(value, def, checks);
                }
                return v;
            };
            var validInt = function (value, def, checks) {
                var v = valid(value, parseInt, def);
                if (checks) {
                    v = runChecks(value, def, checks);
                }
                return v;
            };

            var profile = {
                id: identifier,
                name: self.name(),
                color: self.color(),
                model: self.model(),
                volume: {
                    width: validFloat(self.volumeWidth(), defaultProfile.volume.width, {
                        gt: 0,
                        lt: 10000
                    }),
                    depth: validFloat(self.volumeDepth(), defaultProfile.volume.depth, {
                        gt: 0,
                        lt: 10000
                    }),
                    height: validFloat(
                        self.volumeHeight(),
                        defaultProfile.volume.height,
                        {gt: 0, lt: 10000}
                    ),
                    formFactor: self.volumeFormFactor(),
                    origin: self.volumeOrigin()
                },
                heatedBed: self.heatedBed(),
                heatedChamber: self.heatedChamber(),
                extruder: {
                    count: runChecks(parseInt(self.extruders()), 1, {gt: 0, lt: 100}),
                    offsets: [[0.0, 0.0]],
                    nozzleDiameter: validFloat(
                        self.nozzleDiameter(),
                        defaultProfile.extruder.nozzleDiameter
                    ),
                    sharedNozzle: self.sharedNozzle(),
                    defaultExtrusionLength: validInt(
                        self.defaultExtrusionLength(),
                        defaultProfile.extruder.defaultExtrusionLength
                    )
                },
                axes: {
                    x: {
                        speed: validInt(self.axisXSpeed(), defaultProfile.axes.x.speed, {
                            gt: 0
                        }),
                        inverted: self.axisXInverted()
                    },
                    y: {
                        speed: validInt(self.axisYSpeed(), defaultProfile.axes.y.speed, {
                            gt: 0
                        }),
                        inverted: self.axisYInverted()
                    },
                    z: {
                        speed: validInt(self.axisZSpeed(), defaultProfile.axes.z.speed, {
                            gt: 0
                        }),
                        inverted: self.axisZInverted()
                    },
                    e: {
                        speed: validInt(self.axisESpeed(), defaultProfile.axes.e.speed, {
                            gt: 0
                        }),
                        inverted: self.axisEInverted()
                    }
                }
            };

            self.fillBoundingBoxData(profile);

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

            if (profile.volume.formFactor == "circular") {
                profile.volume.depth = profile.volume.width;
            }

            return profile;
        };

        self.defaultBoundingBox = function (width, depth, height, origin) {
            if (origin == "center") {
                var halfWidth = width / 2.0;
                var halfDepth = depth / 2.0;

                return {
                    x_min: -halfWidth,
                    y_min: -halfDepth,
                    z_min: 0.0,
                    x_max: halfWidth,
                    y_max: halfDepth,
                    z_max: height
                };
            } else {
                return {
                    x_min: 0.0,
                    y_min: 0.0,
                    z_min: 0.0,
                    x_max: width,
                    y_max: depth,
                    z_max: height
                };
            }
        };

        self.toBoundingBoxData = function (box, custom) {
            self.customBoundingBox(custom);
            if (custom) {
                self.boundingBoxMinX(box.x_min);
                self.boundingBoxMinY(box.y_min);
                self.boundingBoxMinZ(box.z_min);
                self.boundingBoxMaxX(box.x_max);
                self.boundingBoxMaxY(box.y_max);
                self.boundingBoxMaxZ(box.z_max);
            } else {
                self.boundingBoxMinX(undefined);
                self.boundingBoxMinY(undefined);
                self.boundingBoxMinZ(undefined);
                self.boundingBoxMaxX(undefined);
                self.boundingBoxMaxY(undefined);
                self.boundingBoxMaxZ(undefined);
            }
            self.toBoundingBoxPlaceholders(box);
        };

        self.toBoundingBoxPlaceholders = function (box) {
            self.boundingBoxMinXPlaceholder(box.x_min);
            self.boundingBoxMinYPlaceholder(box.y_min);
            self.boundingBoxMinZPlaceholder(box.z_min);
            self.boundingBoxMaxXPlaceholder(box.x_max);
            self.boundingBoxMaxYPlaceholder(box.y_max);
            self.boundingBoxMaxZPlaceholder(box.z_max);
        };

        self.fillBoundingBoxData = function (profile) {
            if (self.customBoundingBox()) {
                var defaultBox = self.defaultBoundingBox(
                    self.volumeWidth(),
                    self.volumeDepth(),
                    self.volumeHeight(),
                    self.volumeOrigin()
                );
                profile.volume.custom_box = {
                    x_min:
                        self.boundingBoxMinX() !== undefined
                            ? Math.min(self.boundingBoxMinX(), defaultBox.x_min)
                            : defaultBox.x_min,
                    y_min:
                        self.boundingBoxMinY() !== undefined
                            ? Math.min(self.boundingBoxMinY(), defaultBox.y_min)
                            : defaultBox.y_min,
                    z_min:
                        self.boundingBoxMinZ() !== undefined
                            ? Math.min(self.boundingBoxMinZ(), defaultBox.z_min)
                            : defaultBox.z_min,
                    x_max:
                        self.boundingBoxMaxX() !== undefined
                            ? Math.max(self.boundingBoxMaxX(), defaultBox.x_max)
                            : defaultBox.x_max,
                    y_max:
                        self.boundingBoxMaxY() !== undefined
                            ? Math.max(self.boundingBoxMaxY(), defaultBox.y_max)
                            : defaultBox.y_max,
                    z_max:
                        self.boundingBoxMaxZ() !== undefined
                            ? Math.max(self.boundingBoxMaxZ(), defaultBox.z_max)
                            : defaultBox.z_max
                };
            } else {
                profile.volume.custom_box = false;
            }
        };

        self._sanitize = function (name) {
            return name.replace(/[^a-zA-Z0-9\-_\.\(\) ]/g, "").replace(/ /g, "_");
        };

        self.fromProfileData(cleanProfile());
    }

    function PrinterProfilesViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.access = parameters[1];

        self.requestInProgress = ko.observable(false);

        self.profiles = new ItemListHelper(
            "printerProfiles",
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

        self.createProfileEditor = function (data) {
            var editor = new EditedProfileViewModel(self.profiles);
            if (data !== undefined) {
                editor.fromProfileData(data);
            }
            return editor;
        };

        self.editor = self.createProfileEditor();
        self.currentProfileData = ko.observable();

        self.enableEditorSubmitButton = ko.pureComputed(function () {
            return self.editor.valid() && !self.requestInProgress();
        });

        self.makeDefault = function (data) {
            var profile = {
                id: data.id,
                default: true
            };

            self.updateProfile(profile);
        };

        self.canMakeDefault = function (data) {
            return !data.isdefault();
        };

        self.canRemove = function (data) {
            return !data.iscurrent() && !data.isdefault();
        };

        self.requestData = function () {
            if (!self.loginState.hasPermission(self.access.permissions.CONNECTION)) {
                return;
            }

            return OctoPrint.printerprofiles.list().done(self.fromResponse);
        };

        self.fromResponse = function (data) {
            var items = [];
            var defaultProfile = undefined;
            var currentProfile = undefined;
            var currentProfileData = undefined;
            _.each(data.profiles, function (entry) {
                if (entry.default) {
                    defaultProfile = entry.id;
                }
                if (entry.current) {
                    currentProfile = entry.id;
                    currentProfileData = ko.mapping.fromJS(
                        entry,
                        self.currentProfileData
                    );
                }
                entry["isdefault"] = ko.observable(entry.default);
                entry["iscurrent"] = ko.observable(entry.current);
                items.push(entry);
            });
            self.profiles.updateItems(items);
            self.defaultProfile(defaultProfile);

            if (currentProfile && currentProfileData) {
                self.currentProfile(currentProfile);
                self.currentProfileData(currentProfileData);
            } else {
                // shouldn't normally happen, but just to not have anything else crash...
                log.warn(
                    "Current printer profile could not be detected, using default values"
                );
                self.currentProfile("");
                self.currentProfileData(
                    ko.mapping.fromJS(cleanProfile(), self.currentProfileData)
                );
            }
        };

        self.addProfile = function (callback) {
            var profile = self.editor.toProfileData();
            self.requestInProgress(true);
            OctoPrint.printerprofiles
                .add(profile)
                .done(function () {
                    if (callback !== undefined) {
                        callback();
                    }
                    self.requestData();
                })
                .fail(function (xhr) {
                    var text = gettext(
                        "There was unexpected error while saving the printer profile, please consult the logs."
                    );
                    new PNotify({
                        title: gettext("Could not add profile"),
                        text: text,
                        type: "error",
                        hide: false
                    });
                })
                .always(function () {
                    self.requestInProgress(false);
                });
        };

        self.removeProfile = function (data) {
            var perform = function () {
                self.requestInProgress(true);
                OctoPrint.printerprofiles
                    .delete(data.id, {url: data.resource})
                    .done(function () {
                        self.requestData().always(function () {
                            self.requestInProgress(false);
                        });
                    })
                    .fail(function (xhr) {
                        var text;
                        if (xhr.status == 409) {
                            text = gettext(
                                "Cannot delete the default profile or the currently active profile."
                            );
                        } else {
                            text = gettext(
                                "There was unexpected error while removing the printer profile, please consult the logs."
                            );
                        }
                        new PNotify({
                            title: gettext("Could not delete profile"),
                            text: text,
                            type: "error",
                            hide: false
                        });
                        self.requestInProgress(false);
                    });
            };

            showConfirmationDialog(
                _.sprintf(
                    gettext('You are about to delete the printer profile "%(name)s".'),
                    {name: _.escape(data.name)}
                ),
                perform
            );
        };

        self.updateProfile = function (profile, callback) {
            if (profile == undefined) {
                profile = self.editor.toProfileData();
            }

            self.requestInProgress(true);
            OctoPrint.printerprofiles
                .update(profile.id, profile)
                .done(function () {
                    if (callback !== undefined) {
                        callback();
                    }
                    self.requestData().always(function () {
                        self.requestInProgress(false);
                    });
                })
                .fail(function () {
                    var text = gettext(
                        "There was unexpected error while updating the printer profile, please consult the logs."
                    );
                    new PNotify({
                        title: gettext("Could not update profile"),
                        text: text,
                        type: "error",
                        hide: false
                    });
                    self.requestInProgress(false);
                });
        };

        self.showEditProfileDialog = function (data) {
            self.editor.fromProfileData(data);

            var editDialog = $("#settings_printerProfiles_editDialog");
            var confirmButton = $("button.btn-confirm", editDialog);
            var dialogTitle = $("h3.modal-title", editDialog);

            var add = data === undefined;
            dialogTitle.text(
                add
                    ? gettext("Add Printer Profile")
                    : _.sprintf(gettext('Edit Printer Profile "%(name)s"'), {
                          name: _.escape(data.name)
                      })
            );
            confirmButton.unbind("click");
            confirmButton.bind("click", function () {
                if (self.enableEditorSubmitButton()) {
                    self.confirmEditProfile(add);
                }
            });

            $('ul.nav-pills a[data-toggle="tab"]:first', editDialog).tab("show");
            editDialog
                .modal({
                    minHeight: function () {
                        return Math.max($.fn.modal.defaults.maxHeight() - 80, 250);
                    }
                })
                .css({
                    "margin-left": function () {
                        return -($(this).width() / 2);
                    }
                });
        };

        self.confirmEditProfile = function (add) {
            var callback = function () {
                $("#settings_printerProfiles_editDialog").modal("hide");
            };

            if (add) {
                self.addProfile(callback);
            } else {
                self.updateProfile(undefined, callback);
            }
        };

        self.onSettingsShown = self.requestData;

        self.onUserPermissionsChanged =
            self.onUserLoggedIn =
            self.onUserLoggedOut =
                function () {
                    self.requestData();
                };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: PrinterProfilesViewModel,
        dependencies: ["loginStateViewModel", "accessViewModel"]
    });
});
