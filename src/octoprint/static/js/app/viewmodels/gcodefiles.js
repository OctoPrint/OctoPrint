function GcodeFilesViewModel(printerStateViewModel, loginStateViewModel) {
    var self = this;

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

    // initialize list helper
    self.listHelper = new ItemListHelper(
        "gcodeFiles",
        {
            "name": function(a, b) {
                // sorts ascending
                if (a["name"].toLocaleLowerCase() < b["name"].toLocaleLowerCase()) return -1;
                if (a["name"].toLocaleLowerCase() > b["name"].toLocaleLowerCase()) return 1;
                return 0;
            },
            "upload": function(a, b) {
                // sorts descending
                if (b["date"] === undefined || a["date"] > b["date"]) return -1;
                if (a["date"] < b["date"]) return 1;
                return 0;
            },
            "size": function(a, b) {
                // sorts descending
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
            self.listHelper.selectNone();
        } else {
            self.listHelper.selectItem(function(item) {
                return item.name == filename;
            })
        }
    }

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
        self.isSdReady(data.flags.sdReady);
    }

    self.requestData = function(filenameOverride) {
        $.ajax({
            url: AJAX_BASEURL + "gcodefiles",
            method: "GET",
            dataType: "json",
            success: function(response) {
                if (filenameOverride) {
                    response.filename = filenameOverride
                }
                self.fromResponse(response);
            }
        });
    }

    self.fromResponse = function(response) {
        self.listHelper.updateItems(response.files);

        if (response.filename) {
            // got a file to scroll to
            self.listHelper.switchToItem(function(item) {return item.name == response.filename});
        }

        self.freeSpace(response.free);

        self.highlightFilename(self.printerState.filename());
    }

    self.loadFile = function(filename, printAfterLoad) {
        var file = self.listHelper.getItem(function(item) {return item.name == filename});
        if (!file) return;

        var origin;
        if (file.origin === undefined) {
            origin = "local";
        } else {
            origin = file.origin;
        }

        $.ajax({
            url: AJAX_BASEURL + "gcodefiles/" + origin + "/" + filename,
            type: "POST",
            dataType: "json",
            contentType: "application/json; charset=UTF-8",
            data: JSON.stringify({command: "load", print: printAfterLoad})
        })
    }

    self.removeFile = function(filename) {
        var file = self.listHelper.getItem(function(item) {return item.name == filename});
        if (!file) return;

        var origin;
        if (file.origin === undefined) {
            origin = "local";
        } else {
            origin = file.origin;
        }

        $.ajax({
            url: AJAX_BASEURL + "gcodefiles/" + origin + "/" + filename,
            type: "DELETE",
            success: self.fromResponse
        })
    }

    self.initSdCard = function() {
        self._sendSdCommand("init");
    }

    self.releaseSdCard = function() {
        self._sendSdCommand("release");
    }

    self.refreshSdFiles = function() {
        self._sendSdCommand("refresh");
    }

    self._sendSdCommand = function(command) {
        $.ajax({
            url: AJAX_BASEURL + "control/sd",
            type: "POST",
            dataType: "json",
            data: {command: command}
        });
    }

    self.getPopoverContent = function(data) {
        var output = "<p><strong>Uploaded:</strong> " + data["date"] + "</p>";
        if (data["gcodeAnalysis"]) {
            output += "<p>";
            output += "<strong>Filament:</strong> " + data["gcodeAnalysis"]["filament"] + "<br>";
            output += "<strong>Estimated Print Time:</strong> " + data["gcodeAnalysis"]["estimatedPrintTime"];
            output += "</p>";
        }
        if (data["prints"] && data["prints"]["last"]) {
            output += "<p>";
            output += "<strong>Last Print:</strong> <span class=\"" + (data["prints"]["last"]["success"] ? "text-success" : "text-error") + "\">" + data["prints"]["last"]["date"] + "</span>";
            output += "</p>";
        }
        return output;
    }

    self.getSuccessClass = function(data) {
        if (!data["prints"] || !data["prints"]["last"]) {
            return "";
        }
        return data["prints"]["last"]["success"] ? "text-success" : "text-error";
    }

    self.enableRemove = function(data) {
        return self.loginState.isUser() && !(self.listHelper.isSelected(data) && (self.isPrinting() || self.isPaused()));
    }

    self.enableSelect = function(data, printAfterSelect) {
        var isLoadActionPossible = self.loginState.isUser() && self.isOperational() && !(self.isPrinting() || self.isPaused() || self.isLoading());
        return isLoadActionPossible && !self.listHelper.isSelected(data);
    }

}

