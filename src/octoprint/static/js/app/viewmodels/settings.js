/**
 * Iterates through each node of an Object, recursively
 * on property values of type Object.
 * @param  {*} node initially fed the root object to recurse through
 * @param  {Object} config {
 *     on: function(...) // executes at each node
 *     mode: "array"|null // determines what is returned
 *     _init: indicates whether first node has been or is immedately about to be processed
 *     _path: ["prop", "subprop_of_prop", ...etc]. path array of current node
 * }
 * @return {Array}
 */
function eachDeep(node, config) {
    var nodeResults = [],
        subResults = [],
        k, v;
    if (!config.hasOwnProperty("_init")) {
        config._init = true;
        config._path = [];
        if (!config.hasOwnProperty("mode")) {
            config.mode = null;
        }
    }
    if (!node || node.constructor !== Object) {
        return config.on(node, config);
    }
    for (k in node) {
        v = node[k];
        config._path.push(k);
        subResults = eachDeep(v, config);
        if (config.mode === "array") nodeResults = nodeResults.concat(subResults);
        if (config._path) {
            config._path.pop();
        }
    }
    return nodeResults;
}

function SettingsViewModel(loginStateViewModel, usersViewModel) {
    var self = this;
    var settingKoos = {
        "appearance": {
            "color": ko.observable(undefined),
            "name": ko.observable(undefined)
        },
        "api": {
            "allowCrossOrigin": ko.observable(undefined),
            "enabled": ko.observable(undefined),
            "key": ko.observable(undefined)
        },
        "cura": {
            "config": ko.observable(undefined),
            "enabled": ko.observable(undefined),
            "path": ko.observable(undefined)
        },
        "feature": {
            "alwaysSendChecksum": ko.observable(undefined),
            "repetierTargetTemp": ko.observable(undefined),
            "sdAlwaysAvailable": ko.observable(undefined),
            "sdSupport": ko.observable(undefined),
            "swallowOkAfterResend": ko.observable(undefined),
            "temperatureGraph": ko.observable(undefined),
            "waitForStartOnConnect": ko.observable(undefined)
        },
        "folder": {
            "logs": ko.observable(undefined),
            "plugins": ko.observable(undefined),
            "timelapse": ko.observable(undefined),
            "timelapse_tmp": ko.observable(undefined),
            "uploads": ko.observable(undefined),
            "virtualSd": ko.observable(undefined),
            "watched": ko.observable(undefined)
        },
        "gcodeViewer": {
            "enabled": ko.observable(undefined),
            "mobileSizeThreshold": ko.observable(undefined),
            "sizeThreshold": ko.observable(undefined)
        },
        "notifications": {
            "email": {
                "enabled": ko.observable(undefined),
                "sendgridId": ko.observable(undefined),
                "sendgridKey": ko.observable(undefined)
            },
            "enabled": ko.observable(undefined),
            "textMessage": {
                "countryPrefix": ko.observable(undefined),
                "enabled": ko.observable(undefined),
                "toNumber": ko.observable(undefined),
                "fromNumber": ko.observable(undefined),
                "twilioAcctId": ko.observable(undefined),
                "twilioAcctKey": ko.observable(undefined)
            },
            "cloud": {
                "enabled": ko.observable(undefined),
                "orchestrateId": ko.observable(undefined),
                "orchestrateKey": ko.observable(undefined)
            }
        },
        "plugins": ko.observable(undefined),
        "printerParameters": {
            "bedDimensions": {
                "circular": ko.observable(undefined),
                "x": ko.observable(undefined),
                "y": ko.observable(undefined),
                "r": ko.observable(undefined)
            },
            "defaultExtrusionLength": ko.observable(undefined),
            "extruderOffsets": ko.observableArray([]),
            "invertAxes": ko.observable(undefined),
            "pauseTriggers": ko.observable(undefined),
            "movementSpeed": {
                "x": ko.observable(undefined),
                "y": ko.observable(undefined),
                "z": ko.observable(undefined),
                "e": ko.observable(undefined)
            },
            "numExtruders": ko.observable(undefined)
        },
        "serial": {
            "additionalPorts": ko.observable(undefined),
            "autoconnect": ko.observable(undefined),
            "baudrate": ko.observable(undefined),
            "baudrates": ko.observableArray([]),
            "log": ko.observable(undefined),
            "port": ko.observable(undefined),
            "ports": ko.observableArray([]),
            "timeout": {
                "communication": ko.observable(undefined),
                "connection": ko.observable(undefined),
                "detection": ko.observable(undefined),
                "sdStatus": ko.observable(undefined),
                "temperature": ko.observable(undefined)
            }
        },
        "system": {
            "actions": ko.observableArray([])
        },
        "temperature": {
            "profiles": ko.observableArray(undefined)
        },
        "terminalFilters": ko.observableArray(undefined),
        "webcam": {
            "bitrate": ko.observable(undefined),
            "ffmpeg": ko.observable(undefined),
            "flipH": ko.observable(undefined),
            "flipV": ko.observable(undefined),
            "snapshot": ko.observable(undefined),
            "stream": ko.observable(undefined),
            "timelapse": {
                "options": ko.observable(undefined),
                "postRoll": ko.observable(undefined),
                "type": ko.observable(undefined)
            },
            "watermark": ko.observable(undefined)
        }
    };

    self.flattenKoos = function() {
        eachDeep(settingKoos,{
            on: function bindKooDirectlyToSelf(koo, config) {
                self[config._path.join("_")] = koo;
            }
        });
    };
    self.flattenKoos();

    // Client-only koos & settings
    self._printerParameters_extruderOffsets = ko.observableArray([]);
    self.appearance_available_colors = ko.observable([
        {key: "default", name: gettext("default")},
        {key: "red", name: gettext("red")},
        {key: "orange", name: gettext("orange")},
        {key: "yellow", name: gettext("yellow")},
        {key: "green", name: gettext("green")},
        {key: "blue", name: gettext("blue")},
        {key: "violet", name: gettext("violet")},
        {key: "black", name: gettext("black")}
    ]);
    self.loginState = loginStateViewModel;
    self.notifications_textMessage_country = ko.observable(undefined);
    self.users = usersViewModel;

    // Computed koos
    self.printerParameters_bedDimensions = ko.computed({
        read: function () {
            return {
                x: parseFloat(self.printerParameters_bedDimensions_x()),
                y: parseFloat(self.printerParameters_bedDimensions_y()),
                r: parseFloat(self.printerParameters_bedDimensions_r()),
                circular: self.printerParameters_bedDimensions_circular()
            };
        },
        write: function(value) {
            self.printerParameters_bedDimensionX(value.x);
            self.printerParameters_bedDimensionY(value.y);
            self.printerParameters_bedDimensionR(value.r);
            self.printerParameters_bedDimensions_circular(value.circular);
        },
        owner: self
    });

    self.printerParameters_extruderOffsets = ko.computed({
        read: function readExtruderOffsets() {
            var extruderOffsets = self._printerParameters_extruderOffsets();
            var result = [];
            for (var i = 0; i < extruderOffsets.length; i++) {
                result[i] = {
                    x: parseFloat(extruderOffsets[i].x()),
                    y: parseFloat(extruderOffsets[i].y())
                };
            }
            return result;
        },
        write: function writeExtruderOffsets(value) {
            var result = [];
            if (value && Array.isArray(value)) {
                for (var i = 0; i < value.length; i++) {
                    result[i] = {
                        x: ko.observable(value[i].x),
                        y: ko.observable(value[i].y)
                    };
                }
            }
            self._printerParameters_extruderOffsets(result);
        },
        owner: self
    });

    self.ko_printerParameters_extruderOffsets = ko.computed(function computeOffsets() {
        var extruderOffsets = self._printerParameters_extruderOffsets();
        var numExtruders = self.printerParameters_numExtruders();
        if (!numExtruders) {
            numExtruders = 1;
        }

        if (numExtruders > extruderOffsets.length) {
            for (var i = extruderOffsets.length; i < numExtruders; i++) {
                extruderOffsets[i] = {
                    x: ko.observable(0),
                    y: ko.observable(0)
                };
            }
            self._printerParameters_extruderOffsets(extruderOffsets);
        }

        return extruderOffsets.slice(0, numExtruders);
    });
    /* end computed koos */

    // Member functions

    self.addTemperatureProfile = function() {
        self.temperature_profiles.push({name: "New", extruder:0, bed:0});
    };

    self.addTerminalFilter = function() {
        self.terminalFilters.push({name: "New", regex: "(Send: M105)|(Recv: ok T:)"});
    };

    self.appearance_colorName = function(color) {
        switch (color) {
            case "red":
                return gettext("red");
            case "orange":
                return gettext("orange");
            case "yellow":
                return gettext("yellow");
            case "green":
                return gettext("green");
            case "blue":
                return gettext("blue");
            case "violet":
                return gettext("violet");
            case "black":
                return gettext("black");
            case "default":
                return gettext("default");
            default:
                return color;
        }
    };

    self.getPrinterInvertAxis = function(axis) {
        return _.contains((self.printerParameters_invertAxes() || []), axis.toLowerCase());
    };

    self.koInvertAxis = function(axis) {
        return ko.computed({
            read: function () { return self.getPrinterInvertAxis(axis); },
            write: function (value) { self.setPrinterInvertAxis(axis, value); },
            owner: self
        });
    };

    self.removeTerminalFilter = function(filter) {
        self.terminalFilters.remove(filter);
    };

    self.removeTemperatureProfile = function(profile) {
        self.temperature_profiles.remove(profile);
    };

    self.requestData = function(callback) {
        $.ajax({
            url: API_BASEURL + "settings",
            type: "GET",
            dataType: "json",
            success: function(response) {
                eachDeep(response, {"on": self._setKooFromResponse});
                if (callback) callback();
            }
        });
    };

    self._setGetPayloadProp = function(value, config) {
        refObj = self._saveGetPayload; // init to payload root then traverse
        if (!config || !config._path || !config._path.hasOwnProperty(length)) {
            throw new Error("invalid config");
        }
        finalKey = config._path[config._path.length - 1];
        config._path.forEach(function traverseGetObj(pathSeg) {
            if (refObj.hasOwnProperty(pathSeg) && pathSeg !== finalKey) {
                refObj = refObj[pathSeg];
            } else if (pathSeg !== finalKey) {
                refObj[pathSeg] = {};
                refObj = refObj[pathSeg];
            }
        });
        refObj[finalKey] = value();
    };

    self._setKooFromResponse = function(value, config) {
        refObj = settingKoos;
        if (!config || !config._path || !config._path.hasOwnProperty(length)) {
            throw new Error("invalid config");
        }
        finalKey = config._path[config._path.length - 1];
        config._path.forEach(function traverseGetObj(pathSeg) {
            if (refObj.hasOwnProperty(pathSeg) && pathSeg !== finalKey) {
                refObj = refObj[pathSeg];
            } else if (pathSeg !== finalKey) {
                refObj[pathSeg] = {};
                refObj = refObj[pathSeg];
            }
        });
        refObj[finalKey](value);
    };

    self.saveData = function() {
        self._saveGetPayload = {};
        eachDeep(settingKoos, {"on": self._setGetPayloadProp});

        // Remove client-only settings (not saved/used by server)
        delete self._saveGetPayload.serial.ports;
        delete self._saveGetPayload.serial.baudrates;

        $.ajax({
            url: API_BASEURL + "settings",
            type: "POST",
            dataType: "json",
            contentType: "application/json; charset=UTF-8",
            data: JSON.stringify(self._saveGetPayload),
            success: function(response) {
                eachDeep(response, {"on": self._setKooFromResponse});
                $("#settings_dialog").modal("hide");
            }
        });
    };

    self.setPrinterInvertAxis = function(axis, value) {
        var currInvert = self.printerParameters_invertAxes() || [];
        var currValue = self.getPrinterInvertAxis(axis);
        if (value && !currValue) {
            currInvert.push(axis.toLowerCase());
        } else if (!value && currValue) {
            currInvert = _.without(currInvert, axis.toLowerCase());
        }
        self.printerParameters_invertAxes(currInvert);
    };

    // Init
    self.printerParameters_invertX = self.koInvertAxis('x');
    self.printerParameters_invertY = self.koInvertAxis('y');
    self.printerParameters_invertZ = self.koInvertAxis('z');
}
