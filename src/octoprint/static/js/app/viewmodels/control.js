function ControlViewModel(loginStateViewModel, usersViewModel, settingsViewModel) {
    var self = this;

    self.loginState = loginStateViewModel;
    self.users = usersViewModel;
    self.settings = settingsViewModel;

    self._createToolEntry = function() {
        return {
            name: ko.observable(),
            key: ko.observable()
        }
    };

    self.isErrorOrClosed = ko.observable(undefined);
    self.isOperational = ko.observable(undefined);
    self.isPrinting = ko.observable(undefined);
    self.isPaused = ko.observable(undefined);
    self.isError = ko.observable(undefined);
    self.isReady = ko.observable(undefined);
    self.isLoading = ko.observable(undefined);

    self.extrusionAmount = ko.observable(undefined);
    self.controls = ko.observableArray([]);

    self.feedbackControlLookup = {};

    self.tools = ko.observableArray([]);

    self.settings.printer_numExtruders.subscribe(function(oldVal, newVal) {
        var tools = [];

        var numExtruders = self.settings.printer_numExtruders();
        if (numExtruders > 1) {
            // multiple extruders
            for (var extruder = 0; extruder < numExtruders; extruder++) {
                tools[extruder] = self._createToolEntry();
                tools[extruder]["name"]("Tool " + extruder);
                tools[extruder]["key"]("tool" + extruder);
            }
        } else {
            // only one extruder, no need to add numbers
            tools[0] = self._createToolEntry();
            tools[0]["name"]("Hotend");
            tools[0]["key"]("tool0");
        }

        self.tools(tools);
    });

    self.settings.children.subscribe(function (newVal) {
    	var feedback = function (controls) {
    		for (var i = 0; i < controls.length; i++) {
    			if (controls[i].type == "section")
    				feedback(controls[i].children());
    			else if (controls[i].type == "feedback_command_output" || controls[i].type == "feedback_commands_output" || controls[i].type == "feedback")
    				self.feedbackControlLookup[controls[i].name()] = controls[i].output;
    		}
    	};

    	feedback(newVal);
    	self.controls(newVal);
    });

    self.fromCurrentData = function(data) {
        self._processStateData(data.state);
    }

    self.fromHistoryData = function(data) {
        self._processStateData(data.state);
    }

    self._processStateData = function(data) {
        self.isErrorOrClosed(data.flags.closedOrError);
        self.isOperational(data.flags.operational);
        self.isPaused(data.flags.paused);
        self.isPrinting(data.flags.printing);
        self.isError(data.flags.error);
        self.isReady(data.flags.ready);
        self.isLoading(data.flags.loading);
    }

    self.fromFeedbackCommandData = function(data) {
    	if (data.name in self.feedbackControlLookup) {
    		self.feedbackControlLookup[data.name](data.output);
    	}
    }

    self.sendJogCommand = function(axis, multiplier, distance) {
        if (typeof distance === "undefined")
            distance = $('#jog_distance button.active').data('distance');
        if (self.settings.getPrinterInvertAxis(axis)) {
            multiplier *= -1;
        }

        var data = {
            "command": "jog"
        }
        data[axis] = distance * multiplier;

        $.ajax({
            url: API_BASEURL + "printer/printhead",
            type: "POST",
            dataType: "json",
            contentType: "application/json; charset=UTF-8",
            data: JSON.stringify(data)
        });
    }

    self.sendHomeCommand = function(axis) {
        var data = {
            "command": "home",
            "axes": axis
        }

        $.ajax({
            url: API_BASEURL + "printer/printhead",
            type: "POST",
            dataType: "json",
            contentType: "application/json; charset=UTF-8",
            data: JSON.stringify(data)
        });
    }

    self.sendExtrudeCommand = function() {
        self._sendECommand(1);
    };

    self.sendRetractCommand = function() {
        self._sendECommand(-1);
    };

    self._sendECommand = function(dir) {
        var length = self.extrusionAmount();
        if (!length) length = 5;

        var data = {
            command: "extrude",
            amount: length * dir
        };

        $.ajax({
            url: API_BASEURL + "printer/tool",
            type: "POST",
            dataType: "json",
            contentType: "application/json; charset=UTF-8",
            data: JSON.stringify(data)
        });
    };

    self.sendSelectToolCommand = function(data) {
        if (!data || !data.key()) return;

        var data = {
            command: "select",
            tool: data.key()
        }

        $.ajax({
            url: API_BASEURL + "printer/tool",
            type: "POST",
            dataType: "json",
            contentType: "application/json; charset=UTF-8",
            data: JSON.stringify(data)
        });
    };

    self.sendCustomCommand = function(command) {
        if (!command)
            return;

        var data = undefined;
        if (command.type.indexOf("commands") != -1) {
        	// multi command
        	data = { "commands": command.commands().toString().split('\n') };
        } else if (command.type.indexOf("command") != -1) {
        	// single command
        	data = { "command": command.command() };
        }

        if (command.type.indexOf("parametric_c") != -1) {
            // parametric command(s)
            data["parameters"] = {};
            for (var i = 0; i < command.input().length; i++) {
                data["parameters"][command.input()[i].parameter()] = command.input()[i].value();
            }
        }
        else if (command.type.indexOf("parametric_s") != -1) {
        	// parametric command(s)
        	data["parameters"] = {};
        	data["parameters"][command.slideInput().parameter()] = command.slideInput().value();
        }

        if (data === undefined)
            return;

        $.ajax({
            url: API_BASEURL + "printer/command",
            type: "POST",
            dataType: "json",
            contentType: "application/json; charset=UTF-8",
            data: JSON.stringify(data)
        })
    }

    self.displayMode = function(customControl) {
		if (!customControl)
            return "customControls_emptyTemplate";
			
        switch (customControl.type) {
            case "section":
                return "customControls_sectionTemplate";
            case "command":
            case "commands":
                return "customControls_commandTemplate";
            case "parametric_command":
            case "parametric_commands":
            	return "customControls_parametricCommandTemplate";
			case "parametric_slider_command":
        	case "parametric_slider_commands":
        		return "customControls_parametricSliderCommandTemplate";
        	case "feedback_command":
        	case "feedback_commands":
        		return "customControls_feedbackCommandTemplate";
			case "feedback_command_output":
        	case "feedback_commands_output":
				return "customControls_feedbackCommandOutputTemplate";
            case "feedback":
                return "customControls_feedbackTemplate";
            default:
                return "customControls_emptyTemplate";
        }
    }

	// Dynamic Commands
    self.toggleCollapse = function () {
    	var element = $('#title_' + self.getEntryId(this) + ' div.accordion-inner');

    	var padding_top = parseInt(element.css("padding-top").replace("px", ""));

    	var maxHeight = 0;
    	element.children().each(function (index, value) {
    		var e = $(value);
    		var height = e.position().top + e.outerHeight() - padding_top;
    		maxHeight = height > maxHeight ? height : maxHeight;
    	});

    	this.height(maxHeight);
    }

    self.getEntryId = function (data) {
    	return "custom_command_" + md5(data.name() + ":" + data.type);
    }

    self.bgImage = function(data) { 
    	return data.backgroundColor1() != '' && data.backgroundColor2() != '' ? "linear-gradient(to bottom," + data.backgroundColor1() + "," + data.backgroundColor2() + ")" : '';    	
	}
}
