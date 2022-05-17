$(function () {
    function SettingsViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.access = parameters[1];
        self.printerProfiles = parameters[2];
        self.about = parameters[3];

        // TODO: remove in upcoming version, this is only for backwards compatibility
        self.users = parameters[4];

        // use this promise to do certain things once the SettingsViewModel has processed
        // its first request
        var firstRequest = $.Deferred();
        self.firstRequest = firstRequest.promise();

        self.allViewModels = [];

        self.receiving = ko.observable(false);
        self.sending = ko.observable(false);
        self.exchanging = ko.pureComputed(function () {
            return self.receiving() || self.sending();
        });
        self.outstanding = [];

        self.active = false;
        self.sawUpdateEventWhileActive = false;
        self.ignoreNextUpdateEvent = false;

        self.settingsDialog = undefined;
        self.settings_dialog_update_detected = undefined;
        self.translationManagerDialog = undefined;
        self.translationUploadElement = $(
            "#settings_appearance_managelanguagesdialog_upload"
        );
        self.translationUploadButton = $(
            "#settings_appearance_managelanguagesdialog_upload_start"
        );

        self.translationUploadFilename = ko.observable();
        self.invalidTranslationArchive = ko.pureComputed(function () {
            var name = self.translationUploadFilename();
            return (
                name !== undefined &&
                !(
                    _.endsWith(name.toLocaleLowerCase(), ".zip") ||
                    _.endsWith(name.toLocaleLowerCase(), ".tar.gz") ||
                    _.endsWith(name.toLocaleLowerCase(), ".tgz") ||
                    _.endsWith(name.toLocaleLowerCase(), ".tar")
                )
            );
        });
        self.enableTranslationUpload = ko.pureComputed(function () {
            var name = self.translationUploadFilename();
            return (
                name !== undefined &&
                name.trim() != "" &&
                !self.invalidTranslationArchive()
            );
        });

        self.translations = new ItemListHelper(
            "settings.translations",
            {
                locale: function (a, b) {
                    // sorts ascending
                    if (a["locale"].toLocaleLowerCase() < b["locale"].toLocaleLowerCase())
                        return -1;
                    if (a["locale"].toLocaleLowerCase() > b["locale"].toLocaleLowerCase())
                        return 1;
                    return 0;
                }
            },
            {},
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
            {key: "white", name: gettext("white")}
        ]);

        self.appearance_colorName = function (color) {
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

        self.webcam_available_ratios = ["16:9", "4:3"];
        self.webcam_available_videocodecs = ["libx264", "mpeg2video"];

        var auto_locale = {
            language: "_default",
            display: gettext("Autodetect from browser"),
            english: undefined
        };
        self.locales = ko.observableArray(
            [auto_locale].concat(
                _.sortBy(_.values(AVAILABLE_LOCALES), function (n) {
                    return n.display;
                })
            )
        );
        self.locale_languages = _.keys(AVAILABLE_LOCALES);

        self.api_key = ko.observable(undefined);
        self.api_allowCrossOrigin = ko.observable(undefined);

        self.appearance_name = ko.observable(undefined);
        self.appearance_color = ko.observable(undefined);
        self.appearance_colorTransparent = ko.observable();
        self.appearance_colorIcon = ko.observable();
        self.appearance_defaultLanguage = ko.observable();
        self.appearance_showFahrenheitAlso = ko.observable(undefined);
        self.appearance_fuzzyTimes = ko.observable(undefined);
        self.appearance_closeModalsWithClick = ko.observable(undefined);
        self.appearance_showInternalFilename = ko.observable(undefined);

        self.printer_defaultExtrusionLength = ko.observable(undefined);

        self.webcam_webcamEnabled = ko.observable(undefined);
        self.webcam_timelapseEnabled = ko.observable(undefined);
        self.webcam_streamUrl = ko.observable(undefined);
        self.webcam_streamRatio = ko.observable(undefined);
        self.webcam_streamTimeout = ko.observable(undefined);
        self.webcam_streamWebrtcIceServers = ko.observable(undefined);
        self.webcam_snapshotUrl = ko.observable(undefined);
        self.webcam_snapshotTimeout = ko.observable(undefined);
        self.webcam_snapshotSslValidation = ko.observable(undefined);
        self.webcam_ffmpegPath = ko.observable(undefined);
        self.webcam_ffmpegCommandline = ko.observable(undefined);
        self.webcam_bitrate = ko.observable(undefined);
        self.webcam_ffmpegThreads = ko.observable(undefined);
        self.webcam_ffmpegVideoCodec = ko.observable(undefined);
        self.webcam_watermark = ko.observable(undefined);
        self.webcam_flipH = ko.observable(undefined);
        self.webcam_flipV = ko.observable(undefined);
        self.webcam_rotate90 = ko.observable(undefined);
        self.webcam_cacheBuster = ko.observable(undefined);

        self.feature_temperatureGraph = ko.observable(undefined);
        self.feature_sdSupport = ko.observable(undefined);
        self.feature_keyboardControl = ko.observable(undefined);
        self.feature_pollWatched = ko.observable(undefined);
        self.feature_modelSizeDetection = ko.observable(undefined);
        self.feature_rememberFileFolder = ko.observable(undefined);
        self.feature_printStartConfirmation = ko.observable(undefined);
        self.feature_printCancelConfirmation = ko.observable(undefined);
        self.feature_uploadOverwriteConfirmation = ko.observable(undefined);
        self.feature_g90InfluencesExtruder = ko.observable(undefined);
        self.feature_autoUppercaseBlacklist = ko.observable(undefined);

        self.gcodeAnalysis_runAt = ko.observable(undefined);

        self.serial_port = ko.observable();
        self.serial_baudrate = ko.observable();
        self.serial_exclusive = ko.observable();
        self.serial_lowLatency = ko.observable();
        self.serial_portOptions = ko.observableArray([]);
        self.serial_baudrateOptions = ko.observableArray([]);
        self.serial_autoconnect = ko.observable(undefined);
        self.serial_timeoutConnection = ko.observable(undefined);
        self.serial_timeoutDetectionFirst = ko.observable(undefined);
        self.serial_timeoutDetectionConsecutive = ko.observable(undefined);
        self.serial_timeoutCommunication = ko.observable(undefined);
        self.serial_timeoutCommunicationBusy = ko.observable(undefined);
        self.serial_timeoutTemperature = ko.observable(undefined);
        self.serial_timeoutTemperatureTargetSet = ko.observable(undefined);
        self.serial_timeoutTemperatureAutoreport = ko.observable(undefined);
        self.serial_timeoutSdStatus = ko.observable(undefined);
        self.serial_timeoutSdStatusAutoreport = ko.observable(undefined);
        self.serial_timeoutPosAutoreport = ko.observable(undefined);
        self.serial_timeoutBaudrateDetectionPause = ko.observable(undefined);
        self.serial_timeoutPositionLogWait = ko.observable(undefined);
        self.serial_log = ko.observable(undefined);
        self.serial_additionalPorts = ko.observable(undefined);
        self.serial_additionalBaudrates = ko.observable(undefined);
        self.serial_blacklistedPorts = ko.observable(undefined);
        self.serial_blacklistedBaudrates = ko.observable(undefined);
        self.serial_longRunningCommands = ko.observable(undefined);
        self.serial_checksumRequiringCommands = ko.observable(undefined);
        self.serial_blockedCommands = ko.observable(undefined);
        self.serial_ignoredCommands = ko.observable(undefined);
        self.serial_pausingCommands = ko.observable(undefined);
        self.serial_sdCancelCommand = ko.observable(undefined);
        self.serial_emergencyCommands = ko.observable(undefined);
        self.serial_helloCommand = ko.observable(undefined);
        self.serial_serialErrorBehaviour = ko.observable("cancel");
        self.serial_triggerOkForM29 = ko.observable(undefined);
        self.serial_waitForStart = ko.observable(undefined);
        self.serial_sendChecksum = ko.observable("print");
        self.serial_sendChecksumWithUnknownCommands = ko.observable(undefined);
        self.serial_unknownCommandsNeedAck = ko.observable(undefined);
        self.serial_sdRelativePath = ko.observable(undefined);
        self.serial_sdLowerCase = ko.observable(undefined);
        self.serial_sdAlwaysAvailable = ko.observable(undefined);
        self.serial_swallowOkAfterResend = ko.observable(undefined);
        self.serial_repetierTargetTemp = ko.observable(undefined);
        self.serial_disableExternalHeatupDetection = ko.observable(undefined);
        self.serial_ignoreIdenticalResends = ko.observable(undefined);
        self.serial_firmwareDetection = ko.observable(undefined);
        self.serial_blockWhileDwelling = ko.observable(undefined);
        self.serial_useParityWorkaround = ko.observable(undefined);
        self.serial_sanityCheckTools = ko.observable(undefined);
        self.serial_supportResendsWithoutOk = ko.observable(undefined);
        self.serial_logPositionOnPause = ko.observable(undefined);
        self.serial_logPositionOnCancel = ko.observable(undefined);
        self.serial_abortHeatupOnCancel = ko.observable(undefined);
        self.serial_maxTimeoutsIdle = ko.observable(undefined);
        self.serial_maxTimeoutsPrinting = ko.observable(undefined);
        self.serial_maxTimeoutsLong = ko.observable(undefined);
        self.serial_capAutoreportTemp = ko.observable(undefined);
        self.serial_capAutoreportSdStatus = ko.observable(undefined);
        self.serial_capAutoreportPos = ko.observable(undefined);
        self.serial_capBusyProtocol = ko.observable(undefined);
        self.serial_capEmergencyParser = ko.observable(undefined);
        self.serial_capExtendedM20 = ko.observable(undefined);
        self.serial_sendM112OnError = ko.observable(undefined);
        self.serial_disableSdPrintingDetection = ko.observable(undefined);
        self.serial_ackMax = ko.observable(undefined);
        self.serial_resendRatioThreshold = ko.observable(100);
        self.serial_resendRatioStart = ko.observable(100);
        self.serial_ignoreEmptyPorts = ko.observable(undefined);
        self.serial_enableShutdownActionCommand = ko.observable(undefined);

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
        self.scripts_gcode_beforePrinterDisconnected = ko.observable(undefined);
        self.scripts_gcode_afterToolChange = ko.observable(undefined);
        self.scripts_gcode_beforeToolChange = ko.observable(undefined);

        self.temperature_profiles = ko.observableArray(undefined);
        self.temperature_cutoff = ko.observable(undefined);
        self.temperature_sendAutomatically = ko.observable(undefined);
        self.temperature_sendAutomaticallyAfter = ko.observable(undefined);

        self.system_actions = ko.observableArray([]);

        self.terminalFilters = ko.observableArray([]);

        self.server_commands_systemShutdownCommand = ko.observable(undefined);
        self.server_commands_systemRestartCommand = ko.observable(undefined);
        self.server_commands_serverRestartCommand = ko.observable(undefined);

        self.server_diskspace_warning = ko.observable();
        self.server_diskspace_critical = ko.observable();
        self.server_diskspace_warning_str = sizeObservable(self.server_diskspace_warning);
        self.server_diskspace_critical_str = sizeObservable(
            self.server_diskspace_critical
        );

        self.server_onlineCheck_enabled = ko.observable();
        self.server_onlineCheck_interval = ko.observable();
        self.server_onlineCheck_host = ko.observable();
        self.server_onlineCheck_port = ko.observable();
        self.server_onlineCheck_name = ko.observable();

        self.server_pluginBlacklist_enabled = ko.observable();
        self.server_pluginBlacklist_url = ko.observable();
        self.server_pluginBlacklist_ttl = ko.observable();

        self.server_allowFraming = ko.observable();

        self.settings = undefined;
        self.lastReceivedSettings = undefined;

        self.webcam_ffmpegPathText = ko.observable();
        self.webcam_ffmpegPathOk = ko.observable(false);
        self.webcam_ffmpegPathBroken = ko.observable(false);
        self.webcam_ffmpegPathReset = function () {
            self.webcam_ffmpegPathText("");
            self.webcam_ffmpegPathOk(false);
            self.webcam_ffmpegPathBroken(false);
        };
        self.webcam_streamUrlEscaped = ko.pureComputed(function () {
            return encodeURI(self.webcam_streamUrl());
        });
        self.webcam_streamType = ko.pureComputed(function () {
            try {
                return determineWebcamStreamType(self.webcam_streamUrlEscaped());
            } catch (e) {
                return "";
            }
        });
        self.webcam_streamValid = ko.pureComputed(function () {
            var url = self.webcam_streamUrlEscaped();
            return !url || validateWebcamUrl(url);
        });

        self.server_onlineCheckText = ko.observable();
        self.server_onlineCheckOk = ko.observable(false);
        self.server_onlineCheckBroken = ko.observable(false);
        self.server_onlineCheckReset = function () {
            self.server_onlineCheckText("");
            self.server_onlineCheckOk(false);
            self.server_onlineCheckBroken(false);
        };
        self.server_onlineCheckResolutionText = ko.observable();
        self.server_onlineCheckResolutionOk = ko.observable(false);
        self.server_onlineCheckResolutionBroken = ko.observable(false);
        self.server_onlineCheckResolutionReset = function () {
            self.server_onlineCheckResolutionText("");
            self.server_onlineCheckResolutionOk(false);
            self.server_onlineCheckResolutionBroken(false);
        };

        var folderTypes = ["uploads", "timelapse", "timelapseTmp", "logs", "watched"];

        var checkForDuplicateFolders = function () {
            _.each(folderTypes, function (folderType) {
                var path = self["folder_" + folderType]();
                var duplicate = false;
                _.each(folderTypes, function (otherFolderType) {
                    if (folderType !== otherFolderType) {
                        duplicate =
                            duplicate || path === self["folder_" + otherFolderType]();
                    }
                });
                self.testFolderConfigDuplicate[folderType](duplicate);
            });
        };

        self.testFolderConfigText = {};
        self.testFolderConfigOk = {};
        self.testFolderConfigBroken = {};
        self.testFolderConfigDuplicate = {};
        self.testFolderConfigError = {};
        self.testFolderConfigSuccess = {};
        _.each(folderTypes, function (folderType) {
            self.testFolderConfigText[folderType] = ko.observable("");
            self.testFolderConfigOk[folderType] = ko.observable(false);
            self.testFolderConfigBroken[folderType] = ko.observable(false);
            self.testFolderConfigDuplicate[folderType] = ko.observable(false);
            self.testFolderConfigError[folderType] = ko.pureComputed(function () {
                return (
                    self.testFolderConfigBroken[folderType]() ||
                    self.testFolderConfigDuplicate[folderType]()
                );
            });
            self.testFolderConfigSuccess[folderType] = ko.pureComputed(function () {
                return (
                    self.testFolderConfigOk[folderType]() &&
                    !self.testFolderConfigDuplicate[folderType]()
                );
            });
            self["folder_" + folderType].subscribe(checkForDuplicateFolders);
        });
        self.testFolderConfigReset = function () {
            _.each(folderTypes, function (folderType) {
                self.testFolderConfigText[folderType]("");
                self.testFolderConfigOk[folderType](false);
                self.testFolderConfigBroken[folderType](false);
            });
        };
        self.testFoldersDuplicate = ko.pureComputed(function () {
            var foundDupe = false;
            _.each(folderTypes, function (folderType) {
                foundDupe = foundDupe || self.testFolderConfigDuplicate[folderType]();
            });
            return foundDupe;
        });

        self.observableCopies = {
            feature_waitForStart: "serial_waitForStart",
            feature_sendChecksum: "serial_sendChecksum",
            feature_sdRelativePath: "serial_sdRelativePath",
            feature_sdAlwaysAvailable: "serial_sdAlwaysAvailable",
            feature_swallowOkAfterResend: "serial_swallowOkAfterResend",
            feature_repetierTargetTemp: "serial_repetierTargetTemp",
            feature_disableExternalHeatupDetection:
                "serial_disableExternalHeatupDetection",
            feature_ignoreIdenticalResends: "serial_ignoreIdenticalResends",
            feature_firmwareDetection: "serial_firmwareDetection",
            feature_blockWhileDwelling: "serial_blockWhileDwelling",
            serial_: "feature_"
        };
        _.each(self.observableCopies, function (value, key) {
            if (self.hasOwnProperty(value)) {
                self[key] = self[value];
            }
        });

        self.addTemperatureProfile = function () {
            self.temperature_profiles.push({
                name: "New",
                extruder: 0,
                bed: 0,
                chamber: 0
            });
        };

        self.removeTemperatureProfile = function (profile) {
            self.temperature_profiles.remove(profile);
        };

        self.addTerminalFilter = function () {
            self.terminalFilters.push({
                name: "New",
                regex: "(Send:\\s+(N\\d+\\s+)?M105)|(Recv:\\s+(ok\\s+([PBN]\\d+\\s+)*)?.*([BCLPR]|T\\d*):-?\\d+)"
            });
        };

        self.removeTerminalFilter = function (filter) {
            self.terminalFilters.remove(filter);
        };

        self.testWebcamStreamUrlBusy = ko.observable(false);
        self.testWebcamStreamUrl = function () {
            var url = self.webcam_streamUrlEscaped();
            if (!url) {
                return;
            }

            if (self.testWebcamStreamUrlBusy()) {
                return;
            }

            var text = gettext(
                "If you see your webcam stream below, the entered stream URL is ok."
            );

            var streamType;
            try {
                streamType = self.webcam_streamType();
            } catch (e) {
                streamType = "";
            }

            var webcam_element;
            var webrtc_peer_connection;
            if (streamType === "mjpg") {
                webcam_element = $('<img src="' + url + '">');
            } else if (streamType === "hls") {
                webcam_element = $(
                    '<video id="webcam_hls" muted autoplay style="width: 100%"/>'
                );
                video_element = webcam_element[0];
                if (video_element.canPlayType("application/vnd.apple.mpegurl")) {
                    video_element.src = url;
                } else if (Hls.isSupported()) {
                    var hls = new Hls();
                    hls.loadSource(url);
                    hls.attachMedia(video_element);
                }
            } else if (isWebRTCAvailable() && streamType === "webrtc") {
                webcam_element = $(
                    '<video id="webcam_webrtc" muted autoplay playsinline controls style="width: 100%"/>'
                );
                video_element = webcam_element[0];

                webrtc_peer_connection = startWebRTC(
                    video_element,
                    url,
                    self.webcam_streamWebrtcIceServers()
                );
            } else {
                throw "Unknown stream type " + streamType;
            }

            var message = $("<div id='webcamTestContainer'></div>")
                .append($("<p></p>"))
                .append(text)
                .append(webcam_element);

            self.testWebcamStreamUrlBusy(true);
            showMessageDialog({
                title: gettext("Stream test"),
                message: message,
                onclose: function () {
                    self.testWebcamStreamUrlBusy(false);
                    if (webrtc_peer_connection != null) {
                        webrtc_peer_connection.close();
                        webrtc_peer_connection = null;
                    }
                }
            });
        };

        self.testWebcamSnapshotUrlBusy = ko.observable(false);
        self.testWebcamSnapshotUrl = function (viewModel, event) {
            if (!self.webcam_snapshotUrl()) {
                return;
            }

            if (self.testWebcamSnapshotUrlBusy()) {
                return;
            }

            var errorText = gettext(
                "Could not retrieve snapshot URL, please double check the URL"
            );
            var errorTitle = gettext("Snapshot test failed");

            self.testWebcamSnapshotUrlBusy(true);
            OctoPrint.util
                .testUrl(self.webcam_snapshotUrl(), {
                    method: "GET",
                    response: "bytes",
                    timeout: self.webcam_snapshotTimeout(),
                    validSsl: self.webcam_snapshotSslValidation(),
                    content_type_whitelist: ["image/*"],
                    content_type_guess: true
                })
                .done(function (response) {
                    if (!response.result) {
                        if (
                            response.status &&
                            response.response &&
                            response.response.content_type
                        ) {
                            // we could contact the server, but something else was wrong, probably the mime type
                            errorText = gettext(
                                "Could retrieve the snapshot URL, but it didn't look like an " +
                                    "image. Got this as a content type header: <code>%(content_type)s</code>. Please " +
                                    "double check that the URL is returning static images, not multipart data " +
                                    "or videos."
                            );
                            errorText = _.sprintf(errorText, {
                                content_type: _.escape(response.response.content_type)
                            });
                        }

                        showMessageDialog({
                            title: errorTitle,
                            message: errorText,
                            onclose: function () {
                                self.testWebcamSnapshotUrlBusy(false);
                            }
                        });
                        return;
                    }

                    var content = response.response.content;
                    var contentType = response.response.assumed_content_type;

                    var mimeType = "image/jpeg";
                    if (contentType) {
                        mimeType = contentType.split(";")[0];
                    }

                    var text = gettext(
                        "If you see your webcam snapshot picture below, the entered snapshot URL is ok."
                    );
                    showMessageDialog({
                        title: gettext("Snapshot test"),
                        message: $(
                            "<p>" +
                                text +
                                '</p><p><img src="data:' +
                                mimeType +
                                ";base64," +
                                content +
                                '" style="border: 1px solid black" /></p>'
                        ),
                        onclose: function () {
                            self.testWebcamSnapshotUrlBusy(false);
                        }
                    });
                })
                .fail(function () {
                    showMessageDialog({
                        title: errorTitle,
                        message: errorText,
                        onclose: function () {
                            self.testWebcamSnapshotUrlBusy(false);
                        }
                    });
                });
        };

        self.testWebcamFfmpegPathBusy = ko.observable(false);
        self.testWebcamFfmpegPath = function () {
            if (!self.webcam_ffmpegPath()) {
                return;
            }

            if (self.testWebcamFfmpegPathBusy()) {
                return;
            }

            self.testWebcamFfmpegPathBusy(true);
            OctoPrint.util
                .testExecutable(self.webcam_ffmpegPath())
                .done(function (response) {
                    if (!response.result) {
                        if (!response.exists) {
                            self.webcam_ffmpegPathText(gettext("The path doesn't exist"));
                        } else if (!response.typeok) {
                            self.webcam_ffmpegPathText(gettext("The path is not a file"));
                        } else if (!response.access) {
                            self.webcam_ffmpegPathText(
                                gettext("The path is not an executable")
                            );
                        }
                    } else {
                        self.webcam_ffmpegPathText(gettext("The path is valid"));
                    }
                    self.webcam_ffmpegPathOk(response.result);
                    self.webcam_ffmpegPathBroken(!response.result);
                })
                .always(function () {
                    self.testWebcamFfmpegPathBusy(false);
                });
        };

        self.testOnlineConnectivityConfigBusy = ko.observable(false);
        self.testOnlineConnectivityConfig = function () {
            if (!self.server_onlineCheck_host()) return;
            if (!self.server_onlineCheck_port()) return;
            if (self.testOnlineConnectivityConfigBusy()) return;

            self.testOnlineConnectivityConfigBusy(true);
            OctoPrint.util
                .testServer(
                    self.server_onlineCheck_host(),
                    self.server_onlineCheck_port()
                )
                .done(function (response) {
                    if (!response.result) {
                        self.server_onlineCheckText(
                            gettext("The server is not reachable")
                        );
                    } else {
                        self.server_onlineCheckText(gettext("The server is reachable"));
                    }
                    self.server_onlineCheckOk(response.result);
                    self.server_onlineCheckBroken(!response.result);
                })
                .always(function () {
                    self.testOnlineConnectivityConfigBusy(false);
                });
        };

        self.testOnlineConnectivityResolutionConfigBusy = ko.observable(false);
        self.testOnlineConnectivityResolutionConfig = function () {
            if (!self.server_onlineCheck_name()) return;
            if (self.testOnlineConnectivityResolutionConfigBusy()) return;

            self.testOnlineConnectivityResolutionConfigBusy(true);
            OctoPrint.util
                .testResolution(self.server_onlineCheck_name())
                .done(function (response) {
                    if (!response.result) {
                        self.server_onlineCheckResolutionText(
                            gettext("Name cannot be resolved")
                        );
                    } else {
                        self.server_onlineCheckResolutionText(
                            gettext("Name can be resolved")
                        );
                    }
                    self.server_onlineCheckResolutionOk(response.result);
                    self.server_onlineCheckResolutionBroken(!response.result);
                })
                .always(function () {
                    self.testOnlineConnectivityResolutionConfigBusy(false);
                });
        };

        self.testFolderConfigBusy = ko.observable(false);
        self.testFolderConfig = function (folder) {
            var observable = "folder_" + folder;
            if (!self.hasOwnProperty(observable)) return;

            if (self.testFolderConfigBusy()) return;
            self.testFolderConfigBusy(true);

            var opts = {
                check_type: "dir",
                check_access: "w",
                allow_create_dir: true,
                check_writable_dir: true
            };
            var path = self[observable]();
            OctoPrint.util
                .testPath(path, opts)
                .done(function (response) {
                    if (!response.result) {
                        if (response.broken_symlink) {
                            self.testFolderConfigText[folder](
                                gettext("The path is a broken symlink.")
                            );
                        } else if (!response.exists) {
                            self.testFolderConfigText[folder](
                                gettext("The path does not exist and cannot be created.")
                            );
                        } else if (!response.typeok) {
                            self.testFolderConfigText[folder](
                                gettext("The path is not a folder.")
                            );
                        } else if (!response.access) {
                            self.testFolderConfigText[folder](
                                gettext("The path is not writable.")
                            );
                        }
                    } else {
                        self.testFolderConfigText[folder](gettext("The path is valid"));
                    }
                    self.testFolderConfigOk[folder](response.result);
                    self.testFolderConfigBroken[folder](!response.result);
                })
                .always(function () {
                    self.testFolderConfigBusy(false);
                });
        };

        self.onSettingsHidden = function () {
            self.webcam_ffmpegPathReset();
            self.server_onlineCheckReset();
            self.server_onlineCheckResolutionReset();
            self.testFolderConfigReset();
        };

        self.isDialogActive = function () {
            return self.settingsDialog.is(":visible");
        };

        self.onStartup = function () {
            self.settingsDialog = $("#settings_dialog");
            self.settingsUpdatedDialog = $("#settings_dialog_update_detected");
            self.translationManagerDialog = $(
                "#settings_appearance_managelanguagesdialog"
            );
            self.translationUploadElement = $(
                "#settings_appearance_managelanguagesdialog_upload"
            );
            self.translationUploadButton = $(
                "#settings_appearance_managelanguagesdialog_upload_start"
            );

            self.translationUploadElement.fileupload({
                dataType: "json",
                maxNumberOfFiles: 1,
                autoUpload: false,
                headers: OctoPrint.getRequestHeaders(),
                add: function (e, data) {
                    if (data.files.length == 0) {
                        return false;
                    }

                    self.translationUploadFilename(data.files[0].name);

                    self.translationUploadButton.unbind("click");
                    self.translationUploadButton.bind("click", function () {
                        data.submit();
                        return false;
                    });
                },
                done: function (e, data) {
                    self.translationUploadButton.unbind("click");
                    self.translationUploadFilename(undefined);
                    self.fromTranslationResponse(data.result);
                },
                fail: function (e, data) {
                    self.translationUploadButton.unbind("click");
                    self.translationUploadFilename(undefined);
                }
            });
        };

        self.onAllBound = function (allViewModels) {
            self.allViewModels = allViewModels;

            self.settingsDialog.on("show", function (event) {
                OctoPrint.coreui.settingsOpen = true;
                if (event.target.id == "settings_dialog") {
                    self.requestTranslationData();
                    callViewModels(allViewModels, "onSettingsShown");
                }
            });
            self.settingsDialog.on("hidden", function (event) {
                OctoPrint.coreui.settingsOpen = false;
                if (event.target.id == "settings_dialog") {
                    callViewModels(allViewModels, "onSettingsHidden");
                }
            });
            self.settingsDialog.on("beforeSave", function () {
                callViewModels(allViewModels, "onSettingsBeforeSave");
            });

            $(".reload_all", self.settingsUpdatedDialog).click(function (e) {
                e.preventDefault();
                self.settingsUpdatedDialog.modal("hide");
                self.requestData();
                return false;
            });
            $(".reload_nonconflicts", self.settingsUpdatedDialog).click(function (e) {
                e.preventDefault();
                self.settingsUpdatedDialog.modal("hide");
                self.requestData(true);
                return false;
            });

            // reset scroll position on tab change
            $('ul.nav-list a[data-toggle="tab"]', self.settingsDialog).on(
                "show",
                function () {
                    self._resetScrollPosition();
                }
            );
        };

        self.show = function (tab) {
            // select first or specified tab
            self.selectTab(tab);

            // reset scroll position
            self._resetScrollPosition();

            // show settings, ensure centered position
            self.settingsDialog
                .modal({
                    minHeight: function () {
                        return Math.max($.fn.modal.defaults.maxHeight() - 80, 250);
                    }
                })
                .css({
                    "margin-left": function () {
                        return -($(this).width() / 2);
                    }
                });

            return false;
        };

        self.hide = function () {
            self.settingsDialog.modal("hide");
        };

        self.generateApiKey = function () {
            if (!CONFIG_ACCESS_CONTROL) return;

            showConfirmationDialog(
                gettext(
                    "This will generate a new API Key. The old API Key will cease to function immediately."
                ),
                function () {
                    OctoPrint.settings.generateApiKey().done(function (response) {
                        self.api_key(response.apikey);
                        self.requestData();
                    });
                }
            );
        };

        self.copyApiKey = function () {
            copyToClipboard(self.api_key());
        };

        self.showTranslationManager = function () {
            self.translationManagerDialog.modal();
            return false;
        };

        self.requestData = function (local) {
            // handle old parameter format
            var callback = undefined;
            if (arguments.length === 2 || _.isFunction(local)) {
                var exc = new Error();
                log.warn(
                    "The callback parameter of SettingsViewModel.requestData is deprecated, the method now returns a promise, please use that instead. Stacktrace:",
                    exc.stack || exc.stacktrace || "<n/a>"
                );

                if (arguments.length === 2) {
                    callback = arguments[0];
                    local = arguments[1];
                } else {
                    callback = local;
                    local = false;
                }
            }

            // handler for any explicitly provided callbacks
            var callbackHandler = function () {
                if (!callback) return;
                try {
                    callback();
                } catch (exc) {
                    log.error(
                        "Error calling settings callback",
                        callback,
                        ":",
                        exc.stack || exc.stacktrace || exc
                    );
                }
            };

            // if a request is already active, create a new deferred and return
            // its promise, it will be resolved in the response handler of the
            // current request
            if (self.receiving()) {
                var deferred = $.Deferred();
                self.outstanding.push(deferred);

                if (callback) {
                    // if we have a callback, we need to make sure it will
                    // get called when the deferred is resolved
                    deferred.done(callbackHandler);
                }

                return deferred.promise();
            }

            // perform the request
            self.receiving(true);
            return OctoPrint.settings
                .get()
                .always(function () {
                    self.receiving(false);
                })
                .done(function (response) {
                    self.fromResponse(response, local);

                    if (callback) {
                        var deferred = $.Deferred();
                        deferred.done(callbackHandler);
                        self.outstanding.push(deferred);
                    }

                    // resolve all promises
                    var args = arguments;
                    _.each(self.outstanding, function (deferred) {
                        deferred.resolve(args);
                    });
                    self.outstanding = [];
                })
                .fail(function () {
                    // reject all promises
                    var args = arguments;
                    _.each(self.outstanding, function (deferred) {
                        deferred.reject(args);
                    });
                    self.outstanding = [];
                });
        };

        self.requestTranslationData = function () {
            return OctoPrint.languages.list().done(self.fromTranslationResponse);
        };

        self.fromTranslationResponse = function (response) {
            var translationsByLocale = {};
            _.each(response.language_packs, function (item, key) {
                _.each(item.languages, function (pack) {
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
            _.each(translationsByLocale, function (item) {
                item["packs"].sort(function (a, b) {
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

        self.languagePackDisplay = function (item) {
            return (
                item.display +
                (item.english != undefined ? " (" + item.english + ")" : "")
            );
        };

        self.languagePacksAvailable = ko.pureComputed(function () {
            return self.translations.allSize() > 0;
        });

        self.deleteLanguagePack = function (locale, pack) {
            OctoPrint.languages.delete(locale, pack).done(self.fromTranslationResponse);
        };

        /**
         * Fetches the settings as currently stored in this client instance.
         */
        self.getLocalData = function () {
            var data = {};
            if (self.settings != undefined) {
                data = ko.mapping.toJS(self.settings);
            }

            // some special read functions for various observables
            var specialMappings = {
                feature: {
                    autoUppercaseBlacklist: function () {
                        return splitTextToArray(
                            self.feature_autoUppercaseBlacklist(),
                            ",",
                            true
                        );
                    }
                },
                serial: {
                    additionalPorts: function () {
                        return commentableLinesToArray(self.serial_additionalPorts());
                    },
                    additionalBaudrates: function () {
                        return _.map(
                            splitTextToArray(
                                self.serial_additionalBaudrates(),
                                ",",
                                true,
                                function (item) {
                                    return !isNaN(parseInt(item));
                                }
                            ),
                            function (item) {
                                return parseInt(item);
                            }
                        );
                    },
                    blacklistedPorts: function () {
                        return commentableLinesToArray(self.serial_blacklistedPorts());
                    },
                    blacklistedBaudrates: function () {
                        return _.map(
                            splitTextToArray(
                                self.serial_blacklistedBaudrates(),
                                ",",
                                true,
                                function (item) {
                                    return !isNaN(parseInt(item));
                                }
                            ),
                            function (item) {
                                return parseInt(item);
                            }
                        );
                    },
                    longRunningCommands: function () {
                        return splitTextToArray(
                            self.serial_longRunningCommands(),
                            ",",
                            true
                        );
                    },
                    checksumRequiringCommands: function () {
                        return splitTextToArray(
                            self.serial_checksumRequiringCommands(),
                            ",",
                            true
                        );
                    },
                    blockedCommands: function () {
                        return splitTextToArray(self.serial_blockedCommands(), ",", true);
                    },
                    ignoredCommands: function () {
                        return splitTextToArray(self.serial_ignoredCommands(), ",", true);
                    },
                    pausingCommands: function () {
                        return splitTextToArray(self.serial_pausingCommands(), ",", true);
                    },
                    emergencyCommands: function () {
                        return splitTextToArray(
                            self.serial_emergencyCommands(),
                            ",",
                            true
                        );
                    },
                    externalHeatupDetection: function () {
                        return !self.serial_disableExternalHeatupDetection();
                    },
                    alwaysSendChecksum: function () {
                        return self.serial_sendChecksum() === "always";
                    },
                    neverSendChecksum: function () {
                        return self.serial_sendChecksum() === "never";
                    },
                    ignoreErrorsFromFirmware: function () {
                        return self.serial_serialErrorBehaviour() === "ignore";
                    },
                    disconnectOnErrors: function () {
                        return self.serial_serialErrorBehaviour() === "disconnect";
                    }
                },
                scripts: {
                    gcode: function () {
                        // we have a special handler function for the gcode scripts since the
                        // server will always send us those that have been set already, so we
                        // can't depend on all keys that we support to be present in the
                        // original request we iterate through in mapFromObservables to
                        // generate our response - hence we use our observables instead
                        //
                        // Note: If we ever introduce sub categories in the gcode scripts
                        // here (more _ after the prefix), we'll need to adjust this code
                        // to be able to cope with that, right now it only strips the prefix
                        // and uses the rest as key in the result, no recursive translation
                        // is done!
                        var result = {};
                        var prefix = "scripts_gcode_";
                        var observables = _.filter(_.keys(self), function (key) {
                            return _.startsWith(key, prefix);
                        });
                        _.each(observables, function (observable) {
                            var script = observable.substring(prefix.length);
                            result[script] = self[observable]();
                        });
                        return result;
                    }
                },
                temperature: {
                    profiles: function () {
                        var result = [];
                        _.each(self.temperature_profiles(), function (profile) {
                            try {
                                result.push({
                                    name: profile.name,
                                    extruder: Math.floor(
                                        _.isNumber(profile.extruder)
                                            ? profile.extruder
                                            : parseInt(profile.extruder)
                                    ),
                                    bed: Math.floor(
                                        _.isNumber(profile.bed)
                                            ? profile.bed
                                            : parseInt(profile.bed)
                                    ),
                                    chamber: Math.floor(
                                        _.isNumber(profile.chamber)
                                            ? profile.chamber
                                            : _.isNumber(parseInt(profile.chamber))
                                            ? parseInt(profile.chamber)
                                            : 0
                                    )
                                });
                            } catch (ex) {
                                // ignore
                            }
                        });
                        return result;
                    }
                },
                webcam: {
                    streamWebrtcIceServers: function () {
                        return splitTextToArray(
                            self.webcam_streamWebrtcIceServers(),
                            ",",
                            true
                        );
                    }
                }
            };

            var mapFromObservables = function (data, mapping, keyPrefix) {
                var flag = false;
                var result = {};

                // process all key-value-pairs here
                _.forOwn(data, function (value, key) {
                    var observable = key;
                    if (keyPrefix !== undefined) {
                        observable = keyPrefix + "_" + observable;
                    }

                    if (self.observableCopies.hasOwnProperty(observable)) {
                        // only a copy, skip
                        return;
                    }

                    if (mapping && mapping[key] && _.isFunction(mapping[key])) {
                        result[key] = mapping[key]();
                        flag = true;
                    } else if (_.isPlainObject(value)) {
                        // value is another object, we'll dive deeper
                        var subresult = mapFromObservables(
                            value,
                            mapping && mapping[key] ? mapping[key] : undefined,
                            observable
                        );
                        if (subresult !== undefined) {
                            // we only set something on our result if we got something back
                            result[key] = subresult;
                            flag = true;
                        }
                    } else if (self.hasOwnProperty(observable)) {
                        result[key] = self[observable]();
                        flag = true;
                    }
                });

                // if we set something on our result (flag is true), we return result, else we return undefined
                return flag ? result : undefined;
            };

            // map local observables based on our existing data
            var dataFromObservables = mapFromObservables(data, specialMappings);

            data = deepMerge(data, dataFromObservables);
            return data;
        };

        self.fromResponse = function (response, local) {
            // server side changes to set
            var serverChangedData;

            // client side changes to keep
            var clientChangedData;

            if (local) {
                // local is true, so we'll keep all local changes and only update what's been updated server side
                serverChangedData = getOnlyChangedData(
                    response,
                    self.lastReceivedSettings
                );
                clientChangedData = getOnlyChangedData(
                    self.getLocalData(),
                    self.lastReceivedSettings
                );
            } else {
                // local is false or unset, so we'll forcefully update with the settings from the server
                serverChangedData = response;
                clientChangedData = undefined;
            }

            // last received settings reset to response
            self.lastReceivedSettings = response;

            if (self.settings === undefined) {
                self.settings = ko.mapping.fromJS(serverChangedData);
            } else {
                ko.mapping.fromJS(serverChangedData, self.settings);
            }

            // some special apply functions for various observables
            var specialMappings = {
                appearance: {
                    defaultLanguage: function (value) {
                        self.appearance_defaultLanguage("_default");
                        if (_.includes(self.locale_languages, value)) {
                            self.appearance_defaultLanguage(value);
                        }
                    }
                },
                feature: {
                    autoUppercaseBlacklist: function (value) {
                        self.feature_autoUppercaseBlacklist(value.join(", "));
                    }
                },
                serial: {
                    additionalPorts: function (value) {
                        self.serial_additionalPorts(value.join("\n"));
                    },
                    additionalBaudrates: function (value) {
                        self.serial_additionalBaudrates(value.join(", "));
                    },
                    blacklistedPorts: function (value) {
                        self.serial_blacklistedPorts(value.join("\n"));
                    },
                    blacklistedBaudrates: function (value) {
                        self.serial_blacklistedBaudrates(value.join(", "));
                    },
                    longRunningCommands: function (value) {
                        self.serial_longRunningCommands(value.join(", "));
                    },
                    checksumRequiringCommands: function (value) {
                        self.serial_checksumRequiringCommands(value.join(", "));
                    },
                    blockedCommands: function (value) {
                        self.serial_blockedCommands(value.join(", "));
                    },
                    ignoredCommands: function (value) {
                        self.serial_ignoredCommands(value.join(", "));
                    },
                    pausingCommands: function (value) {
                        self.serial_pausingCommands(value.join(", "));
                    },
                    emergencyCommands: function (value) {
                        self.serial_emergencyCommands(value.join(", "));
                    },
                    externalHeatupDetection: function (value) {
                        self.serial_disableExternalHeatupDetection(!value);
                    },
                    alwaysSendChecksum: function (value) {
                        if (value) {
                            self.serial_sendChecksum("always");
                        }
                    },
                    neverSendChecksum: function (value) {
                        if (value) {
                            self.serial_sendChecksum("never");
                        }
                    },
                    ignoreErrorsFromFirmware: function (value) {
                        if (value) {
                            self.serial_serialErrorBehaviour("ignore");
                        }
                    },
                    disconnectOnErrors: function (value) {
                        if (value) {
                            self.serial_serialErrorBehaviour("disconnect");
                        }
                    }
                },
                terminalFilters: function (value) {
                    self.terminalFilters($.extend(true, [], value));
                },
                temperature: {
                    profiles: function (value) {
                        self.temperature_profiles($.extend(true, [], value));
                    }
                },
                webcam: {
                    streamWebrtcIceServers: function (value) {
                        self.webcam_streamWebrtcIceServers(value.join(", "));
                    }
                }
            };

            var mapToObservables = function (data, mapping, local, keyPrefix) {
                if (!_.isPlainObject(data)) {
                    return;
                }

                // process all key-value-pairs here
                _.forOwn(data, function (value, key) {
                    var observable = key;
                    if (keyPrefix != undefined) {
                        observable = keyPrefix + "_" + observable;
                    }

                    if (self.observableCopies.hasOwnProperty(observable)) {
                        // only a copy, skip
                        return;
                    }

                    var haveLocalVersion = local && local.hasOwnProperty(key);

                    if (
                        mapping &&
                        mapping[key] &&
                        _.isFunction(mapping[key]) &&
                        !haveLocalVersion
                    ) {
                        // if we have a custom apply function for this, we'll use it
                        mapping[key](value);
                    } else if (_.isPlainObject(value)) {
                        // value is another object, we'll dive deeper
                        mapToObservables(
                            value,
                            mapping && mapping[key] ? mapping[key] : undefined,
                            local && local[key] ? local[key] : undefined,
                            observable
                        );
                    } else if (!haveLocalVersion && self.hasOwnProperty(observable)) {
                        // if we have a matching observable, we'll use that
                        self[observable](value);
                    }
                });
            };

            mapToObservables(serverChangedData, specialMappings, clientChangedData);

            firstRequest.resolve();
        };

        self.cancelData = function () {
            // revert unsaved changes
            self.fromResponse(self.lastReceivedSettings);

            self.hide();
        };

        self.saveData = function (data, successCallback, setAsSending) {
            var options;
            if (_.isPlainObject(successCallback)) {
                options = successCallback;
            } else {
                options = {
                    success: successCallback,
                    sending: setAsSending === true
                };
            }

            self.settingsDialog.trigger("beforeSave");

            self.sawUpdateEventWhileSending = false;
            self.sending(data === undefined || options.sending || false);

            if (data === undefined) {
                // we also only send data that actually changed when no data is specified
                var localData = self.getLocalData();
                data = getOnlyChangedData(localData, self.lastReceivedSettings);
            }

            // final validation
            if (self.testFoldersDuplicate()) {
                // duplicate folders configured, we refuse to send any folder config
                // to the server
                delete data.folder;
            }

            self.active = true;
            return OctoPrint.settings
                .save(data)
                .done(function (data, status, xhr) {
                    self.ignoreNextUpdateEvent = !self.sawUpdateEventWhileSending;
                    self.active = false;

                    self.receiving(true);
                    self.sending(false);

                    try {
                        self.fromResponse(data);
                        if (options.success) options.success(data, status, xhr);
                    } finally {
                        self.receiving(false);
                    }
                })
                .fail(function (xhr, status, error) {
                    self.sending(false);
                    self.active = false;
                    if (options.error) options.error(xhr, status, error);
                })
                .always(function (xhr, status) {
                    if (options.complete) options.complete(xhr, status);
                });
        };

        self.onEventSettingsUpdated = function () {
            if (self.active) {
                self.sawUpdateEventWhileActive = true;
            }

            var preventSettingsRefresh = _.any(self.allViewModels, function (viewModel) {
                if (viewModel.hasOwnProperty("onSettingsPreventRefresh")) {
                    try {
                        return viewModel["onSettingsPreventRefresh"]();
                    } catch (e) {
                        log.warn(
                            "Error while calling onSettingsPreventRefresh on",
                            viewModel,
                            ":",
                            e
                        );
                        return false;
                    }
                } else {
                    return false;
                }
            });

            if (preventSettingsRefresh) {
                // if any of our viewmodels prevented this refresh, we'll just return now
                return;
            }

            if (self.isDialogActive()) {
                // dialog is open and not currently busy...
                if (
                    self.sending() ||
                    self.receiving() ||
                    self.active ||
                    self.ignoreNextUpdateEvent
                ) {
                    self.ignoreNextUpdateEvent = false;
                    return;
                }

                if (!hasDataChanged(self.getLocalData(), self.lastReceivedSettings)) {
                    // we don't have local changes, so just fetch new data
                    self.requestData();
                } else {
                    // we have local changes, show update dialog
                    self.settingsUpdatedDialog.modal("show");
                }
            } else {
                // dialog is not open, just fetch new data
                self.requestData();
            }
        };

        self._resetScrollPosition = function () {
            $("#settings_dialog_content", self.settingsDialog).scrollTop(0);

            // also reset any contained tabs/pills/lists to first pane
            $(
                '#settings_dialog_content ul.nav-pills a[data-toggle="tab"]:first',
                self.settingsDialog
            ).tab("show");
            $(
                '#settings_dialog_content ul.nav-list a[data-toggle="tab"]:first',
                self.settingsDialog
            ).tab("show");
            $(
                '#settings_dialog_content ul.nav-tabs a[data-toggle="tab"]:first',
                self.settingsDialog
            ).tab("show");
        };

        self.selectTab = function (tab) {
            if (tab != undefined) {
                if (!_.startsWith(tab, "#")) {
                    tab = "#" + tab;
                }
                $('ul.nav-list a[href="' + tab + '"]', self.settingsDialog).tab("show");
            } else {
                $('ul.nav-list a[data-toggle="tab"]:first', self.settingsDialog).tab(
                    "show"
                );
            }
        };

        self.onServerReconnect = function () {
            // the settings might have changed if the server was just restarted,
            // better refresh them now
            self.requestData();
        };

        self.onUserPermissionsChanged =
            self.onUserLoggedIn =
            self.onUserLoggedOut =
                function () {
                    // we might have other user rights now, refresh (but only if startup has fully completed)
                    if (!self._startupComplete) return;
                    self.requestData();
                };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: SettingsViewModel,
        dependencies: [
            "loginStateViewModel",
            "accessViewModel",
            "printerProfilesViewModel",
            "aboutViewModel",
            "usersViewModel"
        ],
        elements: ["#settings_dialog", "#navbar_settings"]
    });
});
