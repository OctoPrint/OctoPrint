$(function() {
    function NetconnectdViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settingsViewModel = parameters[1];

        self.pollingEnabled = false;
        self.pollingTimeoutId = undefined;

        self.reconnectInProgress = false;
        self.reconnectTimeout = undefined;

        self.enableQualitySorting = ko.observable(false);

        self.hostname = ko.observable();
        self.status = {
            link: ko.observable(),
            connections: {
                ap: ko.observable(),
                wifi: ko.observable(),
                wired: ko.observable()
            },
            wifi: {
                current_ssid: ko.observable(),
                current_address: ko.observable()
            }
        };
        self.statusCurrentWifi = ko.observable();

        self.editorWifi = undefined;
        self.editorWifiSsid = ko.observable();
        self.editorWifiPassphrase1 = ko.observable();
        self.editorWifiPassphrase2 = ko.observable();
        self.editorWifiPassphraseMismatch = ko.computed(function() {
            return self.editorWifiPassphrase1() != self.editorWifiPassphrase2();
        });

        self.working = ko.observable(false);
        self.error = ko.observable(false);

        self.connectionStateText = ko.computed(function() {
            if (self.error()) {
                return gettext("Error while talking to netconnectd, is the service running?");
            } else if (self.status.connections.ap()) {
                return gettext("Acting as access point");
            } else if (self.status.link()) {
                if (self.status.connections.wired()) {
                    return gettext("Connected via wire");
                } else if (self.status.connections.wifi()) {
                    if (self.status.wifi.current_ssid()) {
                        return _.sprintf(gettext("Connected via wifi (SSID \"%(ssid)s\")"), {ssid: self.status.wifi.current_ssid()});
                    } else {
                        return gettext("Connected via wifi (unknown SSID)")
                    }
                } else {
                    return gettext("Connected (unknown connection)");
                }
            } else {
                return gettext("Not connected to network");
            }
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

        self.getEntryId = function(data) {
            return "settings_plugin_netconnectd_wifi_" + md5(data.ssid);
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

            self.hostname(response.hostname);

            self.status.link(response.status.link);
            self.status.connections.ap(response.status.connections.ap);
            self.status.connections.wifi(response.status.connections.wifi);
            self.status.connections.wired(response.status.connections.wired);
            self.status.wifi.current_ssid(response.status.wifi.current_ssid);
            self.status.wifi.current_address(response.status.wifi.current_address);

            self.statusCurrentWifi(undefined);
            if (response.status.wifi.current_ssid && response.status.wifi.current_address) {
                _.each(response.wifis, function(wifi) {
                    if (wifi.ssid == response.status.wifi.current_ssid && wifi.address.toLowerCase() == response.status.wifi.current_address.toLowerCase()) {
                        self.statusCurrentWifi(self.getEntryId(wifi));
                    }
                });
            }

            var enableQualitySorting = false;
            _.each(response.wifis, function(wifi) {
                if (wifi.quality != undefined) {
                    enableQualitySorting = true;
                }
            });
            self.enableQualitySorting(enableQualitySorting);

            var wifis = [];
            _.each(response.wifis, function(wifi) {
                var qualityInt = parseInt(wifi.quality);
                var quality = undefined;
                if (!isNaN(qualityInt)) {
                    if (qualityInt <= 0) {
                        qualityInt = (-1) * qualityInt;
                    }
                    quality = qualityInt;
                }

                wifis.push({
                    ssid: wifi.ssid,
                    address: wifi.address,
                    encrypted: wifi.encrypted,
                    quality: quality,
                    qualityText: (quality != undefined) ? "" + quality + "%" : undefined
                });
            });

            self.listHelper.updateItems(wifis);
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
            if (self.status.connections.ap()) {
                self.reconnectInProgress = true;

                var reconnectText = gettext("OctoPrint is now switching to your configured Wifi connection and therefore shutting down the Access Point. I'm continuously trying to reach it at <strong>%(hostname)s</strong> but it might take a while. If you are not reconnected over the next couple of minutes, please try to reconnect to OctoPrint manually because then I was unable to find it myself.");

                showOfflineOverlay(
                    gettext("Reconnecting..."),
                    _.sprintf(reconnectText, {hostname: self.hostname()}),
                    self.tryReconnect
                );
            }
            self._postCommand("configure_wifi", {ssid: ssid, psk: psk}, successCallback, failureCallback, function() {
                self.working(false);
                if (self.reconnectInProgress) {
                    self.tryReconnect();
                }
            }, 5000);
        };

        self.tryReconnect = function() {
            var hostname = self.hostname();

            var location = window.location.href
            location = location.replace(location.match("https?\\://([^:@]+(:[^@]+)?@)?([^:/]+)")[3], hostname);

            var pingCallback = function(result) {
                if (!result) {
                    return;
                }

                if (self.reconnectTimeout != undefined) {
                    clearTimeout(self.reconnectTimeout);
                    window.location.replace(location);
                }
                hideOfflineOverlay();
                self.reconnectInProgress = false;
            };

            ping(location, pingCallback);
            self.reconnectTimeout = setTimeout(self.tryReconnect, 1000);
        };

        self._postCommand = function (command, data, successCallback, failureCallback, alwaysCallback, timeout) {
            var payload = _.extend(data, {command: command});

            var params = {
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
            };

            if (timeout != undefined) {
                params.timeout = timeout;
            }

            $.ajax(params);
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
        };

        self.onServerDisconnect = function() {
            return !self.reconnectInProgress;
        }

    }

    // view model class, parameters for constructor, container to bind to
    ADDITIONAL_VIEWMODELS.push([NetconnectdViewModel, ["loginStateViewModel", "settingsViewModel"], document.getElementById("settings_plugin_netconnectd_dialog")]);
});
