function GcodeFilesViewModel(printerStateViewModel, loginStateViewModel) {
    var self = this;

    self.filename = "";

    self.printerState = printerStateViewModel;
    self.loginState = loginStateViewModel;

    self.isErrorOrClosed = ko.observable(undefined);
    self.isOperational = ko.observable(undefined);
    self.isPrinting = ko.observable(undefined);
    self.isPaused = ko.observable(undefined);
    self.isError = ko.observable(undefined);
    self.isReady = ko.observable(undefined);
    self.isLoading = ko.observable(undefined);
    self.isSdReady = ko.observable(undefined);

    self.selectedItem = ko.observable(undefined);
    self.requestResponse = ko.observable(undefined);

    self.freeSpace = ko.observable(undefined);
    self.freeSpaceString = ko.computed(function() {
        if (!self.freeSpace())
            return "-";
        return formatSize(self.freeSpace());
    });

	// initialize list helper
    self.listHelper = new ItemListHelper(
        "gcodeFiles",
        {
            "name": function(a, b) {
            	// sorts ascending
            	if (a["type"] == "dir" && b["type"] == "file") return -1;
            	if (a["type"] == "file" && b["type"] == "dir") return 1;

                if (a["name"].toLocaleLowerCase() < b["name"].toLocaleLowerCase()) return -1;
                if (a["name"].toLocaleLowerCase() > b["name"].toLocaleLowerCase()) return 1;
                return 0;
            },
            "upload": function(a, b) {
            	// sorts descending
            	if (a["type"] == "dir" && b["type"] == "file") return -1;
            	if (a["type"] == "file" && b["type"] == "dir") return 1;

                if (b["date"] === undefined || a["date"] > b["date"]) return -1;
                if (a["date"] < b["date"]) return 1;
                return 0;
            },
            "size": function(a, b) {
            	// sorts descending
            	if (a["type"] == "dir" && b["type"] == "file") return -1;
            	if (a["type"] == "file" && b["type"] == "dir") return 1;

                if (b["bytes"] === undefined || a["bytes"] > b["bytes"]) return -1;
                if (a["bytes"] < b["bytes"]) return 1;
                return 0;
            }
        },
        {
            "printed": function(file) {
                return !(file["prints"] && file["prints"]["success"] && file["prints"]["success"] > 0);
            },
            "sd": function(file) {
                return file["origin"] && file["origin"] == "sdcard";
            },
            "local": function(file) {
                return !(file["origin"] && file["origin"] == "sdcard");
            }
        },
        "name",
        [],
        [["sd", "local"]],
        CONFIG_GCODEFILESPERPAGE
    );

    self.onClick = function(data)
    {
    	var obj = $("#image" + data.href);
    	if (obj.next().hasClass("collapsed"))
    	{
    		obj.removeClass("icon-folder-close");
    		obj.addClass("icon-folder-open");
    	}
    	else
    	{
    		obj.removeClass("icon-folder-open");
    		obj.addClass("icon-folder-close");
    	}
	}

    self.isLoadActionPossible = ko.computed(function() {
        return self.loginState.isUser() && !self.isPrinting() && !self.isPaused() && !self.isLoading();
    });

    self.isLoadAndPrintActionPossible = ko.computed(function() {
        return self.loginState.isUser() && self.isOperational() && self.isLoadActionPossible();
    });

    self.printerState.filename.subscribe(function(newValue) {
        self.highlightFilename(newValue);
    });

    self.highlightFilename = function(filename) {
        if (filename == undefined) {
        	self.selectedItem(undefined);
        } else {
        	if (self.listHelper.items().length == 0)
        		return;

        	if (self.listHelper.items()[0] == undefined || !self.selectItem(self.listHelper.items()[0].data, filename))
        		self.selectItem(self.listHelper.items()[1].data, filename);
        }
    };

    self.fromCurrentData = function(data) {
        self._processStateData(data.state);
    };

    self.fromHistoryData = function(data) {
        self._processStateData(data.state);
    };

    self._processStateData = function(data) {
        self.isErrorOrClosed(data.flags.closedOrError);
        self.isOperational(data.flags.operational);
        self.isPaused(data.flags.paused);
        self.isPrinting(data.flags.printing);
        self.isError(data.flags.error);
        self.isReady(data.flags.ready);
        self.isLoading(data.flags.loading);
        self.isSdReady(data.flags.sdReady);
    };

    self.changeSorting = function (sorting) {
    	self.listHelper.changeSorting(sorting);
    };
    self.toggleFilter = function (filter) {
    	self.listHelper.toggleFilter(filter);
    };

    self.displayMode = function (item) {
    	return item.type == "file" ? "fileTemplate" : "dirTemplate";
    };

    self.requestData = function(filenameToFocus, locationToFocus) {
        $.ajax({
            url: API_BASEURL + "files",
            method: "GET",
            dataType: "json",
            success: function(response) {
                self.fromResponse(response, filenameToFocus, locationToFocus);
            }
        });
    };

    self.fromResponse = function(response, filenameToFocus, locationToFocus) {
    	var i = 0;
    	recursiveCheck = function (element, index, list) {
    		element.href = i++;
    		_.each(element.data, recursiveCheck);
    	};
    	_.each(response.directories, recursiveCheck);
        self.listHelper.updateItems(response.directories);

        if (filenameToFocus) {
            // got a file to scroll to
            if (locationToFocus === undefined) {
                locationToFocus = "local";
            }
            self.listHelper.switchToItem(function(item) {return item.name == filenameToFocus && item.origin == locationToFocus});
        }

        if (response.free) {
            self.freeSpace(response.free);
        }

        self.highlightFilename(self.printerState.filename());
        self.requestResponse(response);
    };

    self.loadFile = function (data, printAfterLoad) {
        $.ajax({
            url: data.refs.resource,
            type: "POST",
            dataType: "json",
            contentType: "application/json; charset=UTF-8",
            data: JSON.stringify({command: "select", print: printAfterLoad})
        });
    };

    self.removeFile = function (data) {
        var origin;
        if (data.origin === undefined) {
            origin = "local";
        } else {
        	origin = data.origin;
        }

        $.ajax({
        	url: data.refs.resource,
            type: "DELETE",
            success: function() { self.requestData(); }
        });
    };

    self.initSdCard = function() {
        self._sendSdCommand("init");
    };

    self.releaseSdCard = function() {
        self._sendSdCommand("release");
    };

    self.refreshSdFiles = function() {
        self._sendSdCommand("refresh");
    };

    self._sendSdCommand = function(command) {
        $.ajax({
            url: API_BASEURL + "printer/sd",
            type: "POST",
            dataType: "json",
            contentType: "application/json; charset=UTF-8",
            data: JSON.stringify({command: command})
        });
    };

    self.getPopoverContent = function(data) {
        var output = "<p><strong>Uploaded:</strong> " + formatDate(data["date"]) + "</p>";
        if (data["gcodeAnalysis"]) {
            output += "<p>";
            if (data["gcodeAnalysis"]["filament"] && typeof(data["gcodeAnalysis"]["filament"]) == "object") {
                var filament = data["gcodeAnalysis"]["filament"];
                if (_.keys(filament).length == 1) {
                    output += "<strong>Filament:</strong> " + formatFilament(data["gcodeAnalysis"]["filament"]["tool" + 0]) + "<br>";
                } else {
                    var i = 0;
                    do {
                        output += "<strong>Filament (Tool " + i + "):</strong> " + formatFilament(data["gcodeAnalysis"]["filament"]["tool" + i]) + "<br>";
                        i++;
                    } while (filament.hasOwnProperty("tool" + i));
                }
            }
            output += "<strong>Estimated Print Time:</strong> " + formatDuration(data["gcodeAnalysis"]["estimatedPrintTime"]);
            output += "</p>";
        }
        if (data["prints"] && data["prints"]["last"]) {
            output += "<p>";
            output += "<strong>Last Print:</strong> <span class=\"" + (data["prints"]["last"]["success"] ? "text-success" : "text-error") + "\">" + formatDate(data["prints"]["last"]["date"]) + "</span>";
            output += "</p>";
        }
        return output;
    };

    self.getSuccessClass = function(data) {
        if (!data["prints"] || !data["prints"]["last"]) {
            return "";
        }
        return data["prints"]["last"]["success"] ? "text-success" : "text-error";
    };

    self.selectItem = function (list, filename) {
    	var index = filename.indexOf('/');
    	if (index == -1)
    		index = filename.indexOf('\\');

    	if (index != -1)
		{
    		var subdir = filename.substring(0, index);
    		filename = filename.substring(index + 1);

    		return self.selectItem(_.chain(list).filter(function (v) { return v.name == subdir; }).map(function (v) { return v.data; }).first().value(), filename);
		}
		else 
    	{
    		self.selectedItem(_.chain(list).filter(function (v) { return v.name == filename; }).first().value());
    	}
    	return false;
    };

    self.isSelected = function (data) {
    	if (data == undefined || self.selectedItem() == undefined)
    		return false;

    	var selectedItem = self.selectedItem();
    	return selectedItem.relativepath == data.relativepath;
    };
    self.isPartiallySelected = function (data) {
    	if (data == undefined || self.selectedItem() == undefined)
    		return false;

    	var selectedItem = self.selectedItem();
    	return selectedItem.relativepath.substring(0, data.relativepath.length) == data.relativepath;
    };

    self.enableRemove = function(data) {
    	return self.loginState.isUser() && !(self.isPartiallySelected(data) && (self.isPrinting() || self.isPaused()));
    };

    self.enableSelect = function(data, printAfterSelect) {
    	var isLoadActionPossible = self.loginState.isUser() && self.isOperational() && !(self.isPrinting() || self.isPaused() || self.isLoading());
    	return isLoadActionPossible && !self.isSelected(data);
    };
}

