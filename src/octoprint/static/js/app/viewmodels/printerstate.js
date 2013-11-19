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

    self.filament = ko.observable(undefined);
    self.estimatedPrintTime = ko.observable(undefined);

    self.currentHeight = ko.observable(undefined);

    self.byteString = ko.computed(function() {
        if (!self.filesize())
            return "-";
        var filepos = self.filepos() ? self.filepos() : "-";
        return filepos + " / " + self.filesize();
    });
    self.heightString = ko.computed(function() {
        if (!self.currentHeight())
            return "-";
        return self.currentHeight();
    })
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
    }

    self.fromHistoryData = function(data) {
        self._fromData(data);
    }

    self.fromTimelapseData = function(data) {
        self.timelapse(data);
    }

    self._fromData = function(data) {
        self._processStateData(data.state)
        self._processJobData(data.job);
        self._processProgressData(data.progress);
        self._processZData(data.currentZ);
    }

    self._processStateData = function(data) {
        self.stateString(data.stateString);
        self.isErrorOrClosed(data.flags.closedOrError);
        self.isOperational(data.flags.operational);
        self.isPaused(data.flags.paused);
        self.isPrinting(data.flags.printing);
        self.isError(data.flags.error);
        self.isReady(data.flags.ready);
        self.isSdReady(data.flags.sdReady);
    }

    self._processJobData = function(data) {
        self.filename(data.filename);
        self.filesize(data.filesize);
        self.estimatedPrintTime(data.estimatedPrintTime);
        self.filament(data.filament);
        self.sd(data.sd);
    }

    self._processProgressData = function(data) {
        if (data.progress) {
            self.progress(Math.round(data.progress * 100));
        } else {
            self.progress(undefined);
        }
        self.filepos(data.filepos);
        self.printTime(data.printTime);
        self.printTimeLeft(data.printTimeLeft);
    }

    self._processZData = function(data) {
        self.currentHeight(data);
    }

    self.print = function() {
        var printAction = function() {
            self._jobCommand("start");
        }

        if (self.isPaused()) {
            $("#confirmation_dialog .confirmation_dialog_message").text("This will restart the print job from the beginning.");
            $("#confirmation_dialog .confirmation_dialog_acknowledge").click(function(e) {e.preventDefault(); $("#confirmation_dialog").modal("hide"); printAction(); });
            $("#confirmation_dialog").modal("show");
        } else {
            printAction();
        }

    }

    self.pause = function() {
        self._jobCommand("pause");
    }

    self.cancel = function() {
        self._jobCommand("cancel");
    }

    self._jobCommand = function(command) {
        $.ajax({
            url: AJAX_BASEURL + "control/job",
            type: "POST",
            dataType: "json",
            contentType: "application/json; charset=UTF-8",
            data: JSON.stringify({command: command})
        });
    }
}
