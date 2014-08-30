function TimelapseViewModel(loginStateViewModel) {
    var self = this;

    self.loginState = loginStateViewModel;

    self.timelapseType = ko.observable(undefined);
    self.timelapseTimedInterval = ko.observable(undefined);
    self.timelapsePostRoll = ko.observable(undefined);

    self.persist = ko.observable(false);
    self.isDirty = ko.observable(false);

    self.isErrorOrClosed = ko.observable(undefined);
    self.isOperational = ko.observable(undefined);
    self.isPrinting = ko.observable(undefined);
    self.isPaused = ko.observable(undefined);
    self.isError = ko.observable(undefined);
    self.isReady = ko.observable(undefined);
    self.isLoading = ko.observable(undefined);

    self.timelapseTypeSelected = ko.computed(function() {
        return ("off" != self.timelapseType());
    });
    self.intervalInputEnabled = ko.computed(function() {
        return ("timed" == self.timelapseType());
    });
    self.saveButtonEnabled = ko.computed(function() {
        return self.isDirty() && self.isOperational() && !self.isPrinting() && self.loginState.isUser();
    });

    self.isOperational.subscribe(function(newValue) {
        self.requestData();
    });

    self.timelapseType.subscribe(function(newValue) {
        self.isDirty(true);
    });
    self.timelapseTimedInterval.subscribe(function(newValue) {
        self.isDirty(true);
    });

    // initialize list helper
    self.listHelper = new ItemListHelper(
        "timelapseFiles",
        {
            "name": function(a, b) {
                // sorts ascending
                if (a["name"].toLocaleLowerCase() < b["name"].toLocaleLowerCase()) return -1;
                if (a["name"].toLocaleLowerCase() > b["name"].toLocaleLowerCase()) return 1;
                return 0;
            },
            "creation": function(a, b) {
                // sorts descending
                if (a["date"] > b["date"]) return -1;
                if (a["date"] < b["date"]) return 1;
                return 0;
            },
            "size": function(a, b) {
                // sorts descending
                if (a["bytes"] > b["bytes"]) return -1;
                if (a["bytes"] < b["bytes"]) return 1;
                return 0;
            }
        },
        {
        },
        "name",
        [],
        [],
        CONFIG_TIMELAPSEFILESPERPAGE
    );

    self.requestData = function() {
        $.ajax({
            url: API_BASEURL + "timelapse",
            type: "GET",
            dataType: "json",
            success: self.fromResponse
        });
    };

    self.fromResponse = function(response) {
        var config = response.config;
        if (config === undefined) return;

        self.timelapseType(config.type);
        self.listHelper.updateItems(response.files);

        if (config.type == "timed" && response.config.interval) {
            self.timelapseTimedInterval(response.config.interval);
        } else {
            self.timelapseTimedInterval(undefined);
        }

        self.persist(false);
        self.isDirty(false);
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
    }

    self.removeFile = function(filename) {
        $.ajax({
            url: API_BASEURL + "timelapse/" + filename,
            type: "DELETE",
            dataType: "json",
            success: self.requestData
        });
    }

    self.save = function(data, event) {
        var data = {
            "type": self.timelapseType(),
            "postRoll": self.timelapsePostRoll(),
            "save": self.persist()
        }

        if (self.timelapseType() == "timed") {
            data["interval"] = self.timelapseTimedInterval();
        }

        $.ajax({
            url: API_BASEURL + "timelapse",
            type: "POST",
            dataType: "json",
            data: data,
            success: self.fromResponse
        });
    }
}
