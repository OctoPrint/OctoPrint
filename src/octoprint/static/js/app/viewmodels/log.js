function LogViewModel(loginStateViewModel) {
    var self = this;

    self.loginState = loginStateViewModel;

    // initialize list helper
    self.listHelper = new ItemListHelper(
        "logFiles",
        {
            "name": function(a, b) {
                // sorts ascending
                if (a["name"].toLocaleLowerCase() < b["name"].toLocaleLowerCase()) return -1;
                if (a["name"].toLocaleLowerCase() > b["name"].toLocaleLowerCase()) return 1;
                return 0;
            },
            "modification": function(a, b) {
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
        CONFIG_LOGFILESPERPAGE
    );

    self.requestData = function() {
        $.ajax({
            url: API_BASEURL + "logs",
            type: "GET",
            dataType: "json",
            success: self.fromResponse
        });
    };

    self.fromResponse = function(response) {
        var files = response.files;
        if (files === undefined)
            return;

        self.listHelper.updateItems(files);
    }

    self.removeFile = function(filename) {
        $.ajax({
            url: API_BASEURL + "logs/" + filename,
            type: "DELETE",
            dataType: "json",
            success: self.requestData
        });
    }
}
