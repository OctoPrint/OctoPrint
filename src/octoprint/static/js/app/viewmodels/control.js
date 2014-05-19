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
	
    self._processControls = function (controls) {
    	var control = [];
        for (var i = 0; i < controls.length; i++) {
            control.push(self._processControl(controls[i]));
        }
        return control;
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

    	if (control.hasOwnProperty("height")) c.height = control.height;
    	if (control.hasOwnProperty("left")) c.left = control.left;
    	if (control.hasOwnProperty("top")) c.top = control.top;

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
        } else if (command.type == "commands" || command.type == "parametric_commands" || command.type == "feedback_commands") {
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
    self.customCommandParentObject = {};
    self.customCommandData = {};

    self.showChevron = function (dir, index) {
    	if (dir == "down")
    	{
    		return index < self.controls().length-1;
    	}

    	return index > 0;
    }

    self.switchPlaces = function (index1, index2) {
    	self.settings.switchControls(index1, index2);
    }

    self.toggleCollapse = function () {
    	var element = $('#title_' + self.getEntryId(this));

    	if (this.height() != 0)
    	{
    		this.height(0);
		}
    	else
    	{
    		var maxHeight = 0;
    		element.children().each(function (index, value) {
    			var e = $(value);
    			maxHeight = e.position().top + e.outerHeight() > maxHeight ? e.position().top + e.outerHeight() : maxHeight;
    		});

    		this.height(maxHeight);
    	}

    	self.settings.saveControls(true);
    }

    self.getEntryId = function (data) {
    	return "custom_command_" + md5(data.name() + ":" + data.type);
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

    self.movementStopped = function (data, parentData) {
    	var element = $('#' + self.getEntryId(data));
    	var elementPos = element.position();

    	data.left(elementPos.left);
    	data.top(elementPos.top);

    	parentData.height(0);
    	self.toggleCollapse.call(parentData);
    }

    self.setData = function (parent, data) {
    	self.customCommandParentObject = parent;
    	self.customCommandData = data;
    }

    self.createCommand = function() {
    }
    self.deleteCommand = function() {
    }
    self.editCommand = function() {
    }

    self.deleteSection = function() {
    }
}
