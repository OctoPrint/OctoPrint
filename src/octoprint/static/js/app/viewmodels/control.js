function ControlViewModel(loginStateViewModel, settingsViewModel) {
    var self = this;

    self.loginState = loginStateViewModel;
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

    self.tools = ko.observableArray([]);

    self.feedbackControlLookup = {};

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
    	self.controls(self._processControls(newVal));
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
	
	self._sortByRow = function(controls)
	{
		var rows = [];
		for (var i = 0; i < controls.length; i++)
		{
			if (!rows[controls[i].row()])
				rows[controls[i].row()] = [];
				
			rows[controls[i].row()].push(controls[i]);
		}
			
		for (var i = 0; i < rows.length; i++)
			if (rows[i])
				rows[i] = ko.observableArray(rows[i].sort(function(left, right) {
					if (left.index() < right.index())
						return -1;
			
					if (left.index() > right.index())
						return 1;
				
					return 0;
				}));
			
		return rows;
	}
	
    self._processControls = function (controls) {
    	var control = [];
        for (var i = 0; i < controls.length; i++) {
            control.push(self._processControl(controls[i]));
        }
        return self._sortByRow(control);
    }

    self._processControl = function (control) {
    	var c = { name: control.name, type: control.type };
    	if (control.type == "parametric_command" || control.type == "parametric_commands") {
    		c.input = [];
    		for (var i = 0; i < control.input().length; i++)
    			c.input.push({ name: control.input()[i].name(), parameter: control.input()[i].parameter(), value: control.input()[i].default });

        	c.input = ko.observableArray(c.input);
    	} else if (control.type == "feedback_command" || control.type == "feedback_commands") {
    		c.regex = control.regex;
    		c.template = control.template;
        	c.output = ko.observable("");
            self.feedbackControlLookup[control.name()] = control.output;
        } else if (control.type == "section") {
        	c.children = ko.observableArray(self._processControls(control.children()));
		}
        if (control.hasOwnProperty("command")) c.command = control.command;
        if (control.hasOwnProperty("commands")) c.commands = control.commands;

        c.backgroundColor1 = control.backgroundColor1;
    	c.backgroundColor2 = control.backgroundColor2;
        c.foregroundColor = control.foregroundColor;
		c.row = control.row;
		c.offset = control.offset;
		c.index = control.index;

        return c;
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
        if (command.type == "command" || command.type == "parametric_command" || command.type == "feedback_command") {
            // single command
            data = {"command" : command.command()};
        } else if (command.type == "commands" || command.type == "parametric_commands") {
            // multi command
            data = {"commands": command.commands().toString().split('\n')};
        }

        if (command.type == "parametric_command" || command.type == "parametric_commands") {
            // parametric command(s)
            data["parameters"] = {};
            for (var i = 0; i < command.input().length; i++) {
                data["parameters"][command.input()[i].parameter] = command.input()[i].value;
            }
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
        	case "feedback_command":
        	case "feedback_commands":
                return "customControls_feedbackCommandTemplate";
            case "feedback":
                return "customControls_feedbackTemplate";
            default:
                return "customControls_emptyTemplate";
        }
    }

	// Dynamic Commands
    self.getEntryId = function (data) {
    	return "custom_command_" + md5(data["name"] + ":" + data["type"]);
    };

    $("#customControls").mousemove(function (event) {
    	var msg = "Handler for .mousemove() called at ";
    	msg += event.pageX + ", " + event.pageY;
    	$("#log").append("<div>" + msg + "</div>");
    });

    self.createCommand = function(parent, data) {
    }
    self.deleteCommand = function (parent, data) {
    }
    self.editCommand = function (parent, data) {
    }

    self.deleteSection = function (parent, data) {
    }
}
