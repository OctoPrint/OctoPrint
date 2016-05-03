$(function() {
    function SettingsViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.users = parameters[1];
        self.printerProfiles = parameters[2];
        self.about = parameters[3];

        self.receiving = ko.observable(false);
        self.sending = ko.observable(false);
        self.exchanging = ko.pureComputed(function() {
            return self.receiving() || self.sending();
        });
        self.callbacks = [];

        self.api_enabled = ko.observable(undefined);
        self.api_key = ko.observable(undefined);
        self.api_allowCrossOrigin = ko.observable(undefined);

        self.appearance_name = ko.observable(undefined);
        self.appearance_color = ko.observable(undefined);
        self.appearance_colorTransparent = ko.observable();
        self.appearance_defaultLanguage = ko.observable();

        self.settingsDialog = undefined;
        self.translationManagerDialog = undefined;
        self.translationUploadElement = $("#settings_appearance_managelanguagesdialog_upload");
        self.translationUploadButton = $("#settings_appearance_managelanguagesdialog_upload_start");

        self.translationUploadFilename = ko.observable();
        self.invalidTranslationArchive = ko.pureComputed(function() {
            var name = self.translationUploadFilename();
            return name !== undefined && !(_.endsWith(name.toLocaleLowerCase(), ".zip") || _.endsWith(name.toLocaleLowerCase(), ".tar.gz") || _.endsWith(name.toLocaleLowerCase(), ".tgz") || _.endsWith(name.toLocaleLowerCase(), ".tar"));
        });
        self.enableTranslationUpload = ko.pureComputed(function() {
            var name = self.translationUploadFilename();
            return name !== undefined && name.trim() != "" && !self.invalidTranslationArchive();
        });

        self.translations = new ItemListHelper(
            "settings.translations",
            {
                "locale": function (a, b) {
                    // sorts ascending
                    if (a["locale"].toLocaleLowerCase() < b["locale"].toLocaleLowerCase()) return -1;
                    if (a["locale"].toLocaleLowerCase() > b["locale"].toLocaleLowerCase()) return 1;
                    return 0;
                }
            },
            {
            },
            "locale",
            [],
            [],
            0
        );

        self.appearance_available_colors = ko.observable([
            {key: "default", name: gettext("default")},
            {key: "red", name: gettext("red")},
            {key: "orange", name: gettext("orange")},
            {key: "yellow", name: gettext("yellow")},
            {key: "green", name: gettext("green")},
            {key: "blue", name: gettext("blue")},
            {key: "violet", name: gettext("violet")},
            {key: "black", name: gettext("black")},
            {key: "white", name: gettext("white")},
        ]);

        self.appearance_colorName = function(color) {
            switch (color) {
                case "red":
                    return gettext("red");
                case "orange":
                    return gettext("orange");
                case "yellow":
                    return gettext("yellow");
                case "green":
                    return gettext("green");
                case "blue":
                    return gettext("blue");
                case "violet":
                    return gettext("violet");
                case "black":
                    return gettext("black");
                case "white":
                    return gettext("white");
                case "default":
                    return gettext("default");
                default:
                    return color;
            }
        };

        var auto_locale = {language: "_default", display: gettext("Autodetect from browser"), english: undefined};
        self.locales = ko.observableArray([auto_locale].concat(_.sortBy(_.values(AVAILABLE_LOCALES), function(n) {
            return n.display;
        })));
        self.locale_languages = _.keys(AVAILABLE_LOCALES);

        self.printer_defaultExtrusionLength = ko.observable(undefined);

        self.webcam_streamUrl = ko.observable(undefined);
        self.webcam_snapshotUrl = ko.observable(undefined);
        self.webcam_ffmpegPath = ko.observable(undefined);
        self.webcam_bitrate = ko.observable(undefined);
        self.webcam_ffmpegThreads = ko.observable(undefined);
        self.webcam_watermark = ko.observable(undefined);
        self.webcam_flipH = ko.observable(undefined);
        self.webcam_flipV = ko.observable(undefined);
        self.webcam_rotate90 = ko.observable(undefined);

        self.feature_gcodeViewer = ko.observable(undefined);
        self.feature_temperatureGraph = ko.observable(undefined);
        self.feature_waitForStart = ko.observable(undefined);
        self.feature_alwaysSendChecksum = ko.observable(undefined);
        self.feature_sdSupport = ko.observable(undefined);
        self.feature_sdAlwaysAvailable = ko.observable(undefined);
        self.feature_swallowOkAfterResend = ko.observable(undefined);
        self.feature_repetierTargetTemp = ko.observable(undefined);
        self.feature_disableExternalHeatupDetection = ko.observable(undefined);
        self.feature_keyboardControl = ko.observable(undefined);
        self.feature_pollWatched = ko.observable(undefined);
        self.feature_ignoreIdenticalResends = ko.observable(undefined);

        self.serial_port = ko.observable();
        self.serial_baudrate = ko.observable();
        self.serial_portOptions = ko.observableArray([]);
        self.serial_baudrateOptions = ko.observableArray([]);
        self.serial_autoconnect = ko.observable(undefined);
        self.serial_timeoutConnection = ko.observable(undefined);
        self.serial_timeoutDetection = ko.observable(undefined);
        self.serial_timeoutCommunication = ko.observable(undefined);
        self.serial_timeoutTemperature = ko.observable(undefined);
        self.serial_timeoutSdStatus = ko.observable(undefined);
        self.serial_log = ko.observable(undefined);
        self.serial_additionalPorts = ko.observable(undefined);
        self.serial_longRunningCommands = ko.observable(undefined);
        self.serial_checksumRequiringCommands = ko.observable(undefined);
        self.serial_helloCommand = ko.observable(undefined);
        self.serial_ignoreErrorsFromFirmware = ko.observable(undefined);
        self.serial_disconnectOnErrors = ko.observable(undefined);
        self.serial_triggerOkForM29 = ko.observable(undefined);
        self.serial_supportResendsWithoutOk = ko.observable(undefined);

        self.folder_uploads = ko.observable(undefined);
        self.folder_timelapse = ko.observable(undefined);
        self.folder_timelapseTmp = ko.observable(undefined);
        self.folder_logs = ko.observable(undefined);
        self.folder_watched = ko.observable(undefined);

        self.scripts_gcode_beforePrintStarted = ko.observable(undefined);
        self.scripts_gcode_afterPrintDone = ko.observable(undefined);
        self.scripts_gcode_afterPrintCancelled = ko.observable(undefined);
        self.scripts_gcode_afterPrintPaused = ko.observable(undefined);
        self.scripts_gcode_beforePrintResumed = ko.observable(undefined);
        self.scripts_gcode_afterPrinterConnected = ko.observable(undefined);

        self.temperature_profiles = ko.observableArray(undefined);
        self.temperature_cutoff = ko.observable(undefined);

        self.system_actions = ko.observableArray([]);

        self.terminalFilters = ko.observableArray([]);

        self.server_commands_systemShutdownCommand = ko.observable(undefined);
        self.server_commands_systemRestartCommand = ko.observable(undefined);
        self.server_commands_serverRestartCommand = ko.observable(undefined);

        self.server_diskspace_warning = ko.observable();
        self.server_diskspace_critical = ko.observable();
        self.server_diskspace_warning_str = sizeObservable(self.server_diskspace_warning);
        self.server_diskspace_critical_str = sizeObservable(self.server_diskspace_critical);

        self.settings = undefined;

        self.addTemperatureProfile = function() {
            self.temperature_profiles.push({name: "New", extruder:0, bed:0});
        };

        self.removeTemperatureProfile = function(profile) {
            self.temperature_profiles.remove(profile);
        };

        self.addTerminalFilter = function() {
            self.terminalFilters.push({name: "New", regex: "(Send: M105)|(Recv: ok T:)"})
        };

        self.removeTerminalFilter = function(filter) {
            self.terminalFilters.remove(filter);
        };

        self.onSettingsShown = function() {
          self.requestData();
        };

        self.onStartup = function() {
            self.settingsDialog = $('#settings_dialog');
            self.translationManagerDialog = $('#settings_appearance_managelanguagesdialog');
            self.translationUploadElement = $("#settings_appearance_managelanguagesdialog_upload");
            self.translationUploadButton = $("#settings_appearance_managelanguagesdialog_upload_start");

            self.translationUploadElement.fileupload({
                dataType: "json",
                maxNumberOfFiles: 1,
                autoUpload: false,
                add: function(e, data) {
                    if (data.files.length == 0) {
                        return false;
                    }

                    self.translationUploadFilename(data.files[0].name);

                    self.translationUploadButton.unbind("click");
                    self.translationUploadButton.bind("click", function() {
                        data.submit();
                        return false;
                    });
                },
                done: function(e, data) {
                    self.translationUploadButton.unbind("click");
                    self.translationUploadFilename(undefined);
                    self.fromTranslationResponse(data.result);
                },
                fail: function(e, data) {
                    self.translationUploadButton.unbind("click");
                    self.translationUploadFilename(undefined);
                }
            });
        };

        self.onAllBound = function(allViewModels) {
            self.settingsDialog.on('show', function(event) {
                if (event.target.id == "settings_dialog") {
                    self.requestTranslationData();
                    _.each(allViewModels, function(viewModel) {
                        if (viewModel.hasOwnProperty("onSettingsShown")) {
                            viewModel.onSettingsShown();
                        }
                    });
                }
            });
            self.settingsDialog.on('hidden', function(event) {
                if (event.target.id == "settings_dialog") {
                    _.each(allViewModels, function(viewModel) {
                        if (viewModel.hasOwnProperty("onSettingsHidden")) {
                            viewModel.onSettingsHidden();
                        }
                    });
                }
            });
            self.settingsDialog.on('beforeSave', function () {
                _.each(allViewModels, function (viewModel) {
                    if (viewModel.hasOwnProperty("onSettingsBeforeSave")) {
                        viewModel.onSettingsBeforeSave();
                    }
                });
            });

            // reset scroll position on tab change
            $('ul.nav-list a[data-toggle="tab"]', self.settingsDialog).on("show", function() {
                self._resetScrollPosition();
            });
        };

        self.show = function(tab) {
            // select first or specified tab
            self.selectTab(tab);

            // reset scroll position
            self._resetScrollPosition();

            // show settings, ensure centered position
            self.settingsDialog.modal({
                minHeight: function() { return Math.max($.fn.modal.defaults.maxHeight() - 80, 250); }
            }).css({
                width: 'auto',
                'margin-left': function() { return -($(this).width() /2); }
            });

            return false;
        };

        self.hide = function() {
            self.settingsDialog.modal("hide");
        };

        self.showTranslationManager = function() {
            self.translationManagerDialog.modal();
            return false;
        };

        self.requestData = function(callback) {
            if (self.receiving()) {
                if (callback) {
                    self.callbacks.push(callback);
                }
                return;
            }

            self.receiving(true);
            $.ajax({
                url: API_BASEURL + "settings",
                type: "GET",
                dataType: "json",
                success: function(response) {
                    if (callback) {
                        self.callbacks.push(callback);
                    }

                    try {
                        self.fromResponse(response);

                        var cb;
                        while (self.callbacks.length) {
                            cb = self.callbacks.shift();
                            try {
                                cb();
                            } catch(exc) {
                                log.error("Error calling settings callback", cb, ":", (exc.stack || exc));
                            }
                        }
                    } finally {
                        self.receiving(false);
                        self.callbacks = [];
                    }
                },
                error: function(xhr) {
                    self.receiving(false);
                }
            });
        };

        self.requestTranslationData = function(callback) {
            $.ajax({
                url: API_BASEURL + "languages",
                type: "GET",
                dataType: "json",
                success: function(response) {
                    self.fromTranslationResponse(response);
                    if (callback) callback();
                }
            })
        };

        self.fromTranslationResponse = function(response) {
            var translationsByLocale = {};
            _.each(response.language_packs, function(item, key) {
                _.each(item.languages, function(pack) {
                    var locale = pack.locale;
                    if (!_.has(translationsByLocale, locale)) {
                        translationsByLocale[locale] = {
                            locale: locale,
                            display: pack.locale_display,
                            english: pack.locale_english,
                            packs: []
                        };
                    }

                    translationsByLocale[locale]["packs"].push({
                        identifier: key,
                        display: item.display,
                        pack: pack
                    });
                });
            });

            var translations = [];
            _.each(translationsByLocale, function(item) {
                item["packs"].sort(function(a, b) {
                    if (a.identifier == "_core") return -1;
                    if (b.identifier == "_core") return 1;

                    if (a.display < b.display) return -1;
                    if (a.display > b.display) return 1;
                    return 0;
                });
                translations.push(item);
            });

            self.translations.updateItems(translations);
        };

        self.languagePackDisplay = function(item) {
            return item.display + ((item.english != undefined) ? ' (' + item.english + ')' : '');
        };

        self.languagePacksAvailable = ko.pureComputed(function() {
            return self.translations.allSize() > 0;
        });

        self.deleteLanguagePack = function(locale, pack) {
            $.ajax({
                url: API_BASEURL + "languages/" + locale + "/" + pack,
                type: "DELETE",
                dataType: "json",
                success: function(response) {
                    self.fromTranslationResponse(response);
                }
            })
        };

        self.fromResponse = function(response) {
            if (self.settings === undefined) {
                self.settings = ko.mapping.fromJS(response);
            } else {
                ko.mapping.fromJS(response, self.settings);
            }

            self.api_enabled(response.api.enabled);
            self.api_key(response.api.key);
            self.api_allowCrossOrigin(response.api.allowCrossOrigin);

            self.appearance_name(response.appearance.name);
            self.appearance_color(response.appearance.color);
            self.appearance_colorTransparent(response.appearance.colorTransparent);
            self.appearance_defaultLanguage("_default");
            if (_.includes(self.locale_languages, response.appearance.defaultLanguage)) {
                self.appearance_defaultLanguage(response.appearance.defaultLanguage);
            }

            self.printer_defaultExtrusionLength(response.printer.defaultExtrusionLength);

            self.webcam_streamUrl(response.webcam.streamUrl);
            self.webcam_snapshotUrl(response.webcam.snapshotUrl);
            self.webcam_ffmpegPath(response.webcam.ffmpegPath);
            self.webcam_bitrate(response.webcam.bitrate);
            self.webcam_ffmpegThreads(response.webcam.ffmpegThreads);
            self.webcam_watermark(response.webcam.watermark);
            self.webcam_flipH(response.webcam.flipH);
            self.webcam_flipV(response.webcam.flipV);
            self.webcam_rotate90(response.webcam.rotate90);

            self.feature_gcodeViewer(response.feature.gcodeViewer);
            self.feature_temperatureGraph(response.feature.temperatureGraph);
            self.feature_waitForStart(response.feature.waitForStart);
            self.feature_alwaysSendChecksum(response.feature.alwaysSendChecksum);
            self.feature_sdSupport(response.feature.sdSupport);
            self.feature_sdAlwaysAvailable(response.feature.sdAlwaysAvailable);
            self.feature_swallowOkAfterResend(response.feature.swallowOkAfterResend);
            self.feature_repetierTargetTemp(response.feature.repetierTargetTemp);
            self.feature_disableExternalHeatupDetection(!response.feature.externalHeatupDetection);
            self.feature_keyboardControl(response.feature.keyboardControl);
            self.feature_pollWatched(response.feature.pollWatched);

            self.serial_port(response.serial.port);
            self.serial_baudrate(response.serial.baudrate);
            self.serial_portOptions(response.serial.portOptions);
            self.serial_baudrateOptions(response.serial.baudrateOptions);
            self.serial_autoconnect(response.serial.autoconnect);
            self.serial_timeoutConnection(response.serial.timeoutConnection);
            self.serial_timeoutDetection(response.serial.timeoutDetection);
            self.serial_timeoutCommunication(response.serial.timeoutCommunication);
            self.serial_timeoutTemperature(response.serial.timeoutTemperature);
            self.serial_timeoutSdStatus(response.serial.timeoutSdStatus);
            self.serial_log(response.serial.log);
            self.serial_additionalPorts(response.serial.additionalPorts.join("\n"));
            self.serial_longRunningCommands(response.serial.longRunningCommands.join(", "));
            self.serial_checksumRequiringCommands(response.serial.checksumRequiringCommands.join(", "));
            self.serial_helloCommand(response.serial.helloCommand);
            self.serial_ignoreErrorsFromFirmware(response.serial.ignoreErrorsFromFirmware);
            self.serial_disconnectOnErrors(response.serial.disconnectOnErrors);
            self.serial_triggerOkForM29(response.serial.triggerOkForM29);
            self.serial_supportResendsWithoutOk(response.serial.supportResendsWithoutOk);

            self.folder_uploads(response.folder.uploads);
            self.folder_timelapse(response.folder.timelapse);
            self.folder_timelapseTmp(response.folder.timelapseTmp);
            self.folder_logs(response.folder.logs);
            self.folder_watched(response.folder.watched);

            self.temperature_profiles(response.temperature.profiles);

            self.scripts_gcode_beforePrintStarted(response.scripts.gcode.beforePrintStarted);
            self.scripts_gcode_afterPrintDone(response.scripts.gcode.afterPrintDone);
            self.scripts_gcode_afterPrintCancelled(response.scripts.gcode.afterPrintCancelled);
            self.scripts_gcode_afterPrintPaused(response.scripts.gcode.afterPrintPaused);
            self.scripts_gcode_beforePrintResumed(response.scripts.gcode.beforePrintResumed);
            self.scripts_gcode_afterPrinterConnected(response.scripts.gcode.afterPrinterConnected);

            self.temperature_profiles(response.temperature.profiles);
            self.temperature_cutoff(response.temperature.cutoff);

            self.system_actions(response.system.actions);

            self.terminalFilters(response.terminalFilters);

            self.server_commands_systemShutdownCommand(response.server.commands.systemShutdownCommand);
            self.server_commands_systemRestartCommand(response.server.commands.systemRestartCommand);
            self.server_commands_serverRestartCommand(response.server.commands.serverRestartCommand);
        };

        self.saveData = function (data, successCallback) {
            self.settingsDialog.trigger("beforeSave");

            if (data == undefined) {
                // we only set sending to true when we didn't include data
                self.sending(true);
                data = ko.mapping.toJS(self.settings);

                data = _.extend(data, {
                    "api" : {
                        "enabled": self.api_enabled(),
                        "key": self.api_key(),
                        "allowCrossOrigin": self.api_allowCrossOrigin()
                    },
                    "appearance" : {
                        "name": self.appearance_name(),
                        "color": self.appearance_color(),
                        "colorTransparent": self.appearance_colorTransparent(),
                        "defaultLanguage": self.appearance_defaultLanguage()
                    },
                    "printer": {
                        "defaultExtrusionLength": self.printer_defaultExtrusionLength()
                    },
                    "webcam": {
                        "streamUrl": self.webcam_streamUrl(),
                        "snapshotUrl": self.webcam_snapshotUrl(),
                        "ffmpegPath": self.webcam_ffmpegPath(),
                        "bitrate": self.webcam_bitrate(),
                        "ffmpegThreads": self.webcam_ffmpegThreads(),
                        "watermark": self.webcam_watermark(),
                        "flipH": self.webcam_flipH(),
                        "flipV": self.webcam_flipV(),
                        "rotate90": self.webcam_rotate90()
                    },
                    "feature": {
                        "gcodeViewer": self.feature_gcodeViewer(),
                        "temperatureGraph": self.feature_temperatureGraph(),
                        "waitForStart": self.feature_waitForStart(),
                        "alwaysSendChecksum": self.feature_alwaysSendChecksum(),
                        "sdSupport": self.feature_sdSupport(),
                        "sdAlwaysAvailable": self.feature_sdAlwaysAvailable(),
                        "swallowOkAfterResend": self.feature_swallowOkAfterResend(),
                        "repetierTargetTemp": self.feature_repetierTargetTemp(),
                        "externalHeatupDetection": !self.feature_disableExternalHeatupDetection(),
                        "keyboardControl": self.feature_keyboardControl(),
                        "pollWatched": self.feature_pollWatched()
                    },
                    "serial": {
                        "port": self.serial_port(),
                        "baudrate": self.serial_baudrate(),
                        "autoconnect": self.serial_autoconnect(),
                        "timeoutConnection": self.serial_timeoutConnection(),
                        "timeoutDetection": self.serial_timeoutDetection(),
                        "timeoutCommunication": self.serial_timeoutCommunication(),
                        "timeoutTemperature": self.serial_timeoutTemperature(),
                        "timeoutSdStatus": self.serial_timeoutSdStatus(),
                        "log": self.serial_log(),
                        "additionalPorts": commentableLinesToArray(self.serial_additionalPorts()),
                        "longRunningCommands": splitTextToArray(self.serial_longRunningCommands(), ",", true),
                        "checksumRequiringCommands": splitTextToArray(self.serial_checksumRequiringCommands(), ",", true),
                        "helloCommand": self.serial_helloCommand(),
                        "ignoreErrorsFromFirmware": self.serial_ignoreErrorsFromFirmware(),
                        "disconnectOnErrors": self.serial_disconnectOnErrors(),
                        "triggerOkForM29": self.serial_triggerOkForM29(),
                        "supportResendsWithoutOk": self.serial_supportResendsWithoutOk()
                    },
                    "folder": {
                        "uploads": self.folder_uploads(),
                        "timelapse": self.folder_timelapse(),
                        "timelapseTmp": self.folder_timelapseTmp(),
                        "logs": self.folder_logs(),
                        "watched": self.folder_watched()
                    },
                    "temperature": {
                        "profiles": self.temperature_profiles(),
                        "cutoff": self.temperature_cutoff()
                    },
                    "system": {
                        "actions": self.system_actions()
                    },
                    "terminalFilters": self.terminalFilters(),
                    "scripts": {
                        "gcode": {
                            "beforePrintStarted": self.scripts_gcode_beforePrintStarted(),
                            "afterPrintDone": self.scripts_gcode_afterPrintDone(),
                            "afterPrintCancelled": self.scripts_gcode_afterPrintCancelled(),
                            "afterPrintPaused": self.scripts_gcode_afterPrintPaused(),
                            "beforePrintResumed": self.scripts_gcode_beforePrintResumed(),
                            "afterPrinterConnected": self.scripts_gcode_afterPrinterConnected()
                        }
                    },
                    "server": {
                        "commands": {
                            "systemShutdownCommand": self.server_commands_systemShutdownCommand(),
                            "systemRestartCommand": self.server_commands_systemRestartCommand(),
                            "serverRestartCommand": self.server_commands_serverRestartCommand()
                        }
                    }
                });
            }

            $.ajax({
                url: API_BASEURL + "settings",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify(data),
                success: function(response) {
                    self.receiving(true);
                    self.sending(false);
                    try {
                        self.fromResponse(response);
                        if (successCallback) successCallback(response);
                    } finally {
                        self.receiving(false);
                    }
                },
                error: function(xhr) {
                    self.sending(false);
                }
            });
        };

        self.onEventSettingsUpdated = function() {
            self.requestData();
        };

        self._resetScrollPosition = function() {
            $('.scrollable', self.settingsDialog).scrollTop(0);
        };

        self.selectTab = function(tab) {
            if (tab != undefined) {
                if (!_.startsWith(tab, "#")) {
                    tab = "#" + tab;
                }
                $('ul.nav-list a[href="' + tab + '"]', self.settingsDialog).tab("show");
            } else {
                $('ul.nav-list a:first', self.settingsDialog).tab("show");
            }
        };
    }

    OCTOPRINT_VIEWMODELS.push([
        SettingsViewModel,
        ["loginStateViewModel", "usersViewModel", "printerProfilesViewModel", "aboutViewModel"],
        ["#settings_dialog", "#navbar_settings"]
    ]);
});
