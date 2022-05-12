$(function () {
    function ControlViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settings = parameters[1];
        self.access = parameters[2];

        self._createToolEntry = function () {
            return {
                name: ko.observable(),
                key: ko.observable()
            };
        };

        self.isErrorOrClosed = ko.observable(undefined);
        self.isOperational = ko.observable(undefined);
        self.isPrinting = ko.observable(undefined);
        self.isPaused = ko.observable(undefined);
        self.isError = ko.observable(undefined);
        self.isReady = ko.observable(undefined);
        self.isLoading = ko.observable(undefined);

        self.extrusionAmount = ko.observable(undefined);

        self.controls = ko.observableArray([]);

        self.distances = ko.observableArray([0.1, 1, 10, 100]);
        self.distance = ko.observable(10);

        self.tools = ko.observableArray([]);

        self.feedRate = ko.observable();
        self.flowRate = ko.observable();

        self.feedbackControlLookup = {};

        self.controlsFromServer = [];
        self.additionalControls = [];

        self.webcamDisableTimeout = undefined;
        self.webcamLoaded = ko.observable(false);
        self.webcamMjpgEnabled = ko.observable(false);
        self.webcamHlsEnabled = ko.observable(false);
        self.webcamWebRTCEnabled = ko.observable(false);
        self.webcamError = ko.observable(false);
        self.webcamMuted = ko.observable(true);
        self.webRTCPeerConnection = null;
        self.webcamElementHls = null;
        self.webcamElementWebrtc = null;

        self.keycontrolActive = ko.observable(false);
        self.keycontrolHelpActive = ko.observable(false);
        self.keycontrolPossible = ko.pureComputed(function () {
            return (
                self.loginState.hasPermission(self.access.permissions.CONTROL) &&
                self.settings.feature_keyboardControl() &&
                self.isOperational() &&
                !self.isPrinting() &&
                !$.browser.mobile
            );
        });
        self.showKeycontrols = ko.pureComputed(function () {
            return self.keycontrolActive() && self.keycontrolPossible();
        });

        self.webcamRatioClass = ko.pureComputed(function () {
            if (self.settings.webcam_streamRatio() == "4:3") {
                return "ratio43";
            } else {
                return "ratio169";
            }
        });

        // Subscribe to rotation event to ensure we update calculations.
        // We need to wait for the CSS to be updated by KO, thus we use a timeout to
        // ensure our calculations run after the CSS was updated
        self.settings.webcam_rotate90.subscribe(function () {
            window.setTimeout(function () {
                self._updateVideoTagWebcamLayout();
            }, 1);
        });

        self.settings.printerProfiles.currentProfileData.subscribe(function () {
            self._updateExtruderCount();
            self._updateExtrusionAmount();
            self.settings.printerProfiles
                .currentProfileData()
                .extruder.count.subscribe(self._updateExtruderCount);
        });
        self._updateExtrusionAmount = function () {
            self.extrusionAmount(
                self.settings.printerProfiles
                    .currentProfileData()
                    .extruder.defaultExtrusionLength()
            );
        };
        self._updateExtruderCount = function () {
            var tools = [];

            var numExtruders = self.settings.printerProfiles
                .currentProfileData()
                .extruder.count();
            if (numExtruders > 1) {
                // multiple extruders
                for (var extruder = 0; extruder < numExtruders; extruder++) {
                    tools[extruder] = self._createToolEntry();
                    tools[extruder]["name"](gettext("Tool") + " " + extruder);
                    tools[extruder]["key"]("tool" + extruder);
                }
            } else if (numExtruders === 1) {
                // only one extruder, no need to add numbers
                tools[0] = self._createToolEntry();
                tools[0]["name"](gettext("Hotend"));
                tools[0]["key"]("tool0");
            }

            self.tools(tools);
        };

        self.fromCurrentData = function (data) {
            self._processStateData(data.state);
        };

        self.fromHistoryData = function (data) {
            self._processStateData(data.state);
        };

        self._processStateData = function (data) {
            self.isErrorOrClosed(data.flags.closedOrError);
            self.isOperational(data.flags.operational);
            self.isPaused(data.flags.paused);
            self.isPrinting(data.flags.printing);
            self.isError(data.flags.error);
            self.isReady(data.flags.ready);
            self.isLoading(data.flags.loading);
        };

        self.onEventSettingsUpdated = function (payload) {
            // the webcam url might have changed, make sure we replace it now if the
            // tab is focused
            self._enableWebcam();
            self.requestData();
        };

        self.onEventRegisteredMessageReceived = function (payload) {
            if (payload.key in self.feedbackControlLookup) {
                var outputs = self.feedbackControlLookup[payload.key];
                _.each(payload.outputs, function (value, key) {
                    if (outputs.hasOwnProperty(key)) {
                        outputs[key](value);
                    }
                });
            }
        };

        self.rerenderControls = function () {
            var allControls = self.controlsFromServer.concat(self.additionalControls);
            self.controls(self._processControls(allControls));
        };

        self.requestData = function () {
            if (!self.loginState.hasPermission(self.access.permissions.CONTROL)) {
                return;
            }

            OctoPrint.control.getCustomControls().done(function (response) {
                self._fromResponse(response);
            });
        };

        self._fromResponse = function (response) {
            self.controlsFromServer = response.controls;
            self.rerenderControls();
        };

        self._processControls = function (controls) {
            for (var i = 0; i < controls.length; i++) {
                controls[i] = self._processControl(controls[i]);
            }
            return controls;
        };

        self._processControl = function (control) {
            if (control.hasOwnProperty("processed") && control.processed) {
                return control;
            }

            if (
                control.hasOwnProperty("template") &&
                control.hasOwnProperty("key") &&
                control.hasOwnProperty("template_key") &&
                !control.hasOwnProperty("output")
            ) {
                control.output = ko.observable(control.default || "");
                if (!self.feedbackControlLookup.hasOwnProperty(control.key)) {
                    self.feedbackControlLookup[control.key] = {};
                }
                self.feedbackControlLookup[control.key][control.template_key] =
                    control.output;
            }

            if (control.hasOwnProperty("children")) {
                control.children = ko.observableArray(
                    self._processControls(control.children)
                );
                if (
                    !control.hasOwnProperty("layout") ||
                    !(
                        control.layout == "vertical" ||
                        control.layout == "horizontal" ||
                        control.layout == "horizontal_grid"
                    )
                ) {
                    control.layout = "vertical";
                }

                if (!control.hasOwnProperty("collapsed")) {
                    control.collapsed = false;
                }
            }

            if (control.hasOwnProperty("input")) {
                var attributeToInt = function (obj, key, def) {
                    if (obj.hasOwnProperty(key)) {
                        var val = obj[key];
                        if (_.isNumber(val)) {
                            return val;
                        }

                        var parsedVal = parseInt(val);
                        if (!isNaN(parsedVal)) {
                            return parsedVal;
                        }
                    }
                    return def;
                };

                _.each(control.input, function (element) {
                    if (element.hasOwnProperty("slider") && _.isObject(element.slider)) {
                        element.slider["min"] = attributeToInt(element.slider, "min", 0);
                        element.slider["max"] = attributeToInt(
                            element.slider,
                            "max",
                            255
                        );

                        // try defaultValue, default to min
                        var defaultValue = attributeToInt(
                            element,
                            "default",
                            element.slider.min
                        );

                        // if default value is not w/i range of min and max, correct that
                        if (
                            !_.inRange(
                                defaultValue,
                                element.slider.min,
                                element.slider.max
                            )
                        ) {
                            // use bound closer to configured default value
                            defaultValue =
                                defaultValue < element.slider.min
                                    ? element.slider.min
                                    : element.slider.max;
                        }

                        element.value = ko.observable(defaultValue);
                    } else {
                        element.slider = false;
                        element.value = ko.observable(
                            element.hasOwnProperty("default")
                                ? element["default"]
                                : undefined
                        );
                    }
                });
            }

            if (control.hasOwnProperty("javascript")) {
                var js = control.javascript;

                // if js is a function everything's fine already, but if it's a string
                // we need to eval that first
                if (!_.isFunction(js)) {
                    control.javascript = function (data) {
                        eval(js);
                    };
                }
            }

            if (control.hasOwnProperty("enabled")) {
                var enabled = control.enabled;

                // if js is a function everything's fine already, but if it's a string
                // we need to eval that first
                if (!_.isFunction(enabled)) {
                    control.enabled = function (data) {
                        return eval(enabled);
                    };
                }
            }

            if (!control.hasOwnProperty("additionalClasses")) {
                control.additionalClasses = "";
            }

            control.processed = true;
            return control;
        };

        self.isCustomEnabled = function (data) {
            if (data.hasOwnProperty("enabled")) {
                return data.enabled(data);
            } else {
                return (
                    self.loginState.hasPermission(self.access.permissions.CONTROL) &&
                    self.isOperational()
                );
            }
        };

        self.clickCustom = function (data) {
            var callback;
            if (data.hasOwnProperty("javascript")) {
                callback = data.javascript;
            } else {
                callback = self.sendCustomCommand;
            }

            if (data.confirm) {
                showConfirmationDialog({
                    message: data.confirm,
                    onproceed: function (e) {
                        callback(data);
                    }
                });
            } else {
                callback(data);
            }
        };

        self._getActiveWebcamVideoElement = function () {
            if (self.webcamWebRTCEnabled()) {
                return self.webcamElementWebrtc;
            } else {
                return self.webcamElementHls;
            }
        };

        self.launchWebcamPictureInPicture = function () {
            self._getActiveWebcamVideoElement().requestPictureInPicture();
        };

        self.launchWebcamFullscreen = function () {
            self._getActiveWebcamVideoElement().requestFullscreen();
        };

        self.toggleWebcamMute = function () {
            self.webcamMuted(!self.webcamMuted());
            self.webcamElementWebrtc.muted = self.webcamMuted();
            self.webcamElementHls.muted = self.webcamMuted();
        };

        self.sendJogCommand = function (axis, multiplier, distance) {
            if (typeof distance === "undefined") distance = self.distance();
            if (
                self.settings.printerProfiles.currentProfileData() &&
                self.settings.printerProfiles.currentProfileData()["axes"] &&
                self.settings.printerProfiles.currentProfileData()["axes"][axis] &&
                self.settings.printerProfiles
                    .currentProfileData()
                    ["axes"][axis]["inverted"]()
            ) {
                multiplier *= -1;
            }

            var data = {};
            data[axis] = distance * multiplier;
            OctoPrint.printer.jog(data);
        };

        self.sendHomeCommand = function (axis) {
            OctoPrint.printer.home(axis);
        };

        self.feedRateBusy = ko.observable(false);
        self.feedRateResetter = ko.observable();
        self.sendFeedRateCommand = function () {
            var rate = self.feedRate();
            if (!rate) return;

            rate = _.parseInt(self.feedRate());
            self.feedRateBusy(true);
            OctoPrint.printer
                .setFeedrate(rate)
                .done(function () {
                    self.feedRate(undefined);
                })
                .always(function () {
                    self.feedRateBusy(false);
                });
        };
        self.resetFeedRateDisplay = function () {
            self.cancelFeedRateDisplayReset();
            self.feedRateResetter(
                setTimeout(function () {
                    self.feedRate(undefined);
                    self.feedRateResetter(undefined);
                }, 5000)
            );
        };
        self.cancelFeedRateDisplayReset = function () {
            var resetter = self.feedRateResetter();
            if (resetter) {
                clearTimeout(resetter);
                self.feedRateResetter(undefined);
            }
        };

        self.sendExtrudeCommand = function () {
            self._sendECommand(1);
        };

        self.sendRetractCommand = function () {
            self._sendECommand(-1);
        };

        self.flowRateBusy = ko.observable(false);
        self.flowRateResetter = ko.observable();
        self.sendFlowRateCommand = function () {
            var rate = self.flowRate();
            if (!rate) return;

            rate = _.parseInt(self.flowRate());
            self.flowRateBusy(true);
            OctoPrint.printer
                .setFlowrate(rate)
                .done(function () {
                    self.flowRate(undefined);
                })
                .always(function () {
                    self.flowRateBusy(false);
                });
        };
        self.resetFlowRateDisplay = function () {
            self.cancelFlowRateDisplayReset();
            self.flowRateResetter(
                setTimeout(function () {
                    self.flowRate(undefined);
                    self.flowRateResetter(undefined);
                }, 5000)
            );
        };
        self.cancelFlowRateDisplayReset = function () {
            var resetter = self.flowRateResetter();
            if (resetter) {
                clearTimeout(resetter);
                self.flowRateResetter(undefined);
            }
        };

        self._sendECommand = function (dir) {
            var length = self.extrusionAmount();
            OctoPrint.printer.extrude(length * dir);
        };

        self.sendSelectToolCommand = function (data) {
            if (!data || !data.key()) return;

            OctoPrint.printer.selectTool(data.key());
        };

        self.sendCustomCommand = function (command) {
            if (!command) return;

            var parameters = {};
            if (command.hasOwnProperty("input")) {
                _.each(command.input, function (input) {
                    if (
                        !input.hasOwnProperty("parameter") ||
                        !input.hasOwnProperty("value")
                    ) {
                        return;
                    }

                    parameters[input.parameter] = input.value();
                });
            }

            if (command.hasOwnProperty("command") || command.hasOwnProperty("commands")) {
                var commands = command.commands || [command.command];
                OctoPrint.control.sendGcodeWithParameters(commands, parameters);
            } else if (command.hasOwnProperty("script")) {
                var script = command.script;
                var context = command.context || {};
                OctoPrint.control.sendGcodeScriptWithParameters(
                    script,
                    context,
                    parameters
                );
            }
        };

        self.displayMode = function (customControl) {
            if (customControl.hasOwnProperty("children")) {
                if (customControl.name) {
                    return "customControls_containerTemplate_collapsable";
                } else {
                    return "customControls_containerTemplate_nameless";
                }
            } else {
                return "customControls_controlTemplate";
            }
        };

        self.rowCss = function (customControl) {
            var span = "span2";
            var offset = "";
            if (customControl.hasOwnProperty("width")) {
                span = "span" + customControl.width;
            }
            if (customControl.hasOwnProperty("offset")) {
                offset = "offset" + customControl.offset;
            }
            return span + " " + offset;
        };

        self.onUserPermissionsChanged =
            self.onUserLoggedIn =
            self.onUserLoggedOut =
                function () {
                    self.syncWebcamElements();
                    self.requestData();
                };

        self._disableWebcam = function () {
            // only disable webcam stream if tab is out of focus for more than 5s,
            // otherwise we might cause more load by the constant connection creation
            // than by the actual webcam stream

            // safari bug doesn't release the mjpeg stream, so we just disable this for
            // safari.
            if (OctoPrint.coreui.browser.safari) {
                return;
            }

            var timeout = self.settings.webcam_streamTimeout() || 5;
            self.webcamDisableTimeout = setTimeout(function () {
                log.debug("Unloading webcam stream");
                $("#webcam_image").attr("src", "");
                self.webcamLoaded(false);
            }, timeout * 1000);
        };

        self._enableWebcam = function () {
            if (
                OctoPrint.coreui.selectedTab != "#control" ||
                !OctoPrint.coreui.browserTabVisible
            ) {
                return;
            }

            if (self.webcamDisableTimeout != undefined) {
                clearTimeout(self.webcamDisableTimeout);
            }

            // IF disabled then we dont need to do anything
            if (self.settings.webcam_webcamEnabled() == false) {
                return;
            }

            // Determine stream type and switch to corresponding webcam.
            var streamType = self.settings.webcam_streamType();
            if (streamType == "mjpg") {
                self._switchToMjpgWebcam();
            } else if (streamType == "hls") {
                self._switchToHlsWebcam();
            } else if (isWebRTCAvailable() && streamType == "webrtc") {
                self._switchToWebRTCWebcam();
            } else {
                throw "Unknown stream type " + streamType;
            }
        };

        self.onWebcamLoaded = function () {
            if (self.webcamLoaded()) return;

            log.debug("Webcam stream loaded");
            self.webcamLoaded(true);
            self.webcamError(false);
        };

        self.onWebcamErrored = function () {
            log.debug("Webcam stream failed to load/disabled");
            self.webcamLoaded(false);
            self.webcamError(true);
        };

        self.onTabChange = function (current, previous) {
            if (current == "#control") {
                self._enableWebcam();
            } else if (previous == "#control") {
                self._disableWebcam();
            }
        };

        self.onBrowserTabVisibilityChange = function (status) {
            if (status) {
                self._enableWebcam();
            } else {
                self._disableWebcam();
            }
        };

        self.onAllBound = function (allViewModels) {
            var additionalControls = [];
            callViewModels(allViewModels, "getAdditionalControls", function (method) {
                additionalControls = additionalControls.concat(method());
            });
            if (additionalControls.length > 0) {
                self.additionalControls = additionalControls;
                self.rerenderControls();
            }
            self._enableWebcam();

            self.extrusionAmount(
                self.settings.printerProfiles
                    .currentProfileData()
                    .extruder.defaultExtrusionLength()
            );
        };

        self.syncWebcamElements = function () {
            self.webcamElementHls = document.getElementById("webcam_hls");
            self.webcamElementWebrtc = document.getElementById("webcam_webrtc");
        };

        self.onStartup = function () {
            self.syncWebcamElements();
        };

        self.onFocus = function (data, event) {
            if (!self.settings.feature_keyboardControl()) return;
            self.keycontrolActive(true);
        };

        self.onMouseOver = function (data, event) {
            if (!self.settings.feature_keyboardControl()) return;
            $("#webcam_container").focus();
            self.keycontrolActive(true);
        };

        self.onMouseOut = function (data, event) {
            if (!self.settings.feature_keyboardControl()) return;
            $("#webcam_container").blur();
            self.keycontrolActive(false);
        };

        self.toggleKeycontrolHelp = function () {
            self.keycontrolHelpActive(!self.keycontrolHelpActive());
        };

        self.onKeyDown = function (data, event) {
            if (!self.settings.feature_keyboardControl()) return;

            var button = undefined;
            var visualizeClick = true;

            switch (event.which) {
                case 37: // left arrow key
                    // X-
                    button = $("#control-xdec");
                    break;
                case 38: // up arrow key
                    // Y+
                    button = $("#control-yinc");
                    break;
                case 39: // right arrow key
                    // X+
                    button = $("#control-xinc");
                    break;
                case 40: // down arrow key
                    // Y-
                    button = $("#control-ydec");
                    break;
                case 49: // number 1
                case 97: // numpad 1
                    // Distance 0.1
                    button = $("#control-distance01");
                    visualizeClick = false;
                    break;
                case 50: // number 2
                case 98: // numpad 2
                    // Distance 1
                    button = $("#control-distance1");
                    visualizeClick = false;
                    break;
                case 51: // number 3
                case 99: // numpad 3
                    // Distance 10
                    button = $("#control-distance10");
                    visualizeClick = false;
                    break;
                case 52: // number 4
                case 100: // numpad 4
                    // Distance 100
                    button = $("#control-distance100");
                    visualizeClick = false;
                    break;
                case 33: // page up key
                case 87: // w key
                    // z lift up
                    button = $("#control-zinc");
                    break;
                case 34: // page down key
                case 83: // s key
                    // z lift down
                    button = $("#control-zdec");
                    break;
                case 36: // home key
                    // xy home
                    button = $("#control-xyhome");
                    break;
                case 35: // end key
                    // z home
                    button = $("#control-zhome");
                    break;
                default:
                    event.preventDefault();
                    return false;
            }

            if (button === undefined) {
                return false;
            } else {
                event.preventDefault();
                if (visualizeClick) {
                    button.addClass("active");
                    setTimeout(function () {
                        button.removeClass("active");
                    }, 150);
                }
                button.click();
            }
        };

        self.stripDistanceDecimal = function (distance) {
            return distance.toString().replace(".", "");
        };

        self._switchToMjpgWebcam = function () {
            var webcamImage = $("#webcam_image");
            var currentSrc = webcamImage.attr("src");

            // safari bug doesn't release the mjpeg stream, so we just set it up the once
            if (OctoPrint.coreui.browser.safari && currentSrc != undefined) {
                return;
            }

            var newSrc = self.settings.webcam_streamUrlEscaped();
            if (currentSrc != newSrc) {
                if (self.settings.webcam_cacheBuster()) {
                    if (newSrc.lastIndexOf("?") > -1) {
                        newSrc += "&";
                    } else {
                        newSrc += "?";
                    }
                    newSrc += new Date().getTime();
                }

                self.webcamLoaded(false);
                self.webcamError(false);
                webcamImage.attr("src", newSrc);

                self.webcamHlsEnabled(false);
                self.webcamMjpgEnabled(true);
                self.webcamWebRTCEnabled(false);
            }
        };

        self._switchToHlsWebcam = function () {
            var video = self.webcamElementHls;
            video.onresize = self._updateVideoTagWebcamLayout;

            // Ensure WebRTC is unloaded
            if (self.webRTCPeerConnection != null) {
                self.webRTCPeerConnection.close();
                self.webRTCPeerConnection = null;
            }

            // Check for native playback options: https://developer.mozilla.org/en-US/docs/Web/API/HTMLMediaElement/canPlayType
            if (
                video != null &&
                typeof video.canPlayType != undefined &&
                video.canPlayType("application/vnd.apple.mpegurl") == "probably"
            ) {
                video.src = self.settings.webcam_streamUrlEscaped();
            } else if (Hls.isSupported()) {
                self.hls = new Hls();
                self.hls.loadSource(self.settings.webcam_streamUrlEscaped());
                self.hls.attachMedia(video);
            }

            self.webcamMjpgEnabled(false);
            self.webcamHlsEnabled(true);
            self.webcamWebRTCEnabled(false);
        };

        self._switchToWebRTCWebcam = function () {
            if (!isWebRTCAvailable()) {
                return;
            }
            var video = self.webcamElementWebrtc;
            video.onresize = self._updateVideoTagWebcamLayout;

            // Ensure HLS is unloaded
            if (self.hls != null) {
                self.webcamElementHls.src = null;
                self.hls.destroy();
                self.hls = null;
            }

            // Close any existing, disconnected connection
            if (
                self.webRTCPeerConnection != null &&
                self.webRTCPeerConnection.connectionState != "connected"
            ) {
                self.webRTCPeerConnection.close();
                self.webRTCPeerConnection = null;
            }

            // Open a new connection if necessary
            if (self.webRTCPeerConnection == null) {
                self.webRTCPeerConnection = startWebRTC(
                    video,
                    self.settings.webcam_streamUrlEscaped(),
                    self.settings.webcam_streamWebrtcIceServers()
                );
            }

            self.webcamMjpgEnabled(false);
            self.webcamHlsEnabled(false);
            self.webcamWebRTCEnabled(true);
        };

        self._updateVideoTagWebcamLayout = function () {
            // Get all elements we need
            var player = self._getActiveWebcamVideoElement();
            var rotationContainer = document.querySelector(
                "#webcam_video_container .webcam_rotated"
            );
            var rotationTarget = document.querySelector(
                "#webcam_video_container .webcam_rotated .rotation_target"
            );
            var unrotationContainer = document.querySelector(
                "#webcam_video_container .webcam_unrotated"
            );
            var unrotationTarget = document.querySelector(
                "#webcam_video_container .webcam_unrotated .rotation_target"
            );

            // If we found the rotation container, the view is rotated 90 degrees. This
            // means we need to manually calculate the player dimensions and apply them
            // to the rotation target where height = width and width = height (to
            // accomodate the rotation). The target is centered in the container and
            // rotated around its center, so after we manually resized the container
            // everything will layout nicely.
            if (rotationContainer && player.videoWidth && player.videoHeight) {
                // Calculate the height the video will have in the UI, based on the
                // video width and the aspect ratio.
                var aspectRatio = player.videoWidth / player.videoHeight;
                var height = aspectRatio * rotationContainer.offsetWidth;

                // Enforce the height on the rotation container and the rotation target.
                // Width of the container will be 100%, height will be calculated
                //
                // The size of the rotation target (the element that has the 90 deg
                // transform) is the inverse size of the container (so height -> width
                // and width -> height)
                rotationContainer.style.height = height + "px";
                rotationTarget.style.height = rotationContainer.offsetWidth + "px";
                rotationTarget.style.width = rotationContainer.offsetHeight + "px";

                // Remove the padding we used to give the element an initial height.
                rotationContainer.style.paddingBottom = 0;
            }

            // We are not rotated, clean up all changes we might have done before
            if (unrotationContainer) {
                unrotationContainer.style.height = null;
                unrotationContainer.style.paddingBottom = 0;
                unrotationTarget.style.height = null;
                unrotationTarget.style.width = null;
            }
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: ControlViewModel,
        dependencies: ["loginStateViewModel", "settingsViewModel", "accessViewModel"],
        elements: ["#control", "#control_link"]
    });
});
