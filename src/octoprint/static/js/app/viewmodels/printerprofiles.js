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
                    height: 200
                },
                heatedBed: false,
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
        self.editorModel = ko.observable();

        self.editorVolumeWidth = ko.observable();
        self.editorVolumeDepth = ko.observable();
        self.editorVolumeHeight = ko.observable();
        self.editorVolumeFormFactor = ko.observable();

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

        self.koEditorExtruderOffsets = ko.computed(function() {
            var extruderOffsets = self.editorExtruderOffsets();
            var numExtruders = self.editorExtruders();
            if (!numExtruders) {
                numExtruders = 1;
            }

            if (numExtruders > extruderOffsets.length) {
                for (var i = extruderOffsets.length; i < numExtruders; i++) {
                    extruderOffsets[i] = {
                        x: ko.observable(0),
                        y: ko.observable(0)
                    }
                }
                self.editorExtruderOffsets(extruderOffsets);
            }

            return extruderOffsets.slice(0, numExtruders);
        });

        self.makeDefault = function(data) {
            var profile = {
                id: data.id,
                default: true
            };

            self.updateProfile(profile);
        };

        self.requestData = function() {
            $.ajax({
                url: API_BASEURL + "printerprofiles",
                type: "GET",
                dataType: "json",
                success: self.fromResponse
            })
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
            $.ajax({
                url: API_BASEURL + "printerprofiles",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify({profile: profile}),
                success: function() {
                    if (callback !== undefined) {
                        callback();
                    }
                    self.requestData();
                }
            });
        };

        self.removeProfile = function(data) {
            $.ajax({
                url: data.resource,
                type: "DELETE",
                dataType: "json",
                success: self.requestData
            })
        };

        self.updateProfile = function(profile, callback) {
            if (profile == undefined) {
                profile = self._editorData();
            }

            $.ajax({
                url: API_BASEURL + "printerprofiles/" + profile.id,
                type: "PATCH",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify({profile: profile}),
                success: function() {
                    if (callback !== undefined) {
                        callback();
                    }
                    self.requestData();
                }
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

            self.editorHeatedBed(data.heatedBed);

            self.editorNozzleDiameter(data.extruder.nozzleDiameter);
            self.editorExtruders(data.extruder.count);
            var offsets = [];
            _.each(data.extruder.offsets, function(offset) {
                offsets.push({
                    x: ko.observable(offset[0]),
                    y: ko.observable(offset[1])
                });
            });
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
                self.confirmEditProfile(add);
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
            var profile = {
                id: self.editorIdentifier(),
                name: self.editorName(),
                color: self.editorColor(),
                model: self.editorModel(),
                volume: {
                    width: parseFloat(self.editorVolumeWidth()),
                    depth: parseFloat(self.editorVolumeDepth()),
                    height: parseFloat(self.editorVolumeHeight()),
                    formFactor: self.editorVolumeFormFactor()
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
                    }
                }
            };

            if (self.editorExtruders() > 1) {
                for (var i = 1; i < self.editorExtruders(); i++) {
                    var offset = [0.0, 0.0];
                    if (i < self.editorExtruderOffsets().length) {
                        offset = [parseFloat(self.editorExtruderOffsets()[i]["x"]()), parseFloat(self.editorExtruderOffsets()[i]["y"]())];
                    }
                    profile.extruder.offsets.push(offset);
                }
            }

            return profile;
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