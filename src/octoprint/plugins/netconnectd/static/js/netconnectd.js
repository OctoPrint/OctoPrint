$(function() {
    function NetconnectdViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settingsViewModel = parameters[1];

        self.settings = undefined;

        self.data = {
            wifis: ko.observableArray([]),
            status: {
                ap: ko.observable(),
                connectedToWifi: ko.observable()
            }
        };

        self.editorWifiSsid = ko.observable();
        self.editorWifiPassphrase1 = ko.observable();
        self.editorWifiPassphrase2 = ko.observable();

        self.editorWifiPassphraseMismatch = ko.computed(function() {
            return self.editorWifiPassphrase1() != self.editorWifiPassphrase2();
        });

        self.connectionStateText = ko.computed(function() {
            if (self.data.status.ap()) {
                return gettext("Access Point is active");
            } else if (self.data.status.connectedToWifi()) {
                return gettext("Connected to configured Wifi");
            } else {
                return gettext("Connected")
            }
        });

        // initialize list helper
        self.listHelper = new ItemListHelper(
            "wifis",
            {
                "name": function (a, b) {
                    // sorts ascending
                    if (a["name"].toLocaleLowerCase() < b["name"].toLocaleLowerCase()) return -1;
                    if (a["name"].toLocaleLowerCase() > b["name"].toLocaleLowerCase()) return 1;
                    return 0;
                },
                "quality": function (a, b) {
                    // sorts descending
                    if (a["quality"] > b["quality"]) return -1;
                    if (a["quality"] < b["quality"]) return 1;
                    return 0;
                }
            },
            {
            },
            "quality",
            [],
            [],
            10
        );

        self.fromResponse = function (response) {
            if (response.error !== undefined) {
                return;
            }
            ko.mapping.fromJS(response, self.data);
            self.listHelper.updateItems(response.wifis);
        };

        self.configureWifi = function(data) {
            if (data.encrypted) {
                self.editorWifiSsid(data.ssid);
                self.editorWifiPassphrase1(undefined);
                self.editorWifiPassphrase2(undefined);
                $("#settings_plugin_netconnectd_wificonfig").modal("show");
            } else {
                self.confirmWifiConfiguration();
            }
        };

        self.confirmWifiConfiguration = function() {
            self.sendWifiConfig(self.editorWifiSsid(), self.editorWifiPassphrase1(), function() {
                self.editorWifiSsid(undefined);
                self.editorWifiPassphrase1(undefined);
                self.editorWifiPassphrase2(undefined);
                $("#settings_plugin_netconnectd_wificonfig").modal("hide");
            })
        };

        self.sendStartAp = function() {
            self._postCommand("start_ap", {});
        };

        self.sendStopAp = function() {
            self._postCommand("stop_ap", {});
        };

        self.sendWifiRefresh = function(force) {
            if (force === undefined) force = false;
            self._postCommand("list_wifi", {force: force}, function(response) {
                self.fromResponse({"wifis": response});
            });
        };

        self.sendWifiConfig = function(ssid, psk, callback) {
            self._postCommand("configure_wifi", {ssid: ssid, psk: psk});
        };

        self._postCommand = function (command, data, successCallback, failureCallback) {
            var payload = _.extend(data, {command: command});

            $.ajax({
                url: API_BASEURL + "plugin/netconnectd",
                type: "POST",
                dataType: "json",
                data: payload,
                success: function(response) {
                    if (successCallback) successCallback(response);
                },
                fail: function() {
                    if (failureCallback) failureCallback();
                }
            });
        };

        self.requestData = function () {
            $.ajax({
                url: API_BASEURL + "plugin/netconnectd",
                type: "GET",
                dataType: "json",
                success: self.fromResponse
            });
        };

        self.onBeforeBinding = function() {
            self.settings = self.settingsViewModel.settings;
        };

        self.onStartup = function() {
            self.requestData();
        };
    }

    // view model class, parameters for constructor, container to bind to
    ADDITIONAL_VIEWMODELS.push([NetconnectdViewModel, ["loginStateViewModel", "settingsViewModel"], document.getElementById("settings_plugin_netconnectd_dialog")]);
});
