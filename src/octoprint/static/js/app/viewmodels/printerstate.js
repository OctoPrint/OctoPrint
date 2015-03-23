function PrinterStateViewModel(loginStateViewModel) {
    var self = this;

    self.loginState = loginStateViewModel;

    self.stateString = ko.observable(undefined);
    self.isErrorOrClosed = ko.observable(undefined);
    self.isOperational = ko.observable(undefined);
    self.isPrinting = ko.observable(undefined);
    self.isPaused = ko.observable(undefined);
    self.isError = ko.observable(undefined);
    self.isReady = ko.observable(undefined);
    self.isLoading = ko.observable(undefined);
    self.isSdReady = ko.observable(undefined);

    self.filename = ko.observable(undefined);
    self.progress = ko.observable(undefined);
    self.filesize = ko.observable(undefined);
    self.filepos = ko.observable(undefined);
    self.printTime = ko.observable(undefined);
    self.printTimeLeft = ko.observable(undefined);
    self.sd = ko.observable(undefined);
    self.timelapse = ko.observable(undefined);

    self.filament = ko.observableArray([]);
    self.estimatedPrintTime = ko.observable(undefined);

    self.currentHeight = ko.observable(undefined);

    self.estimatedPrintTimeString = ko.computed(function() {
        if (!self.estimatedPrintTime())
            return "-";
        return formatDuration(self.estimatedPrintTime());
    });
    self.byteString = ko.computed(function() {
        if (!self.filesize())
            return "-";
        var filepos = self.filepos() ? formatSize(self.filepos()) : "-";
        return filepos + " / " + formatSize(self.filesize());
    });
    self.heightString = ko.computed(function() {
        if (!self.currentHeight())
            return "-";
        return _.sprintf("%.02fmm", self.currentHeight());
    });
    self.printTimeString = ko.computed(function() {
        if (!self.printTime())
            return "-";
        return formatDuration(self.printTime());
    });
    self.printTimeLeftString = ko.computed(function() {
        if (!self.printTimeLeft())
            return "-";
        return formatDuration(self.printTimeLeft());
    });
    self.progressString = ko.computed(function() {
        if (!self.progress())
            return 0;
        return self.progress();
    });
    self.pauseString = ko.computed(function() {
        if (self.isPaused())
            return "Continue";
        else
            return "Pause";
    });

    self.timelapseString = ko.computed(function() {
        var timelapse = self.timelapse();

        if (!timelapse || !timelapse.hasOwnProperty("type"))
            return "-";

        var type = timelapse["type"];
        if (type == "zchange") {
            return "On Z Change";
        } else if (type == "timed") {
            return "Timed (" + timelapse["options"]["interval"] + "s)";
        } else {
            return "-";
        }
    });

    self.fromCurrentData = function(data) {
        self._fromData(data);
    };

    self.fromHistoryData = function(data) {
        self._fromData(data);
    };

    self.fromTimelapseData = function(data) {
        self.timelapse(data);
    };

    self._fromData = function(data) {
        self._processStateData(data.state);
        self._processJobData(data.job);
        self._processProgressData(data.progress);
        self._processZData(data.currentZ);
    };

    self._processStateData = function(data) {
        self.stateString(data.stateString);
        self.isErrorOrClosed(data.flags.closedOrError);
        self.isOperational(data.flags.operational);
        self.isPaused(data.flags.paused);
        self.isPrinting(data.flags.printing);
        self.isError(data.flags.error);
        self.isReady(data.flags.ready);
        self.isSdReady(data.flags.sdReady);
    };

    self._processJobData = function(data) {
        if (data.file) {
            self.filename(data.file.name);
            self.filesize(data.file.size);
            self.sd(data.file.origin == "sdcard");
        } else {
            self.filename(undefined);
            self.filesize(undefined);
            self.sd(undefined);
        }

        self.estimatedPrintTime(data.estimatedPrintTime);

        var result = [];
        if (data.filament && typeof(data.filament) == "object" && _.keys(data.filament).length > 0) {
            var i = 0;
            do {
                var key = "tool" + i;
                if (data.filament.hasOwnProperty(key) && data.filament[key].hasOwnProperty("length") && data.filament[key].length > 0) {
                    result.push({
                        name: ko.observable("Tool " + i),
                        data: ko.observable(data.filament[key])
                    });
                }
                i++;
            } while (data.filament.hasOwnProperty("tool" + i));
        }
        self.filament(result);
    };

    self._processProgressData = function(data) {
        if (data.completion) {
            self.progress(data.completion);
        } else {
            self.progress(undefined);
        }
        self.filepos(data.filepos);
        self.printTime(data.printTime);
        self.printTimeLeft(data.printTimeLeft);
    };

    self._processZData = function(data) {
        self.currentHeight(data);
    };

    self.print = function() {
        var restartCommand = function() {
            self._jobCommand("restart");
        };

        if (self.isPaused()) {
            $("#confirmation_dialog .confirmation_dialog_message").text("This will restart the print job from the beginning.");
            $("#confirmation_dialog .confirmation_dialog_acknowledge").unbind("click");
            $("#confirmation_dialog .confirmation_dialog_acknowledge").click(function(e) {e.preventDefault(); $("#confirmation_dialog").modal("hide"); restartCommand(); });
            $("#confirmation_dialog").modal("show");
        } else {
            self._jobCommand("start");
        }

    };

    self.pause = function() {
        self._jobCommand("pause");
    };

    self.cancel = function() {
        self._jobCommand("cancel");
    };

    self._jobCommand = function(command) {
        $.ajax({
            url: API_BASEURL + "job",
            type: "POST",
            dataType: "json",
            contentType: "application/json; charset=UTF-8",
            data: JSON.stringify({command: command})
        });
    }
}
