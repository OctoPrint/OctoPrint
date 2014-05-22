function SettingsViewModel(loginStateViewModel, usersViewModel, dialogsViewModel) {
    var self = this;

    self.loginState = loginStateViewModel;
    self.users = usersViewModel;
    self.dialogs = dialogsViewModel;

    self.api_enabled = ko.observable(undefined);
    self.api_key = ko.observable(undefined);

    self.appearance_name = ko.observable(undefined);
    self.appearance_color = ko.observable(undefined);

    self.appearance_available_colors = ko.observable(["default", "red", "orange", "yellow", "green", "blue", "violet", "black"]);

    self.printer_movementSpeedX = ko.observable(undefined);
    self.printer_movementSpeedY = ko.observable(undefined);
    self.printer_movementSpeedZ = ko.observable(undefined);
    self.printer_movementSpeedE = ko.observable(undefined);
    self.printer_invertAxes = ko.observable(undefined);
    self.printer_numExtruders = ko.observable(undefined);

    self._printer_extruderOffsets = ko.observableArray([]);
    self.printer_extruderOffsets = ko.computed({
        read: function() {
            var extruderOffsets = self._printer_extruderOffsets();
            var result = [];
            for (var i = 0; i < extruderOffsets.length; i++) {
                result[i] = {
                    x: parseFloat(extruderOffsets[i].x()),
                    y: parseFloat(extruderOffsets[i].y())
                }
            }
            return result;
        },
        write: function(value) {
            var result = [];
            if (value && Array.isArray(value)) {
                for (var i = 0; i < value.length; i++) {
                    result[i] = {
                        x: ko.observable(value[i].x),
                        y: ko.observable(value[i].y)
                    }
                }
            }
            self._printer_extruderOffsets(result);
        },
        owner: self
    });
    self.ko_printer_extruderOffsets = ko.computed(function() {
        var extruderOffsets = self._printer_extruderOffsets();
        var numExtruders = self.printer_numExtruders();
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
            self._printer_extruderOffsets(extruderOffsets);
        }

        return extruderOffsets.slice(0, numExtruders);
    });

    self.printer_bedDimensionX = ko.observable(undefined);
    self.printer_bedDimensionY = ko.observable(undefined);
    self.printer_bedDimensionR = ko.observable(undefined);
    self.printer_bedCircular = ko.observable(undefined);
    self.printer_bedDimensions = ko.computed({
        read: function () {
            return {
                x: parseFloat(self.printer_bedDimensionX()),
                y: parseFloat(self.printer_bedDimensionY()),
                r: parseFloat(self.printer_bedDimensionR()),
                circular: self.printer_bedCircular()
            };
        },
        write: function(value) {
            self.printer_bedDimensionX(value.x);
            self.printer_bedDimensionY(value.y);
            self.printer_bedDimensionR(value.r);
            self.printer_bedCircular(value.circular);
        },
        owner: self
    });

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
    self.feature_sdAlwaysAvailable = ko.observable(undefined);
    self.feature_swallowOkAfterResend = ko.observable(undefined);
    self.feature_repetierTargetTemp = ko.observable(undefined);

    self.serial_port = ko.observable();
    self.serial_baudrate = ko.observable();
    self.serial_portOptions = ko.observableArray([]);
    self.serial_baudrateOptions = ko.observableArray([]);
    self.serial_autoconnect = ko.observable(undefined);
    self.serial_timeoutConnection = ko.observable(undefined);
    self.serial_timeoutDetection = ko.observable(undefined);
    self.serial_timeoutCommunication = ko.observable(undefined);
    self.serial_timeoutTemperature = ko.observable(undefined);
    self.serial_timeoutSdStatus = ko.observable(undefined);
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

    self.children = ko.observableArray([]); // Controls
    self.sortControls = function (left, right) {
    	if (left.row() < right.row())
    		return -1;

    	if (left.row() > right.row())
    		return 1;

    	return 0;
    };

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

    self.requestData = function(callback) {
        $.ajax({
            url: API_BASEURL + "settings",
            type: "GET",
            dataType: "json",
            success: function(response) {
                self.fromResponse(response);
                if (callback) callback();
            }
        });
    };

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
        self.printer_numExtruders(response.printer.numExtruders);
        self.printer_extruderOffsets(response.printer.extruderOffsets);
        self.printer_bedDimensions(response.printer.bedDimensions);

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
        self.feature_sdAlwaysAvailable(response.feature.sdAlwaysAvailable);
        self.feature_swallowOkAfterResend(response.feature.swallowOkAfterResend);
        self.feature_repetierTargetTemp(response.feature.repetierTargetTemp);

        self.serial_port(response.serial.port);
        self.serial_baudrate(response.serial.baudrate);
        self.serial_portOptions(response.serial.portOptions);
        self.serial_baudrateOptions(response.serial.baudrateOptions);
        self.serial_autoconnect(response.serial.autoconnect);
        self.serial_timeoutConnection(response.serial.timeoutConnection);
        self.serial_timeoutDetection(response.serial.timeoutDetection);
        self.serial_timeoutCommunication(response.serial.timeoutCommunication);
        self.serial_timeoutTemperature(response.serial.timeoutTemperature);
        self.serial_timeoutSdStatus(response.serial.timeoutSdStatus);
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

        var children = [];
        for (var i = 0; i < response.controls.length; i++)
        {
        	children.push(self._processControl(response.controls[i]));
        }
        self.children(children.sort(self.sortControls));
    }

    self._processControl = function (customControl)
    {
    	customControl.name = ko.observable(customControl.name);
    	if (customControl.type != "section") {
    		if (customControl.hasOwnProperty("command"))
    			customControl.command = ko.observable(customControl.command);

    		if (customControl.hasOwnProperty("commands"))
    			if (customControl.commands.indexOf(',') >= 0)
    				customControl.commands = ko.observable(customControl.commands);
    			else
    				customControl.commands = ko.observable(customControl.commands.toString().replace(/\,/g, '\n'));

			if (!customControl.hasOwnProperty("left"))
				customControl.left = ko.observable(0);
			else
				customControl.left = ko.observable(customControl.left);

			if (!customControl.hasOwnProperty("top"))
				customControl.top = ko.observable(0);
			else
				customControl.top = ko.observable(customControl.top);
    	}
    	else 
		{
			var c = [];
    		for (var j = 0; j < customControl.children.length; j++)
    			c[j] = self._processControl(customControl.children[j]);

    		customControl.children = ko.observableArray(c);

    		if (!customControl.hasOwnProperty("height"))
    			customControl.height = ko.observable(0);
    		else
    			customControl.height = ko.observable(customControl.height);

			customControl.settingsHeight = ko.observable(0);

    		if (!customControl.hasOwnProperty("row"))
    			customControl.row = ko.observable(0);
    		else
    			customControl.row = ko.observable(customControl.row);
    	}

    	if (customControl.type == "parametric_command" || customControl.type == "parametric_commands") {
    		for (var j = 0; j < customControl.input.length; j++)
    			customControl.input[j] = { name: ko.observable(customControl.input[j].name), parameter: ko.observable(customControl.input[j].parameter), defaultValue: ko.observable(customControl.input[j].default), value: ko.observable(customControl.input[j].default) };

    		customControl.input = ko.observableArray(customControl.input);
    	}

    	if (customControl.type == "feedback_command_output" || customControl.type == "feedback_commands_output")
    	{
    		customControl.regex = ko.observable(customControl.regex);
    		customControl.template = ko.observable(customControl.template);
    		customControl.output = ko.observable("");
    	}
    	if (customControl.type == "feedback_command" || customControl.type == "feedback_commands") {
    		customControl.regex = ko.observable(customControl.regex);
    		customControl.template = ko.observable(customControl.template);
    	}

    	if (customControl.type == "feedback" || customControl.type == "feedback") {
    		customControl.output = ko.observable("");
    	}

    	if (!customControl.hasOwnProperty("css"))
    		customControl.css = ko.observable("");
    	else
    		customControl.css = ko.observable(customControl.css);
		
		if (!customControl.hasOwnProperty("backgroundColor1"))
        	customControl.backgroundColor1 = ko.observable("");
        else
        	customControl.backgroundColor1 = ko.observable(customControl.backgroundColor1);

    	if (!customControl.hasOwnProperty("backgroundColor2"))
    		customControl.backgroundColor2 = ko.observable("");
    	else
    		customControl.backgroundColor2 = ko.observable(customControl.backgroundColor2);

        if (!customControl.hasOwnProperty("foregroundColor"))
        	customControl.foregroundColor = ko.observable("");
        else
        	customControl.foregroundColor = ko.observable(customControl.foregroundColor);

    	return customControl;
    }

    self._customControlToArray = function (customControl)
    {
    	var c = { 
			name: customControl.name(), 
			foregroundColor: customControl.foregroundColor(), 
			backgroundColor1: customControl.backgroundColor1(), 
			backgroundColor2: customControl.backgroundColor2(),
			css: customControl.css()
    	};

    	if (customControl.hasOwnProperty("height")) c.height = customControl.height();
    	if (customControl.hasOwnProperty("left")) c.left = customControl.left();
    	if (customControl.hasOwnProperty("top")) c.top = customControl.top();
				
    	switch(customControl.type)
    	{
    		case "command":
    		case "commands":
    			if (customControl.hasOwnProperty("command"))
    			{
    				if (customControl.command().indexOf('\n') == -1)
					{
    					c.type = "command";
    					c.command = customControl.command();
    				}
    				else {
    					c.type = "commands";
    					c.commands = customControl.command().toString().split('\n');
    				}
    			}
    			else
    			{
    				c.type = "commands";
    				c.commands = customControl.commands().toString().split('\n');
    			}
    			break;
    		case "parametric_command":
    		case "parametric_commands":
    			if (customControl.hasOwnProperty("command")) {
    				if (customControl.command().indexOf('\n') == -1) {
    					c.type = "parametric_command";
    					c.command = customControl.command();
    				}
    				else {
    					c.type = "parametric_commands";
    					c.commands = customControl.command().toString().split('\n');
    				}
    			}
    			else {
    				c.type = "parametric_commands";
    				c.commands = customControl.commands().toString().split('\n');
    			}

    			c.input = [];
    			for (var i = 0; i < customControl.input().length; i++)
    				c.input.push({ name: customControl.input()[i].name(), parameter: customControl.input()[i].parameter(), default: customControl.input()[i].defaultValue() });

    			break;
			case "feedback_command":
    		case "feedback_commands":
    			if (customControl.hasOwnProperty("command") && customControl.command().indexOf('\n') == -1) {
    				c.type = "feedback_command";
    				c.command = customControl.command();
    			}
    			else {
    				c.type = "feedback_commands";
    				c.commands = customControl.commands().toString().split('\n');
    			}

    			c.regex = customControl.regex();
    			c.template = customControl.template();
    			break;
    		case "feedback_command_output":
    		case "feedback_commands_output":
    			if (customControl.hasOwnProperty("command") && customControl.command().indexOf('\n') == -1) {
    				c.type = "feedback_command_output";
    				c.command = customControl.command();
    			}
    			else {
    				c.type = "feedback_commands_output";
    				c.commands = customControl.commands().toString().split('\n');
    			}

    			c.regex = customControl.regex();
    			c.template = customControl.template();
    			break;
    		case "feedback":
    			c.type = "feedback";
    			break;
    		case "section":
    			c.type = "section";
    			c.children = [];
    			for (var i = 0; i < customControl.children().length; i++)
    				c.children.push(self._customControlToArray(customControl.children()[i]));
    			break;
    	}

    	return c;
    }

    self.saveData = function () {
    	var controls = [];
    	for (var i = 0; i < self.children().length; i++)
    		controls.push(self._customControlToArray(self.children()[i]));

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
                "invertAxes": self.printer_invertAxes(),
                "numExtruders": self.printer_numExtruders(),
                "extruderOffsets": self.printer_extruderOffsets(),
                "bedDimensions": self.printer_bedDimensions()
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
                "sdAlwaysAvailable": self.feature_sdAlwaysAvailable(),
                "swallowOkAfterResend": self.feature_swallowOkAfterResend(),
                "repetierTargetTemp": self.feature_repetierTargetTemp()
            },
            "serial": {
                "port": self.serial_port(),
                "baudrate": self.serial_baudrate(),
                "autoconnect": self.serial_autoconnect(),
                "timeoutConnection": self.serial_timeoutConnection(),
                "timeoutDetection": self.serial_timeoutDetection(),
                "timeoutCommunication": self.serial_timeoutCommunication(),
                "timeoutTemperature": self.serial_timeoutTemperature(),
                "timeoutSdStatus": self.serial_timeoutSdStatus(),
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
            "terminalFilters": self.terminalFilters(),
            "controls": controls
        };

        $.ajax({
            url: API_BASEURL + "settings",
            type: "POST",
            dataType: "json",
            contentType: "application/json; charset=UTF-8",
            data: JSON.stringify(data),
            success: function(response) {
                self.fromResponse(response);
                $("#settings_dialog").modal("hide");
            }
        });
    }

    self.displayMode = function (customControl) {
    	if (!customControl)
    		return "customControls_emptyTemplate";

    	switch (customControl.type) {
    		case "section":
    			return "settings_customControls_sectionTemplate";
    		case "command":
    		case "commands":
    			return "settings_customControls_commandTemplate";
    		case "parametric_command":
    		case "parametric_commands":
    			return "settings_customControls_parametricCommandTemplate";
    		case "feedback_command":
    		case "feedback_commands":
    			return "settings_customControls_feedbackCommandTemplate";
			case "feedback_command_output":
    		case "feedback_commands_output":
				return "settings_customControls_feedbackCommandOutputTemplate";
    		case "feedback":
    			return "settings_customControls_feedbackTemplate";
    		default:
    			return "settings_customControls_emptyTemplate";
    	}
    }

	// Dynamic Commands
    self.customCommandData = ko.observable(self._processControl({name: ""}));
    self.customCommandParent = undefined;
    self.event = undefined;

    self.editStyle = function (type) {
    	return ko.computed({
    		read: function () {
    			if (type == "bgColor1")
    				return self.customCommandData().backgroundColor1();

    			if (type == "bgColor2")
    				return self.customCommandData().backgroundColor2();

    			if (type == "fgColor")
    				return self.customCommandData().foregroundColor();

    			if (type == "bgImage")
    				return self.customCommandData().backgroundColor1() != '' && self.customCommandData().backgroundColor2() != '' ? "linear-gradient(to bottom," + self.customCommandData().backgroundColor1() + "," + self.customCommandData().backgroundColor2() + ")" : '';

    			return self.customCommandData().css();
    		},
    		write: function (value) {
    			self.customCommandData().backgroundColor1(type == "bgColor1" ? value : (type == "bgColor2" || type == "fgColor" ? self.customCommandData().backgroundColor1() : ""));
    			self.customCommandData().backgroundColor2(type == "bgColor2" ? value : (type == "bgColor1" || type == "fgColor" ? self.customCommandData().backgroundColor2() : ""));
    			self.customCommandData().foregroundColor(type == "fgColor" ? value : (type == "bgColor1" || type == "bgColor2" ? self.customCommandData().foregroundColor() : ""));
    			self.customCommandData().css(type == "css" ? value : "");
    		},
    		owner: this
    	});
    }

    self.bgImage = function(data) {
    	return ko.computed(function () {
    		return data.backgroundColor1() != '' && data.backgroundColor2() != '' ? "linear-gradient(to bottom," + data.backgroundColor1() + "," + data.backgroundColor2() + ")" : '';
    	});
	}

    self.showChevron = function (dir, index) {
    	if (dir == "down") {
    		return index < self.children().length - 1;
    	}

    	return index > 0;
    }

    self.switchPlaces = function (index1, index2) {
    	self.children()[index1].row(index2);
    	self.children()[index2].row(index1);

    	self.children(self.children().sort(self.sortControls));
    }

    self.toggleCollapse = function () {
    	var element = $('#title_' + self.getEntryId(this));

    	if (this.settingsHeight() != 0)
    		this.settingsHeight(0);
    	else {
    		var maxHeight = 0;
    		element.children().each(function (index, value) {
    			var e = $(value);
    			maxHeight = e.position().top + e.outerHeight() > maxHeight ? e.position().top + e.outerHeight() : maxHeight;
    		});

    		this.settingsHeight(maxHeight + 1);
    	}
    }

    self.getEntryId = function (data) {
    	return "settings_custom_command_" + md5(data.name() + ":" + data.type);
    }

    self.adjustContainer = function () {
    	var element = $(this);
    	var pos = element.position();
    	var parent = element.parents(".collapse:first");

    	var maxHeight = 0;
    	parent.children().each(function (index, value) {
    		var e = $(value);
    		maxHeight = e.position().top + e.outerHeight() > maxHeight ? e.position().top + e.outerHeight() : maxHeight;
    	});

    	parent.height(maxHeight + 50);
    }

    self.movementStopped = function (ui, data, parentData) {
    	data.left(ui.position.left);
    	data.top(ui.position.top);

    	parentData.settingsHeight(0);
    	self.toggleCollapse.call(parentData);
    }

    self.setData = function (event, parent, data) {
    	self.event = event;
    	self.customCommandParent = parent;
    	self.customCommandData(data);
    }

    self.createCommand = function (command) {
    	var customControlType = $("#customControl_create_overlay");
    	var customControlTypeAck = $(".confirmation_dialog_acknowledge", customControlType);

    	self.dialogs.name("");
    	self.dialogs.commands("");
    	self.dialogs.type(command);

    	if (command.indexOf('parametric') != -1)
    		self.dialogs.inputs([{ name: "", parameter: "", defaultValue: "" }]);

    	customControlTypeAck.unbind("click");
    	customControlTypeAck.bind("click", function (e) {
    		e.preventDefault();
    		customControlType.modal("hide");

    		switch (command) {
    			case "command":
    				self.customCommandData().children.push(self._processControl({ type: "commands", name: self.dialogs.name(), commands: self.dialogs.commands(), top: Math.round(self.event.offsetY / 5) * 5, left: Math.round(self.event.offsetX / 5) * 5 }));
    				break;
    			case "parametric_command":
    				var inputs = [];
    				for (var i = 0; i < self.dialogs.inputs().length; i++)
    				{
    					var input = self.dialogs.inputs()[i];
    					if (input.name != "" && input.parameter != "")
    						inputs.push({ name: input.name, parameter: input.parameter, default: input.defaultValue });
    				}

    				self.customCommandData().children.push(self._processControl({ type: "parametric_commands", name: self.dialogs.name(), commands: self.dialogs.commands(), input: inputs, top: Math.round(self.event.offsetY / 5) * 5, left: Math.round(self.event.offsetX / 5) * 5 }));
    				break;
    			case "feedback_command":
    				self.customCommandData().children.push(self._processControl({ type: "feedback_commands", name: self.dialogs.name(), commands: self.dialogs.commands(), regex: self.dialogs.regex(), template: self.dialogs.template(), top: Math.round(self.event.offsetY / 5) * 5, left: Math.round(self.event.offsetX / 5) * 5 }));
    				break;
				case "feedback_command_output":
					self.customCommandData().children.push(self._processControl({ type: "feedback_commands_output", name: self.dialogs.name(), commands: self.dialogs.commands(), regex: self.dialogs.regex(), template: self.dialogs.template(), top: Math.round(self.event.offsetY / 5) * 5, left: Math.round(self.event.offsetX / 5) * 5 }));
					break;
				case "feedback":
					self.customCommandData().children.push(self._processControl({ type: "feedback", name: self.dialogs.name(), top: Math.round(self.event.offsetY / 5) * 5, left: Math.round(self.event.offsetX / 5) * 5 }));
					break;
    			case "section":
    				self.children.push(self._processControl({ type: "section", name: self.dialogs.name(), children: [], height: 30 }));
    				break;

    		}
    	});
    	customControlType.modal("show");
    }
    self.deleteCommand = function () {
    	if (self.customCommandParent === self)
    		self.children.remove(self.customCommandData());
    	else {
    		self.customCommandParent.children.remove(self.customCommandData());

    		self.customCommandParent.settingsHeight(0);
    		self.toggleCollapse.call(self.customCommandParent);
    	}
    }
    self.editCommand = function () {
    	var customControlType = $("#customControl_create_overlay");
    	var customControlTypeAck = $(".confirmation_dialog_acknowledge", customControlType);

    	self.dialogs.name(self.customCommandData().name());

    	self.dialogs.type(self.customCommandData().type);

    	if (self.customCommandData().hasOwnProperty("commands"))
    		self.dialogs.commands(self.customCommandData().commands());
    	if (self.customCommandData().hasOwnProperty("command"))
    		self.dialogs.commands(self.customCommandData().command());

    	if (self.customCommandData().hasOwnProperty("input"))
    	{
    		var inputs = [];
    		for (var i = 0; i < self.customCommandData().input().length; i++) {
    			var input = self.customCommandData().input()[i];
    			if (input.name != "" && input.parameter != "")
    				inputs.push({ name: input.name(), parameter: input.parameter(), defaultValue: input.defaultValue() });
    		}

    		self.dialogs.inputs(inputs);
		}

    	if (self.customCommandData().hasOwnProperty("template"))
    		self.dialogs.template(self.customCommandData().template());

    	if (self.customCommandData().hasOwnProperty("regex"))
    		self.dialogs.regex(self.customCommandData().regex());

    	customControlTypeAck.unbind("click");
    	customControlTypeAck.bind("click", function (e) {
    		e.preventDefault();
    		customControlType.modal("hide");

    		self.customCommandData().name(self.dialogs.name());
    		self.customCommandData().commands(self.dialogs.commands());

    		switch (self.customCommandData().type) {
				case "parametric_command":
    			case "parametric_commands":
    				var inputs = [];
    				for (var i = 0; i < self.dialogs.inputs().length; i++) {
    					var input = self.dialogs.inputs()[i];
    					if (input.name != "" && input.parameter != "")
    						inputs.push({ name: ko.observable(input.name), parameter: ko.observable(input.parameter), defaultValue: ko.observable(input.defaultValue), value: ko.observable(input.defaultValue) });
    				}

    				self.customCommandData().input(inputs);
    				break;
    			case "feedback_command":
    			case "feedback_commands":
    			case "feedback_command_output":
    			case "feedback_commands_output":
    				self.customCommandData().regex(self.dialogs.regex());
    				self.customCommandData().template(self.dialogs.template());
    				break;
    		}
    	});
    	customControlType.modal("show");
    }
}
