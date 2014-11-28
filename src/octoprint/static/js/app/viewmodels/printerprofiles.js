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
        self.profiles.updateItems(data.profiles);
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
    }
}