function SettingsViewModel(loginStateViewModel, usersViewModel) {
    var self = this;

    self.loginState = loginStateViewModel;
    self.users = usersViewModel;

    self.api_enabled = ko.observable(undefined);
    self.api_key = ko.observable(undefined);

    self.appearance_name = ko.observable(undefined);
    self.appearance_color = ko.observable(undefined);

    /* I did attempt to allow arbitrary gradients but cross browser support via knockout or jquery was going to be horrible */
    self.appearance_available_colors = ko.observable(["default", "red", "orange", "yellow", "green", "blue", "violet", "black"]);

    self.printer_movementSpeedX = ko.observable(undefined);
    self.printer_movementSpeedY = ko.observable(undefined);
    self.printer_movementSpeedZ = ko.observable(undefined);
    self.printer_movementSpeedE = ko.observable(undefined);
    self.printer_invertAxes = ko.observable(undefined);

    self.webcam_streamUrl = ko.observable(undefined);
    self.webcam_snapshotUrl = ko.observable(undefined);
    self.webcam_ffmpegPath = ko.observable(undefined);
    self.webcam_bitrate = ko.observable(undefined);
    self.webcam_watermark = ko.observable(undefined);
    self.webcam_flipH = ko.observable(undefined);
    self.webcam_flipV = ko.observable(undefined);

    self.feature_gcodeViewer = ko.observable(undefined);
    self.feature_temperatureGraph = ko.observable(undefined);
    self.feature_waitForStart = ko.observable(undefined);
    self.feature_alwaysSendChecksum = ko.observable(undefined);
    self.feature_sdSupport = ko.observable(undefined);
    self.feature_swallowOkAfterResend = ko.observable(undefined);

    self.serial_port = ko.observable();
    self.serial_baudrate = ko.observable();
    self.serial_portOptions = ko.observableArray([]);
    self.serial_baudrateOptions = ko.observableArray([]);
    self.serial_autoconnect = ko.observable(undefined);
    self.serial_timeoutConnection = ko.observable(undefined);
    self.serial_timeoutDetection = ko.observable(undefined);
    self.serial_timeoutCommunication = ko.observable(undefined);
    self.serial_log = ko.observable(undefined);

    self.folder_uploads = ko.observable(undefined);
    self.folder_timelapse = ko.observable(undefined);
    self.folder_timelapseTmp = ko.observable(undefined);
    self.folder_logs = ko.observable(undefined);

    self.cura_enabled = ko.observable(undefined);
    self.cura_path = ko.observable(undefined);
    self.cura_config = ko.observable(undefined);

    self.temperature_profiles = ko.observableArray(undefined);

    self.system_actions = ko.observableArray([]);

    self.terminalFilters = ko.observableArray([]);

    self.addTemperatureProfile = function() {
        self.temperature_profiles.push({name: "New", extruder:0, bed:0});
    };

    self.removeTemperatureProfile = function(profile) {
        self.temperature_profiles.remove(profile);
    };

    self.addTerminalFilter = function() {
        self.terminalFilters.push({name: "New", regex: "(Send: M105)|(Recv: ok T:)"})
    };

    self.removeTerminalFilter = function(filter) {
        self.terminalFilters.remove(filter);
    };

    self.getPrinterInvertAxis = function(axis) {
        return _.contains((self.printer_invertAxes() || []), axis.toLowerCase());
    };

    self.setPrinterInvertAxis = function(axis, value) {
        var currInvert = self.printer_invertAxes() || [];
        var currValue = self.getPrinterInvertAxis(axis);
        if (value && !currValue) {
            currInvert.push(axis.toLowerCase());
        } else if (!value && currValue) {
            currInvert = _.without(currInvert, axis.toLowerCase());
        }
        self.printer_invertAxes(currInvert);
    };

    self.koInvertAxis = function (axis) { return ko.computed({
        read: function () { return self.getPrinterInvertAxis(axis); },
        write: function (value) { self.setPrinterInvertAxis(axis, value); },
        owner: self
    })};

    self.printer_invertX = self.koInvertAxis('x');
    self.printer_invertY = self.koInvertAxis('y');
    self.printer_invertZ = self.koInvertAxis('z');

    self.requestData = function() {
        $.ajax({
            url: AJAX_BASEURL + "settings",
            type: "GET",
            dataType: "json",
            success: self.fromResponse
        });
    }

    self.fromResponse = function(response) {
        self.api_enabled(response.api.enabled);
        self.api_key(response.api.key);

        self.appearance_name(response.appearance.name);
        self.appearance_color(response.appearance.color);

        self.printer_movementSpeedX(response.printer.movementSpeedX);
        self.printer_movementSpeedY(response.printer.movementSpeedY);
        self.printer_movementSpeedZ(response.printer.movementSpeedZ);
        self.printer_movementSpeedE(response.printer.movementSpeedE);
        self.printer_invertAxes(response.printer.invertAxes);

        self.webcam_streamUrl(response.webcam.streamUrl);
        self.webcam_snapshotUrl(response.webcam.snapshotUrl);
        self.webcam_ffmpegPath(response.webcam.ffmpegPath);
        self.webcam_bitrate(response.webcam.bitrate);
        self.webcam_watermark(response.webcam.watermark);
        self.webcam_flipH(response.webcam.flipH);
        self.webcam_flipV(response.webcam.flipV);

        self.feature_gcodeViewer(response.feature.gcodeViewer);
        self.feature_temperatureGraph(response.feature.temperatureGraph);
        self.feature_waitForStart(response.feature.waitForStart);
        self.feature_alwaysSendChecksum(response.feature.alwaysSendChecksum);
        self.feature_sdSupport(response.feature.sdSupport);
        self.feature_swallowOkAfterResend(response.feature.swallowOkAfterResend);

        self.serial_port(response.serial.port);
        self.serial_baudrate(response.serial.baudrate);
        self.serial_portOptions(response.serial.portOptions);
        self.serial_baudrateOptions(response.serial.baudrateOptions);
        self.serial_autoconnect(response.serial.autoconnect);
        self.serial_timeoutConnection(response.serial.timeoutConnection);
        self.serial_timeoutDetection(response.serial.timeoutDetection);
        self.serial_timeoutCommunication(response.serial.timeoutCommunication);
        self.serial_log(response.serial.log);

        self.folder_uploads(response.folder.uploads);
        self.folder_timelapse(response.folder.timelapse);
        self.folder_timelapseTmp(response.folder.timelapseTmp);
        self.folder_logs(response.folder.logs);

        self.cura_enabled(response.cura.enabled);
        self.cura_path(response.cura.path);
        self.cura_config(response.cura.config);

        self.temperature_profiles(response.temperature.profiles);

        self.system_actions(response.system.actions);

        self.terminalFilters(response.terminalFilters);
    }

    self.saveData = function() {
        var data = {
            "api" : {
                "enabled": self.api_enabled(),
                "key": self.api_key()
            },
            "appearance" : {
                "name": self.appearance_name(),
                "color": self.appearance_color()
            },
            "printer": {
                "movementSpeedX": self.printer_movementSpeedX(),
                "movementSpeedY": self.printer_movementSpeedY(),
                "movementSpeedZ": self.printer_movementSpeedZ(),
                "movementSpeedE": self.printer_movementSpeedE(),
                "invertAxes": self.printer_invertAxes()
            },
            "webcam": {
                "streamUrl": self.webcam_streamUrl(),
                "snapshotUrl": self.webcam_snapshotUrl(),
                "ffmpegPath": self.webcam_ffmpegPath(),
                "bitrate": self.webcam_bitrate(),
                "watermark": self.webcam_watermark(),
                "flipH": self.webcam_flipH(),
                "flipV": self.webcam_flipV()
            },
            "feature": {
                "gcodeViewer": self.feature_gcodeViewer(),
                "temperatureGraph": self.feature_temperatureGraph(),
                "waitForStart": self.feature_waitForStart(),
                "alwaysSendChecksum": self.feature_alwaysSendChecksum(),
                "sdSupport": self.feature_sdSupport(),
                "swallowOkAfterResend": self.feature_swallowOkAfterResend()
            },
            "serial": {
                "port": self.serial_port(),
                "baudrate": self.serial_baudrate(),
                "autoconnect": self.serial_autoconnect(),
                "timeoutConnection": self.serial_timeoutConnection(),
                "timeoutDetection": self.serial_timeoutDetection(),
                "timeoutCommunication": self.serial_timeoutCommunication(),
                "log": self.serial_log()
            },
            "folder": {
                "uploads": self.folder_uploads(),
                "timelapse": self.folder_timelapse(),
                "timelapseTmp": self.folder_timelapseTmp(),
                "logs": self.folder_logs()
            },
            "temperature": {
                "profiles": self.temperature_profiles()
            },
            "system": {
                "actions": self.system_actions()
            },
            "cura": {
                "enabled": self.cura_enabled(),
                "path": self.cura_path(),
                "config": self.cura_config()
            },
            "terminalFilters": self.terminalFilters()
        }

        $.ajax({
            url: AJAX_BASEURL + "settings",
            type: "POST",
            dataType: "json",
            contentType: "application/json; charset=UTF-8",
            data: JSON.stringify(data),
            success: function(response) {
                self.fromResponse(response);
                $("#settings_dialog").modal("hide");
            }
        })
    }

}
