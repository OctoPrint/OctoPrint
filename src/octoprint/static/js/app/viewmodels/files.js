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
    	var obj = $("#image" + data.name);
    	if (obj.parent().hasClass("collapsed"))
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
        	self.selectNone(self.listHelper);
        } else {
        	self.selectNone(self.listHelper);
        	self.selectItem(self.listHelper, filename);
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
		
    	var itemlist = self.listHelper.items();
    	for (var i = 0; i < itemList.length; i++) {
    		if (itemList[i].type == "dir")
    			itemList[i].files.changeSorting(sorting);
		}
    };
    self.toggleFilter = function (filter) {
    	self.listHelper.toggleFilter(filter);

    	var itemlist = self.listHelper.items();
    	for (var i = 0; i < itemList.length; i++) {
    		if (itemList[i].type == "dir")
    			itemList[i].files.toggleFilter(filter);
    	}
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
    	var files = response.files;

    	var dirs = {};
    	var looseFiles = [];

    	_.each(files, function (element, index, list) {
    		element.type = "file";
        	if (!element.hasOwnProperty("relativepath"))
			{
        		element.relativepath = "";
        		looseFiles.push(element);
			}
        	else
        	{
        		var path = element.relativepath.substring(0, element.relativepath.lastIndexOf("/"));
        		if (path == "")
        			looseFiles.push(element);
        		else
        		{
        			if (!dirs.hasOwnProperty(path))
        				dirs[path] = [];

        			dirs[path].push(element);
				}
			}
            if (!element.hasOwnProperty("size")) element.size = undefined;
            if (!element.hasOwnProperty("date")) element.date = undefined;
        });

        var itemlist = []
        _.each(dirs, function (element, index, list) {
        	var list = new ItemListHelper(
				"gcodeFiles",
				{
					"name": function (a, b) {
						if (a["type"] == "dir") a.files.changeSorting("name");
						if (b["type"] == "dir") b.files.changeSorting("name");

        				// sorts ascending
        				if (a["type"] == "dir" && b["type"] == "file") return -1;
        				if (a["type"] == "file" && b["type"] == "dir") return 1;

        				if (a["name"].toLocaleLowerCase() < b["name"].toLocaleLowerCase()) return -1;
        				if (a["name"].toLocaleLowerCase() > b["name"].toLocaleLowerCase()) return 1;
        				return 0;
        			},
					"upload": function (a, b) {
						if (a["type"] == "dir") a.files.changeSorting("upload");
						if (b["type"] == "dir") b.files.changeSorting("upload");

        				// sorts descending
        				if (a["type"] == "dir" && b["type"] == "file") return -1;
        				if (a["type"] == "file" && b["type"] == "dir") return 1;

        				if (b["date"] === undefined || a["date"] > b["date"]) return -1;
        				if (a["date"] < b["date"]) return 1;
        				return 0;
        			},
					"size": function (a, b) {
						if (a["type"] == "dir") a.files.changeSorting("size");
						if (b["type"] == "dir") b.files.changeSorting("size");

        				// sorts descending
        				if (a["type"] == "dir" && b["type"] == "file") return -1;
        				if (a["type"] == "file" && b["type"] == "dir") return 1;

        				if (b["bytes"] === undefined || a["bytes"] > b["bytes"]) return -1;
        				if (a["bytes"] < b["bytes"]) return 1;
        				return 0;
        			}
				},
				{
        			"printed": function (file) {
        				return !(file["prints"] && file["prints"]["success"] && file["prints"]["success"] > 0);
        			},
        			"sd": function (file) {
        				return file["origin"] && file["origin"] == "sdcard";
        			},
        			"local": function (file) {
        				return !(file["origin"] && file["origin"] == "sdcard");
        			}
				},
				"name",
				[],
				[["sd", "local"]],
				CONFIG_GCODEFILESPERPAGE
			);
        	list.updateItems(element);

        	itemlist.push({
        		"name": index,
        		"type": "dir",
				"files": list
        	});
        });
        _.each(looseFiles, function (element, index, list) {
        	itemlist.push(element);
        });
        self.listHelper.updateItems(itemlist);

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
    };

    self.findItem = function (item) {
    	return item.name == self.filename;
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
        if (file.origin === undefined) {
            origin = "local";
        } else {
            origin = file.origin;
        }

        $.ajax({
            url: file.refs.resource,
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

    self.selectNone = function (list) {
    	var itemList = list.items();
    	for (var i = 0; i < itemList.length; i++) {
    		if (itemList[i].type == "dir") {
    			itemList[i].files.selectNone();
    		}
    	}
    };
    self.selectItem = function (list, filename) {
    	var index = filename.indexOf('/');
    	if (index == -1)
    		index = filename.indexOf('\\');

    	if (index != -1)
		{
    		list.selectNone();

    		var subdir = filename.substring(0, index);
    		filename = filename.substring(index + 1);

    		itemList = list.items();
    		for (var i = 0; i < itemList.length; i++)
    		{
    			if (itemList[i].type == "dir")
    			{
    				if (itemList[i].name == subdir)
    					self.selectItem(itemList[i].files, filename);
				}
    		}
		}
		else 
    	{
    		self.filename = filename;
    		list.selectItem(self.findItem);
		}
    };

    self.isSelected = function (data) {
    	var list = self.listHelper;
    	var subdir = data.relativepath.substring(0, data.relativepath.lastIndexOf("/"));
    	while (subdir != "") {
    		var index = subdir.indexOf('/');
    		if (index == -1)
    			index = subdir.length;

    		self.filename = subdir.substring(0, index);
    		subdir = subdir.substring(index + 1);

    		list = list.getItem(self.findItem).files;
    	}

    	var selected = list.isSelected(data);

    	return list.isSelected(data);
    };

    self.enableRemove = function(data) {
        return self.loginState.isUser() && !(self.listHelper.isSelected(data) && (self.isPrinting() || self.isPaused()));
    };

    self.enableSelect = function(data, printAfterSelect) {
    	var isLoadActionPossible = self.loginState.isUser() && self.isOperational() && !(self.isPrinting() || self.isPaused() || self.isLoading());
    	return isLoadActionPossible && !self.isSelected(data);
    };
}

