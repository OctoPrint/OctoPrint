function PrinterProfilesViewModel() {
    var self = this;

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
        5
    );
    self.defaultProfile = ko.observable();
    self.currentProfile = ko.observable();

    self.editorName = ko.observable();
    self.editorColor = ko.observable();
    self.editorIdentifier = ko.observable();

    self.editorWidth = ko.observable();
    self.editorDepth = ko.observable();
    self.editorHeight = ko.observable();
    self.editorFormFactor = ko.observable();

    self.editorHeatedBed = ko.observable();

    self.editorExtruders = ko.observable();
    self.editorExtruderOffsets = ko.observableArray();

    self.editorAxisXSpeed = ko.observable();
    self.editorAxisYSpeed = ko.observable();
    self.editorAxisZSpeed = ko.observable();
    self.editorAxisESpeed = ko.observable();

    self.editorAxisXInverted = ko.observable(false);
    self.editorAxisYInverted = ko.observable(false);
    self.editorAxisZInverted = ko.observable(false);

    self.requestData = function() {
        $.ajax({
            url: API_BASEURL + "printerProfiles",
            type: "GET",
            dataType: "json",
            success: self.fromResponse
        })
    };

    self.fromResponse = function(data) {
        var items = [];
        var defaultProfile = undefined;
        var currentProfile = undefined;
        _.each(data.profiles, function(entry) {
            if (entry.default) {
                defaultProfile = entry.id;
            }
            if (entry.current) {
                currentProfile = entry.id;
            }
            items.push({
                id: ko.observable(entry.id),
                name: ko.observable(entry.name),
                model: ko.observable(entry.model),
                volume: {
                    width: ko.observable(entry.volume.width),
                    depth: ko.observable(entry.volume.depth),
                    height: ko.observable(entry.volume.height),
                    formFactor: ko.observable(entry.volume.formFactor)
                },
                heatedBed: ko.observable(entry.heatedBed),
                axes: {
                    x: {
                        speed: ko.observable(entry.axes.x.speed),
                        inverted: ko.observable(entry.axes.x.inverted)
                    },
                    y: {
                        speed: ko.observable(entry.axes.y.speed),
                        inverted: ko.observable(entry.axes.y.inverted)
                    },
                    z: {
                        speed: ko.observable(entry.axes.z.speed),
                        inverted: ko.observable(entry.axes.z.inverted)
                    },
                    e: {
                        speed: ko.observable(entry.axes.e.speed),
                        inverted: ko.observable(entry.axes.e.inverted)
                    }
                },
                isdefault: ko.observable(entry.default),
                iscurrent: ko.observable(entry.current),
                resource: ko.observable(entry.resource)
            });
        });
        self.profiles.updateItems(items);
        self.defaultProfile(defaultProfile);
        self.currentProfile(currentProfile);
    };

    self.addProfile = function() {
        var profile = self._editorData();
        $.ajax({
            url: API_BASEURL + "printerProfiles/" + profile.id,
            type: "PUT",
            dataType: "json",
            contentType: "application/json; charset=UTF-8",
            data: JSON.stringify({profile: profile})
        });
    };

    self.removeProfile = function(data) {
        $.ajax({
            url: data.resource,
            type: "DELETE",
            dataType: "json"
        })
    };

    self.updateProfile = function(identifier, profile) {
        if (profile == undefined) {
            profile = self._editorData();
        }

        $.ajax({
            url: API_BASEURL + "printerProfiles/" + profile.id,
            type: "PATCH",
            dataType: "json",
            contentType: "application/json; charset=UTF-8",
            data: JSON.stringify({profile: profile})
        });
    };

    self._editorData = function() {
        var profile = {
            name: self.editorName(),
            color: self.editorColor(),
            id: self.editorIdentifier(),
            volume: {
                width: self.editorWidth(),
                depth: self.editorDepth(),
                height: self.editorHeight(),
                type: self.editorFormFactor()
            },
            heatedBed: self.editorHeatedBed(),
            extruder: {
                count: self.editorExtruders(),
                offsets: [
                    [0.0, 0.0]
                ]
            },
            axes: {
                x: {
                    speed: self.editorAxisXSpeed(),
                    inverted: self.editorAxisXInverted()
                },
                y: {
                    speed: self.editorAxisYSpeed(),
                    inverted: self.editorAxisYInverted()
                },
                z: {
                    speed: self.editorAxisZSpeed(),
                    inverted: self.editorAxisZInverted()
                }
            }
        };

        if (self.editorExtruders() > 1) {
            for (var i = 1; i < self.editorExtruders(); i++) {
                var offset = [0.0, 0.0];
                if (i < self.editorExtruderOffsets().length) {
                    offset = self.editorExtruderOffsets()[i];
                }
                profile.extruder.offsets.push(offset);
            }
        }

        return profile;
    };

    self.onStartup = function() {
        self.requestData();
    };
}