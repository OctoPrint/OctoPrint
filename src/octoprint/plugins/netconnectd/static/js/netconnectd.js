$(function() {
    function NetconnectdViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settingsViewModel = parameters[1];

        self.pollingEnabled = false;
        self.pollingTimeoutId = undefined;

        self.enableQualitySorting = ko.observable(false);

        self.statusAp = ko.observable();
        self.statusLink = ko.observable();
        self.statusWifiAvailable = ko.observable();

        self.editorWifi = undefined;
        self.editorWifiSsid = ko.observable();
        self.editorWifiPassphrase1 = ko.observable();
        self.editorWifiPassphrase2 = ko.observable();

        self.working = ko.observable(false);

        self.editorWifiPassphraseMismatch = ko.computed(function() {
            return self.editorWifiPassphrase1() != self.editorWifiPassphrase2();
        });

        self.error = ko.observable(false);
        self.connectionStateText = ko.computed(function() {
            if (self.error()) {
                return gettext("Error while talking to netconnectd, is the service running?")
            } else if (self.statusAp() && !self.statusWifiAvailable()) {
                return gettext("Access Point is active, wifi configured but not available");
            } else if (self.statusAp() && self.statusWifiAvailable()) {
                return gettext("Access Point is active, wifi configured");
            } else if (self.statusLink()) {
                return gettext("Connected");
            }

            return gettext("Unknown connection state");
        });

        // initialize list helper
        self.listHelper = new ItemListHelper(
            "wifis",
            {
                "ssid": function (a, b) {
                    // sorts ascending
                    if (a["ssid"].toLocaleLowerCase() < b["ssid"].toLocaleLowerCase()) return -1;
                    if (a["ssid"].toLocaleLowerCase() > b["ssid"].toLocaleLowerCase()) return 1;
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

        self.getEntryId = function(ssid) {
            return "settings_plugin_netconnectd_connectbutton_" + md5(data.ssid);
        };

        self.refresh = function() {
            self.requestData();
        };

        self.fromResponse = function (response) {
            if (response.error !== undefined) {
                self.error(true);
                return;
            } else {
                self.error(false);
            }

            self.statusAp(response.status.ap);
            self.statusLink(response.status.link);
            self.statusWifiAvailable(response.status.wifi_available);

            var enableQualitySorting = false;
            _.each(response.wifis, function(wifi) {
                if (wifi.quality != undefined) {
                    enableQualitySorting = true;
                }
            });
            self.enableQualitySorting(enableQualitySorting);

            self.listHelper.updateItems(response.wifis);
            if (!enableQualitySorting) {
                self.listHelper.changeSorting("ssid");
            }

            if (self.pollingEnabled) {
                self.pollingTimeoutId = setTimeout(function() {
                    self.requestData();
                }, 30000)
            }
        };

        self.configureWifi = function(data) {
            self.editorWifi = data;
            self.editorWifiSsid(data.ssid);
            self.editorWifiPassphrase1(undefined);
            self.editorWifiPassphrase2(undefined);
            if (data.encrypted) {
                $("#settings_plugin_netconnectd_wificonfig").modal("show");
            } else {
                self.confirmWifiConfiguration();
            }
        };

        self.confirmWifiConfiguration = function() {
            self.sendWifiConfig(self.editorWifiSsid(), self.editorWifiPassphrase1(), function() {
                self.editorWifi = undefined;
                self.editorWifiSsid(undefined);
                self.editorWifiPassphrase1(undefined);
                self.editorWifiPassphrase2(undefined);
                $("#settings_plugin_netconnectd_wificonfig").modal("hide");
            });
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

        self.sendWifiConfig = function(ssid, psk, successCallback, failureCallback) {
            self.working(true);
            self._postCommand("configure_wifi", {ssid: ssid, psk: psk}, successCallback, failureCallback, function() {
                self.working(false);
            });
        };

        self._postCommand = function (command, data, successCallback, failureCallback, alwaysCallback) {
            var payload = _.extend(data, {command: command});

            $.ajax({
                url: API_BASEURL + "plugin/netconnectd",
                type: "POST",
                dataType: "json",
                data: JSON.stringify(payload),
                contentType: "application/json; charset=UTF-8",
                success: function(response) {
                    if (successCallback) successCallback(response);
                },
                error: function() {
                    if (failureCallback) failureCallback();
                },
                complete: function() {
                    if (alwaysCallback) alwaysCallback();
                }
            });
        };

        self.requestData = function () {
            if (self.pollingTimeoutId != undefined) {
                clearTimeout(self.pollingTimeoutId);
                self.pollingTimeoutId = undefined;
            }

            $.ajax({
                url: API_BASEURL + "plugin/netconnectd",
                type: "GET",
                dataType: "json",
                success: self.fromResponse
            });
        };

        self.onBeforeBinding = function() {
            self.settings = self.settingsViewModel.settings;
            self.requestData();
        };

        self.onDataUpdaterReconnect = function() {
            self.requestData();
        };

        self.onSettingsShown = function() {
            self.pollingEnabled = true;
            self.requestData();
        };

        self.onSettingsHidden = function() {
            if (self.pollingTimeoutId != undefined) {
                self.pollingTimeoutId = undefined;
            }
            self.pollingEnabled = false;
        }

    }

    // view model class, parameters for constructor, container to bind to
    ADDITIONAL_VIEWMODELS.push([NetconnectdViewModel, ["loginStateViewModel", "settingsViewModel"], document.getElementById("settings_plugin_netconnectd_dialog")]);
});
